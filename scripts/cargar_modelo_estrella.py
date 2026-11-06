import json
import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OLAP_SQL_DIR = BASE_DIR / "etl" / "olap"
OLAP_DATA_DIR = BASE_DIR / "data" / "olap"

ENTRADA_CSV = PROCESSED_DIR / "dataset_tratado.csv"
SALIDA_DB = OLAP_DATA_DIR / "modelo_estrella.db"
SALIDA_RESUMEN = OLAP_DATA_DIR / "carga_resumen.json"

FUENTES_INCLUIDAS = ["Medicina Legal (SIRDEC)", "SIEVCAC (CNMH)"]
UNIDAD_INCLUIDA = "persona"

SIN_INFORMACION = "Sin informacion"

DEPARTAMENTOS_SUR = {"Narino", "Cauca", "Putumayo", "Caqueta", "Huila"}

DEPARTAMENTO_CANONICO = {
    "AMAZONAS": "Amazonas",
    "ANTIOQUIA": "Antioquia",
    "ARAUCA": "Arauca",
    "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y SANTA CATALINA": "Archipielago de San Andres, Providencia y Santa Catalina",
    "ATLANTICO": "Atlantico",
    "BOGOTA, D. C.": "Bogota D.C.",
    "BOLIVAR": "Bolivar",
    "BOYACA": "Boyaca",
    "CALDAS": "Caldas",
    "CAQUETA": "Caqueta",
    "CASANARE": "Casanare",
    "CAUCA": "Cauca",
    "CESAR": "Cesar",
    "CHOCO": "Choco",
    "CORDOBA": "Cordoba",
    "CUNDINAMARCA": "Cundinamarca",
    "DESAPARECIDOS EN EL EXTRANJERO": "Desaparecidos en el extranjero",
    "EXTERIOR": "Exterior",
    "GUAINIA": "Guainia",
    "GUAVIARE": "Guaviare",
    "HUILA": "Huila",
    "LA GUAJIRA": "La Guajira",
    "MAGDALENA": "Magdalena",
    "META": "Meta",
    "NARINO": "Narino",
    "NORTE DE SANTANDER": "Norte de Santander",
    "PUTUMAYO": "Putumayo",
    "QUINDIO": "Quindio",
    "RISARALDA": "Risaralda",
    "SANTANDER": "Santander",
    "SIN INFORMACION": SIN_INFORMACION,
    "SUCRE": "Sucre",
    "TOLIMA": "Tolima",
    "VALLE DEL CAUCA": "Valle del Cauca",
    "VAUPES": "Vaupes",
    "VICHADA": "Vichada",
}

ZONA_CANONICO = {
    "CABECERA MUNICIPAL": "Cabecera municipal",
    "PARTE RURAL (VEREDA Y CAMPO)": "Parte rural (vereda y campo)",
    "CENTRO POBLADO (CORREGIMIENTO, INSPECCION DE POLICIA Y CASERIO)": (
        "Centro poblado (corregimiento, inspeccion de policia y caserio)"
    ),
    "SIN INFORMACION": SIN_INFORMACION,
}

CALIDAD_CANONICO = {
    "CIVIL": "Civil",
    "COMBATIENTE": "Combatiente",
    "SIN INFORMACION": SIN_INFORMACION,
}


def _clave_normalizada(valor):
    if pd.isna(valor):
        return None
    texto = str(valor).replace("�", "").upper().strip()
    reemplazos = str.maketrans("ÁÉÍÓÚÑ", "AEIOUN")
    texto = texto.translate(reemplazos)
    texto = " ".join(texto.split())
    return texto


def normalizar_departamento(valor):
    clave = _clave_normalizada(valor)
    if clave is None:
        return SIN_INFORMACION
    return DEPARTAMENTO_CANONICO.get(clave, valor.strip() if isinstance(valor, str) else SIN_INFORMACION)


def normalizar_zona(valor):
    clave = _clave_normalizada(valor)
    if clave is None:
        return SIN_INFORMACION
    return ZONA_CANONICO.get(clave, SIN_INFORMACION)


def normalizar_calidad(valor):
    clave = _clave_normalizada(valor)
    if clave is None:
        return SIN_INFORMACION
    return CALIDAD_CANONICO.get(clave, SIN_INFORMACION)


def normalizar_municipio(valor):
    if pd.isna(valor):
        return SIN_INFORMACION
    texto = str(valor).replace("�", "").strip()
    if not texto or _clave_normalizada(texto) == "SIN INFORMACION":
        return SIN_INFORMACION
    return texto.title()


def normalizar_sexo(valor):
    if not isinstance(valor, str) or not valor.strip():
        return SIN_INFORMACION
    texto = valor.strip()
    if _clave_normalizada(texto) == "SIN INFORMACION":
        return SIN_INFORMACION
    return texto.title()


def macro_region_de(departamento):
    return "Sur" if departamento in DEPARTAMENTOS_SUR else "Resto"


def codigo_dane(valor):
    if pd.isna(valor):
        return None
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto or None


NOMBRES_MES = [
    None, "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def periodo_acuerdo_de(anio):
    if anio is None:
        return SIN_INFORMACION
    anio = int(anio)
    if 2007 <= anio <= 2016:
        return "Antes (2007-2016)"
    if 2017 <= anio <= 2025:
        return "Despues (2017-2025)"
    return "Fuera de rango comparable"


def construir_dim_tiempo(df):
    filas = [{
        "id_tiempo": 0, "anio": None, "semestre": None, "trimestre": None,
        "mes": None, "nombre_mes": None, "periodo_acuerdo": SIN_INFORMACION,
    }]

    con_mes = df.loc[df["anio"].notna() & df["mes"].notna(), ["anio", "mes"]].drop_duplicates()
    for anio, mes in con_mes.itertuples(index=False):
        anio, mes = int(anio), int(mes)
        trimestre = (mes - 1) // 3 + 1
        filas.append({
            "id_tiempo": anio * 100 + mes,
            "anio": anio,
            "semestre": 1 if mes <= 6 else 2,
            "trimestre": trimestre,
            "mes": mes,
            "nombre_mes": NOMBRES_MES[mes],
            "periodo_acuerdo": periodo_acuerdo_de(anio),
        })

    sin_mes = df.loc[df["anio"].notna() & df["mes"].isna(), "anio"].drop_duplicates()
    for anio in sin_mes:
        anio = int(anio)
        filas.append({
            "id_tiempo": anio * 100,
            "anio": anio,
            "semestre": None,
            "trimestre": None,
            "mes": None,
            "nombre_mes": "Mes desconocido",
            "periodo_acuerdo": periodo_acuerdo_de(anio),
        })

    dim = pd.DataFrame(filas).drop_duplicates(subset="id_tiempo").reset_index(drop=True)
    return dim


def id_tiempo_de(anio, mes):
    if pd.isna(anio):
        return 0
    if pd.isna(mes):
        return int(anio) * 100
    return int(anio) * 100 + int(mes)


def construir_dim_geografia(df):
    tmp = pd.DataFrame({
        "departamento": df["departamento"].apply(normalizar_departamento),
        "municipio": df["municipio"].apply(normalizar_municipio),
        "codigo_dane_departamento": df["codigo_dane_departamento"].apply(codigo_dane),
        "codigo_dane_municipio": df["codigo_dane_municipio"].apply(codigo_dane),
    })
    combinaciones = tmp.drop_duplicates(subset=["departamento", "municipio"]).copy()
    es_doble_sin_info = (combinaciones["departamento"] == SIN_INFORMACION) & (
        combinaciones["municipio"] == SIN_INFORMACION
    )
    combinaciones = combinaciones.loc[~es_doble_sin_info].copy()
    combinaciones["macro_region"] = combinaciones["departamento"].apply(macro_region_de)
    combinaciones = combinaciones.sort_values(["departamento", "municipio"]).reset_index(drop=True)
    combinaciones.insert(0, "id_geografia", range(1, len(combinaciones) + 1))

    sin_info = pd.DataFrame([{
        "id_geografia": 0, "macro_region": SIN_INFORMACION,
        "codigo_dane_departamento": None, "departamento": SIN_INFORMACION,
        "codigo_dane_municipio": None, "municipio": SIN_INFORMACION,
    }])
    dim = pd.concat([sin_info, combinaciones], ignore_index=True)
    return dim[[
        "id_geografia", "macro_region", "codigo_dane_departamento",
        "departamento", "codigo_dane_municipio", "municipio",
    ]]


def construir_dim_simple(valores_unicos, columna, id_columna, incluir_sin_info=True):
    valores = sorted(v for v in valores_unicos if v and v != SIN_INFORMACION)
    filas = []
    if incluir_sin_info:
        filas.append({id_columna: 0, columna: SIN_INFORMACION})
    for i, valor in enumerate(valores, start=1):
        filas.append({id_columna: i, columna: valor})
    return pd.DataFrame(filas)


def construir_dim_zona(df):
    zonas = df.loc[df["fuente"] == "Medicina Legal (SIRDEC)", "detalle"].apply(normalizar_zona)
    return construir_dim_simple(zonas.unique(), "zona_hecho", "id_zona")


def construir_dim_victima(df):
    sexo = df["sexo"].apply(normalizar_sexo)
    calidad = pd.Series(SIN_INFORMACION, index=df.index)
    es_sievcac = df["fuente"] == "SIEVCAC (CNMH)"
    calidad.loc[es_sievcac] = df.loc[es_sievcac, "detalle"].apply(normalizar_calidad)

    combinaciones = pd.DataFrame({"sexo": sexo, "calidad_victima": calidad}).drop_duplicates()
    combinaciones = combinaciones.sort_values(["sexo", "calidad_victima"]).reset_index(drop=True)
    combinaciones.insert(0, "id_victima", range(1, len(combinaciones) + 1))
    return combinaciones


ESTADO_GRUPO = {
    "Desaparecido": "Sin resolver",
    "Aparecido con vida": "Resuelto",
    "Aparecido sin vida": "Resuelto",
}


def construir_dim_estado(df):
    estados = sorted(df["estado_victima"].dropna().unique())
    filas = [{"id_estado": 0, "estado_victima": SIN_INFORMACION, "grupo_desenlace": SIN_INFORMACION}]
    filas += [{"id_estado": i, "estado_victima": e, "grupo_desenlace": ESTADO_GRUPO.get(e, SIN_INFORMACION)}
              for i, e in enumerate(estados, start=1)]
    return pd.DataFrame(filas)[["id_estado", "grupo_desenlace", "estado_victima"]]


def construir_dim_fuente(df):
    combinaciones = (
        df[["fuente", "tipo_evento", "nivel_fuente"]]
        .fillna(SIN_INFORMACION)
        .drop_duplicates()
        .sort_values(["fuente", "tipo_evento"])
        .reset_index(drop=True)
    )
    combinaciones.insert(0, "id_fuente", range(1, len(combinaciones) + 1))
    sin_info = pd.DataFrame([{
        "id_fuente": 0, "fuente": SIN_INFORMACION,
        "tipo_evento": SIN_INFORMACION, "nivel_fuente": SIN_INFORMACION,
    }])
    return pd.concat([sin_info, combinaciones], ignore_index=True)


def construir_fact(df, dim_geografia, dim_zona, dim_victima, dim_estado, dim_fuente):
    geo_key = pd.DataFrame({
        "departamento": df["departamento"].apply(normalizar_departamento),
        "municipio": df["municipio"].apply(normalizar_municipio),
    })
    geo_lookup = dim_geografia.set_index(["departamento", "municipio"])["id_geografia"]
    id_geografia = geo_key.set_index(["departamento", "municipio"]).index.map(geo_lookup).fillna(0).astype(int)

    zona_valor = pd.Series(SIN_INFORMACION, index=df.index)
    es_ml = df["fuente"] == "Medicina Legal (SIRDEC)"
    zona_valor.loc[es_ml] = df.loc[es_ml, "detalle"].apply(normalizar_zona)
    zona_lookup = dim_zona.set_index("zona_hecho")["id_zona"]
    id_zona = zona_valor.map(zona_lookup).fillna(0).astype(int)

    sexo = df["sexo"].apply(normalizar_sexo)
    calidad = pd.Series(SIN_INFORMACION, index=df.index)
    es_sievcac = df["fuente"] == "SIEVCAC (CNMH)"
    calidad.loc[es_sievcac] = df.loc[es_sievcac, "detalle"].apply(normalizar_calidad)
    victima_lookup = dim_victima.set_index(["sexo", "calidad_victima"])["id_victima"]
    victima_key = pd.DataFrame({"sexo": sexo, "calidad_victima": calidad})
    id_victima = victima_key.set_index(["sexo", "calidad_victima"]).index.map(victima_lookup).fillna(0).astype(int)

    estado_lookup = dim_estado.set_index("estado_victima")["id_estado"]
    id_estado = df["estado_victima"].map(estado_lookup).fillna(0).astype(int)

    fuente_key = df[["fuente", "tipo_evento", "nivel_fuente"]].fillna(SIN_INFORMACION)
    fuente_lookup = dim_fuente.set_index(["fuente", "tipo_evento"])["id_fuente"]
    id_fuente = fuente_key.set_index(["fuente", "tipo_evento"]).index.map(fuente_lookup).fillna(0).astype(int)

    id_tiempo = [id_tiempo_de(a, m) for a, m in zip(df["anio"], df["mes"])]

    fact = pd.DataFrame({
        "id_registro": df["id_registro"],
        "id_tiempo": id_tiempo,
        "id_geografia": id_geografia.values,
        "id_zona": id_zona.values,
        "id_victima": id_victima.values,
        "id_estado": id_estado.values,
        "id_fuente": id_fuente.values,
        "num_personas": 1,
        "flag_sigue_desaparecida": (df["estado_victima"] == "Desaparecido").astype(int),
        "flag_aparecio_viva": (df["estado_victima"] == "Aparecido con vida").astype(int),
        "flag_aparecio_sin_vida": (df["estado_victima"] == "Aparecido sin vida").astype(int),
    })
    return fact


def ejecutar_script_sql(conexion, ruta):
    sql = ruta.read_text(encoding="utf-8")
    conexion.executescript(sql)


def main():
    if not ENTRADA_CSV.exists():
        raise SystemExit(
            f"Falta {ENTRADA_CSV}. Ejecuta 'python scripts/aplicar_tratamiento.py' primero."
        )

    print(f"Leyendo {ENTRADA_CSV} ...")
    df = pd.read_csv(ENTRADA_CSV, low_memory=False)

    df = df[
        df["fuente"].isin(FUENTES_INCLUIDAS) & (df["unidad_de_analisis"] == UNIDAD_INCLUIDA)
    ].copy()
    print(f"Registros filtrados (Medicina Legal + SIEVCAC, unidad=persona): {len(df):,}")

    dim_tiempo = construir_dim_tiempo(df)
    dim_geografia = construir_dim_geografia(df)
    dim_zona = construir_dim_zona(df)
    dim_victima = construir_dim_victima(df)
    dim_estado = construir_dim_estado(df)
    dim_fuente = construir_dim_fuente(df)

    fact = construir_fact(df, dim_geografia, dim_zona, dim_victima, dim_estado, dim_fuente)

    assert fact["id_registro"].is_unique, "id_registro no es unico en fact_desaparicion"
    assert len(fact) == len(df), "La carga cambio el numero de filas (rompe la granularidad)"

    OLAP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SALIDA_DB.exists():
        SALIDA_DB.unlink()

    print(f"Creando esquema en {SALIDA_DB} ...")
    conexion = sqlite3.connect(SALIDA_DB)
    try:
        ejecutar_script_sql(conexion, OLAP_SQL_DIR / "01_crear_modelo.sql")
        ejecutar_script_sql(conexion, OLAP_SQL_DIR / "02_indices.sql")

        print("Cargando dimensiones y tabla de hechos ...")
        dim_tiempo.to_sql("dim_tiempo", conexion, if_exists="append", index=False)
        dim_geografia.to_sql("dim_geografia", conexion, if_exists="append", index=False)
        dim_zona.to_sql("dim_zona", conexion, if_exists="append", index=False)
        dim_victima.to_sql("dim_victima", conexion, if_exists="append", index=False)
        dim_estado.to_sql("dim_estado", conexion, if_exists="append", index=False)
        dim_fuente.to_sql("dim_fuente", conexion, if_exists="append", index=False)
        fact.to_sql("fact_desaparicion", conexion, if_exists="append", index=False)
        conexion.commit()
    finally:
        conexion.close()

    resumen = {
        "registros_cargados": int(len(fact)),
        "dim_tiempo": int(len(dim_tiempo)),
        "dim_geografia": int(len(dim_geografia)),
        "dim_zona": int(len(dim_zona)),
        "dim_victima": int(len(dim_victima)),
        "dim_estado": int(len(dim_estado)),
        "dim_fuente": int(len(dim_fuente)),
        "por_fuente": df["fuente"].value_counts().to_dict(),
    }
    SALIDA_RESUMEN.write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Listo.")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
