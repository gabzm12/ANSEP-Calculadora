"""Análisis nodal fasorial de ramas independientes. No depende de Streamlit."""
from dataclasses import asdict, dataclass, field
import json
import math
from numbers import Integral

import numpy as np


class ValidationError(ValueError):
    """Datos de entrada que no representan un circuito admitido."""


@dataclass
class Branch:
    name: str
    a: int
    b: int
    mode: str = "Z"
    real: float = 0.0
    imag: float = 0.0


@dataclass
class VoltageSource:
    name: str
    positive: int
    negative: int
    magnitude: float
    angle: float
    r: float
    x: float
    kind: str = "Fuente de voltaje"


@dataclass
class CurrentSource:
    name: str
    from_node: int
    to_node: int
    mode: str = "Rectangular"
    value1: float = 0.0
    value2: float = 0.0


@dataclass
class Network:
    nodes: int = 4
    units: str = "p.u."
    branches: list[Branch] = field(default_factory=list)
    voltages: list[VoltageSource] = field(default_factory=list)
    currents: list[CurrentSource] = field(default_factory=list)


@dataclass
class Result:
    ybus: np.ndarray
    ibus: np.ndarray
    zbus: np.ndarray | None = None
    vbus: np.ndarray | None = None
    stamps: list = field(default_factory=list)
    injections: list = field(default_factory=list)
    flows: list = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    condition: float = math.inf
    rank: int = 0
    checks: dict = field(default_factory=dict)


def polar(magnitude, angle):
    # Reducir el ángulo evita desbordar la conversión a radianes.
    return magnitude * np.exp(1j * np.deg2rad(angle % 360))


def rectangular(z, digits=6):
    threshold = 0.5 * 10 ** (-digits)
    real = 0.0 if abs(z.real) < threshold else z.real
    imag = 0.0 if abs(z.imag) < threshold else z.imag
    return f"{real:.{digits}f}{imag:+.{digits}f}j"


def polar_text(z, digits=6):
    angle = float(np.angle(z, deg=True)) if z != 0 else 0.0
    return f"{abs(z):.{digits}f} ∠ {angle:.{digits}f}°"


def _finite(value, label):
    if isinstance(value, (bool, str)):
        raise ValidationError(f"{label}: introduce un número finito.")
    try:
        valid = math.isfinite(value)
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not valid:
        raise ValidationError(f"{label}: introduce un número finito; no se admite NaN ni infinito.")


def _pair(a, b, n, label):
    for node in (a, b):
        _finite(node, label + ": nodo")
        if int(node) != node or not 0 <= node <= n:
            raise ValidationError(f"{label}: los nodos deben ser enteros entre 0 y {n}.")
    if a == b:
        raise ValidationError(f"{label}: los terminales deben ser nodos distintos.")


def _inverse(z, label):
    if z == 0:
        raise ValidationError(f"{label}: Z = 0 representa un cortocircuito o una fuente ideal de voltaje; no se admite. Una conexión ausente se elimina de la tabla.")
    y = 1 / z
    if not np.isfinite(y) or y == 0:
        raise ValidationError(f"{label}: la inversa de Z está fuera del rango numérico.")
    return y


def validate(net):
    _finite(net.nodes, "Número de nodos")
    if not isinstance(net.nodes, Integral) or not 1 <= net.nodes <= 100:
        raise ValidationError("El número de nodos debe ser un entero entre 1 y 100, sin contar tierra.")
    if net.units not in ("p.u.", "SI"):
        raise ValidationError("Unidades admitidas: p.u. o SI (Ω, S, V, A).")
    names = set()
    for item in [*net.branches, *net.voltages, *net.currents]:
        if not isinstance(item.name, str) or not item.name.strip() or len(item.name) > 80:
            raise ValidationError("Cada elemento necesita un identificador de 1 a 80 caracteres.")
        if item.name in names:
            raise ValidationError(f"Identificador repetido: {item.name}. Usa nombres únicos en las tres tablas.")
        names.add(item.name)
    for b in net.branches:
        _pair(b.a, b.b, net.nodes, b.name)
        _finite(b.real, b.name + ": R/G")
        _finite(b.imag, b.name + ": X/B")
        if b.mode not in ("Z", "Y"):
            raise ValidationError(f"{b.name}: selecciona Z o Y.")
        if b.mode == "Z":
            _inverse(complex(b.real, b.imag), b.name)
    for s in net.voltages:
        _pair(s.positive, s.negative, net.nodes, s.name)
        for attr in ("magnitude", "angle", "r", "x"):
            _finite(getattr(s, attr), f"{s.name}: {attr}")
        if s.magnitude < 0:
            raise ValidationError(f"{s.name}: la magnitud del voltaje no puede ser negativa.")
        if s.kind not in ("Generador", "Motor", "Fuente de voltaje"):
            raise ValidationError(f"{s.name}: tipo de fuente desconocido.")
        _inverse(complex(s.r, s.x), s.name)
    for s in net.currents:
        _pair(s.from_node, s.to_node, net.nodes, s.name)
        _finite(s.value1, s.name + ": valor 1")
        _finite(s.value2, s.name + ": valor 2")
        if s.mode not in ("Rectangular", "Polar"):
            raise ValidationError(f"{s.name}: selecciona Rectangular o Polar.")
        if s.mode == "Polar" and s.value1 < 0:
            raise ValidationError(f"{s.name}: la magnitud de corriente no puede ser negativa.")


def solve(net):
    validate(net)
    n = int(net.nodes)
    result = Result(np.zeros((n, n), complex), np.zeros(n, complex))
    adjacency = [set() for _ in range(n + 1)]

    def stamp(name, a, b, y, description):
        a, b = int(a), int(b)
        if y != 0:
            adjacency[a].add(b)
            adjacency[b].add(a)
        terms = []
        if a:
            terms.append((a - 1, a - 1, y))
        if b:
            terms.append((b - 1, b - 1, y))
        if a and b:
            terms.extend([(a - 1, b - 1, -y), (b - 1, a - 1, -y)])
        for i, j, value in terms:
            result.ybus[i, j] += value
        result.stamps.append(dict(name=name, a=a, b=b, y=y, terms=terms, description=description))

    def inject(name, source, target, current):
        source, target = int(source), int(target)
        if target:
            result.ibus[target - 1] += current
        if source:
            result.ibus[source - 1] -= current
        result.injections.append(dict(name=name, source=source, target=target, current=current))

    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        for b in net.branches:
            value = complex(b.real, b.imag)
            y = _inverse(value, b.name) if b.mode == "Z" else value
            desc = f"y = 1 / ({rectangular(value)}) = {rectangular(y)}" if b.mode == "Z" else f"y = G+jB = {rectangular(y)} (entrada directa)"
            stamp(b.name, b.a, b.b, y, desc)
            if y == 0:
                result.warnings.append(f"{b.name}: Y = 0 es un circuito abierto; no establece conectividad.")
            if b.real < 0:
                result.warnings.append(f"{b.name}: R/G negativa; se interpreta como elemento activo lineal.")
        for s in net.voltages:
            z = complex(s.r, s.x)
            e = polar(s.magnitude, s.angle)
            y, current = _inverse(z, s.name), e / z
            if not np.isfinite(current):
                raise ValidationError(f"{s.name}: corriente Norton fuera del rango numérico.")
            stamp(s.name, s.positive, s.negative, y, f"Norton: E = {rectangular(e)}; Zs = {rectangular(z)}; Ys = 1/Zs = {rectangular(y)}; IN = E/Zs = {rectangular(current)} ({polar_text(current)}).")
            inject(s.name, s.negative, s.positive, current)
            if s.r < 0:
                result.warnings.append(f"{s.name}: resistencia serie negativa; elemento activo lineal.")
        for s in net.currents:
            current = polar(s.value1, s.value2) if s.mode == "Polar" else complex(s.value1, s.value2)
            inject(s.name, s.from_node, s.to_node, current)
    if not np.isfinite(result.ybus).all() or not np.isfinite(result.ibus).all():
        raise ValidationError("La suma de los elementos desborda el rango numérico. Reescala las unidades.")

    seen, pending = {0}, [0]
    while pending:
        for node in adjacency[pending.pop()] - seen:
            seen.add(node)
            pending.append(node)
    floating = sorted(set(range(1, n + 1)) - seen)
    if floating:
        result.errors.append(f"Nodos sin camino de admitancias a tierra: {floating}. Las fuentes de corriente no fijan una referencia de voltaje.")
    try:
        singular_values = np.linalg.svd(result.ybus, compute_uv=False)
        result.rank = int(np.sum(singular_values > singular_values[0] * n * np.finfo(float).eps))
        result.condition = float(singular_values[0] / singular_values[-1]) if singular_values[-1] else math.inf
        if result.rank < n:
            result.errors.append(f"Ybus es singular numéricamente (rango {result.rank}/{n}); no existe una solución nodal única.")
        elif result.condition >= 1e12 or not math.isfinite(result.condition):
            result.errors.append("Ybus está mal condicionada (κ₂ ≥ 10¹²). Revisa escalas, valores extremos y cancelaciones.")
        elif result.condition > 1e8:
            result.warnings.append("Ybus tiene un condicionamiento elevado (κ₂ > 10⁸); los datos pueden amplificar errores.")
        if result.errors:
            return result
        result.vbus = np.linalg.solve(result.ybus, result.ibus)
        result.zbus = np.linalg.inv(result.ybus)
    except np.linalg.LinAlgError:
        result.errors.append("No fue posible factorizar Ybus; revisa singularidades y escalas.")
        result.vbus = result.zbus = None
        return result
    if not np.isfinite(result.vbus).all() or not np.isfinite(result.zbus).all():
        result.errors.append("La solución excede el rango numérico. Reescala las unidades.")
        result.vbus = result.zbus = None
        return result

    # Verificación independiente de KCL, desde las leyes constitutivas originales.
    v = np.r_[0j, result.vbus]
    outgoing = np.zeros(n, complex)
    flow_scale = np.zeros(n, float)

    def flow(name, a, b, current, scale=None):
        a, b = int(a), int(b)
        scale = abs(current) if scale is None else scale
        result.flows.append(dict(name=name, a=a, b=b, current=current))
        if a:
            outgoing[a - 1] += current
            flow_scale[a - 1] += scale
        if b:
            outgoing[b - 1] -= current
            flow_scale[b - 1] += scale

    for b in net.branches:
        value = complex(b.real, b.imag)
        dv = v[int(b.a)] - v[int(b.b)]
        ymag = abs(1 / value) if b.mode == "Z" else abs(value)
        scale = (abs(v[int(b.a)]) + abs(v[int(b.b)])) * ymag
        flow(b.name, b.a, b.b, dv / value if b.mode == "Z" else dv * value, scale)
    for s in net.voltages:
        current = (v[int(s.positive)] - v[int(s.negative)] - polar(s.magnitude, s.angle)) / complex(s.r, s.x)
        scale = (abs(v[int(s.positive)]) + abs(v[int(s.negative)]) + s.magnitude) / abs(complex(s.r, s.x))
        flow(s.name, s.positive, s.negative, current, scale)
    for s in net.currents:
        flow(s.name, s.from_node, s.to_node, polar(s.value1, s.value2) if s.mode == "Polar" else complex(s.value1, s.value2))
    if not np.isfinite(outgoing).all() or not np.isfinite(flow_scale).all():
        result.errors.append("Las corrientes o su escala de verificación exceden el rango numérico. Reescala los datos.")
        result.vbus = result.zbus = None
        return result
    norm = lambda a: float(np.linalg.norm(a, ord=np.inf))
    residual = norm(result.ybus @ result.vbus - result.ibus)
    denominator = norm(result.ybus) * norm(result.vbus) + norm(result.ibus)
    if not math.isfinite(residual) or not math.isfinite(denominator):
        result.errors.append("La verificación excede el rango numérico. Reescala los datos.")
        result.vbus = result.zbus = None
        return result
    backward = residual / denominator if denominator else residual
    identity = norm(result.ybus @ result.zbus - np.eye(n))
    kcl = norm(outgoing)
    kcl_relative = kcl / norm(flow_scale) if norm(flow_scale) else kcl
    result.checks = dict(residual=residual, backward_error=backward, identity_error=identity, kcl_error=kcl, kcl_relative=kcl_relative)
    result.checks["passed"] = bool(backward <= 1e-10 and identity <= 1e-8 and kcl_relative <= 1e-10)
    if not result.checks["passed"]:
        result.errors.append("La solución no superó las verificaciones numéricas; no debe considerarse validada.")
    return result


def network_json(net):
    validate(net)
    return json.dumps({"version": 1, **asdict(net)}, ensure_ascii=False, indent=2, allow_nan=False)


def network_from_json(text):
    try:
        data = json.loads(text)
        if data.pop("version", None) != 1:
            raise ValidationError("Versión de archivo no admitida; se requiere version = 1.")
        data["branches"] = [Branch(**r) for r in data.get("branches", [])]
        data["voltages"] = [VoltageSource(**r) for r in data.get("voltages", [])]
        data["currents"] = [CurrentSource(**r) for r in data.get("currents", [])]
        net = Network(**data)
        validate(net)
        return net
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
        raise ValidationError(f"Archivo de circuito inválido: {exc}") from exc
