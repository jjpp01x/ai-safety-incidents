import pandas as pd
import pytest

from aisid.data import COLUMNAS_REQUERIDAS, DatasetError, TIPOS, load_incidents, validar

FILA_OK = {
    "id": "INC-999",
    "fecha": "2020-01-01",
    "empresa": "ACME",
    "sistema": "Modelo X",
    "tipo_fallo": "sesgo",
    "severidad": "3",
    "pais": "EE. UU.",
    "dominio": "Consumo",
    "evidencia": "Oficial",
    "estado": "Mitigado",
    "resumen": "Resumen.",
    "fuente": "Fuente",
    "url": "https://example.org/a",
    "detectable_dd": "si",
    "control_dd": "Evaluación desagregada previa al despliegue",
    "url_archivo": "https://web.archive.org/web/20200101000000/https://example.org/a",
}


def df_de(*filas: dict) -> pd.DataFrame:
    return pd.DataFrame(list(filas), dtype=str)


def test_dataset_real_carga_y_es_valido():
    df = load_incidents()
    assert len(df) >= 15, "el entregable pide una recopilación de 10-15 incidentes como mínimo"
    assert set(COLUMNAS_REQUERIDAS).issubset(df.columns)
    assert set(df["tipo_fallo"].astype(str)) == set(TIPOS), "los 4 tipos deben estar representados"
    assert df["fecha"].is_monotonic_increasing


def test_columnas_derivadas():
    df = load_incidents()
    assert df["severidad"].between(1, 5).all()
    assert (df["anio"] == df["fecha"].dt.year).all()
    assert df["tipo_label"].notna().all()


def test_dataset_valido_no_devuelve_errores():
    assert validar(df_de(FILA_OK)) == []


@pytest.mark.parametrize(
    ("campo", "valor", "fragmento"),
    [
        ("tipo_fallo", "otro", "taxonomía"),
        ("severidad", "9", "severidad"),
        ("severidad", "alta", "severidad"),
        ("fecha", "01/01/2020", "YYYY-MM-DD"),
        ("fecha", "2099-01-01", "futuro"),
        ("url", "example.org", "URL absoluta"),
        ("url_archivo", "https://example.org/copia", "Internet Archive"),
        ("empresa", "", "vacía"),
    ],
)
def test_validar_detecta_filas_corruptas(campo, valor, fragmento):
    errores = validar(df_de({**FILA_OK, campo: valor}))
    assert any(fragmento in e for e in errores), errores


def test_validar_detecta_ids_duplicados():
    errores = validar(df_de(FILA_OK, {**FILA_OK, "url": "https://example.org/b"}))
    assert any("duplicados" in e for e in errores)


def test_validar_detecta_columna_ausente():
    df = df_de(FILA_OK).drop(columns=["fuente"])
    assert any("faltan columnas" in e for e in validar(df))


def test_load_incidents_falla_ruidosamente(tmp_path):
    csv = tmp_path / "malo.csv"
    df_de({**FILA_OK, "severidad": "7"}).to_csv(csv, index=False)
    with pytest.raises(DatasetError, match="severidad"):
        load_incidents(csv)


def test_detectabilidad_forma_parte_del_contrato():
    from aisid.data import COLUMNAS_REQUERIDAS

    assert "detectable_dd" in COLUMNAS_REQUERIDAS
    assert "control_dd" in COLUMNAS_REQUERIDAS


def test_detectabilidad_fuera_de_vocabulario_invalida_el_dataset():
    from aisid.data import DETECTABILIDAD, load_incidents, validar

    df = load_incidents().astype({"detectable_dd": str})
    df.loc[0, "detectable_dd"] = "quiza"

    errores = validar(df)

    assert any("detectable_dd" in e for e in errores)
    assert set(DETECTABILIDAD) == {"si", "parcial", "no"}


def test_url_archivo_es_opcional_pero_debe_ser_de_internet_archive():
    """Una fuente puede no tener copia; lo que no puede es tener una copia falsa."""
    assert validar(df_de({**FILA_OK, "url_archivo": ""})) == []
    errores = validar(df_de({**FILA_OK, "url_archivo": "https://example.org/copia"}))
    assert any("Internet Archive" in e for e in errores)


def test_toda_fuente_es_verificable_a_diez_anos_vista():
    """La trazabilidad no puede depender de que un dominio siga en pie.

    Se cumple de dos formas: con copia en Internet Archive, o citando un
    repositorio cuya permanencia es su función (EDGAR de la SEC), donde una
    copia externa no añade nada.
    """
    from aisid.data import HOSTS_PERMANENTES

    df = load_incidents()
    frágiles = df["id"][
        (df["url_archivo"].astype(str).str.strip() == "")
        & ~df["url"].str.startswith(HOSTS_PERMANENTES)
    ].tolist()
    assert not frágiles, f"sin copia archivada ni repositorio permanente: {frágiles}"


def test_ninguna_fuente_apunta_a_la_raiz_de_un_dominio():
    """Citar la portada de un medio no es citar: el criterio pide el documento."""
    from urllib.parse import urlparse
    df = load_incidents()
    raices = df["id"][df["url"].map(lambda u: urlparse(u).path.strip("/") == "")].tolist()
    assert not raices, f"apuntan a la raíz del dominio: {raices}"
