"""Estado y operaciones de captura de V2; reutiliza la validación de V1."""
from copy import deepcopy
from dataclasses import asdict

from power_system import Branch, CurrentSource, Network, ValidationError, VoltageSource, validate

GROUPS = {"branches": Branch, "voltages": VoltageSource, "currents": CurrentSource}


def new_draft(group, nodes):
    if group == "branches":
        return dict(a=1, b=2 if nodes > 1 else 0, mode="Z", r=0.0, x=0.1, g=0.0, susceptance=-10.0)
    if group == "voltages":
        return dict(positive=1, negative=0, kind="Generador", magnitude=1.0, angle=0.0, r=0.0, x=0.1)
    return dict(from_node=0, to_node=1, mode="Polar", magnitude=0.0, angle=0.0, real=0.0, imag=0.0)


def item_draft(group, item, nodes):
    draft = new_draft(group, nodes)
    values = asdict(item)
    values.pop("name")
    if group == "branches":
        real, imag = values.pop("real"), values.pop("imag")
        values.update(dict(r=real, x=imag) if item.mode == "Z" else dict(g=real, susceptance=imag))
    elif group == "currents":
        a, b = values.pop("value1"), values.pop("value2")
        values.update(dict(magnitude=a, angle=b) if item.mode == "Polar" else dict(real=a, imag=b))
    draft.update(values)
    return draft


def draft_fields(group, draft):
    if group == "branches":
        return dict(a=int(draft["a"]), b=int(draft["b"]), mode=draft["mode"],
                    real=draft["r"] if draft["mode"] == "Z" else draft["g"],
                    imag=draft["x"] if draft["mode"] == "Z" else draft["susceptance"])
    if group == "currents":
        return dict(from_node=int(draft["from_node"]), to_node=int(draft["to_node"]), mode=draft["mode"],
                    value1=draft["magnitude"] if draft["mode"] == "Polar" else draft["real"],
                    value2=draft["angle"] if draft["mode"] == "Polar" else draft["imag"])
    return {k: draft[k] for k in ("positive", "negative", "kind", "magnitude", "angle", "r", "x")}


def next_id(net, group, fields):
    prefix = {"branches": "R", "currents": "I", "voltages": {"Generador": "G", "Motor": "M"}.get(fields.get("kind"), "E")}[group]
    names = {x.name for g in GROUPS for x in getattr(net, g)}
    number = 1
    while f"{prefix}{number}" in names:
        number += 1
    return f"{prefix}{number}"


def save_element(net, group, draft, editing=None):
    """Operación atómica: una captura inválida no modifica el circuito."""
    fields = draft_fields(group, draft)
    name = editing or next_id(net, group, fields)
    item = GROUPS[group](name=name, **fields)
    # Validar sólo la captura permite reparar redes con varios nodos fuera de rango.
    candidate = Network(net.nodes, net.units)
    getattr(candidate, group).append(item)
    validate(candidate)
    updated = deepcopy(net)
    items = getattr(updated, group)
    if editing:
        indices = [i for i, old in enumerate(items) if old.name == editing]
        if not indices:
            raise ValidationError("El elemento ya no existe. Abre de nuevo el formulario.")
        items[indices[0]] = item
    else:
        items.append(item)
    return updated, name


def delete_element(net, group, name):
    updated = deepcopy(net)
    setattr(updated, group, [x for x in getattr(updated, group) if x.name != name])
    return updated


def input_issues(net):
    """Diagnósticos de captura por elemento, sin cambiar ni resolver la red."""
    issues = []
    for group in GROUPS:
        for item in getattr(net, group):
            sample = Network(net.nodes, net.units)
            getattr(sample, group).append(item)
            try:
                validate(sample)
            except ValidationError as exc:
                issues.append((group, item.name, str(exc)))
    return issues
