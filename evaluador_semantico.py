"""Evaluador semántico de lógica de primer orden."""

import itertools
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

RESERVED = {"forall", "exists"}
MAX_LINES = 3000
MONO = ("Consolas", 11)

# El AST son tuplas:
#   términos:  ("var", n)  ("fn", n, args)       (una constante es un fn sin args)
#   fórmulas:  ("pred", n, args)  ("eq", t1, t2)  ("not", f)
#              ("bin", op, f1, f2)  ("q", "∀"/"∃", var, f)


class FormulaError(Exception):
    def __init__(self, msg, pos=None):
        super().__init__(msg)
        self.msg = msg
        self.pos = pos


def tokenize(text):
    toks = []
    i, n = 0, len(text)
    id_re = re.compile(r"[^\W\d]\w*")
    multi = [("<->", "IFF"), ("<=>", "IFF"), ("->", "IMP"), ("=>", "IMP"),
             ("/\\", "AND"), ("\\/", "OR")]
    single = {"¬": "NOT", "~": "NOT", "!": "NOT",
              "∧": "AND", "&": "AND", "∨": "OR", "|": "OR",
              "→": "IMP", "↔": "IFF", "∀": "FORALL", "∃": "EXISTS",
              "(": "LP", ")": "RP", ",": "COMMA", "=": "EQ", ".": "DOT"}
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        hit = False
        for s, kind in multi:
            if text.startswith(s, i):
                toks.append((kind, s, i))
                i += len(s)
                hit = True
                break
        if hit:
            continue
        if c in single:
            toks.append((single[c], c, i))
            i += 1
            continue
        m = id_re.match(text, i)
        if not m:
            raise FormulaError(f"Carácter no válido: '{c}'", i)
        word = m.group(0)
        if word.lower() == "forall":
            toks.append(("FORALL", word, i))
        elif word.lower() == "exists":
            toks.append(("EXISTS", word, i))
        else:
            toks.append(("ID", word, i))
        i = m.end()
    return toks


class Parser:
    # De mayor a menor precedencia: ¬ ∀ ∃ > ∧ > ∨ > → > ↔
    # Los cuantificadores y ¬ solo toman la fórmula que les sigue.
    # → asocia a la derecha, lo demás a la izquierda.

    def __init__(self, text, funcs, preds):
        self.text = text
        self.toks = tokenize(text)
        self.i = 0
        self.funcs = funcs
        self.preds = preds

    def peek(self):
        if self.i < len(self.toks):
            return self.toks[self.i]
        return ("EOF", "", len(self.text))

    @staticmethod
    def describe(t):
        return "el final de la fórmula" if t[0] == "EOF" else f"'{t[1]}'"

    def expect(self, kind, desc):
        t = self.peek()
        if t[0] != kind:
            raise FormulaError(f"Se esperaba {desc} pero se encontró {self.describe(t)}", t[2])
        self.i += 1
        return t

    def parse(self):
        if not self.toks:
            raise FormulaError("La fórmula está vacía.", 0)
        f = self.iff()
        t = self.peek()
        if t[0] == "RP":
            raise FormulaError("Paréntesis ')' sin su pareja '('", t[2])
        if t[0] != "EOF":
            raise FormulaError(f"Símbolo inesperado {self.describe(t)}", t[2])
        return f

    def iff(self):
        left = self.imp()
        while self.peek()[0] == "IFF":
            self.i += 1
            left = ("bin", "↔", left, self.imp())
        return left

    def imp(self):
        left = self.or_()
        if self.peek()[0] == "IMP":
            self.i += 1
            return ("bin", "→", left, self.imp())
        return left

    def or_(self):
        left = self.and_()
        while self.peek()[0] == "OR":
            self.i += 1
            left = ("bin", "∨", left, self.and_())
        return left

    def and_(self):
        left = self.unary()
        while self.peek()[0] == "AND":
            self.i += 1
            left = ("bin", "∧", left, self.unary())
        return left

    def unary(self):
        t = self.peek()
        k = t[0]
        if k == "NOT":
            self.i += 1
            return ("not", self.unary())
        if k in ("FORALL", "EXISTS"):
            self.i += 1
            v = self.expect("ID", "el nombre de una variable después del cuantificador")
            name = v[1]
            if name in self.funcs or name in self.preds:
                raise FormulaError(f"'{name}' es un símbolo del lenguaje y no puede usarse como "
                                   f"variable cuantificada", v[2])
            if self.peek()[0] == "DOT":
                self.i += 1
            return ("q", "∀" if k == "FORALL" else "∃", name, self.unary())
        if k == "LP":
            self.i += 1
            f = self.iff()
            nt = self.peek()
            if nt[0] != "RP":
                raise FormulaError(f"Falta ')' para cerrar el paréntesis abierto en la posición "
                                   f"{t[2] + 1}", nt[2])
            self.i += 1
            return f
        if k == "ID":
            return self.atom()
        raise FormulaError("Se esperaba una fórmula (predicado, ¬, cuantificador o paréntesis) "
                           f"pero se encontró {self.describe(t)}", t[2])

    def atom(self):
        t = self.peek()
        name = t[1]
        if name in self.preds:
            self.i += 1
            return ("pred", name, self.args(name, self.preds[name], t))
        t1 = self.term()
        if self.peek()[0] == "EQ":
            self.i += 1
            return ("eq", t1, self.term())
        raise FormulaError(f"'{name}' no es un predicado declarado. Se esperaba un predicado "
                           f"P(...) o una igualdad 't1 = t2'", t[2])

    def args(self, name, ar, tok):
        if ar == 0:
            # las constantes se pueden escribir con o sin paréntesis vacíos
            if self.peek()[0] == "LP":
                self.i += 1
                self.expect("RP", "')'")
            return []
        self.expect("LP", f"'(' después de '{name}' (aridad {ar})")
        args = []
        if self.peek()[0] != "RP":
            args.append(self.term())
            while self.peek()[0] == "COMMA":
                self.i += 1
                args.append(self.term())
        self.expect("RP", f"')' al final de los argumentos de '{name}'")
        if len(args) != ar:
            raise FormulaError(f"'{name}' tiene aridad {ar} pero se usó con {len(args)} "
                               f"argumento(s)", tok[2])
        return args

    def term(self):
        t = self.peek()
        if t[0] != "ID":
            raise FormulaError("Se esperaba un término (variable, constante o f(...)) "
                               f"pero se encontró {self.describe(t)}", t[2])
        self.i += 1
        name = t[1]
        if name in self.funcs:
            return ("fn", name, self.args(name, self.funcs[name], t))
        if name in self.preds:
            raise FormulaError(f"'{name}' es un predicado y no puede usarse como término", t[2])
        if self.peek()[0] == "LP":
            raise FormulaError(f"El símbolo '{name}' no está declarado en el lenguaje "
                               f"(¿falta declararlo o separar el cuantificador?)", t[2])
        return ("var", name)


def fmt_term(t):
    if t[0] == "var" or not t[2]:
        return t[1]
    return f"{t[1]}({', '.join(fmt_term(a) for a in t[2])})"


def fmt(f):
    k = f[0]
    if k == "pred":
        return f"{f[1]}({', '.join(fmt_term(a) for a in f[2])})" if f[2] else f[1]
    if k == "eq":
        return f"{fmt_term(f[1])} = {fmt_term(f[2])}"
    if k == "not":
        s = fmt(f[1])
        return f"¬({s})" if f[1][0] == "eq" else f"¬{s}"
    if k == "bin":
        return f"({fmt(f[2])} {f[1]} {fmt(f[3])})"
    return f"{f[1]}{f[2]} {fmt(f[3])}"


def fmt_top(f):
    # igual que fmt pero sin los paréntesis de afuera
    s = fmt(f)
    return s[1:-1] if f[0] == "bin" else s


def term_vars(t):
    if t[0] == "var":
        return {t[1]}
    out = set()
    for a in t[2]:
        out |= term_vars(a)
    return out


def free_vars(f):
    k = f[0]
    if k == "pred":
        out = set()
        for a in f[2]:
            out |= term_vars(a)
        return out
    if k == "eq":
        return term_vars(f[1]) | term_vars(f[2])
    if k == "not":
        return free_vars(f[1])
    if k == "bin":
        return free_vars(f[2]) | free_vars(f[3])
    return free_vars(f[3]) - {f[2]}


# interpretación y validación de lo que escribe el usuario 

ELEM_RE = re.compile(r"^[\w.'+*#-]+$")


class Interp:
    def __init__(self, domain):
        self.domain = domain
        self.funcs = {}   # nombre -> {tupla: valor}
        self.preds = {}   # nombre -> conjunto de tuplas


def parse_symbols(text, kind):
    res, errs = {}, []
    for it in [s.strip() for s in re.split(r"[,;]", text) if s.strip()]:
        m = re.fullmatch(r"([^\W\d]\w*)\s*/\s*(\d+)", it)
        if not m:
            errs.append(f"Símbolo {kind} inválido: '{it}'. Usa el formato nombre/aridad (ej. f/2).")
            continue
        name, ar = m.group(1), int(m.group(2))
        if name.lower() in RESERVED:
            errs.append(f"'{name}' es una palabra reservada.")
        elif name in res:
            errs.append(f"El símbolo {kind} '{name}' está repetido.")
        elif kind == "predicado" and ar < 1:
            errs.append(f"El predicado '{name}' debe tener aridad al menos 1.")
        else:
            res[name] = ar
    return res, errs


def parse_domain(text):
    errs = []
    t = text.strip()
    if t.startswith("{") and t.endswith("}"):
        t = t[1:-1]
    if not t.strip():
        return [], ["El dominio no puede ser vacío."]
    domain = []
    for it in [s.strip() for s in re.split(r"[,;\n]", t)]:
        if not it:
            errs.append("Hay un elemento vacío en el dominio (revisa comas repetidas o sobrantes).")
        elif not ELEM_RE.match(it) or "->" in it:
            errs.append(f"Elemento inválido en el dominio: '{it}' (usa letras, dígitos o _, sin espacios).")
        elif it in domain:
            errs.append(f"El elemento '{it}' está repetido en el dominio.")
        else:
            domain.append(it)
    return domain, errs


def parse_function_table(name, ar, text, domain):
    errs, table = [], {}
    dset = set(domain)
    line_errors = False
    for no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.replace("→", "->").replace("↦", "->")
        if "->" in line:
            left, right = line.split("->", 1)
        elif ar == 0:
            left, right = "", line
        else:
            errs.append(f"Línea {no}: falta '->' en «{raw.strip()}».")
            line_errors = True
            continue
        left, right = left.strip(), right.strip()
        if left.startswith("(") and left.endswith(")"):
            left = left[1:-1]
        args = tuple(s.strip() for s in left.split(",")) if left else ()
        if len(args) != ar:
            errs.append(f"Línea {no}: {name} tiene aridad {ar} pero la tupla ({', '.join(args)}) "
                        f"tiene {len(args)} componente(s).")
            line_errors = True
            continue
        bad = [a for a in args if a not in dset]
        if bad:
            errs.append(f"Línea {no}: elemento(s) fuera del dominio en la tupla: {', '.join(bad)}.")
            line_errors = True
            continue
        if right not in dset:
            errs.append(f"Línea {no}: el valor '{right}' no pertenece al dominio "
                        f"(¿quedó un '?' sin completar?).")
            line_errors = True
            continue
        if args in table and table[args] != right:
            errs.append(f"Línea {no}: la tupla ({', '.join(args)}) tiene dos valores distintos "
                        f"({table[args]} y {right}); una función asigna un único valor.")
            line_errors = True
            continue
        table[args] = right
    # lo de abajo solo tiene sentido si las líneas estaban bien escritas
    if not line_errors:
        if not table:
            errs.append("La función no puede estar vacía.")
        elif len(domain) ** ar <= 100000:
            missing = [t for t in itertools.product(domain, repeat=ar) if t not in table]
            if missing:
                ej = "; ".join("(" + ", ".join(t) + ")" for t in missing[:6])
                errs.append(f"Faltan {len(missing)} tupla(s) de D^{ar} (una función debe estar "
                            f"definida en todo el dominio). Ejemplos: {ej}")
    return table, errs


def parse_pred_table(name, ar, text, domain):
    errs, rel = [], set()
    dset = set(domain)
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    body = "\n".join(lines).strip()
    if not body:
        return rel, ["La relación no puede ser vacía."]
    if "(" in body or ")" in body:
        items = re.findall(r"\(([^()]*)\)", body)
        leftover = re.sub(r"\([^()]*\)", "", body)
        if re.sub(r"[\s,;]", "", leftover):
            errs.append(f"Texto no válido fuera de las tuplas: «{leftover.strip()}» "
                        f"(revisa los paréntesis).")
            return rel, errs
    elif ar == 1:
        items = re.split(r"[,;\n]", body)
    else:
        items = re.split(r"[;\n]", body)
    con_parentesis = "(" in body
    for it in items:
        it = it.strip()
        if not it and not con_parentesis:
            continue   # sobrante tipo "a; b;"
        args = tuple(s.strip() for s in it.split(","))
        if len(args) != ar:
            errs.append(f"La tupla ({it}) tiene {len(args)} componente(s) pero {name} tiene aridad {ar}.")
            continue
        bad = [a for a in args if a not in dset]
        if bad:
            errs.append(f"La tupla ({it}) tiene elemento(s) fuera del dominio: "
                        f"{', '.join(b if b else '(vacío)' for b in bad)}.")
            continue
        rel.add(args)
    if not rel and not errs:
        errs.append("La relación no puede ser vacía.")
    return rel, errs


# semántica 

class Node:
    def __init__(self, text, value, info, children=None, label=None):
        self.text = text
        self.value = value
        self.info = info
        self.children = children or []
        self.label = label


def eval_term(t, env, I):
    if t[0] == "var":
        return env[t[1]]
    args = tuple(eval_term(a, env, I) for a in t[2])
    return I.funcs[t[1]][args]


def vf(b):
    return "Verdadero" if b else "Falso"


def eval_formula(f, env, I):
    k = f[0]
    text = fmt_top(f)

    if k == "pred":
        vals = [eval_term(a, env, I) for a in f[2]]
        val = tuple(vals) in I.preds[f[1]]
        info = []
        det = [f"{fmt_term(a)} = {v}" for a, v in zip(f[2], vals)
               if not (a[0] == "fn" and not a[2])]
        if det:
            info.append("Valores: " + ", ".join(det) + ".")
        info.append(f"({', '.join(vals)}) {'∈' if val else '∉'} {f[1]}^I.")
        return Node(text, val, info)

    if k == "eq":
        v1, v2 = eval_term(f[1], env, I), eval_term(f[2], env, I)
        info = [f"{fmt_term(f[1])} = {v1} y {fmt_term(f[2])} = {v2}, "
                f"luego {v1} {'=' if v1 == v2 else '≠'} {v2}."]
        return Node(text, v1 == v2, info)

    if k == "not":
        c = eval_formula(f[1], env, I)
        info = [f"«{c.text}» es {vf(c.value)}, así que su negación es {vf(not c.value)}."]
        return Node(text, not c.value, info, [c])

    if k == "bin":
        op = f[1]
        l = eval_formula(f[2], env, I)
        # ∧, ∨ y → no miran el lado derecho si el izquierdo ya decide
        if op == "∧":
            if not l.value:
                return Node(text, False, [f"El primer conjunto «{l.text}» es falso; basta para "
                                          f"que la conjunción sea falsa."], [l])
            r = eval_formula(f[3], env, I)
            info = ["Ambos conjuntos son verdaderos."] if r.value else \
                   [f"«{l.text}» es verdadero pero «{r.text}» es falso."]
            return Node(text, r.value, info, [l, r])
        if op == "∨":
            if l.value:
                return Node(text, True, [f"El primer disyunto «{l.text}» es verdadero; basta para "
                                         f"que la disyunción sea verdadera."], [l])
            r = eval_formula(f[3], env, I)
            info = [f"«{l.text}» es falso y «{r.text}» es verdadero."] if r.value else \
                   ["Ambos disyuntos son falsos."]
            return Node(text, r.value, info, [l, r])
        if op == "→":
            if not l.value:
                return Node(text, True, [f"El antecedente «{l.text}» es falso, por lo que la "
                                         f"implicación es verdadera."], [l])
            r = eval_formula(f[3], env, I)
            info = ["Antecedente y consecuente son verdaderos."] if r.value else \
                   ["El antecedente es verdadero y el consecuente es falso, "
                    "por lo que la implicación es falsa."]
            return Node(text, r.value, info, [l, r])
        r = eval_formula(f[3], env, I)
        same = l.value == r.value
        info = [f"Ambos lados son {vf(l.value)}." if same else
                f"Los lados difieren: «{l.text}» es {vf(l.value)} y «{r.text}» es {vf(r.value)}."]
        return Node(text, same, info, [l, r])

    # cuantificadores: se recorre D y se corta apenas aparece testigo o contraejemplo
    q, var, body = f[1], f[2], f[3]
    btxt = fmt_top(body)
    dom = "{" + ", ".join(I.domain) + "}"
    children, tested = [], []
    result, witness = (q == "∀"), None
    for d in I.domain:
        env2 = dict(env)
        env2[var] = d
        c = eval_formula(body, env2, I)
        c.label = f"{var} = {d}"
        children.append(c)
        tested.append(d)
        if q == "∀" and not c.value:
            result, witness = False, d
            break
        if q == "∃" and c.value:
            result, witness = True, d
            break
    n = len(I.domain)
    if q == "∀" and not result:
        info = [f"Contraejemplo: {var} = {witness} no satisface «{btxt}».",
                f"Basta con este elemento para que ∀ sea falso (se revisó: {', '.join(tested)})."]
    elif q == "∀":
        info = [f"Comprobación completa: los {n} elementos de D = {dom} satisfacen «{btxt}»."]
    elif result:
        info = [f"Testigo: {var} = {witness} satisface «{btxt}».",
                f"Basta con este elemento para que ∃ sea verdadero (se revisó: {', '.join(tested)})."]
    else:
        info = [f"Comprobación completa: ninguno de los {n} elementos de D = {dom} satisface «{btxt}»."]
    return Node(text, result, info, children)


def render(node, depth, out):
    if len(out) > MAX_LINES:
        return
    pad = "    " * depth
    lab = f"[{node.label}]  " if node.label else ""
    out.append(f"{pad}{lab}{node.text}   ⇒ {vf(node.value)}")
    for line in node.info:
        out.append(f"{pad}      ↳ {line}")
    for ch in node.children:
        render(ch, depth + 1, out)


HELP_TEXT = (
    "SINTAXIS DE FÓRMULAS\n\n"
    "Conectivos: ¬  ∧  ∨  →  ↔      Cuantificadores: ∀x  ∃x      Igualdad: t1 = t2\n"
    "Con el teclado también sirven: ~  &  |  ->  <->  forall  exists\n\n"
    "Precedencia (mayor a menor): ¬ ∀ ∃  >  ∧  >  ∨  >  →  >  ↔\n"
    "• ¬, ∀ y ∃ afectan solo a la fórmula que les sigue justo después:\n"
    "  ∀x P(x) → Q(x)  se lee  (∀x P(x)) → Q(x). Usa paréntesis para abarcar más.\n"
    "• → asocia a la derecha.\n"
    "• Deja un espacio entre el cuantificador y lo que sigue:  ∀x P(x)  (o  ∀x. P(x)).\n\n"
    "Los símbolos declarados en la pestaña Lenguaje son funciones, constantes o predicados;\n"
    "cualquier otro identificador se toma como variable.\n"
    "Si la fórmula tiene variables libres aparece el panel Entorno para asignarlas."
)


# interfaz

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Evaluador semántico — MM3032 Lógica Matemática")
        self.geometry("1040x780")
        self.minsize(900, 650)
        self.symbol_texts = {}   # (tipo, nombre, aridad) -> Text
        self.built_sig = None    # firma del lenguaje con el que se armaron las pestañas
        self.env_vars = {}
        bar = tk.Menu(self)
        hp = tk.Menu(bar, tearoff=0)
        hp.add_command(label="Guía de sintaxis",
                       command=lambda: messagebox.showinfo("Guía de sintaxis", HELP_TEXT))
        bar.add_cascade(label="Ayuda", menu=hp)
        self.config(menu=bar)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)
        self._tab_language()
        self._tab_interp()
        self._tab_formula()
        self.rebuild_symbol_tabs(silent=True)

    # pestaña 1 
    def _tab_language(self):
        f = ttk.Frame(self.nb, padding=14)
        self.nb.add(f, text="1. Lenguaje")
        ttk.Label(f, text="Declara los símbolos como nombre/aridad, separados por comas.",
                  font=("Segoe UI", 11, "bold")).pack(anchor="w")
        b1 = ttk.LabelFrame(f, text="Símbolos funcionales", padding=8)
        b1.pack(fill="x", pady=8)
        self.func_var = tk.StringVar()
        ttk.Entry(b1, textvariable=self.func_var, font=MONO).pack(fill="x")
        ttk.Label(b1, text="Formato: s/1, suma/2, c/0      (aridad 0 = constante)",
                  foreground="#555").pack(anchor="w")
        b2 = ttk.LabelFrame(f, text="Predicados", padding=8)
        b2.pack(fill="x", pady=8)
        self.pred_var = tk.StringVar()
        ttk.Entry(b2, textvariable=self.pred_var, font=MONO).pack(fill="x")
        ttk.Label(b2, text="Formato: P/1, R/2      (aridad mínima 1)", foreground="#555").pack(anchor="w")
        ttk.Button(f, text="Aplicar lenguaje", command=self.apply_language).pack(anchor="w", pady=6)
        self.lang_status = tk.Label(f, text="", justify="left", wraplength=900, anchor="w")
        self.lang_status.pack(fill="x")

    def read_language(self):
        funcs, e1 = parse_symbols(self.func_var.get(), "funcional")
        preds, e2 = parse_symbols(self.pred_var.get(), "predicado")
        errs = e1 + e2
        for n in set(funcs) & set(preds):
            errs.append(f"El nombre '{n}' está declarado como función y como predicado.")
        return funcs, preds, errs

    def apply_language(self):
        funcs, preds, errs = self.read_language()
        if errs:
            self.lang_status.config(text="Errores:\n• " + "\n• ".join(errs), fg="#b00020")
            return
        self.rebuild_symbol_tabs(silent=True)
        fs = ", ".join(f"{n}/{a}" for n, a in funcs.items()) or "(ninguno)"
        ps = ", ".join(f"{n}/{a}" for n, a in preds.items()) or "(ninguno)"
        self.lang_status.config(text=f"Lenguaje válido.\nFunciones: {fs}\nPredicados: {ps}\n"
                                     f"Sigue con la pestaña «2. Interpretación».", fg="#117a33")

    # pestaña 2
    def _tab_interp(self):
        f = ttk.Frame(self.nb, padding=14)
        self.nb.add(f, text="2. Interpretación")
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text="Dominio D:", font=("Segoe UI", 11, "bold")).pack(side="left")
        self.domain_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.domain_var, font=MONO).pack(side="left", fill="x",
                                                                    expand=True, padx=6)
        ttk.Button(top, text="Actualizar tablas de símbolos",
                   command=self.rebuild_symbol_tabs).pack(side="left")
        ttk.Label(f, text="Elementos separados por coma, sin repetir y al menos uno (formato: a, b, c).",
                  foreground="#555").pack(anchor="w", pady=(2, 8))
        self.sym_nb = ttk.Notebook(f)
        self.sym_nb.pack(fill="both", expand=True)

    def rebuild_symbol_tabs(self, silent=False):
        funcs, preds, errs = self.read_language()
        if errs:
            if not silent:
                messagebox.showerror("Lenguaje inválido", "\n".join(errs))
            return
        # guardo lo que ya estaba escrito para no perderlo al reconstruir
        old = {k: w.get("1.0", "end-1c") for k, w in self.symbol_texts.items()}
        for t in self.sym_nb.tabs():
            w = self.nametowidget(t)
            self.sym_nb.forget(t)
            w.destroy()
        self.symbol_texts = {}
        for name, ar in funcs.items():
            self._sym_tab("f", name, ar, old)
        for name, ar in preds.items():
            self._sym_tab("p", name, ar, old)
        self.built_sig = (tuple(funcs.items()), tuple(preds.items()))

    def _sym_tab(self, kind, name, ar, old):
        fr = ttk.Frame(self.sym_nb, padding=8)
        self.sym_nb.add(fr, text=f"{name}/{ar}")
        if kind == "f":
            hint = (f"Función {name} de aridad {ar}. Una línea por tupla de D^{ar}:  «a, b -> c»  "
                    f"significa  {name}^I(a, b) = c.\nConstante: «-> c».  Debe quedar definida en "
                    f"TODAS las tuplas del dominio. Las líneas que empiezan con # se ignoran.")
        else:
            hint = (f"Predicado {name} de aridad {ar}. Escribe las tuplas que pertenecen a "
                    f"{name}^I, separadas por «;» o por líneas, por ejemplo (a,b); (b,c).\n"
                    f"{'Si es unario basta con: a; b.  ' if ar == 1 else ''}"
                    f"La relación no puede ser vacía.")
        ttk.Label(fr, text=hint, wraplength=900, foreground="#333", justify="left").pack(anchor="w")
        ttk.Button(fr, text="Generar plantilla con todas las tuplas",
                   command=lambda: self.template(kind, name, ar)).pack(anchor="w", pady=6)
        box = ttk.Frame(fr)
        box.pack(fill="both", expand=True)
        txt = tk.Text(box, height=10, font=MONO, undo=True)
        sb = ttk.Scrollbar(box, command=txt.yview)
        txt.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        txt.insert("1.0", old.get((kind, name, ar), ""))
        self.symbol_texts[(kind, name, ar)] = txt

    def template(self, kind, name, ar):
        domain, errs = parse_domain(self.domain_var.get())
        if errs:
            messagebox.showerror("Dominio inválido", "Corrige el dominio primero:\n" + "\n".join(errs))
            return
        if len(domain) ** ar > 2000:
            messagebox.showwarning("Demasiadas tuplas",
                                   f"D^{ar} tiene {len(domain) ** ar} tuplas; mejor escríbelas a mano.")
            return
        txt = self.symbol_texts[(kind, name, ar)]
        if txt.get("1.0", "end-1c").strip() and not messagebox.askyesno(
                "Reemplazar", "El cuadro ya tiene contenido. ¿Lo reemplazo por la plantilla?"):
            return
        tuples = list(itertools.product(domain, repeat=ar))
        if kind == "f":
            lines = [f"{', '.join(t)} -> ?" if ar else "-> ?" for t in tuples]
        else:
            lines = ["(" + ", ".join(t) + ")" for t in tuples]
            lines.insert(0, "# Borra las tuplas que NO pertenecen a la relación")
        txt.delete("1.0", "end")
        txt.insert("1.0", "\n".join(lines))

    def read_interpretation(self, funcs, preds, domain):
        sig = (tuple(funcs.items()), tuple(preds.items()))
        if sig != self.built_sig:
            return None, ["El lenguaje cambió desde la última vez. Presiona «Actualizar tablas de "
                          "símbolos» en la pestaña 2."]
        I = Interp(domain)
        errs = []
        for name, ar in funcs.items():
            tbl, e = parse_function_table(name, ar, self.symbol_texts[("f", name, ar)].get("1.0", "end-1c"), domain)
            errs += [f"Función {name}/{ar}: {m}" for m in e]
            I.funcs[name] = tbl
        for name, ar in preds.items():
            rel, e = parse_pred_table(name, ar, self.symbol_texts[("p", name, ar)].get("1.0", "end-1c"), domain)
            errs += [f"Predicado {name}/{ar}: {m}" for m in e]
            I.preds[name] = rel
        return (None if errs else I), errs

    # pestaña 3 
    def _tab_formula(self):
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="3. Fórmula y evaluación")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text="Fórmula:", font=("Segoe UI", 11, "bold")).pack(side="left")
        self.formula_var = tk.StringVar()
        self.formula_entry = ttk.Entry(row, textvariable=self.formula_var, font=("Segoe UI Symbol", 14))
        self.formula_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.formula_entry.bind("<Return>", lambda e: self.on_evaluate())

        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=4)
        for s in ["¬", "∧", "∨", "→", "↔", "∀", "∃", "(", ")", ",", "="]:
            ttk.Button(bar, text=s, width=3, command=lambda s=s: self.ins(s)).pack(side="left", padx=2)
        ttk.Button(bar, text="⌫", width=3, command=self.backspace).pack(side="left", padx=(8, 2))
        ttk.Button(bar, text="Limpiar", command=lambda: self.formula_var.set("")).pack(side="left", padx=2)

        act = ttk.Frame(f)
        act.pack(fill="x", pady=4)
        ttk.Button(act, text="Analizar fórmula", command=self.on_analyze).pack(side="left")
        ttk.Button(act, text="Evaluar", command=self.on_evaluate).pack(side="left", padx=6)
        ttk.Button(act, text="Exportar resultado…", command=self.export_result).pack(side="left")

        self.env_frame = ttk.LabelFrame(f, text="Entorno (valores para las variables libres)", padding=8)
        self.env_frame.pack(fill="x", pady=6)
        ttk.Label(self.env_frame, text="Presiona «Analizar fórmula» para detectar las variables libres.").pack(anchor="w")

        box = ttk.Frame(f)
        box.pack(fill="both", expand=True)
        self.out = tk.Text(box, font=MONO, wrap="word", height=14)
        sb = ttk.Scrollbar(box, command=self.out.yview)
        self.out.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.out.pack(side="left", fill="both", expand=True)
        self.out.tag_configure("ok", foreground="#117a33", font=("Segoe UI", 22, "bold"))
        self.out.tag_configure("bad", foreground="#b00020", font=("Segoe UI", 22, "bold"))
        self.out.tag_configure("err", foreground="#b00020")
        self.out.tag_configure("h", font=("Segoe UI", 11, "bold"))
        self.out.insert("1.0", "Declara el lenguaje, llena la interpretación y escribe una fórmula.\n"
                               "En Ayuda → Guía de sintaxis están las reglas de escritura.")

    def ins(self, s):
        e = self.formula_entry
        e.focus_set()
        e.insert(e.index(tk.INSERT), s)

    def backspace(self):
        e = self.formula_entry
        e.focus_set()
        i = e.index(tk.INSERT)
        if i > 0:
            e.delete(i - 1)

    def refresh_env(self, free, domain):
        for w in self.env_frame.winfo_children():
            w.destroy()
        old = self.env_vars
        self.env_vars = {}
        if not free:
            ttk.Label(self.env_frame, text="La fórmula es cerrada: no necesita entorno.").pack(anchor="w")
            return
        ttk.Label(self.env_frame, text="Elige un elemento de D para cada variable libre:").pack(side="left", padx=(0, 10))
        for v in free:
            var = old.get(v, tk.StringVar())   # si ya había un valor para v lo conservo
            self.env_vars[v] = var
            ttk.Label(self.env_frame, text=f"{v} =").pack(side="left")
            ttk.Combobox(self.env_frame, textvariable=var, values=domain, width=8).pack(side="left", padx=(2, 12))

    # validación y evaluación 
    def gather(self):
        errors = []
        funcs, preds, e = self.read_language()
        errors += [("Lenguaje", m) for m in e]
        domain, e = parse_domain(self.domain_var.get())
        errors += [("Dominio", m) for m in e]
        dom_ok = not e
        interp = None
        if not errors:
            interp, e = self.read_interpretation(funcs, preds, domain)
            errors += [("Interpretación", m) for m in e]
        ast, free = None, []
        text = self.formula_var.get()
        if not any(s == "Lenguaje" for s, _ in errors):
            try:
                ast = Parser(text, funcs, preds).parse()
                free = sorted(free_vars(ast))
            except FormulaError as ex:
                msg = ex.msg
                if ex.pos is not None:
                    msg += f" (posición {ex.pos + 1})\n    {text}\n    {' ' * ex.pos}^"
                errors.append(("Fórmula", msg))
        else:
            errors.append(("Fórmula", "No se puede validar hasta corregir el lenguaje."))
        return dict(errors=errors, domain=domain if dom_ok else [], interp=interp, ast=ast, free=free)

    def _reset_out(self):
        self.out.delete("1.0", "end")

    def _esc(self, text, tag=None):
        self.out.insert("end", text, tag)

    def show_errors(self, errors):
        self._reset_out()
        self._esc("SIN VALOR DE VERDAD\n", "bad")
        self._esc("La entrada tiene errores; mientras no se corrijan no se asigna Verdadero ni Falso.\n\n", "h")
        for sec, msg in errors:
            self._esc(f"• [{sec}] {msg}\n", "err")

    def on_analyze(self):
        ctx = self.gather()
        if ctx["ast"] is not None:
            self.refresh_env(ctx["free"], ctx["domain"])
        if ctx["errors"]:
            self.show_errors(ctx["errors"])
            return
        self._reset_out()
        self._esc("Fórmula analizada correctamente.\n", "h")
        self._esc(f"Con paréntesis completos: {fmt_top(ctx['ast'])}\n")
        if ctx["free"]:
            self._esc(f"Variables libres: {', '.join(ctx['free'])}\n")
            self._esc("Asigna un valor de D a cada una en el panel Entorno y presiona «Evaluar».\n")
        else:
            self._esc("La fórmula es cerrada (sin variables libres).\n")

    def on_evaluate(self):
        ctx = self.gather()
        errors = list(ctx["errors"])
        env = {}
        if ctx["ast"] is not None:
            self.refresh_env(ctx["free"], ctx["domain"])
            for v in ctx["free"]:
                val = self.env_vars[v].get().strip()
                if not val:
                    errors.append(("Entorno", f"Falta asignar la variable libre '{v}'."))
                elif ctx["domain"] and val not in ctx["domain"]:
                    errors.append(("Entorno", f"La asignación {v} = '{val}' no es un elemento del dominio D."))
                else:
                    env[v] = val
        if errors:
            self.show_errors(errors)
            return
        ast, I = ctx["ast"], ctx["interp"]
        node = eval_formula(ast, env, I)
        self._reset_out()
        self._esc(vf(node.value).upper() + "\n", "ok" if node.value else "bad")
        self._esc(f"Fórmula: {fmt_top(ast)}\n")
        self._esc("Dominio: D = {" + ", ".join(I.domain) + "}\n")
        if env:
            self._esc("Entorno: " + ", ".join(f"{v} = {env[v]}" for v in ctx["free"]) + "\n")
        self._esc("\nRazón decisiva: ", "h")
        self._esc(" ".join(node.info) + "\n")
        self._esc("\nJustificación detallada:\n", "h")
        lines = []
        render(node, 0, lines)
        self._esc("\n".join(lines[:MAX_LINES]) + "\n")
        if len(lines) > MAX_LINES:
            self._esc(f"... (justificación cortada a {MAX_LINES} líneas)\n", "err")

    def export_result(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Texto", "*.txt")],
                                            title="Guardar resultado")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.out.get("1.0", "end-1c"))


if __name__ == "__main__":
    App().mainloop()
