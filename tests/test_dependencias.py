"""Toda dependencia que el codigo importa tiene que estar declarada en los tres sitios.

Existe porque el dashboard desplegado se cayo con ModuleNotFoundError: plotly. plotly
estaba en requirements.txt, pero pyproject.toml no declaraba dependencias y uv.lock, que
se genera de el, bloqueaba cero paquetes. Streamlit Cloud instalo desde el lock y plotly
nunca llego. Un fichero de dependencias correcto no basta si otro dice lo contrario.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Modulos que trae el entorno de ejecucion o la propia biblioteca estandar.
DE_LA_STDLIB_O_PROPIOS = {"aisid"}


def _modulos_importados() -> set[str]:
    """Modulos de primer nivel que importa el codigo que se ejecuta en produccion."""
    import sys

    fuentes = [RAIZ / "app.py", *(RAIZ / "src").rglob("*.py")]
    modulos: set[str] = set()
    for fuente in fuentes:
        arbol = ast.parse(fuente.read_text(encoding="utf-8"), filename=str(fuente))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                modulos.update(a.name.split(".")[0] for a in nodo.names)
            elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                modulos.add(nodo.module.split(".")[0])
    return {
        m
        for m in modulos
        if m not in sys.stdlib_module_names and m not in DE_LA_STDLIB_O_PROPIOS
    }


def _declarados_en_requirements() -> set[str]:
    texto = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
    nombres = set()
    for linea in texto.splitlines():
        linea = linea.strip()
        if linea and not linea.startswith(("#", "-")):
            nombres.add(linea.split("==")[0].split(">=")[0].split("[")[0].strip().lower())
    return nombres


def _declarados_en_pyproject() -> set[str]:
    datos = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    deps = datos["project"].get("dependencies", [])
    return {d.split("==")[0].split(">=")[0].split("[")[0].strip().lower() for d in deps}


def _bloqueados_en_uv_lock() -> set[str]:
    texto = (RAIZ / "uv.lock").read_text(encoding="utf-8")
    datos = tomllib.loads(texto)
    return {p["name"].strip().lower() for p in datos.get("package", [])}


def test_todo_import_esta_en_requirements() -> None:
    faltan = _modulos_importados() - _declarados_en_requirements()
    assert not faltan, f"importados pero ausentes de requirements.txt: {sorted(faltan)}"


def test_todo_import_esta_en_pyproject() -> None:
    faltan = _modulos_importados() - _declarados_en_pyproject()
    assert not faltan, f"importados pero ausentes de pyproject.toml: {sorted(faltan)}"


def test_uv_lock_incluye_las_dependencias_declaradas() -> None:
    """El lock es lo que Streamlit Cloud instala: si no las bloquea, no se instalan."""
    faltan = _declarados_en_pyproject() - _bloqueados_en_uv_lock()
    assert not faltan, f"declaradas en pyproject pero sin bloquear en uv.lock: {sorted(faltan)}"


def test_requirements_y_pyproject_no_se_contradicen() -> None:
    solo_req = _declarados_en_requirements() - _declarados_en_pyproject()
    solo_pyp = _declarados_en_pyproject() - _declarados_en_requirements()
    assert not (solo_req or solo_pyp), (
        f"solo en requirements.txt: {sorted(solo_req)}; solo en pyproject.toml: {sorted(solo_pyp)}"
    )
