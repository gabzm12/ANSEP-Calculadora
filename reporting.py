"""Presentación y exportación: los cálculos no se redondean."""
import io
import json
import zipfile
import numpy as np
import pandas as pd
from power_system import network_json, polar_text, rectangular


def matrix_frame(matrix, digits=6):
    return pd.DataFrame([[rectangular(z, digits) for z in row] for row in matrix],
                        index=[f"Nodo {i+1}" for i in range(matrix.shape[0])],
                        columns=[f"Nodo {i+1}" for i in range(matrix.shape[1])])


def vector_frame(vector, unit, digits=6):
    return pd.DataFrame({"Nodo": range(1, len(vector)+1),
                         f"Rectangular ({unit})": [rectangular(z, digits) for z in vector],
                         f"Magnitud ({unit})": [f"{abs(z):.{digits}f}" for z in vector],
                         "Ángulo (°)": [f"{np.angle(z, deg=True):.{digits}f}" for z in vector],
                         f"Polar ({unit})": [polar_text(z, digits) for z in vector]})


def matrix_latex(matrix, digits=6):
    matrix = np.asarray(matrix)
    if matrix.ndim == 1:
        matrix = matrix[:, None]
    return r"\begin{bmatrix}" + r" \\ ".join(" & ".join(rectangular(z, digits).replace("j", r"\,j") for z in row) for row in matrix) + r"\end{bmatrix}"


def cell_equation(result, i, j, digits=6):
    terms = [(s["name"], value) for s in result.stamps for row, col, value in s["terms"] if row == i and col == j]
    expression = " + ".join(f"({rectangular(z, digits)}) [{name}]" for name, z in terms) or "0 (sin contribuciones)"
    return f"Y[{i+1},{j+1}] = {expression} = {rectangular(result.ybus[i,j], digits)}"


def injection_equation(result, node, digits=6):
    terms = []
    for s in result.injections:
        if s["target"] == node:
            terms.append((s["name"], s["current"]))
        if s["source"] == node:
            terms.append((s["name"], -s["current"]))
    expression = " + ".join(f"({rectangular(z, digits)}) [{name}]" for name, z in terms) or "0"
    return f"I[{node}] = {expression} = {rectangular(result.ibus[node-1], digits)}"


def check_text(result):
    c = result.checks
    return (f"||YV−I||∞ = {c['residual']:.3e}; error relativo de resolución = {c['backward_error']:.3e} (límite 1e−10).\n\n"
            f"||YZ−Id||∞ = {c['identity_error']:.3e} (límite 1e−8).\n\n"
            f"Residuo KCL = {c['kcl_error']:.3e}; KCL relativo = {c['kcl_relative']:.3e} (límite 1e−10).\n\n"
            f"Estado: {'VERIFICADO' if c['passed'] else 'NO VERIFICADO'}.")


def report_markdown(net, result, digits=6):
    yu, zu, vu, iu = ("p.u.",)*4 if net.units == "p.u." else ("S", "Ω", "V", "A")
    lines = ["# Informe de análisis nodal", f"Nodos: {net.nodes} (sin tierra). Unidades: {net.units}.",
             "Nodo 0 = referencia. Ángulos en grados; corrientes positivas inyectadas al nodo. En p.u. se requieren bases compatibles; en SI se usan Ω, S, V y A sin prefijos.",
             "## 1. Datos de entrada", "```json\n" + network_json(net) + "\n```",
             "## 2. Admitancias y equivalentes de Norton",
             r"$$y=\frac{1}{R+jX}=\frac{R-jX}{R^2+X^2},\quad y=G+jB,\quad I_N=\frac{E}{Z_s}$$",
             "Fuente con terminal positivo a y negativo b: corriente saliente a→b = (Va−Vb−E)/Zs. Norton inyecta +E/Zs en a y −E/Zs en b. La etiqueta Motor no invierte el fasor ni la polaridad."]
    for s in result.stamps:
        lines.append(f"- {s['name']} ({s['a']}–{s['b']}): {s['description']}")
    lines.extend(["## 3. Construcción de Ybus", r"$$Y_{ii}=\sum y_{ik},\qquad Y_{ij}=-\sum y_{ij}\ (i\ne j)$$",
                  "Se suman las ramas en paralelo. Una rama a tierra sólo contribuye a la diagonal del nodo distinto de cero.", f"Unidad: {yu}."])
    equations = [cell_equation(result, i, j, digits) for i in range(net.nodes) for j in range(net.nodes)]
    lines.extend(["```text\n" + "\n".join(equations) + "\n```", "$$Y_{bus}=" + matrix_latex(result.ybus, digits) + "$$", "## 4. Construcción de Ibus"])
    for s in result.injections:
        lines.append(f"- {s['name']}: {s['source']} → {s['target']}; I = {rectangular(s['current'], digits)} {iu}. Se suma en destino y se resta en origen; tierra no tiene ecuación.")
    lines.extend(["```text\n" + "\n".join(injection_equation(result, i, digits) for i in range(1, net.nodes+1)) + "\n```",
                  "$$I_{bus}=" + matrix_latex(result.ibus, digits) + "$$", "## 5. Zbus y voltajes",
                  f"Rango numérico: {result.rank}/{net.nodes}. Condición κ₂(Ybus): {result.condition:.6g}."])
    if result.vbus is not None:
        lines.extend(["Se obtiene Zbus con numpy.linalg.inv. Los voltajes se resuelven directamente con numpy.linalg.solve(Ybus, Ibus), sin usar la inversa para resolver.",
                      "$$Z_{bus}=Y_{bus}^{-1}=" + matrix_latex(result.zbus, digits) + "$$", f"Unidad de Zbus: {zu}.",
                      r"$$Y_{bus}V_{bus}=I_{bus},\qquad V_{bus}=" + matrix_latex(result.vbus, digits) + "$$",
                      r"$$|V|=\sqrt{(\Re V)^2+(\Im V)^2},\quad \theta=\operatorname{atan2}(\Im V,\Re V)\,180/\pi$$"])
        for i, v in enumerate(result.vbus, 1):
            lines.append(f"- V{i} = {rectangular(v, digits)} = {polar_text(v, digits)} {vu}.")
        lines.append("## 6. Corrientes y verificación independiente de KCL")
        for f in result.flows:
            lines.append(f"- {f['name']}, sentido {f['a']} → {f['b']}: {rectangular(f['current'], digits)} {iu}.")
        lines.extend(["Las corrientes se recalculan desde los elementos originales: (Va−Vb)/Z, Y(Va−Vb), (Va−Vb−E)/Zs y las fuentes de corriente prescritas. Su suma saliente debe ser cero en cada nodo.",
                      "Error relativo de resolución = ||YV−I||∞ / (||Y||∞ ||V||∞ + ||I||∞). KCL relativo = máximo residuo nodal / máxima suma nodal de escalas de elementos: |y|(|Va|+|Vb|) para ramas, (|Va|+|Vb|+|E|)/|Zs| para fuentes de voltaje y |I| para fuentes de corriente. Esta escala evita falsas alarmas en vacío por cancelación. Si el denominador es cero, se usa el residuo absoluto.",
                      "## 7. Verificaciones numéricas", check_text(result)])
    lines.extend(["## Diagnóstico", *[f"- ERROR: {s}" for s in result.errors], *[f"- Aviso: {s}" for s in result.warnings]])
    if not result.errors and not result.warnings:
        lines.append("Sin incidencias detectadas.")
    lines.extend(["## Alcance", "Redes lineales fasoriales independientes. No incluye acoplamiento magnético, impedancias mutuas, flujo de potencia no lineal, transformadores ideales con relación de transformación, cortocircuitos ideales ni fuentes ideales de voltaje. No convierte automáticamente entre unidades ni bases.",
                  "Los valores se muestran redondeados; las verificaciones usan toda la precisión de NumPy."])
    return "\n\n".join(lines)


def export_zip(net, result, digits=6):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("circuito.json", network_json(net))
        archive.writestr("procedimiento.md", report_markdown(net, result, digits))
        for name, matrix in (("Ybus", result.ybus), ("Zbus", result.zbus)):
            if matrix is not None:
                rows = [{"fila": i+1, "columna": j+1, "real": z.real, "imag": z.imag} for i, row in enumerate(matrix) for j, z in enumerate(row)]
                archive.writestr(name + ".csv", pd.DataFrame(rows).to_csv(index=False))
        for name, vector in (("Ibus", result.ibus), ("Vbus", result.vbus)):
            if vector is not None:
                rows = [{"nodo": i+1, "real": z.real, "imag": z.imag, "magnitud": abs(z), "angulo_grados": np.angle(z, deg=True)} for i, z in enumerate(vector)]
                archive.writestr(name + ".csv", pd.DataFrame(rows).to_csv(index=False))
        archive.writestr("diagnostico.json", json.dumps({"units": net.units, "errors": result.errors, "warnings": result.warnings, "condition": result.condition if np.isfinite(result.condition) else None, "checks": result.checks}, ensure_ascii=False, indent=2, allow_nan=False))
    return output.getvalue()
