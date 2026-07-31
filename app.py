"""Dashboard de incidentes de AI safety.

Ejecutar:  streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))  # despliegue sin instalar el paquete

import pandas as pd
import streamlit as st

from aisid.charts import (
    barras_detectabilidad,
    barras_por_tipo,
    heatmap_anio_tipo,
    heatmap_tipo_detectabilidad,
    severidad_por_dominio,
    timeline,
)
from aisid.data import ETIQUETA_TIPO, TIPOS, DatasetError, load_incidents
from aisid.metrics import calidad_evidencia, kpis, por_detectabilidad
from aisid.theme import FUENTE, tema

ROOT = Path(__file__).resolve().parent
CASO = ROOT / "case_studies" / "cadena-de-suministro-openai-huggingface.md"
METODOLOGIA = ROOT / "data" / "DATASET.md"

st.set_page_config(
    page_title="AI Safety Incident Tracker",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def cargar() -> pd.DataFrame:
    return load_incidents()


@st.cache_data
def leer(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def estilos(modo: str) -> None:
    t = tema(modo)
    st.markdown(
        f"""
        <style>
          .stApp {{ background: {t["plane"]}; }}
          header[data-testid="stHeader"] {{ background: transparent; }}
          [data-testid="stToolbar"], [data-testid="stDecoration"],
          [data-testid="stAppDeployButton"], #MainMenu, footer {{ display: none !important; }}
          [data-testid="stSidebar"], [data-testid="stSidebarContent"] {{
            background: {t["surface"]};
          }}
          [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
          [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stCaption {{
            color: {t["ink_secondary"]} !important;
          }}
          [data-testid="stSidebar"] [data-baseweb="select"] > div,
          [data-testid="stSidebar"] [data-baseweb="input"] {{
            background: {t["surface"]}; border-color: {t["grid"]}; color: {t["ink"]};
          }}
          [data-testid="stSidebar"] [data-baseweb="select"] div {{ color: {t["ink"]}; }}
          html, body, [class*="css"], .stMarkdown, p, li {{
            font-family: {FUENTE}; color: {t["ink_secondary"]};
          }}
          h1, h2, h3, h4, strong {{ color: {t["ink"]}; letter-spacing: -0.01em; }}
          h1 {{ font-size: 1.75rem; font-weight: 650; margin-bottom: .1rem; }}
          section[data-testid="stSidebar"] {{
            background: {t["surface"]}; border-right: 1px solid {t["grid"]};
          }}
          .tile {{
            background: {t["surface"]}; border: 1px solid {t["grid"]};
            border-radius: 10px; padding: 14px 16px; height: 100%; min-height: 116px;
          }}
          .tile .k {{
            font-size: 0.72rem; text-transform: uppercase; letter-spacing: .07em;
            color: {t["muted"]}; margin-bottom: 6px;
          }}
          .tile .v {{
            font-size: 1.55rem; font-weight: 640; color: {t["ink"]}; white-space: nowrap;
            font-variant-numeric: tabular-nums; line-height: 1.1;
          }}
          .tile .s {{ font-size: 0.78rem; color: {t["muted"]}; margin-top: 4px; }}
          .card {{
            background: {t["surface"]}; border: 1px solid {t["grid"]};
            border-radius: 10px; padding: 14px 16px 4px 16px; margin-bottom: 10px;
          }}
          .card h4 {{ margin: 0 0 2px 0; font-size: 0.95rem; font-weight: 620; }}
          .card .sub {{ font-size: 0.8rem; color: {t["muted"]}; margin-bottom: 8px; }}
          .stTabs [data-baseweb="tab-list"] {{ gap: 22px; border-bottom: 1px solid {t["grid"]}; }}
          .stTabs [data-baseweb="tab"] {{ padding: 6px 0; color: {t["muted"]}; }}
          .stTabs [aria-selected="true"] {{ color: {t["ink"]} !important; }}
          .lede {{ color: {t["muted"]}; font-size: 0.92rem; margin-bottom: 1.1rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def tile(col, clave: str, valor: object, sub: str = "") -> None:
    col.markdown(
        f'<div class="tile"><div class="k">{clave}</div>'
        f'<div class="v">{valor}</div><div class="s">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def card(titulo: str, sub: str) -> None:
    st.markdown(
        f'<div class="card"><h4>{titulo}</h4><div class="sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


try:
    df = cargar()
except DatasetError as exc:  # el contrato del CSV se rompió: dilo, no lo escondas
    st.error(f"No se pudo cargar el dataset.\n\n```\n{exc}\n```")
    st.stop()

# ---------------------------------------------------------------- filtros
with st.sidebar:
    st.markdown("### Filtros")
    tipos = st.multiselect(
        "Tipo de fallo",
        options=list(TIPOS),
        default=list(TIPOS),
        format_func=lambda t: ETIQUETA_TIPO[t],
        placeholder="Todos",
    )
    anio_min, anio_max = int(df["anio"].min()), int(df["anio"].max())
    rango = st.slider("Periodo", anio_min, anio_max, (anio_min, anio_max))
    sev_min = st.slider("Severidad mínima", 1, 5, 1)
    dominios = st.multiselect(
        "Dominio", options=sorted(df["dominio"].unique()), default=[], placeholder="Todos"
    )
    st.markdown("---")
    # El tema viaja en la URL (?tema=dark): así un enlace compartido llega como se envió.
    oscuro = st.toggle("Modo oscuro", value=st.query_params.get("tema") == "dark")
    modo = "dark" if oscuro else "light"
    st.query_params["tema"] = modo
    st.caption(
        "Los colores de los 4 tipos de fallo están fijados por entidad: filtrar "
        "no repinta las series que quedan."
    )

estilos(modo)

f = df[
    df["tipo_fallo"].astype(str).isin(tipos)
    & df["anio"].between(*rango)
    & (df["severidad"] >= sev_min)
]
if dominios:
    f = f[f["dominio"].isin(dominios)]

# ---------------------------------------------------------------- cabecera
st.markdown("# AI Safety Incident Tracker")
st.markdown(
    '<div class="lede">Incidentes públicos y documentados de sistemas de IA en producción, '
    "clasificados por modo de fallo y severidad. Cada fila es trazable a una fuente primaria.</div>",
    unsafe_allow_html=True,
)

k = kpis(f)
cols = st.columns(6, gap="small")
tile(cols[0], "Incidentes", k["incidentes"], f"de {len(df)} en el dataset")
tile(cols[1], "Severidad media", f'{k["severidad_media"]:.2f}', "escala 1–5")
tile(cols[2], "Severidad ≥ 4", f'{k["pct_severidad_alta"]:.0f}%', "daño grave o irreversible")
tile(cols[3], "Modo dominante", k["tipo_dominante"], "por nº de incidentes")
tile(cols[4], "Organizaciones", k["empresas"], "públicas y privadas")
tile(cols[5], "Periodo", k["rango"], "años cubiertos")

if f.empty:
    st.warning("Ningún incidente cumple los filtros seleccionados.")
    st.stop()

st.markdown("")
panorama, diligencia, caso, dataset, metodo = st.tabs(
    ["Panorama", "¿Era previsible?", "Caso en profundidad", "Dataset", "Metodología"]
)

# ---------------------------------------------------------------- panorama
with panorama:
    izq, der = st.columns([1, 1], gap="medium")
    with izq:
        card("Incidentes por modo de fallo", "Recuento y severidad media de cada categoría")
        st.plotly_chart(barras_por_tipo(f, modo), use_container_width=True,
                        config={"displayModeBar": False})
    with der:
        card("Severidad media por dominio de aplicación",
             "Dónde duele más, no dónde hay más — entre paréntesis, el nº de incidentes")
        st.plotly_chart(severidad_por_dominio(f, modo), use_container_width=True,
                        config={"displayModeBar": False})

    card("Línea temporal", "Cada punto es un incidente; el eje vertical es su severidad (1–5)")
    st.plotly_chart(timeline(f, modo), use_container_width=True,
                    config={"displayModeBar": False})

    card("Densidad por año y modo de fallo", "Cuántos incidentes de cada tipo por año")
    st.plotly_chart(heatmap_anio_tipo(f, modo), use_container_width=True,
                    config={"displayModeBar": False})

    ev = calidad_evidencia(f)
    st.caption(
        "Calidad de la evidencia: "
        + " · ".join(f"{r.evidencia} {r.pct:.0f}%" for r in ev.itertuples())
    )

# ------------------------------------------------------------- diligencia
with diligencia:
    d = por_detectabilidad(f)
    previsibles = d.loc[d["detectable_dd"] != "no", "incidentes"].sum()
    pct = 100 * previsibles / len(f)

    st.markdown(
        f"### {pct:.0f} % de estos incidentes eran total o parcialmente previsibles\n\n"
        "La pregunta que convierte un registro de incidentes en un instrumento de "
        "inversor no es *qué salió mal*, sino **cuánto de esto se habría visto venir** "
        "con controles que ya existían en el momento del despliegue. Cada fila del "
        "dataset lleva, además del veredicto, el control concreto que lo habría "
        "detectado: sin nombrar el control, la respuesta sería una opinión."
    )

    izq, der = st.columns([1, 1], gap="medium")
    with izq:
        card("Detectabilidad en revisión previa", "Recuento y porcentaje sobre el filtro activo")
        st.plotly_chart(barras_detectabilidad(f, modo), use_container_width=True,
                        config={"displayModeBar": False})
    with der:
        card("Modo de fallo × detectabilidad", "Qué clase de fallo se anticipa y cuál no")
        st.plotly_chart(heatmap_tipo_detectabilidad(f, modo), use_container_width=True,
                        config={"displayModeBar": False})

    card("El control que lo habría anticipado", "Una fila por incidente, con su veredicto")
    st.dataframe(
        f[["id", "empresa", "sistema", "tipo_label", "detectable_label", "control_dd"]].rename(
            columns={"tipo_label": "tipo_fallo", "detectable_label": "¿previsible?",
                     "control_dd": "control que lo habría detectado"}
        ),
        use_container_width=True,
        hide_index=True,
        height=420,
    )

    st.caption(
        "Límite declarado: esta columna es la única del dataset que es un juicio y no "
        "un hecho comprobable. Se emite con conocimiento del desenlace, que es "
        "precisamente la información que no tiene quien hace la revisión previa — "
        "el porcentaje es por tanto un techo optimista, no una estimación."
    )

# ---------------------------------------------------------------- caso
with caso:
    st.markdown(leer(CASO))

# ---------------------------------------------------------------- dataset
with dataset:
    card("Registros", "Vista de tabla del dataset filtrado — el gráfico nunca es la única lectura")
    tabla = f[[
        "id", "fecha", "empresa", "sistema", "tipo_label", "severidad",
        "dominio", "pais", "estado", "evidencia", "fuente", "url",
    ]].rename(columns={"tipo_label": "tipo_fallo"})
    st.dataframe(
        tabla,
        use_container_width=True,
        hide_index=True,
        height=560,
        column_config={
            "fecha": st.column_config.DateColumn("fecha", format="YYYY-MM-DD"),
            "severidad": st.column_config.ProgressColumn(
                "severidad", min_value=0, max_value=5, format="%d"
            ),
            "url": st.column_config.LinkColumn("fuente (URL)", display_text="abrir"),
        },
    )
    st.download_button(
        "Descargar selección en CSV",
        tabla.to_csv(index=False).encode("utf-8"),
        file_name="ai_safety_incidents_seleccion.csv",
        mime="text/csv",
    )
    with st.expander("Ver resúmenes"):
        for r in f.sort_values("fecha", ascending=False).itertuples():
            st.markdown(
                f"**{r.fecha:%Y-%m-%d} · {r.empresa} — {r.sistema}**  \n"
                f"`{r.tipo_label}` · severidad {r.severidad}/5 · {r.estado}  \n"
                f"{r.resumen} [{r.fuente}]({r.url})"
            )

# ---------------------------------------------------------------- metodología
with metodo:
    st.markdown(leer(METODOLOGIA))
