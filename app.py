"""ANSEP V2: captura guiada; el motor y las exportaciones siguen siendo los de V1."""
from copy import deepcopy
from dataclasses import asdict
import json

import pandas as pd
import streamlit as st

from examples import EXAMPLES
from power_system import (Network, ValidationError, network_from_json, network_json,
                          polar_text, rectangular, solve)
from reporting import (cell_equation, check_text, export_zip, injection_equation,
                       matrix_frame, matrix_latex, report_markdown, vector_frame)
from ui_model import (GROUPS, delete_element, input_issues, item_draft, new_draft, save_element)
from ui_style import CSS

st.set_page_config(page_title="ANSEP · Sistemas de potencia", page_icon="⚡", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

STEPS = ["Configuración", "Conexiones", "Fuentes", "Resumen", "Resultados", "Procedimiento"]
# Etiquetas de presentación: conservar las claves y los circuitos de referencia de V1.
EXAMPLE_LABELS = {"PDF · página 1 · 4 nodos": "Ejemplo 4 nodos",
                  "PDF · página 3 · 5 nodos": "Ejemplo 5 nodos"}
DESCRIPTIONS = ["Define los nodos y las unidades de tu circuito.",
                "Registra únicamente las conexiones que existen en tu red.",
                "Introduce los datos de las fuentes; la aplicación hace las conversiones.",
                "Revisa los elementos y su conexión antes de consultar los resultados.",
                "Consulta los voltajes, las matrices y la comprobación del circuito.",
                "Sigue el desarrollo matemático desde los datos hasta la solución."]


def reset_draft(group):
    st.session_state.drafts[group] = new_draft(group, st.session_state.network.nodes)
    st.session_state.editing[group] = None
    st.session_state.dirty[group] = False
    st.session_state.pop("form_error_" + group, None)


def replace_network(net, title):
    st.session_state.network = deepcopy(net)
    st.session_state.drafts = {}
    st.session_state.editing = {}
    st.session_state.dirty = {}
    for group in GROUPS:
        reset_draft(group)
    st.session_state.undo = None
    st.session_state.circuit_title = title
    st.session_state.flash = f"{title}: circuito cargado."
    st.session_state.pop("import_error", None)


if "network" not in st.session_state:
    # Recuperar también las ediciones de la sesión anterior si sigue abierta en V1.
    previous = deepcopy(st.session_state.get("base_network", Network()))
    revision = st.session_state.get("editor_revision", 0)
    legacy_raw = {}
    for group, cls in GROUPS.items():
        changes = st.session_state.get(f"{group}_{revision}", {})
        if changes:
            rows = [asdict(item) for item in getattr(previous, group)]
            for index, values in changes.get("edited_rows", {}).items():
                if int(index) < len(rows):
                    rows[int(index)].update(values)
            rows = [r for i,r in enumerate(rows) if i not in changes.get("deleted_rows", [])]
            rows.extend(changes.get("added_rows", []))
            legacy_raw[group] = rows
            try:
                setattr(previous, group, [cls(**row) for row in rows])
            except TypeError:
                pass
    try:
        previous = network_from_json(network_json(previous))
    except (ValidationError, TypeError):
        previous = deepcopy(st.session_state.get("base_network", Network()))
    if legacy_raw:
        st.session_state.legacy_raw = legacy_raw
    replace_network(previous, "Mi circuito")
    st.session_state.pop("flash", None)
    st.session_state.navigation = 0
    st.session_state.source_view = "voltages"
    st.session_state.source_choice = "voltages"
    st.session_state.digits = 4


def go(step):
    st.session_state.navigation = step


def config_changed():
    net = st.session_state.network
    net.nodes = int(st.session_state.node_count)
    net.units = st.session_state.unit_mode
    st.session_state.undo = None


def load_example():
    title = st.session_state.example
    replace_network(EXAMPLES[title](), EXAMPLE_LABELS.get(title, title))
    go(0 if title == "Circuito vacío" else 3)


def import_file():
    uploaded = st.session_state.get("circuit_upload")
    if uploaded is None:
        return
    try:
        if uploaded.size > 2_000_000:
            raise ValidationError("El archivo excede el límite de 2 MB.")
        net = network_from_json(uploaded.getvalue().decode("utf-8-sig"))
        replace_network(net, uploaded.name)
        go(3)
    except (ValidationError, UnicodeError) as exc:
        st.session_state.import_error = str(exc)


def record_field(group, field, widget_key):
    st.session_state.drafts[group][field] = st.session_state[widget_key]
    st.session_state.dirty[group] = True
    st.session_state.pop("form_error_" + group, None)


def draft_widget(group, field, label, kind="number", **kwargs):
    key = f"{group}_{field}"
    # Los borradores tienen vida independiente de los widgets que Streamlit limpia al navegar.
    value = st.session_state.drafts[group][field]
    st.session_state[key] = value
    callback = dict(key=key, on_change=record_field, args=(group, field, key))
    if kind == "select":
        return st.selectbox(label, **callback, **kwargs)
    return st.number_input(label, **callback, format="%.6f", **kwargs)


def node_field(group, field, label, help_text):
    selected = int(st.session_state.drafts[group][field])
    nodes = st.session_state.network.nodes
    options = list(range(nodes + 1))
    if selected not in options:
        options.append(selected)
    def display(node):
        if node == 0:
            return "0 · Tierra / referencia"
        return f"Nodo {node}" + (" · fuera de la configuración" if node > nodes else "")
    return draft_widget(group, field, label, "select", options=options, format_func=display, help=help_text)


def save_form(group):
    try:
        updated, name = save_element(st.session_state.network, group, st.session_state.drafts[group], st.session_state.editing[group])
        editing = st.session_state.editing[group]
        st.session_state.network = updated
        st.session_state.undo = None
        reset_draft(group)
        st.session_state.flash = f"{name}: {'cambios guardados' if editing else 'elemento agregado'}."
    except (ValidationError, ValueError, TypeError) as exc:
        st.session_state["form_error_" + group] = str(exc)


def begin_edit(group, name):
    item = next(x for x in getattr(st.session_state.network, group) if x.name == name)
    st.session_state.drafts[group] = item_draft(group, item, st.session_state.network.nodes)
    st.session_state.editing[group] = name
    st.session_state.dirty[group] = False
    st.session_state.pop("form_error_" + group, None)
    if group != "branches":
        st.session_state.source_view = group
        st.session_state.source_choice = group
    go(1 if group == "branches" else 2)


def delete_saved(group, name):
    st.session_state.undo = deepcopy(st.session_state.network)
    st.session_state.network = delete_element(st.session_state.network, group, name)
    if st.session_state.editing[group] == name:
        reset_draft(group)
    st.session_state.flash = f"{name} eliminado. Puedes deshacerlo desde la barra lateral."


def undo_delete():
    if st.session_state.undo is not None:
        st.session_state.network = st.session_state.undo
        st.session_state.undo = None
        st.session_state.flash = "Eliminación deshecha."


def source_changed():
    st.session_state.source_choice = st.session_state.source_view


def units():
    return ("p.u.",)*4 if st.session_state.network.units == "p.u." else ("S", "Ω", "V", "A")


def table_rows(group):
    net = st.session_state.network
    yu, zu, vu, iu = units()
    digits = st.session_state.digits
    rows = []
    for item in getattr(net, group):
        if group == "branches":
            row = {"ID":item.name, "Conexión":f"{item.a} ↔ {item.b}", "Entrada":"Impedancia" if item.mode == "Z" else "Admitancia",
                   "Valor":rectangular(complex(item.real,item.imag), digits), "Unidad":zu if item.mode == "Z" else yu}
        elif group == "voltages":
            row = {"ID":item.name, "Tipo":item.kind, "Terminales":f"(+) {item.positive} / (−) {item.negative}",
                   f"Voltaje ({vu})":f"{item.magnitude:.{digits}f} ∠ {item.angle:.{digits}f}°", f"Impedancia ({zu})":rectangular(complex(item.r,item.x), digits)}
        else:
            value = f"{item.value1:.{digits}f} ∠ {item.value2:.{digits}f}°" if item.mode == "Polar" else rectangular(complex(item.value1,item.value2), digits)
            row = {"ID":item.name, "Sentido":f"{item.from_node} → {item.to_node}", "Forma":item.mode, f"Corriente ({iu})":value}
        rows.append(row)
    return rows


def registered(group, label):
    rows = table_rows(group)
    st.subheader(label)
    if not rows:
        st.caption("Aún no hay elementos registrados en esta sección.")
        return
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    selection, edit, delete = st.columns([3,1,1], vertical_alignment="bottom")
    with selection:
        name = st.selectbox("Seleccionar elemento", [r["ID"] for r in rows], key=f"manage_{group}")
    edit.button("Editar", key=f"edit_{group}", on_click=begin_edit, args=(group,name), width="stretch")
    delete.button("Eliminar", key=f"delete_{group}", on_click=delete_saved, args=(group,name), width="stretch")


def form_footer(group, label):
    if "form_error_" + group in st.session_state:
        st.error(st.session_state["form_error_" + group])
    c1,c2 = st.columns(2)
    editing = st.session_state.editing[group]
    c1.button("Guardar cambios" if editing else label, type="primary", width="stretch", key=f"save_{group}", on_click=save_form, args=(group,))
    c2.button("Cancelar edición" if editing else "Restablecer formulario", width="stretch", key=f"cancel_{group}", on_click=reset_draft, args=(group,))
    st.caption("El circuito sólo cambia al guardar. Los campos confirmados se conservan al navegar entre pasos.")


def branch_form():
    group = "branches"
    yu,zu,_,_ = units()
    with st.container(border=True):
        st.subheader(f"Editar {st.session_state.editing[group]}" if st.session_state.editing[group] else "Agregar conexión")
        c1,c2 = st.columns(2)
        with c1:
            node_field(group,"a","Nodo inicial","Uno de los extremos de la conexión. Nodo 0 es tierra.")
        with c2:
            node_field(group,"b","Nodo final","El otro extremo. Debe ser distinto al nodo inicial.")
        mode = draft_widget(group,"mode","Datos disponibles","select",options=["Z","Y"],format_func=lambda m: "Impedancia · R + jX" if m=="Z" else "Admitancia · G + jB")
        c1,c2 = st.columns(2)
        if mode == "Z":
            with c1:
                draft_widget(group,"r",f"Resistencia R ({zu})",help="Componente real de la impedancia. Si no hay resistencia, introduce 0.")
            with c2:
                draft_widget(group,"x",f"Reactancia X ({zu})",help="Componente imaginaria: positiva inductiva, negativa capacitiva.")
        else:
            with c1:
                draft_widget(group,"g",f"Conductancia G ({yu})",help="Componente real de la admitancia.")
            with c2:
                draft_widget(group,"susceptance",f"Susceptancia B ({yu})",help="Componente imaginaria de la admitancia: negativa para una inductancia ideal.")
        with st.expander("Ejemplo de captura"):
            st.write("Para una rama j0.25 entre los nodos 1 y 2: selecciona Impedancia, R = 0 y X = 0.25. Si va a tierra, selecciona 0 como uno de los extremos.")
            st.caption("Puedes guardar varias ramas entre los mismos nodos. Sin conexión: no agregues una fila. Z = 0 es un cortocircuito ideal y no se admite; Y = 0 es circuito abierto.")
        form_footer(group,"Agregar conexión")
    registered(group,"Conexiones registradas")


def voltage_form():
    group = "voltages"
    _,zu,vu,_ = units()
    with st.container(border=True):
        st.subheader(f"Editar {st.session_state.editing[group]}" if st.session_state.editing[group] else "Agregar generador, motor o fuente")
        draft_widget(group,"kind","Tipo de elemento","select",options=["Generador","Motor","Fuente de voltaje"])
        st.markdown("**Conexión**")
        c1,c2 = st.columns(2)
        with c1:
            node_field(group,"positive","Nodo positivo (+)","Terminal positiva del voltaje interno de la fuente.")
        with c2:
            node_field(group,"negative","Nodo negativo (−)","Terminal negativa. Selecciona 0 si está conectada a tierra.")
        st.markdown("**Voltaje interno**")
        c1,c2 = st.columns(2)
        with c1:
            draft_widget(group,"magnitude",f"Magnitud del voltaje ({vu})",min_value=0.0,help="Valor del voltaje interno. Siempre es una magnitud no negativa.")
        with c2:
            draft_widget(group,"angle","Ángulo del voltaje (°)",help="Desfase en grados. Puedes introducir ángulos negativos.")
        st.markdown("**Impedancia interna en serie**")
        c1,c2 = st.columns(2)
        with c1:
            draft_widget(group,"r",f"Resistencia interna R ({zu})",help="Componente real. Introduce 0 si la impedancia sólo tiene reactancia.")
        with c2:
            draft_widget(group,"x",f"Reactancia interna X ({zu})",help="Componente imaginaria. R y X no pueden ser cero simultáneamente.")
        with st.expander("Ejemplo de captura"):
            st.write("Generador 1.25∠0° conectado al nodo 3 a través de j1.25: positivo 3, negativo 0, magnitud 1.25, ángulo 0°, R = 0 y X = 1.25.")
            st.caption("La aplicación calcula su equivalente de Norton. No agregues otra fuente de corriente para representar este mismo generador. Un motor usa la polaridad indicada; no inviertas su signo por la etiqueta.")
        form_footer(group,"Agregar fuente de voltaje")
    registered(group,"Generadores, motores y fuentes registrados")


def current_form():
    group = "currents"
    _,_,_,iu = units()
    with st.container(border=True):
        st.subheader(f"Editar {st.session_state.editing[group]}" if st.session_state.editing[group] else "Agregar fuente de corriente")
        c1,c2 = st.columns(2)
        with c1:
            node_field(group,"from_node","Nodo de origen","La corriente sale de este nodo. Para inyectar desde tierra selecciona 0.")
        with c2:
            node_field(group,"to_node","Nodo de destino","La corriente entra a este nodo: es una inyección positiva.")
        mode = draft_widget(group,"mode","Forma de la corriente","select",options=["Polar","Rectangular"])
        c1,c2 = st.columns(2)
        if mode == "Polar":
            with c1:
                draft_widget(group,"magnitude",f"Magnitud de corriente ({iu})",min_value=0.0,help="Valor no negativo de la corriente.")
            with c2:
                draft_widget(group,"angle","Ángulo de corriente (°)",help="Desfase en grados respecto a la referencia.")
        else:
            with c1:
                draft_widget(group,"real",f"Parte real de corriente ({iu})",help="Componente real de I = real + j·imaginaria. Puede ser negativa.")
            with c2:
                draft_widget(group,"imag",f"Parte imaginaria de corriente ({iu})",help="Coeficiente que multiplica a j. Puede ser negativo.")
        with st.expander("Ejemplo de captura"):
            st.write("Para inyectar 1∠−90° en el nodo 2: origen 0, destino 2, forma Polar, magnitud 1 y ángulo −90°. En Rectangular, el mismo fasor es real 0 e imaginaria −1.")
            st.caption("Las formas tienen campos independientes: cambiar de forma no convierte ni reinterpreta los valores del otro formulario.")
        form_footer(group,"Agregar fuente de corriente")
    registered(group,"Fuentes de corriente registradas")


def evaluate():
    try:
        return solve(st.session_state.network)
    except ValidationError as exc:
        st.error(str(exc))
        st.button("Revisar circuito", on_click=go, args=(3,), key="review_invalid")
        return None


def diagnose(result):
    for error in result.errors:
        st.error(error)
    for warning in result.warnings:
        st.warning(warning)


def downloads(result=None):
    net = st.session_state.network
    digits = st.session_state.digits
    st.subheader("Guardar y exportar")
    c1,c2,c3 = st.columns(3)
    try:
        data = network_json(net)
    except ValidationError:
        st.caption("Corrige los datos señalados para exportar el circuito.")
        return
    c1.download_button("Circuito · JSON",data,"circuito.json","application/json",width="stretch",key="export_json")
    if result is not None:
        c2.download_button("Procedimiento · Markdown",report_markdown(net,result,digits),"procedimiento.md","text/markdown",width="stretch",key="export_report")
        c3.download_button("Resultados · ZIP",export_zip(net,result,digits),"analisis_nodal.zip","application/zip",width="stretch",key="export_zip")
    st.caption("JSON permite retomar el trabajo. El ZIP conserva matrices y vectores CSV a precisión completa, el procedimiento y los diagnósticos.")


def show_matrix(matrix, symbol, unit):
    st.caption(f"{unit} · Filas y columnas en orden de nodos 1 a {st.session_state.network.nodes}.")
    st.dataframe(matrix_frame(matrix,st.session_state.digits),width="stretch")
    if st.session_state.network.nodes <= 6:
        with st.expander("Ver notación matricial"):
            st.latex(symbol + "=" + matrix_latex(matrix,st.session_state.digits))


def results_page(result):
    digits = st.session_state.digits
    yu,zu,vu,iu = units()
    diagnose(result)
    if result.checks.get("passed"):
        st.success("Solución verificada · Ybus · Zbus = Id, Ybus · Vbus = Ibus y KCL cumplen las tolerancias.")
    tabs = st.tabs(["Voltajes nodales", "Ybus", "Zbus", "Corrientes"])
    with tabs[0]:
        st.subheader("Voltajes respecto a tierra")
        if result.vbus is None:
            st.info("Completa o corrige el circuito para obtener los voltajes.")
        else:
            st.dataframe(vector_frame(result.vbus,vu,digits),hide_index=True,width="stretch")
            with st.expander("Copiar voltajes"):
                st.code("\n".join(f"V{i} = {rectangular(v,digits)} = {polar_text(v,digits)} {vu}" for i,v in enumerate(result.vbus,1)),language=None)
    with tabs[1]:
        st.subheader("Matriz de admitancias Ybus")
        show_matrix(result.ybus,"Y_{bus}",yu)
    with tabs[2]:
        st.subheader("Matriz de impedancias Zbus")
        if result.zbus is not None:
            show_matrix(result.zbus,"Z_{bus}",zu)
        else:
            st.info("La matriz inversa no está disponible. Consulta el diagnóstico del circuito.")
    with tabs[3]:
        st.subheader("Corrientes inyectadas Ibus")
        st.dataframe(vector_frame(result.ibus,iu,digits),hide_index=True,width="stretch")
        st.caption("Incluye automáticamente los equivalentes Norton de las fuentes de voltaje.")
    if result.checks:
        with st.expander("Comprobaciones matemáticas y corrientes de los elementos"):
            c1,c2,c3 = st.columns(3)
            c1.metric("Residuo YV − I", f"{result.checks['residual']:.2e}")
            c2.metric("Error YZ − Id", f"{result.checks['identity_error']:.2e}")
            c3.metric("Residuo KCL", f"{result.checks['kcl_error']:.2e}")
            st.caption(f"κ₂(Ybus) = {result.condition:.4g} · Rango {result.rank}/{st.session_state.network.nodes}")
            st.markdown(check_text(result))
            st.dataframe(pd.DataFrame([{"Elemento":f["name"],"Sentido":f"{f['a']} → {f['b']}",f"Corriente ({iu})":rectangular(f["current"],digits)} for f in result.flows]),hide_index=True,width="stretch")
    downloads(result)


def procedure_page(result):
    net = st.session_state.network
    digits = st.session_state.digits
    diagnose(result)
    with st.expander("1. De impedancias a admitancias y equivalentes Norton",expanded=True):
        st.latex(r"y=\frac{1}{R+jX}=\frac{R-jX}{R^2+X^2},\quad E=|E|(\cos\theta+j\sin\theta),\quad I_N=E/Z_s")
        st.write("Una fuente de voltaje inyecta E/Zs en su terminal positivo y extrae la misma corriente en el negativo. Su admitancia interna se agrega entre ambos terminales.")
        for s in result.stamps:
            st.text(f"{s['name']} · nodos {s['a']}–{s['b']}: {s['description']}")
    with st.expander("2. Construcción de cada elemento de Ybus"):
        st.latex(r"Y_{ii}=\sum_k y_{ik},\qquad Y_{ij}=-\sum_{\text{ramas }i-j} y_{ij}\quad(i\ne j)")
        st.write("Cada rama entre a y b suma y en Yaa e Ybb y resta y en Yab e Yba. Se omiten los índices de tierra. Las ramas en paralelo se suman.")
        row = st.selectbox("Fila a desarrollar",range(1,net.nodes+1),key="procedure_row")
        for j in range(net.nodes):
            st.text(cell_equation(result,row-1,j,digits))
        st.caption("El informe descargable contiene todas las filas.")
    with st.expander("3. Construcción del vector Ibus"):
        for s in result.injections:
            st.text(f"{s['name']}: {s['source']} → {s['target']}; I = {rectangular(s['current'],digits)}. +I en destino, −I en origen.")
        for i in range(1,net.nodes+1):
            st.text(injection_equation(result,i,digits))
    with st.expander("4. Inversa Zbus y solución de voltajes"):
        st.latex(r"Z_{bus}=Y_{bus}^{-1},\qquad Y_{bus}V_{bus}=I_{bus}")
        st.write("Después de revisar la referencia a tierra, el rango y el condicionamiento, NumPy obtiene Zbus con inv y resuelve Vbus directamente con solve, sin usar la inversa para resolver.")
        if result.vbus is not None and net.nodes <= 6:
            st.latex("V_{bus}=" + matrix_latex(result.vbus,digits))
        st.latex(r"|V|=\sqrt{(\Re V)^2+(\Im V)^2},\quad\theta=\operatorname{atan2}(\Im V,\Re V)\frac{180}{\pi}")
    with st.expander("5. Verificación independiente de los resultados"):
        st.latex(r"\epsilon_V=\frac{\|YV-I\|_\infty}{\|Y\|_\infty\|V\|_\infty+\|I\|_\infty},\quad\epsilon_Z=\|YZ-\mathrm{Id}\|_\infty")
        st.write("KCL se calcula nuevamente desde los elementos originales: (Va−Vb)/Z, Y(Va−Vb), (V+−V−−E)/Zs y las corrientes prescritas. La suma saliente debe ser cero en cada nodo.")
        st.caption("La escala de KCL suma |y|(|Va|+|Vb|) para ramas, (|Va|+|Vb|+|E|)/|Zs| para fuentes de voltaje y |I| para fuentes de corriente. Esto tolera cancelaciones en vacío. Si el denominador es cero, se usa el residuo absoluto.")
        if result.checks:
            st.markdown(check_text(result))
        else:
            st.info("Las comprobaciones estarán disponibles cuando la red tenga una solución admisible.")
    downloads(result)


# Navegación y herramientas disponibles desde cualquier paso.
with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 9h18M16 9v14"/><circle cx="7" cy="9" r="3"/><circle cx="25" cy="9" r="3"/><circle cx="16" cy="23" r="3"/></svg></div><div class="brand-name">ANSEP</div><div class="brand-sub">Héctor Gabriel Méndez Melchor · 2226703</div></div>',unsafe_allow_html=True)
    st.radio("Espacio de trabajo",range(6),format_func=lambda i:f"{i+1:02d}  {STEPS[i]}",key="navigation",label_visibility="collapsed")
    st.divider()
    with st.expander("Circuitos de referencia"):
        st.selectbox("Selecciona un circuito",list(EXAMPLES),format_func=lambda name:EXAMPLE_LABELS.get(name,name),key="example")
        st.button("Cargar circuito",on_click=load_example,key="load_example",width="stretch")
        st.caption("Reemplaza el circuito y sus borradores. Guarda antes tu trabajo como JSON.")
    with st.expander("Abrir / guardar circuito"):
        try:
            st.download_button("Guardar circuito · JSON",network_json(st.session_state.network),"circuito.json","application/json",width="stretch",key="sidebar_json")
        except ValidationError:
            st.caption("Corrige los nodos fuera de rango para guardar el circuito.")
        st.file_uploader("Selecciona un archivo JSON",type=["json"],key="circuit_upload",help="Formato compatible con la V1. Máximo 2 MB.")
        st.button("Importar archivo",on_click=import_file,key="import_file",disabled=st.session_state.get("circuit_upload") is None,width="stretch")
        if "import_error" in st.session_state:
            st.error(st.session_state.import_error)
        st.caption("Importar reemplaza el circuito actual. Un archivo inválido no modifica tus datos.")
        if "legacy_raw" in st.session_state:
            st.download_button("Respaldo de captura V1",json.dumps(st.session_state.legacy_raw,ensure_ascii=False,default=str),"captura_v1.json","application/json")
    with st.expander("Presentación y ayuda"):
        st.radio("Decimales en resultados",[2,4,6],horizontal=True,key="digits")
        st.caption("El redondeo es sólo visual. La presentación admite los temas claro y oscuro de Streamlit.")
        st.caption("Redes lineales de ramas independientes. Sin acoplamiento magnético ni flujo de potencia no lineal.")
    if st.session_state.undo is not None:
        st.button("Deshacer última eliminación",on_click=undo_delete,key="undo_delete",width="stretch")
    st.caption("Tu trabajo se conserva al navegar. Descarga el JSON antes de cerrar o recargar la sesión.")

net = st.session_state.network
step = st.session_state.navigation
st.markdown(f'<div class="page-label">ANÁLISIS NODAL · PASO {step+1} DE 6</div>',unsafe_allow_html=True)
st.title(STEPS[step])
st.markdown(f'<div class="subtitle">{DESCRIPTIONS[step]}</div>',unsafe_allow_html=True)
st.markdown(f'<div class="status-strip"><span><b>{net.nodes}</b> nodos</span><span><b>{len(net.branches)}</b> conexiones</span><span><b>{len(net.voltages)+len(net.currents)}</b> fuentes</span><span>{net.units}</span><span>Referencia: nodo <b>0</b></span></div>',unsafe_allow_html=True)
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))
pending = [STEPS[1] if g == "branches" else ("Fuentes de voltaje" if g == "voltages" else "Fuentes de corriente") for g in GROUPS if st.session_state.dirty[g]]
if pending:
    st.caption("Borrador sin guardar: " + ", ".join(pending) + ". Los resultados usan sólo elementos guardados.")

if step == 0:
    with st.container(border=True):
        st.subheader("Datos generales")
        c1,c2 = st.columns(2)
        st.session_state.node_count = net.nodes
        st.session_state.unit_mode = net.units
        with c1:
            st.number_input("Cantidad de nodos",min_value=1,max_value=100,step=1,key="node_count",on_change=config_changed,help="Cuenta los nodos 1, 2, 3… sin incluir tierra. Hasta 100 nodos.")
        with c2:
            st.selectbox("Sistema de unidades",["p.u.","SI"],format_func=lambda u:"Por unidad (p.u.)" if u=="p.u." else "Sistema Internacional (SI)",key="unit_mode",on_change=config_changed)
        st.caption("El nodo 0 es tierra o referencia. Su voltaje es cero y no se incluye en el número de nodos.")
    title = "Valores por unidad" if net.units == "p.u." else "Unidades del Sistema Internacional"
    explanation = "Introduce todos los valores en p.u. con bases compatibles." if net.units == "p.u." else "Impedancia en Ω · admitancia en S · voltaje en V · corriente en A. Convierte antes los prefijos kV, kA o mS."
    st.markdown(f'<div class="guide-card"><p class="guide-title">{title}</p><p class="guide-copy">{explanation}</p></div>',unsafe_allow_html=True)
    st.caption("Cambiar unidades reinterpreta los números; no los convierte. Cambiar nodos conserva los elementos y señala los terminales que necesiten corrección.")
    for _,_,message in input_issues(net):
        st.warning(message)
elif step == 1:
    branch_form()
elif step == 2:
    st.session_state.source_view = st.session_state.get("source_choice", "voltages")
    st.radio("Tipo de fuente",["voltages","currents"],format_func=lambda s:"Generadores, motores y voltajes" if s=="voltages" else "Fuentes de corriente",horizontal=True,key="source_view",on_change=source_changed)
    if st.session_state.source_view == "voltages":
        voltage_form()
    else:
        current_form()
elif step == 3:
    issues = input_issues(net)
    for group,name,message in issues:
        st.warning(message)
        st.button(f"Corregir {name}",on_click=begin_edit,args=(group,name),key=f"fix_{group}_{name}")
    if not any(getattr(net,g) for g in GROUPS):
        st.info("Tu circuito está vacío. Agrega conexiones y fuentes, o carga un ejercicio de referencia.")
    for group,label in (("branches","Conexiones"),("voltages","Fuentes de voltaje"),("currents","Fuentes de corriente")):
        with st.container(border=True):
            registered(group,label)
    if not issues and any(getattr(net,g) for g in GROUPS):
        result = evaluate()
        if result is not None:
            diagnose(result)
            if result.checks.get("passed"):
                st.success("El circuito tiene una solución verificada. Continúa a Resultados.")
    downloads()
elif step in (4,5):
    result = evaluate()
    if result is not None:
        if step == 4:
            results_page(result)
        else:
            procedure_page(result)

st.divider()
back,_,forward = st.columns([1,1,1])
back.button("← Anterior",on_click=go,args=(step-1,),disabled=step==0,key="previous",width="stretch")
forward.button("Siguiente →" if step<3 else ("Ver resultados →" if step==3 else "Ver procedimiento →"),on_click=go,args=(step+1,),disabled=step==5,key="next",type="primary",width="stretch")
