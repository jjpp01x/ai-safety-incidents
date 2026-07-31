"""Agregaciones del dashboard.

Todo el cálculo vive aquí y no en la capa de UI: así se puede testear sin
levantar Streamlit y reutilizar desde un notebook o un informe.
"""

from __future__ import annotations

import pandas as pd

from .data import DETECTABILIDAD, ETIQUETA_DETECTABILIDAD, ETIQUETA_TIPO, TIPOS

SEVERIDAD_ALTA = 4


def kpis(df: pd.DataFrame) -> dict[str, object]:
    """Cifras de cabecera. Sobre un df vacío devuelve ceros, no explota."""
    if df.empty:
        return {
            "incidentes": 0,
            "severidad_media": 0.0,
            "pct_severidad_alta": 0.0,
            "tipo_dominante": "—",
            "empresas": 0,
            "rango": "—",
        }
    conteo = df["tipo_fallo"].value_counts()
    return {
        "incidentes": int(len(df)),
        "severidad_media": round(float(df["severidad"].mean()), 2),
        "pct_severidad_alta": round(
            100 * float((df["severidad"] >= SEVERIDAD_ALTA).mean()), 1
        ),
        "tipo_dominante": ETIQUETA_TIPO[str(conteo.idxmax())],
        "empresas": int(df["empresa"].nunique()),
        "rango": f"{int(df['anio'].min())}–{int(df['anio'].max())}",
    }


def por_tipo(df: pd.DataFrame) -> pd.DataFrame:
    """Un tipo por fila, siempre los 4, aunque el filtro deje alguno a cero."""
    base = pd.DataFrame({"tipo_fallo": list(TIPOS)})
    if df.empty:
        base["incidentes"] = 0
        base["severidad_media"] = 0.0
    else:
        agg = (
            df.groupby("tipo_fallo", observed=False)
            .agg(incidentes=("id", "count"), severidad_media=("severidad", "mean"))
            .reset_index()
        )
        agg["tipo_fallo"] = agg["tipo_fallo"].astype(str)
        base = base.merge(agg, on="tipo_fallo", how="left").fillna(
            {"incidentes": 0, "severidad_media": 0.0}
        )
    base["incidentes"] = base["incidentes"].astype(int)
    base["severidad_media"] = base["severidad_media"].round(2)
    base["tipo_label"] = base["tipo_fallo"].map(ETIQUETA_TIPO)
    return base


def por_anio_tipo(df: pd.DataFrame) -> pd.DataFrame:
    """Matriz año × tipo con todos los años del rango, incluidos los de cero."""
    if df.empty:
        return pd.DataFrame(columns=[ETIQUETA_TIPO[t] for t in TIPOS])
    tabla = pd.crosstab(df["anio"], df["tipo_fallo"], dropna=False)
    tabla = tabla.reindex(columns=list(TIPOS), fill_value=0)
    tabla = tabla.reindex(range(int(df["anio"].min()), int(df["anio"].max()) + 1), fill_value=0)
    tabla.columns = [ETIQUETA_TIPO[c] for c in tabla.columns]
    tabla.index.name = "anio"
    return tabla


def por_dominio(df: pd.DataFrame) -> pd.DataFrame:
    """Dominios ordenados por severidad media: dónde duele más, no dónde hay más."""
    if df.empty:
        return pd.DataFrame(columns=["dominio", "incidentes", "severidad_media"])
    out = (
        df.groupby("dominio")
        .agg(incidentes=("id", "count"), severidad_media=("severidad", "mean"))
        .reset_index()
        .sort_values(["severidad_media", "incidentes"], ascending=[True, True])
    )
    out["severidad_media"] = out["severidad_media"].round(2)
    return out.reset_index(drop=True)


def calidad_evidencia(df: pd.DataFrame) -> pd.DataFrame:
    """Reparto por tipo de fuente: cuánto del dataset se apoya en documento primario."""
    if df.empty:
        return pd.DataFrame(columns=["evidencia", "incidentes", "pct"])
    out = df["evidencia"].value_counts().rename_axis("evidencia").reset_index(name="incidentes")
    out["pct"] = (100 * out["incidentes"] / len(df)).round(1)
    return out


def por_detectabilidad(df: pd.DataFrame) -> pd.DataFrame:
    """Reparto por detectabilidad en diligencia previa.

    Es la vista que convierte un registro de incidentes en un instrumento de
    inversor: no "qué salió mal", sino "cuánto de esto se habría visto venir".
    """
    base = pd.DataFrame({"detectable_dd": list(DETECTABILIDAD)})
    if df.empty:
        base["incidentes"] = 0
        base["severidad_media"] = 0.0
        base["pct"] = 0.0
    else:
        agg = (
            df.groupby("detectable_dd", observed=False)
            .agg(incidentes=("id", "count"), severidad_media=("severidad", "mean"))
            .reset_index()
        )
        agg["detectable_dd"] = agg["detectable_dd"].astype(str)
        base = base.merge(agg, on="detectable_dd", how="left").fillna(
            {"incidentes": 0, "severidad_media": 0.0}
        )
        base["pct"] = (100 * base["incidentes"] / len(df)).round(1)
    base["incidentes"] = base["incidentes"].astype(int)
    base["severidad_media"] = base["severidad_media"].round(2)
    base["detectable_label"] = base["detectable_dd"].map(ETIQUETA_DETECTABILIDAD)
    return base


def detectabilidad_por_tipo(df: pd.DataFrame) -> pd.DataFrame:
    """Cruce tipo de fallo × detectabilidad: qué modos de fallo se anticipan y cuáles no."""
    if df.empty:
        return pd.DataFrame(columns=[ETIQUETA_DETECTABILIDAD[d] for d in DETECTABILIDAD])
    tabla = pd.crosstab(df["tipo_fallo"], df["detectable_dd"], dropna=False)
    tabla = tabla.reindex(columns=list(DETECTABILIDAD), fill_value=0)
    tabla = tabla.reindex(list(TIPOS), fill_value=0)
    tabla.columns = [ETIQUETA_DETECTABILIDAD[c] for c in tabla.columns]
    tabla.index = [ETIQUETA_TIPO[t] for t in tabla.index]
    tabla.index.name = "tipo_fallo"
    return tabla
