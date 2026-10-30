"""Transcripciones de los diagramas, no de las matrices manuscritas."""
from power_system import Branch, CurrentSource, Network, VoltageSource


def pdf_four_nodes():
    return Network(4, "p.u.", [
        Branch("L12", 1, 2, "Z", 0, .125),
        Branch("L13", 1, 3, "Z", 0, .25),
        Branch("L14", 1, 4, "Z", 0, .4),
        Branch("L23", 2, 3, "Z", 0, .25),
        Branch("L24", 2, 4, "Z", 0, .2),
    ], [
        VoltageSource("G3", 3, 0, 1.25, 0, 0, 1.25, "Generador"),
        VoltageSource("M4", 4, 0, .85, -45, 0, 1.25, "Motor"),
    ])


def pdf_five_nodes():
    return Network(5, "p.u.", [
        Branch("L12", 1, 2, "Z", 0, .4),
        Branch("L13", 1, 3, "Z", 0, .5),
        Branch("L23", 2, 3, "Z", 0, .25),
        Branch("L25", 2, 5, "Z", 0, .2),
        Branch("L34", 3, 4, "Z", 0, .125),
        Branch("L45", 4, 5, "Z", 0, .5),
    ], [
        VoltageSource("E1", 1, 0, 1.1, 0, 0, 1, "Generador"),
        VoltageSource("E5", 5, 0, .9, -30, 0, 1.25, "Motor"),
    ])


def two_nodes():
    return Network(2, "SI", [Branch("R12", 1, 2, "Z", 2, 0), Branch("R20", 2, 0, "Z", 4, 0)],
                   [VoltageSource("E1", 1, 0, 10, 0, 1, 0)])


EXAMPLES = {"Circuito vacío": Network, "Ejemplo resistivo · 2 nodos": two_nodes,
            "PDF · página 1 · 4 nodos": pdf_four_nodes, "PDF · página 3 · 5 nodos": pdf_five_nodes}
