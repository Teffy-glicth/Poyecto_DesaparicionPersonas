import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
ENTRADA = BASE_DIR / "data" / "processed" / "dataset_tratado.csv"
SALIDA_DIR = BASE_DIR / "etapa6" / "datos"
SALIDA_SUPERVISADO = SALIDA_DIR / "supervisado_ml_2007_2025.csv"
SALIDA_CLUSTERING = SALIDA_DIR / "clustering_municipios.csv"
SALIDA_RESUMEN = SALIDA_DIR / "preparacion_resumen.json"

ANIO_INICIO = 2007
ANIO_FIN = 2025
MIN_CASOS_MUNICIPIO = 30

FUENTE_ML = "Medicina Legal (SIRDEC)"
FUENTE_SIEVCAC = "SIEVCAC (CNMH)"

ZONAS = {
    "Cabecera municipal": "Cabecera municipal",
    "Centro poblado (corregimiento, inspección de policía y caserío)": "Centro poblado",
    "Parte rural (vereda y campo)": "Rural",
    "Sin información": "Sin informacion",
}
ZONAS_RURALES = {"Centro poblado", "Rural"}

CLASIFICACIONES = {
    "Desaparicion forzada (presunta)": "Forzada presunta",
    "Sin informacion": "Sin informacion",
}


def cargar():
    df = pd.read_csv(ENTRADA, encoding="utf-8-sig", low_memory=False)
    return df[df["unidad_de_analisis"] == "persona"].copy()


def codigo_dane(serie):
    return pd.to_numeric(serie, errors="coerce").astype("Int64").astype("string").str.zfill(5)


def filtrar_periodo(df):
    return df[df["anio"].between(ANIO_INICIO, ANIO_FIN)].copy()


def preparar_medicina_legal(personas):
    ml = filtrar_periodo(personas[personas["fuente"] == FUENTE_ML])
    ml["zona"] = ml["detalle"].map(ZONAS).fillna("Sin informacion")
    ml["clasificacion"] = ml["tipo_evento"].map(CLASIFICACIONES).fillna("Sin informacion")
    ml["departamento"] = ml["departamento"].replace({"Sin Información": "Sin informacion"})
    ml["codigo_municipio"] = codigo_dane(ml["codigo_dane_municipio"])
    ml["anio"] = ml["anio"].astype(int)
    ml["mes"] = ml["mes"].astype("Int64")
    return ml


def construir_supervisado(ml):
    columnas = ["id_registro", "sexo", "departamento", "zona", "clasificacion", "anio", "mes", "estado_victima"]
    return ml[columnas].reset_index(drop=True)


def construir_clustering(ml, personas):
    sievcac = filtrar_periodo(personas[personas["fuente"] == FUENTE_SIEVCAC])
    sievcac["codigo_municipio"] = codigo_dane(sievcac["codigo_dane_municipio"])

    base = ml.dropna(subset=["codigo_municipio"])
    base = base[~base["codigo_municipio"].str.endswith("999")].copy()
    base["es_mujer"] = (base["sexo"] == "Mujer").astype(int)
    base["es_rural"] = base["zona"].isin(ZONAS_RURALES).astype(int)
    base["es_forzada"] = (base["clasificacion"] == "Forzada presunta").astype(int)
    base["es_post2016"] = (base["anio"] > 2016).astype(int)
    base["sigue_desaparecida"] = (base["estado_victima"] == "Desaparecido").astype(int)
    base["aparecio_con_vida"] = (base["estado_victima"] == "Aparecido con vida").astype(int)
    base["aparecio_sin_vida"] = (base["estado_victima"] == "Aparecido sin vida").astype(int)

    nombres = (
        base.groupby("codigo_municipio")[["municipio", "departamento"]]
        .agg(lambda s: s.value_counts().index[0])
    )
    indicadores = base.groupby("codigo_municipio").agg(
        casos_ml=("id_registro", "size"),
        pct_mujer=("es_mujer", "mean"),
        pct_rural=("es_rural", "mean"),
        pct_forzada_presunta=("es_forzada", "mean"),
        pct_post2016=("es_post2016", "mean"),
        pct_sigue_desaparecida=("sigue_desaparecida", "mean"),
        pct_aparecio_con_vida=("aparecio_con_vida", "mean"),
        pct_aparecio_sin_vida=("aparecio_sin_vida", "mean"),
    )

    conflicto = sievcac.groupby("codigo_municipio").agg(
        casos_sievcac=("id_registro", "size"),
        latitud=("latitud", "mean"),
        longitud=("longitud", "mean"),
    )

    municipios = nombres.join(indicadores).join(conflicto, how="left")
    municipios["casos_sievcac"] = municipios["casos_sievcac"].fillna(0).astype(int)
    municipios = municipios[municipios["casos_ml"] >= MIN_CASOS_MUNICIPIO].copy()
    municipios["log_casos"] = np.log1p(municipios["casos_ml"])
    municipios["pct_conflicto"] = municipios["casos_sievcac"] / (
        municipios["casos_sievcac"] + municipios["casos_ml"]
    )

    porcentajes = [c for c in municipios.columns if c.startswith("pct_")]
    municipios[porcentajes] = municipios[porcentajes].round(4)
    municipios["log_casos"] = municipios["log_casos"].round(4)

    orden = [
        "municipio",
        "departamento",
        "log_casos",
        "pct_mujer",
        "pct_rural",
        "pct_forzada_presunta",
        "pct_post2016",
        "pct_conflicto",
        "casos_ml",
        "casos_sievcac",
        "pct_sigue_desaparecida",
        "pct_aparecio_con_vida",
        "pct_aparecio_sin_vida",
        "latitud",
        "longitud",
    ]
    return municipios[orden].reset_index()


def resumir(personas, supervisado, municipios):
    ml_total = int((personas["fuente"] == FUENTE_ML).sum())
    return {
        "periodo": [ANIO_INICIO, ANIO_FIN],
        "supervisado": {
            "archivo": SALIDA_SUPERVISADO.name,
            "registros_medicina_legal_total": ml_total,
            "registros_en_periodo": int(len(supervisado)),
            "excluidos_fuera_de_periodo_o_sin_anio": ml_total - int(len(supervisado)),
            "variable_objetivo": "estado_victima",
            "predictoras": ["sexo", "departamento", "zona", "clasificacion", "anio", "mes"],
            "distribucion_objetivo": supervisado["estado_victima"].value_counts().to_dict(),
            "distribucion_objetivo_pct": supervisado["estado_victima"]
            .value_counts(normalize=True)
            .mul(100)
            .round(2)
            .to_dict(),
            "mes_faltante": int(supervisado["mes"].isna().sum()),
        },
        "clustering": {
            "archivo": SALIDA_CLUSTERING.name,
            "unidad": "municipio (codigo DANE)",
            "minimo_casos_ml": MIN_CASOS_MUNICIPIO,
            "excluidos": "codigos DANE terminados en 999 (municipio sin informacion) y casos en el extranjero",
            "municipios": int(len(municipios)),
            "variables_agrupamiento": [
                "log_casos",
                "pct_mujer",
                "pct_rural",
                "pct_forzada_presunta",
                "pct_post2016",
                "pct_conflicto",
            ],
            "variables_descriptivas_meta": [
                "casos_ml",
                "casos_sievcac",
                "pct_sigue_desaparecida",
                "pct_aparecio_con_vida",
                "pct_aparecio_sin_vida",
                "latitud",
                "longitud",
            ],
            "municipios_sin_coordenadas": int(municipios["latitud"].isna().sum()),
        },
    }


def main():
    SALIDA_DIR.mkdir(parents=True, exist_ok=True)
    personas = cargar()
    ml = preparar_medicina_legal(personas)
    supervisado = construir_supervisado(ml)
    municipios = construir_clustering(ml, personas)

    supervisado.to_csv(SALIDA_SUPERVISADO, index=False, encoding="utf-8")
    municipios.to_csv(SALIDA_CLUSTERING, index=False, encoding="utf-8")

    resumen = resumir(personas, supervisado, municipios)
    SALIDA_RESUMEN.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{SALIDA_SUPERVISADO.name}: {len(supervisado)} registros")
    print(f"{SALIDA_CLUSTERING.name}: {len(municipios)} municipios")


if __name__ == "__main__":
    main()
