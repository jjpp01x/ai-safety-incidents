import pandas as pd
import pytest

from aisid.charts import barras_por_tipo, heatmap_anio_tipo, severidad_por_dominio, timeline
from aisid.data import TIPOS, enriquecer, load_incidents
from aisid.metrics import calidad_evidencia, kpis, por_anio_tipo, por_dominio, por_tipo
from aisid.theme import color_tipo


@pytest.fixture(scope="module")
def df():
    return load_incidents()


@pytest.fixture
def vacio(df):
    return df.iloc[0:0]


def test_kpis(df):
    k = kpis(df)
    assert k["incidentes"] == len(df)
    assert 1 <= k["severidad_media"] <= 5
    assert 0 <= k["pct_severidad_alta"] <= 100
    assert k["empresas"] == df["empresa"].nunique()
    assert "–" in str(k["rango"])


def test_kpis_sobre_vacio_no_explota(vacio):
    assert kpis(vacio)["incidentes"] == 0


def test_por_tipo_siempre_devuelve_los_cuatro(df, vacio):
    assert list(por_tipo(df)["tipo_fallo"]) == list(TIPOS)
    assert por_tipo(df)["incidentes"].sum() == len(df)
    assert list(por_tipo(vacio)["incidentes"]) == [0, 0, 0, 0]


def test_por_tipo_severidad_media_coincide(df):
    esperado = df[df["tipo_fallo"] == "seguridad"]["severidad"].mean()
    fila = por_tipo(df).set_index("tipo_fallo").loc["seguridad"]
    assert fila["severidad_media"] == round(esperado, 2)


def test_por_anio_tipo_rellena_anios_sin_incidentes(df):
    tabla = por_anio_tipo(df)
    assert tabla.values.sum() == len(df)
    assert list(tabla.index) == list(range(int(tabla.index.min()), int(tabla.index.max()) + 1))
    assert len(tabla.columns) == 4


def test_por_dominio_ordenado_por_severidad(df):
    d = por_dominio(df)
    assert d["incidentes"].sum() == len(df)
    assert d["severidad_media"].is_monotonic_increasing


def test_calidad_evidencia_suma_cien(df):
    assert calidad_evidencia(df)["incidentes"].sum() == len(df)
    assert abs(calidad_evidencia(df)["pct"].sum() - 100) < 0.5


def test_color_sigue_a_la_entidad_no_al_ranking(df):
    """Un filtro que quita una serie no debe repintar las supervivientes."""
    completo = color_tipo("light")
    filtrado = df[df["tipo_fallo"] != "sesgo"]
    fig = barras_por_tipo(filtrado, "light")
    colores = dict(zip(por_tipo(filtrado).sort_values("incidentes")["tipo_fallo"],
                       fig.data[0].marker.color))
    for tipo, color in colores.items():
        assert color == completo[tipo]


@pytest.mark.parametrize("modo", ["light", "dark"])
@pytest.mark.parametrize(
    "fabrica", [barras_por_tipo, timeline, heatmap_anio_tipo, severidad_por_dominio]
)
def test_los_graficos_se_construyen_en_ambos_modos(df, fabrica, modo):
    fig = fabrica(df, modo)
    assert fig.layout.height > 0
    assert len(fig.data) > 0


@pytest.mark.parametrize(
    "fabrica", [barras_por_tipo, timeline, heatmap_anio_tipo, severidad_por_dominio]
)
def test_los_graficos_toleran_un_filtro_sin_resultados(vacio, fabrica):
    fabrica(vacio, "light")


def test_heatmap_usa_ejes_categoricos_y_etiqueta_cada_celda(df):
    """Sin type='category' Plotly leería los años como una escala numérica."""
    fig = heatmap_anio_tipo(df, "light")
    assert fig.layout.xaxis.type == "category"
    assert fig.layout.yaxis.type == "category"
    tabla = por_anio_tipo(df)
    assert len(fig.layout.annotations) == int((tabla.values > 0).sum())
    # Ancladas por índice de categoría, no por el año como número.
    assert all(0 <= a.x < len(tabla.index) for a in fig.layout.annotations)


def test_timeline_tiene_leyenda_con_dos_o_mas_series(df):
    fig = timeline(df, "light")
    assert fig.layout.showlegend is True
    assert len(fig.data) == 4


def test_enriquecer_no_muta_el_original():
    crudo = pd.DataFrame(
        [{
            "id": "INC-001", "fecha": "2020-01-01", "empresa": "ACME", "sistema": "X",
            "tipo_fallo": "sesgo", "severidad": "3", "pais": "ES", "dominio": "Consumo",
            "evidencia": "Oficial", "estado": "Mitigado", "resumen": "r",
            "fuente": "f", "url": "https://e.org",
        }],
        dtype=str,
    )
    enriquecer(crudo)
    assert not pd.api.types.is_integer_dtype(crudo["severidad"])
    assert not pd.api.types.is_datetime64_any_dtype(crudo["fecha"])
