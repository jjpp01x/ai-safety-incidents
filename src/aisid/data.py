"""Carga y validación del dataset de incidentes.

El dataset es la pieza frágil de este proyecto: se mantiene a mano. Por eso el
contrato se valida al cargar y falla ruidosamente, en vez de dejar que una fila
mal escrita se convierta en una barra silenciosamente equivocada del dashboard.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "incidents.csv"

TIPOS: tuple[str, ...] = ("contencion", "sesgo", "alucinacion", "seguridad")

ETIQUETA_TIPO: dict[str, str] = {
    "contencion": "Contención",
    "sesgo": "Sesgo",
    "alucinacion": "Alucinación",
    "seguridad": "Seguridad",
}

COLUMNAS_REQUERIDAS: tuple[str, ...] = (
    "id",
    "fecha",
    "empresa",
    "sistema",
    "tipo_fallo",
    "severidad",
    "pais",
    "dominio",
    "evidencia",
    "estado",
    "resumen",
    "fuente",
    "url",
)

SEVERIDAD_MIN = 1
SEVERIDAD_MAX = 5


class DatasetError(ValueError):
    """El CSV incumple el contrato documentado en data/DATASET.md."""


def validar(df: pd.DataFrame) -> list[str]:
    """Devuelve la lista de incumplimientos del contrato. Vacía = dataset válido."""
    errores: list[str] = []

    faltan = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltan:
        return [f"faltan columnas obligatorias: {', '.join(faltan)}"]

    for col in COLUMNAS_REQUERIDAS:
        vacias = df.index[df[col].astype(str).str.strip() == ""].tolist()
        if vacias:
            errores.append(f"columna '{col}' vacía en las filas {vacias}")

    duplicados = df["id"][df["id"].duplicated()].tolist()
    if duplicados:
        errores.append(f"ids duplicados: {duplicados}")

    tipos_malos = sorted(set(df["tipo_fallo"]) - set(TIPOS))
    if tipos_malos:
        errores.append(f"tipo_fallo fuera de la taxonomía {TIPOS}: {tipos_malos}")

    severidad = pd.to_numeric(df["severidad"], errors="coerce")
    fuera = df["id"][
        severidad.isna()
        | (severidad < SEVERIDAD_MIN)
        | (severidad > SEVERIDAD_MAX)
        | (severidad != severidad.round())
    ].tolist()
    if fuera:
        errores.append(f"severidad no es un entero {SEVERIDAD_MIN}-{SEVERIDAD_MAX} en: {fuera}")

    fechas = pd.to_datetime(df["fecha"], format="%Y-%m-%d", errors="coerce")
    no_parseables = df["id"][fechas.isna()].tolist()
    if no_parseables:
        errores.append(f"fecha no es YYYY-MM-DD en: {no_parseables}")
    futuras = df["id"][fechas > pd.Timestamp.today().normalize()].tolist()
    if futuras:
        errores.append(f"fecha en el futuro en: {futuras}")

    sin_url = df["id"][~df["url"].astype(str).str.startswith(("http://", "https://"))].tolist()
    if sin_url:
        errores.append(f"url no es una URL absoluta en: {sin_url}")

    return errores


def enriquecer(df: pd.DataFrame) -> pd.DataFrame:
    """Tipos nativos + columnas derivadas que el dashboard usa en todas partes."""
    out = df.copy()
    out["fecha"] = pd.to_datetime(out["fecha"], format="%Y-%m-%d")
    out["severidad"] = pd.to_numeric(out["severidad"]).astype(int)
    out["anio"] = out["fecha"].dt.year
    out["tipo_fallo"] = pd.Categorical(out["tipo_fallo"], categories=TIPOS, ordered=True)
    out["tipo_label"] = out["tipo_fallo"].map(ETIQUETA_TIPO).astype(str)
    return out.sort_values("fecha").reset_index(drop=True)


def load_incidents(path: str | Path = DATA_PATH) -> pd.DataFrame:
    """Carga el CSV, valida el contrato y devuelve el DataFrame enriquecido."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    errores = validar(df)
    if errores:
        raise DatasetError("dataset inválido:\n- " + "\n- ".join(errores))
    return enriquecer(df)
