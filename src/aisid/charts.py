"""Figuras Plotly del dashboard.

Reglas aplicadas en todas ellas: un solo eje de valor por gráfico, leyenda
presente cuando hay 2+ series, etiquetas directas en lugar de un número sobre
cada punto, rejilla recesiva y tooltip en todas las marcas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .data import ETIQUETA_TIPO
from .metrics import (
    detectabilidad_por_tipo,
    por_anio_tipo,
    por_detectabilidad,
    por_dominio,
    por_tipo,
)
from .theme import FUENTE, SECUENCIAL, color_tipo, tema

_HOVER = "%{hovertext}<extra></extra>"


def _base(fig: go.Figure, modo: str, alto: int = 320, leyenda: bool = False) -> go.Figure:
    t = tema(modo)
    fig.update_layout(
        height=alto,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor=t["surface"],
        plot_bgcolor=t["surface"],
        font=dict(family=FUENTE, size=13, color=t["ink_secondary"]),
        hoverlabel=dict(
            bgcolor=t["surface"],
            bordercolor=t["axis"],
            font=dict(family=FUENTE, size=12, color=t["ink"]),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            title=None,
            font=dict(color=t["ink_secondary"]),
        ),
        showlegend=leyenda,
    )
    fig.update_xaxes(
        showgrid=False, zeroline=False, linecolor=t["axis"], tickcolor=t["axis"],
        tickfont=dict(color=t["muted"]), title=None,
    )
    fig.update_yaxes(
        gridcolor=t["grid"], zeroline=False, linecolor=t["axis"], tickcolor=t["axis"],
        tickfont=dict(color=t["muted"]), title=None,
    )
    return fig


def barras_por_tipo(df: pd.DataFrame, modo: str = "light") -> go.Figure:
    """Magnitud por categoría: barras horizontales, ordenadas, con etiqueta directa."""
    t = tema(modo)
    d = por_tipo(df).sort_values("incidentes")
    colores = color_tipo(modo)
    fig = go.Figure(
        go.Bar(
            x=d["incidentes"],
            y=d["tipo_label"],
            orientation="h",
            marker=dict(color=[colores[k] for k in d["tipo_fallo"]], line=dict(width=0)),
            width=0.55,
            text=[
                f"{int(n)}  ·  sev. media {s:.1f}"
                for n, s in zip(d["incidentes"], d["severidad_media"])
            ],
            textposition="outside",
            textfont=dict(color=t["ink_secondary"], size=12),
            hovertext=[
                f"<b>{lab}</b><br>{int(n)} incidentes<br>Severidad media: {s:.2f}"
                for lab, n, s in zip(d["tipo_label"], d["incidentes"], d["severidad_media"])
            ],
            hovertemplate=_HOVER,
            cliponaxis=False,
        )
    )
    fig.update_xaxes(showticklabels=False, showline=False, ticks="")
    fig.update_yaxes(showgrid=False, tickfont=dict(color=t["ink"], size=13))
    fig.update_layout(xaxis=dict(range=[0, max(1, d["incidentes"].max()) * 1.75]))
    return _base(fig, modo, alto=280)


def timeline(df: pd.DataFrame, modo: str = "light") -> go.Figure:
    """Cada incidente en el tiempo contra su severidad. Color = tipo, con leyenda."""
    t = tema(modo)
    colores = color_tipo(modo)
    fig = go.Figure()
    for tipo, etiqueta in ETIQUETA_TIPO.items():
        sub = df[df["tipo_fallo"] == tipo]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=sub["fecha"],
                y=sub["severidad"],
                mode="markers",
                name=etiqueta,
                marker=dict(
                    size=13,
                    color=colores[tipo],
                    line=dict(width=2, color=t["surface"]),
                    opacity=0.95,
                ),
                hovertext=[
                    f"<b>{e} — {s}</b><br>{f:%d %b %Y} · severidad {sev}/5<br>{etiqueta}"
                    for e, s, f, sev in zip(
                        sub["empresa"], sub["sistema"], sub["fecha"], sub["severidad"]
                    )
                ],
                hovertemplate=_HOVER,
            )
        )
    fig.update_yaxes(range=[0.5, 5.5], dtick=1, title=None)
    fig.update_layout(hovermode="closest")
    return _base(fig, modo, alto=340, leyenda=True)


def heatmap_anio_tipo(df: pd.DataFrame, modo: str = "light") -> go.Figure:
    """Densidad año × tipo. Magnitud = una sola tinta, claro a oscuro."""
    t = tema(modo)
    tabla = por_anio_tipo(df)
    if tabla.empty:
        return _base(go.Figure(), modo, alto=300)
    z = tabla.T.values
    # Los ceros van como hueco, no como el paso más claro de la rampa: "no pasó
    # nada" y "pasó poco" no deben parecerse.
    z_pintado = np.where(z == 0, np.nan, z)
    fig = go.Figure(
        go.Heatmap(
            z=z_pintado,
            x=[str(a) for a in tabla.index],
            y=list(tabla.columns),
            colorscale=[[i / (len(SECUENCIAL) - 1), c] for i, c in enumerate(SECUENCIAL)],
            zmin=0,
            xgap=2,
            ygap=2,
            showscale=False,
            hovertext=[
                [
                    f"<b>{col}</b><br>{anio}: {int(v)} incidente{'s' if v != 1 else ''}"
                    for anio, v in zip(tabla.index, fila)
                ]
                for col, fila in zip(tabla.columns, z)
            ],
            hovertemplate=_HOVER,
        )
    )
    # Etiqueta directa dentro de la celda; en las celdas oscuras, tinta invertida.
    umbral = max(1, z.max()) * 0.6
    # En un eje categórico la anotación se ancla por índice: pasar "2016" como
    # texto haría que Plotly lo leyera como la coordenada numérica 2016.
    for i, fila in enumerate(z):
        for j, v in enumerate(fila):
            if v == 0:
                continue
            fig.add_annotation(
                x=j, y=i, text=str(int(v)), showarrow=False,
                font=dict(family=FUENTE, size=12, color="#ffffff" if v >= umbral else t["ink"]),
            )
    # Años y tipos son categorías: sin type="category" Plotly lee "2015" como número.
    fig.update_xaxes(
        type="category", showgrid=False, showline=False, ticks="",
        tickfont=dict(color=t["muted"]),
    )
    fig.update_yaxes(
        type="category", showgrid=False, showline=False, ticks="",
        tickfont=dict(color=t["ink"]),
    )
    return _base(fig, modo, alto=300)


def severidad_por_dominio(df: pd.DataFrame, modo: str = "light") -> go.Figure:
    """Severidad media por dominio de aplicación: una magnitud, una sola tinta."""
    t = tema(modo)
    d = por_dominio(df)
    if d.empty:
        return _base(go.Figure(), modo, alto=300)
    tinta = SECUENCIAL[4] if modo == "light" else SECUENCIAL[3]
    fig = go.Figure(
        go.Bar(
            x=d["severidad_media"],
            y=d["dominio"],
            orientation="h",
            marker=dict(color=tinta, line=dict(width=0)),
            width=0.5,
            text=[f"{s:.1f}  ({int(n)})" for s, n in zip(d["severidad_media"], d["incidentes"])],
            textposition="outside",
            textfont=dict(color=t["ink_secondary"], size=12),
            hovertext=[
                f"<b>{dom}</b><br>Severidad media: {s:.2f}<br>{int(n)} incidentes"
                for dom, s, n in zip(d["dominio"], d["severidad_media"], d["incidentes"])
            ],
            hovertemplate=_HOVER,
            cliponaxis=False,
        )
    )
    fig.update_xaxes(showticklabels=False, showline=False, ticks="", range=[0, 6.4])
    fig.update_yaxes(showgrid=False, tickfont=dict(color=t["ink"], size=13))
    # La marca no engorda al filtrar: la altura sigue al nº de categorías, no al revés.
    return _base(fig, modo, alto=max(140, min(300, 42 * len(d) + 40)))


def barras_detectabilidad(df: pd.DataFrame, modo: str = "light") -> go.Figure:
    """Cuánto del daño registrado era previsible.

    Una sola serie, ordenada por la escala natural de la variable (sí → no) en
    lugar de por magnitud: aquí el orden ES la lectura, y reordenar por tamaño
    destruiría la progresión que hace legible el gráfico.
    """
    t = tema(modo)
    d = por_detectabilidad(df).iloc[::-1]
    escala = [SECUENCIAL[-1], SECUENCIAL[len(SECUENCIAL) // 2], SECUENCIAL[1]]
    fig = go.Figure(
        go.Bar(
            x=d["incidentes"],
            y=d["detectable_label"],
            orientation="h",
            marker=dict(color=escala, line=dict(width=0)),
            width=0.55,
            text=[f"{int(n)}  ·  {p:.0f} %" for n, p in zip(d["incidentes"], d["pct"])],
            textposition="outside",
            textfont=dict(color=t["ink_secondary"], size=12),
            hovertext=[
                f"<b>{lab}</b><br>{int(n)} incidentes ({p:.0f} %)<br>Severidad media: {s:.2f}"
                for lab, n, p, s in zip(
                    d["detectable_label"], d["incidentes"], d["pct"], d["severidad_media"]
                )
            ],
            hovertemplate=_HOVER,
            cliponaxis=False,
        )
    )
    fig.update_xaxes(showticklabels=False, showline=False, ticks="")
    fig.update_yaxes(showgrid=False, tickfont=dict(color=t["ink"], size=13))
    fig.update_layout(xaxis=dict(range=[0, max(1, d["incidentes"].max()) * 1.75]))
    return _base(fig, modo, alto=240)


def heatmap_tipo_detectabilidad(df: pd.DataFrame, modo: str = "light") -> go.Figure:
    """Cruce modo de fallo × detectabilidad: qué clase de fallo se ve venir y cuál no."""
    t = tema(modo)
    tabla = detectabilidad_por_tipo(df)
    z = tabla.to_numpy(dtype=float)
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=list(tabla.columns),
            y=list(tabla.index),
            colorscale=SECUENCIAL,
            showscale=False,
            xgap=3,
            ygap=3,
            text=[[("" if v == 0 else f"{int(v)}") for v in fila] for fila in z],
            texttemplate="%{text}",
            textfont=dict(family=FUENTE, size=13, color=t["ink"]),
            hovertext=[
                [f"<b>{tipo}</b><br>Detectable: {col}<br>{int(v)} incidentes"
                 for col, v in zip(tabla.columns, fila)]
                for tipo, fila in zip(tabla.index, z)
            ],
            hovertemplate=_HOVER,
        )
    )
    fig.update_xaxes(showgrid=False, side="top", tickfont=dict(color=t["ink"], size=12))
    fig.update_yaxes(showgrid=False, autorange="reversed", tickfont=dict(color=t["ink"], size=12))
    return _base(fig, modo, alto=260)
