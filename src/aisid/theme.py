"""Sistema visual del dashboard.

Los cuatro colores categóricos están asignados a los cuatro tipos de fallo de
forma fija: el color sigue a la entidad, nunca a su posición en el ranking. Si un
filtro deja fuera "Sesgo", los otros tres no se repintan.

Ambas paletas (clara y oscura) pasan las seis comprobaciones del validador
(banda de luminosidad, suelo de croma, separación CVD en protan/deutan/tritan,
suelo de visión normal y contraste sobre la superficie). La paleta clara emite un
WARN de contraste en aqua y amarillo, lo que obliga a etiquetas visibles y a una
vista de tabla: ambas están implementadas.
"""

from __future__ import annotations

from .data import TIPOS

# Rampa secuencial azul (magnitud), de claro a oscuro. Nunca arcoíris.
SECUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

LIGHT = {
    "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"],
    "surface": "#fcfcfb",
    "plane": "#f9f9f7",
    "ink": "#0b0b0b",
    "ink_secondary": "#52514e",
    "muted": "#898781",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
}

DARK = {
    "series": ["#3987e5", "#d95926", "#199e70", "#c98500"],
    "surface": "#1a1a19",
    "plane": "#0d0d0d",
    "ink": "#ffffff",
    "ink_secondary": "#c3c2b7",
    "muted": "#898781",
    "grid": "#2c2c2a",
    "axis": "#383835",
}

FUENTE = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def tema(modo: str = "light") -> dict:
    return DARK if modo == "dark" else LIGHT


def color_tipo(modo: str = "light") -> dict[str, str]:
    """Asignación fija tipo de fallo -> color, idéntica en todos los gráficos."""
    return dict(zip(TIPOS, tema(modo)["series"]))
