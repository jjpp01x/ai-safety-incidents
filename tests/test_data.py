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
