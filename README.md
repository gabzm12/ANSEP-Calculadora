# ANSEP · Calculadora de sistemas eléctricos de potencia

Héctor Gabriel Méndez Melchor · 2226703

Aplicación universitaria de análisis nodal fasorial con **Python, Streamlit, NumPy y Pandas**. La V2 organiza la captura en seis pasos con formularios guiados, identificadores automáticos y borradores persistentes durante la navegación. Conserva el motor de V1: construye Ybus e Ibus, obtiene Zbus cuando existe una inversa numéricamente confiable y resuelve los voltajes con `numpy.linalg.solve`.

## Ejecutar desde VS Code (Windows / PowerShell)

1. Abre esta carpeta en VS Code y selecciona **Python: Select Interpreter → .venv\Scripts\python.exe**.
2. Abre una terminal en la carpeta del proyecto.
3. Ejecuta:

```powershell
.\.venv\Scripts\python.exe -B -m streamlit run app.py
```

Abre la dirección local que indique Streamlit (normalmente `http://localhost:8501`). Detén el servidor con `Ctrl+C`. No es necesario activar el entorno ni cambiar la política de PowerShell.

**El entorno `.venv` existente no fue modificado.** Se utilizó su intérprete con `-B` para evitar escribir bytecode. Versiones comprobadas: Python 3.14, Streamlit 1.66.1, NumPy 2.5.4 y Pandas 3.1.0.

Si necesitas instalar dependencias desde cero, crea un entorno **distinto** para conservar `.venv`:

```powershell
py -m venv .venv_nodal
.\.venv_nodal\Scripts\python.exe -m pip install -r requirements.txt
.\.venv_nodal\Scripts\python.exe -m streamlit run app.py
```

Se requiere Python 3.10 o posterior compatible con las versiones instaladas. `requirements.txt` define rangos admitidos; la verificación de esta entrega corresponde a las versiones indicadas arriba.

## Uso de la V2

Navega desde la barra lateral o con **Anterior / Siguiente**. En pantallas estrechas, abre la barra lateral con la flecha de la esquina superior izquierda.

1. **Configuración:** indica los nodos sin contar tierra y elige p.u. o SI. El nodo 0 es tierra y tiene voltaje cero.
2. **Conexiones:** elige ambos extremos y selecciona Impedancia o Admitancia. Los campos muestran **Resistencia R / Reactancia X** o **Conductancia G / Susceptancia B**, con sus unidades. Pulsa **Agregar conexión**. No registres pares sin conexión.
3. **Fuentes:** elige generadores/motores/voltajes o fuentes de corriente. Completa el formulario con polaridad o sentido, magnitud/ángulo y, si corresponde, impedancia interna. Las ayudas junto a los campos y los ejemplos desplegables explican cada entrada.
4. **Resumen:** consulta todos los elementos y sus valores. Selecciona uno y pulsa **Editar** o **Eliminar**. Los errores de nodos fuera de rango incluyen un botón para abrir directamente el elemento afectado.
5. **Resultados:** consulta voltajes, Ybus, Zbus e Ibus. Las verificaciones aparecen compactas; puedes desplegar los residuos y las corrientes de los elementos, copiar voltajes o descargar resultados.
6. **Procedimiento:** revisa las conversiones, Norton, cada entrada de Ybus, Ibus, la inversa, la solución y KCL. Descarga el desarrollo completo en Markdown o ZIP.

Los identificadores se generan automáticamente (`R1`, `G1`, `M1`, `E1`, `I1`), sin colisionar con IDs importados. Editar conserva el identificador. Las tablas son de consulta: usa el formulario para modificar los datos. Tras eliminar, puedes **Deshacer última eliminación**; esta opción permanece hasta la siguiente modificación del circuito.

**Borradores:** los campos confirmados con Enter o al abandonar el campo se conservan al navegar; no afectan los resultados hasta pulsar **Agregar** o **Guardar cambios**. El aviso de borrador indica dónde hay capturas pendientes. **Cancelar edición / Restablecer formulario** descarta sólo ese borrador. Los formularios Z/Y y polar/rectangular mantienen campos separados: cambiar la forma no convierte ni reinterpreta los valores de la otra forma.

En **Presentación y ayuda** elige dos, cuatro o seis decimales para los resultados; inicialmente se seleccionan cuatro. Las entradas muestran seis decimales; los cálculos mantienen precisión completa. Usa punto decimal, por ejemplo `0.125`. El estilo utiliza los temas claro y oscuro nativos de Streamlit y se adapta al ancho de pantalla.

Cambiar nodos **no borra** elementos; se señalan los terminales fuera de rango y puedes corregirlos uno a uno. Cambiar unidades **no convierte** valores. **Circuitos de referencia** carga los ejemplos de V1. **Abrir / guardar circuito** permite exportar e importar el mismo JSON de V1 desde cualquier paso. Cargar o importar reemplaza el circuito y los borradores; un archivo inválido deja intactos los datos actuales.

El estado permanece en la sesión de Streamlit. **Descarga JSON antes de cerrar o recargar la pestaña**; el archivo contiene el circuito guardado, no borradores pendientes. No hay almacenamiento permanente automático.

### Convenciones y unidades

- `Z = R+jX`, `Y = G+jB`; `X > 0` representa reactancia inductiva, y su susceptancia es negativa.
- Fuentes de corriente `origen → destino`: **−I en origen, +I en destino**. Tierra no tiene ecuación.
- Fuente de voltaje: `E = V(+) − V(−)` en vacío. La corriente desde (+) hacia (−) es `(V+−V−−E)/Zs`. Norton añade `1/Zs` entre esos nodos e inyecta `+E/Zs` en (+), `−E/Zs` en (−).
- La etiqueta **Motor** no cambia signos automáticamente. La polaridad y el ángulo especificados determinan el resultado.
- SI: impedancias en **Ω**, admitancias en **S**, voltajes en **V** y corrientes en **A**, sin prefijos. En un equivalente monofásico, usa voltajes de fase coherentes; no mezcles voltajes de línea y fase.
- p.u.: todos los valores deben tener bases compatibles. El programa no calcula ni convierte bases.
- Una rama ausente se omite. `Z = 0` es un cortocircuito ideal y se rechaza. `Y = 0` es circuito abierto: se conserva explícitamente y se avisa que no establece conectividad.
- Varias filas entre el mismo par de nodos se suman en paralelo. Una impedancia a tierra contribuye sólo a la diagonal.

### Diagnósticos

Se rechazan datos incompletos, NaN/infinito, nodos inválidos, terminales iguales, IDs duplicados, magnitudes polares negativas, Z nula y fuentes ideales de voltaje. Se detectan nodos flotantes y aislados, singularidades por cancelación y mal condicionamiento. Las fuentes de corriente no crean un camino de admitancias a tierra. Varias subredes separadas pueden resolverse si cada una tiene referencia a tierra.

Se impide la solución para rango deficiente o `κ₂(Ybus) ≥ 10¹²`; se advierte desde `κ₂ > 10⁸`. Son umbrales numéricos deliberados, no propiedades físicas universales. Una resistencia/conductancia negativa se acepta como elemento activo lineal y genera una advertencia.

La comprobación final exige error relativo de resolución ≤ `1e-10`, `||Ybus Zbus − Id||∞ ≤ 1e-8` y KCL relativo ≤ `1e-10`. KCL se calcula desde las leyes constitutivas originales, con una escala que contempla cancelaciones en circuitos en vacío. Las fórmulas y valores de los residuos se muestran en el procedimiento. Una verificación aprobada no sustituye la revisión de los datos introducidos.

## Ejercicios del profesor

El PDF se encontró en la **raíz del proyecto**, no en una subcarpeta `ejercicios`. Se revisaron visualmente sus cinco páginas porque son imágenes escaneadas sin texto extraíble útil.

- Páginas 1–2: red de cuatro nodos; transcripción y prueba incluidas.
- Páginas 3–4: red de cinco nodos; transcripción y prueba incluidas.
- Página 5: esquema sin referencia común ni polaridades completas visibles; no se usa como prueba de referencia para evitar asumir datos eléctricos no indicados.
- No se identificaron símbolos o parámetros de acoplamiento magnético en los diagramas revisados. No fue necesario excluir un ejercicio por ese motivo.

Consulta `VALIDACION.md` para datos, correcciones y resultados, y `validation/` para informes completos reproducibles. Los ejemplos se pueden cargar desde la barra lateral.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Las pruebas usan `unittest`, sin dependencias adicionales. Incluyen las 19 pruebas matemáticas y de exportación de V1 sin cambios, pruebas de formularios/navegación/importación con `streamlit.testing.v1.AppTest` y controles de integridad del motor. Las matrices y vectores de los tres ejemplos se contrastan con un archivo NumPy congelado antes del rediseño. Consulta `VALIDACION_V2.md` y `validation/v2-test-results.txt`. El ejecutor de Streamlit necesita sockets locales incluso sin navegador; un entorno aislado que los bloquee debe permitirlos para ejecutar esas pruebas.

Sólo motor y exportaciones, sin sockets:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_power_system.py -v
```

Regenerar circuitos e informes de referencia:

```powershell
.\.venv\Scripts\python.exe -B generate_validation.py
```

## Archivos

| Archivo | Responsabilidad |
|---|---|
| `app.py` | Navegación, formularios, resumen, resultados y procedimiento |
| `ui_model.py` | Borradores y operaciones de captura, edición y eliminación |
| `ui_style.py` | Diseño visual adaptable |
| `.streamlit/config.toml` | Paleta, temas nativos claro/oscuro y controles de presentación |
| `power_system.py` | Modelos, validación, ensamblado y cálculo |
| `reporting.py` | Tablas, LaTeX, informe Markdown y ZIP |
| `examples.py` | Circuitos transcritos del PDF y ejemplo resistivo |
| `tests/` | Pruebas matemáticas y de interfaz |
| `generate_validation.py` | Generación reproducible de informes de referencia |
| `validation/` | Circuitos, informes, diagnósticos y registro de pruebas |
| `backups/app_original.py` | Copia íntegra del código anterior |
| `backups/v1_ui/` | Interfaz V1 y sus pruebas originales antes del rediseño |
| `validation/v1_baseline/` | Resultados y hashes de V1 usados para comprobar V2 |

La actualización V2 no modifica `power_system.py`, `reporting.py`, `examples.py` ni `tests/test_power_system.py`. Se verifica su identidad mediante SHA-256. Las pruebas de interfaz V1 se ejecutaron antes del cambio, se conservaron en el respaldo y se adaptaron al flujo de formularios V2.

## Limitaciones

No implementa ramas magnéticamente acopladas, impedancias mutuas, flujo de potencia Newton–Raphson/Gauss–Seidel, fuentes ideales de voltaje, cortocircuitos ideales, transformadores ideales con relación de transformación ni conversión de bases. Los transformadores del primer ejercicio sólo aportan la reactancia serie ya referida en p.u. La carga debe ser una impedancia/admitancia lineal, no una potencia constante. No se calculan transitorios, armónicos ni frecuencia a partir de L/C: se introduce directamente la reactancia a la frecuencia de estudio.

La exportación del procedimiento es Markdown con fórmulas LaTeX (necesita un visor compatible para renderizarlas); los datos CSV conservan precisión numérica. No se genera PDF desde la interfaz.
