
# Evaluador semántico de lógica de primer orden

Universidad del Valle de Guatemala — MM3032 Lógica Matemática  
Equipo 5

## Integrantes

- Andrés Rafael Chivalán Marroquín
- José Roberto Rodríguez Reyes
- Sergio Andreé Álvarez Herrarte

## Descripción

Aplicación de escritorio desarrollada en Python que permite definir un lenguaje de lógica de primer orden, ingresar una interpretación finita y evaluar fórmulas para determinar si son verdaderas o falsas bajo esa interpretación. Además del resultado, muestra una explicación de los pasos decisivos de la evaluación.

El programa admite fórmulas abiertas y cerradas. Cuando existen variables libres, solicita que se les asigne un elemento del dominio antes de evaluar.

## Funcionalidades

- Lenguaje configurable: declaración de funciones, constantes y predicados mediante nombre/aridad.
- Interpretación finita: definición de un dominio no vacío, tablas de funciones y conjuntos de tuplas para las relaciones.
- Conectivos y cuantificadores: ¬, ∧, ∨, →, ↔, ∀ y ∃, además de igualdad entre términos.
- Validación de entradas: revisión de nombres, aridades, elementos del dominio, tuplas, funciones incompletas y asignaciones inválidas.
- Variables libres: detección y selección de valores mediante un entorno.
- Justificación del resultado: explicación con testigos, contraejemplos o comprobaciones completas según corresponda.
- Herramientas adicionales: botones para símbolos lógicos, plantillas de tuplas, alternativas de escritura con teclado, guía de sintaxis y exportación del resultado a .txt.

## Tecnologías

- Python 3: lenguaje de programación.
- Tkinter y ttk: interfaz gráfica.
- re: reconocimiento y validación de texto mediante expresiones regulares.
- itertools: generación de combinaciones de elementos del dominio.

El proyecto utiliza módulos de la biblioteca estándar de Python; no requiere paquetes externos de pip.

## Ejecución

1. Tener Python 3 instalado, con soporte para Tkinter.
2. Abrir una terminal en la carpeta que contiene evaluador_semantico.py.
3. Ejecutar:

   bash
   python evaluador_semantico.py
   

   En Windows también puede utilizarse:

   powershell
   py evaluador_semantico.py
   

4. La aplicación abrirá una ventana con las pestañas 1. Lenguaje, 2. Interpretación y 3. Fórmula y evaluación.

## Ejemplo de uso

### 1. Declarar el lenguaje

En la pestaña Lenguaje ingresar:

Símbolos funcionales:

text
s/1, z/0


Predicados:

text
L/2, E/1


Después, pulsar Aplicar lenguaje.

### 2. Definir la interpretación

En la pestaña Interpretación, ingresar el dominio:

text
0, 1, 2


Completar las subpestañas de la siguiente forma:

Función s/1:

text
0 -> 1
1 -> 2
2 -> 0


Constante z/0:

text
-> 0


Predicado L/2 (interpretado aquí como «menor o igual»):

text
(0,0)
(0,1)
(0,2)
(1,1)
(1,2)
(2,2)


Predicado E/1 (interpretado aquí como «ser par»):

text
0; 2


Los nombres L y E no tienen un significado matemático fijo: el usuario define qué tuplas pertenecen a cada relación.

### 3. Evaluar una fórmula

En la pestaña Fórmula y evaluación, ingresar:

text
∀x ∃y L(x,y)


Pulsar Evaluar. Para la interpretación anterior, el resultado es VERDADERO, porque para cada elemento del dominio existe al menos uno que es mayor o igual a él.

Otros ejemplos:

| Fórmula | Resultado esperado | Explicación breve |
| --- | --- | --- |
| E(z) | Verdadero | z vale 0 y 0 pertenece a E. |
| E(s(z)) | Falso | s(0) vale 1 y 1 no pertenece a E. |
| ∀x L(x,s(x)) | Falso | Para x = 2, s(2) = 0 y (2,0) no está en L. |
| ∃x (E(x) ∧ ¬(x = z)) | Verdadero | El elemento 2 es un testigo. |

Para probar una fórmula abierta, ingresar E(x), pulsar Analizar fórmula y asignar un valor a x en el apartado Entorno.

Nota de sintaxis: en esta versión, los elementos numéricos del dominio no se escriben directamente como términos de una fórmula (E(2) no se admite). Para representarlos se utilizan constantes declaradas, funciones o variables con un entorno; por ejemplo, E(z) o E(s(s(z))).

## Organización del código

El proyecto se encuentra en un único archivo, evaluador_semantico.py, organizado por responsabilidades:

| Componente | Responsabilidad |
| --- | --- |
| tokenize() y Parser | Reconocer y analizar la sintaxis de las fórmulas. |
| parse_symbols() | Leer nombres y aridades de funciones y predicados. |
| parse_domain() | Leer y validar los elementos del dominio. |
| parse_function_table() | Validar y almacenar las tablas de funciones y constantes. |
| parse_pred_table() | Validar y almacenar los conjuntos de tuplas de los predicados. |
| Interp y read_interpretation() | Reunir el dominio y la interpretación de cada símbolo. |
| free_vars() y refresh_env() | Identificar variables libres y mostrar sus asignaciones. |
| eval_term() y eval_formula() | Calcular los valores de los términos y la verdad de las fórmulas. |
| App | Administrar la interfaz gráfica y mostrar los resultados. |

Las funciones se representan mediante diccionarios de entradas y resultados, las constantes como funciones de aridad cero y los predicados mediante conjuntos de tuplas verdaderas. La aplicación valida las entradas antes de evaluar y no asigna un valor de verdad cuando detecta errores.

## Uso de herramientas de inteligencia artificial

Se utilizó ChatGPT (OpenAI) como herramienta de apoyo para consultas puntuales sobre conceptos, sintaxis y estructuras de Python, así como para revisión y análisis del código existente. El apoyo se orientó a aclarar dudas y comprender decisiones de implementación, en el marco del aprendizaje y la revisión del proyecto.

### Referencia de la herramienta

OpenAI. (2026). ChatGPT [Herramienta de inteligencia artificial para consultas conceptuales de Python y revisión de código]. https://chat.openai.com/

## Archivos del proyecto

text
Proyecto-LM-Grupo-5-main/
├── evaluador_semantico.py
└── README.md

