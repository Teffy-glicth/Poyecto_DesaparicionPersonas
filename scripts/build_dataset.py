# -*- coding: utf-8 -*-
"""
Construccion del dataset consolidado - Etapa 1, Punto 4.

Integra 4 fuentes ya recolectadas (sin descargar nada nuevo) en un unico
dataset largo (stacking / concatenacion vertical hacia un esquema comun),
respetando la granularidad nativa de cada fuente:

  - IOM Missing Migrants (Global, 1 fila = 1 incidente)
  - ACLED - Abduction/forced disappearance (Global, 1 fila = agregado semanal
    por pais/admin1)
  - Medicina Legal - Desaparecidos en Colombia (Nacional/Regional, 1 fila = 1 persona)
  - SIEVCAC - Victimas Desaparicion Forzada (Nacional/Regional, 1 fila = 1 persona)

No se realiza limpieza ni diagnostico de calidad (eso corresponde a otra
etapa/integrante). Las unicas transformaciones aplicadas son las minimas
necesarias para poder unir las fuentes en un esquema comun: renombrar
columnas, homologar fechas/geografia/categorias y parsear coordenadas.
"""
import json
import re
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

COLUMNS = [
    "id_registro", "id_original", "fuente", "nivel_fuente", "unidad_de_analisis",
    "num_personas", "tipo_evento", "estado_victima", "sexo", "edad",
    "anio", "mes", "fecha",
    "pais", "region", "departamento", "municipio",
    "codigo_dane_departamento", "codigo_dane_municipio",
    "latitud", "longitud", "detalle", "narrativa",
]


def parse_lat_lon_comma(value):
    """'lat, lon' -> (lat, lon) como floats."""
    if pd.isna(value):
        return None, None
    try:
        lat_str, lon_str = str(value).split(",")
        return float(lat_str.strip()), float(lon_str.strip())
    except (ValueError, AttributeError):
        return None, None


def parse_wkt_point(value):
    """'POINT (lon lat)' -> (lat, lon) como floats."""
    if pd.isna(value):
        return None, None
    m = re.search(r"POINT\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s*\)", str(value))
    if not m:
        return None, None
    lon, lat = float(m.group(1)), float(m.group(2))
    return lat, lon


# ---------------------------------------------------------------------------
# Fuente 1: IOM Missing Migrants (Global) - 1 fila = 1 incidente
# ---------------------------------------------------------------------------
def load_iom():
    df = pd.read_excel(RAW / "Globales" / "Missing_Migrants_Global_Figures_allData.xlsx")

    fecha = pd.to_datetime(df["Incident Date"], errors="coerce")
    lat_lon = df["Coordinates"].apply(parse_lat_lon_comma)
    lat = lat_lon.apply(lambda t: t[0])
    lon = lat_lon.apply(lambda t: t[1])

    def estado(row):
        muertos = row["Number of Dead"] or 0
        desaparecidos = row["Minimum Estimated Number of Missing"] or 0
        if muertos > 0 and desaparecidos > 0:
            return "Fallecido y desaparecido (mixto)"
        if muertos > 0:
            return "Aparecido sin vida"
        if desaparecidos > 0:
            return "Desaparecido"
        return "Sin informacion"

    out = pd.DataFrame({
        "id_original": df["Main ID"].astype(str),
        "fuente": "IOM Missing Migrants",
        "nivel_fuente": "Global",
        "unidad_de_analisis": "evento_agregado",
        "num_personas": df["Total Number of Dead and Missing"],
        "tipo_evento": "Desaparicion/muerte de persona migrante",
        "estado_victima": df.apply(estado, axis=1),
        "sexo": "Sin informacion",
        "edad": pd.NA,
        "anio": fecha.dt.year.fillna(df["Incident Year"]),
        "mes": fecha.dt.month,
        "fecha": fecha,
        "pais": df["Country of Incident"],
        "region": df["Region of Incident"],
        "departamento": pd.NA,
        "municipio": pd.NA,
        "codigo_dane_departamento": pd.NA,
        "codigo_dane_municipio": pd.NA,
        "latitud": lat,
        "longitud": lon,
        "detalle": df["Cause of Death"],
        "narrativa": pd.NA,
    })
    out["id_registro"] = "IOM-" + out["id_original"]
    return out[COLUMNS]


# ---------------------------------------------------------------------------
# Fuente 2: ACLED - Abduction/forced disappearance (Global)
# 1 fila = agregado semanal por pais/admin1 (no es incidente individual)
# ---------------------------------------------------------------------------
def load_acled():
    path = RAW / "Globales" / "ACLED Data_2026-08-25_event_date_from_2001-08-23_event_date_to_2026-08-21.csv"
    df = pd.read_csv(path, encoding="utf-8-sig")

    fecha = pd.to_datetime(df["week"], errors="coerce")
    id_original = (df["week"].astype(str) + "_" + df["country"].astype(str)
                   + "_" + df["admin1"].astype(str))

    out = pd.DataFrame({
        "id_original": id_original,
        "fuente": "ACLED",
        "nivel_fuente": "Global",
        "unidad_de_analisis": "evento_agregado",
        "num_personas": df["events"],
        "tipo_evento": "Abduccion/desaparicion forzada (conflicto armado)",
        "estado_victima": "Sin informacion (evento agregado)",
        "sexo": "Sin informacion",
        "edad": pd.NA,
        "anio": fecha.dt.year,
        "mes": fecha.dt.month,
        "fecha": fecha,
        "pais": df["country"],
        "region": df["region"],
        "departamento": pd.NA,
        "municipio": pd.NA,
        "codigo_dane_departamento": pd.NA,
        "codigo_dane_municipio": pd.NA,
        "latitud": df["centroid_latitude"],
        "longitud": df["centroid_longitude"],
        "detalle": df["admin1"],
        "narrativa": pd.NA,
    })
    out["id_registro"] = "ACLED-" + pd.Series(range(len(out)), index=out.index).astype(str)
    return out[COLUMNS]


# ---------------------------------------------------------------------------
# Fuente 3: Medicina Legal - Desaparecidos en Colombia (Nacional/Regional)
# 1 fila = 1 persona
# ---------------------------------------------------------------------------
ESTADO_ML_MAP = {
    "Desaparecido": "Desaparecido",
    "Aparecio vivo": "Aparecido con vida",
    "Aparecio muerto": "Aparecido sin vida",
}


def load_medicina_legal():
    path = RAW / "Nacionales" / "Desaparecidos_en_Colombia_-_Histórico_junio_de_2026_20260824.csv"
    df = pd.read_csv(path, encoding="utf-8")

    anio_col = pd.to_numeric(df["Año de la desaparición"], errors="coerce")
    # La fuente usa "1900-01-01" como centinela de fecha desconocida (siempre
    # coincide con Año/Mes = "Sin informacion"); se homologa a nulo real.
    fecha = pd.to_datetime(df["Fecha de la desaparición"], errors="coerce")
    fecha = fecha.where(anio_col.notna())
    cod_depto = pd.to_numeric(df["Codigo Dane Departamento"], errors="coerce")
    cod_mun = pd.to_numeric(df["Codigo Dane Municipio"], errors="coerce")

    tipo_evento = df["Clasificación de la desaparición"].replace({
        "Desaparición presuntamente forzada": "Desaparicion forzada (presunta)",
        "Sin información": "Sin informacion",
    })

    out = pd.DataFrame({
        "id_original": df["ID"].astype(str),
        "fuente": "Medicina Legal (SIRDEC)",
        "nivel_fuente": "Nacional",
        "unidad_de_analisis": "persona",
        "num_personas": 1,
        "tipo_evento": tipo_evento,
        "estado_victima": df["Estado de la desaparición"].map(ESTADO_ML_MAP).fillna("Sin informacion"),
        "sexo": df["Sexo del desaparecido"],
        "edad": pd.NA,
        "anio": anio_col,
        "mes": fecha.dt.month,
        "fecha": fecha,
        "pais": df["País donde ocurre la desaparición"],
        "region": pd.NA,
        "departamento": df["Departamento donde ocurre la desaparición DANE"],
        "municipio": df["Municipio donde ocurre la desaparición DANE"],
        "codigo_dane_departamento": cod_depto,
        "codigo_dane_municipio": cod_mun,
        "latitud": pd.NA,
        "longitud": pd.NA,
        "detalle": df["Zona donde ocurre la desaparición"],
        "narrativa": pd.NA,
    })
    out["id_registro"] = "ML-" + out["id_original"]
    return out[COLUMNS]


# ---------------------------------------------------------------------------
# Fuente 4: SIEVCAC - Victimas Desaparicion Forzada (Nacional/Regional)
# 1 fila = 1 persona
# ---------------------------------------------------------------------------
ESTADO_SIEVCAC_MAP = {
    "DESAPARECIDO": "Desaparecido",
    "SIGUE DESAPARECIDO PERO EXISTE INFORMACIÓN": "Desaparecido",
    "CONTINÚA SECUESTRADO": "Desaparecido",
    "APARECIÓ MUERTO": "Aparecido sin vida",
    "MUERTO EN CAUTIVERIO": "Aparecido sin vida",
    "APARECIÓ VIVO": "Aparecido con vida",
    "LIBERADO": "Aparecido con vida",
}
SEXO_SIEVCAC_MAP = {
    "HOMBRE": "Hombre",
    "MUJER": "Mujer",
    "SIN INFORMACION": "Sin informacion",
}


def load_sievcac():
    path = (RAW / "Nacionales" /
            "Sistema_de_Información_de_Eventos_de_Violencia_del_Conflicto_Armado_SIEVCAC_-_Víctimas_DF_Desaparición_Forzada_20260824.csv")
    df = pd.read_csv(path, encoding="utf-8")

    anio_num = pd.to_numeric(df["Año"].astype(str).str.replace(",", "", regex=False), errors="coerce")
    anio_num = anio_num.where(anio_num > 0)  # 0 = "sin informacion"
    mes_num = pd.to_numeric(df["Mes"], errors="coerce")
    mes_num = mes_num.where(mes_num > 0)
    dia_num = pd.to_numeric(df["Día"], errors="coerce")

    fecha = pd.to_datetime(
        dict(year=anio_num, month=mes_num, day=dia_num.where(dia_num.between(1, 31))),
        errors="coerce",
    )

    lat_lon = df["latitud-longitud"].apply(parse_wkt_point)
    lat = lat_lon.apply(lambda t: t[0])
    lon = lat_lon.apply(lambda t: t[1])

    out = pd.DataFrame({
        "id_original": df["ID Persona"].astype(str),
        "fuente": "SIEVCAC (CNMH)",
        "nivel_fuente": "Nacional",
        "unidad_de_analisis": "persona",
        "num_personas": 1,
        "tipo_evento": "Desaparicion forzada (conflicto armado)",
        "estado_victima": df["Situación Actual de la Víctima"].map(ESTADO_SIEVCAC_MAP).fillna("Sin informacion"),
        "sexo": df["Sexo"].map(SEXO_SIEVCAC_MAP).fillna("Sin informacion"),
        "edad": pd.NA,
        "anio": anio_num,
        "mes": mes_num,
        "fecha": fecha,
        "pais": "Colombia",
        "region": pd.NA,
        "departamento": df["Departamento"],
        "municipio": df["Municipio"],
        "codigo_dane_departamento": pd.NA,
        "codigo_dane_municipio": pd.to_numeric(df["Código DANE de Municipio"], errors="coerce"),
        "latitud": lat,
        "longitud": lon,
        "detalle": df["Calidad de la Víctima o la Baja"],
        "narrativa": pd.NA,
    })
    out["id_registro"] = "SIEVCAC-" + out["id_original"]
    return out[COLUMNS]


# ---------------------------------------------------------------------------
# Fuente 5: Encuesta propia de caracterizacion (Primaria) - 1 fila = 1 persona
# reportada por un familiar. Se excluyen las respuestas sin consentimiento.
# ---------------------------------------------------------------------------
MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def parse_fecha_libre(texto):
    """Extrae (anio, mes) de texto libre en espanol, cuando sea posible."""
    if pd.isna(texto):
        return None, None
    texto = str(texto).strip().lower()

    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", texto)
    if m:
        dia, mes, anio = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mes <= 12:
            return anio, mes

    for nombre, num in MESES_ES.items():
        if nombre in texto:
            m_anio = re.search(r"(19|20)\d{2}", texto)
            if m_anio:
                return int(m_anio.group(0)), num

    m = re.search(r"\b(\d{1,2})/(\d{4})\b", texto)
    if m:
        mes, anio = int(m.group(1)), int(m.group(2))
        if 1 <= mes <= 12:
            return anio, mes

    m = re.search(r"(19|20)\d{2}", texto)
    if m:
        return int(m.group(0)), None

    return None, None


def parse_edad(valor):
    if pd.isna(valor):
        return None
    m = re.search(r"\d+", str(valor))
    return int(m.group(0)) if m else None


SEXO_ENCUESTA_MAP = {
    "Masculino": "Hombre",
    "Femenino": "Mujer",
    "Prefiero no decir": "Sin informacion",
}


def load_encuesta():
    path = RAW / "Primarias" / "encuesta_caracterizacion_desaparecidos.xlsx"
    df = pd.read_excel(path)
    col_consentimiento = "¿Autoriza el uso anónimo de esta información con fines académicos?"
    col_edad = ("¿Qué edad, sea exacta o aproximada, tenía su familiar en el "
                "momento en que ocurrieron los hechos ?")
    col_ocupacion = "¿A que se dedicaba en esa época? ¿Cuál era su profesión principal?"
    col_sexo = "Sexo de la persona desaparecida"
    col_fecha_exacta = "Fecha exacta"
    col_fecha_aprox = "Fecha aproximada\n\n"
    col_lugar = "¿En qué municipio, barrio o lugar específico se encontraba o fue visto por última vez?"
    col_circunstancia = "¿Qué estaba haciendo su familiar ese día o bajo qué circunstancias ocurrió la desaparición?"
    col_tipo = "Según su conocimiento, ¿cuál considera que fue el tipo de hecho?"

    # Se excluyen las respuestas que no autorizaron el uso de su informacion
    # (requisito etico, no es limpieza de calidad).
    df = df[df[col_consentimiento] == "Si"].reset_index(drop=True)

    fecha_exacta = pd.to_datetime(df[col_fecha_exacta], errors="coerce")
    anio_mes_libre = df[col_fecha_aprox].apply(parse_fecha_libre)
    anio_libre = anio_mes_libre.apply(lambda t: t[0])
    mes_libre = anio_mes_libre.apply(lambda t: t[1])

    anio = fecha_exacta.dt.year.combine_first(pd.Series(anio_libre, dtype="Float64"))
    mes = fecha_exacta.dt.month.combine_first(pd.Series(mes_libre, dtype="Float64"))

    out = pd.DataFrame({
        "id_original": df["ID"].astype(str),
        "fuente": "Encuesta propia de caracterizacion",
        "nivel_fuente": "Nacional",
        "unidad_de_analisis": "persona",
        "num_personas": 1,
        "tipo_evento": df[col_tipo].fillna("Sin informacion"),
        "estado_victima": "Desaparecido",
        "sexo": df[col_sexo].map(SEXO_ENCUESTA_MAP).fillna("Sin informacion"),
        "edad": df[col_edad].apply(parse_edad),
        "anio": anio,
        "mes": mes,
        "fecha": fecha_exacta,
        "pais": "Colombia",
        "region": pd.NA,
        "departamento": pd.NA,
        "municipio": df[col_lugar].str.strip(),
        "codigo_dane_departamento": pd.NA,
        "codigo_dane_municipio": pd.NA,
        "latitud": pd.NA,
        "longitud": pd.NA,
        "detalle": df[col_ocupacion],
        "narrativa": df[col_circunstancia],
    })
    out["id_registro"] = "ENCUESTA-" + out["id_original"]
    return out[COLUMNS]


# ---------------------------------------------------------------------------
# Fuente 6: Entrevista anonima a un familiar (Primaria) - 1 caso puntual,
# transcrita en data/Primarias/entrevista_transcripcion.md; audio disponible
# en data/Primarias/entrevista_audio.mp4 (reproducible desde Fuentes de datos).
# ---------------------------------------------------------------------------
def load_entrevista():
    out = pd.DataFrame([{
        "id_original": "1",
        "fuente": "Entrevista familiar anonima",
        "nivel_fuente": "Nacional",
        "unidad_de_analisis": "persona",
        "num_personas": 1,
        "tipo_evento": "Desconocida",
        "estado_victima": "Desaparecido",
        "sexo": "Hombre",
        "edad": 28,
        "anio": 2006,
        "mes": pd.NA,
        "fecha": pd.NaT,
        "pais": "Colombia",
        "region": pd.NA,
        "departamento": "Tolima",
        "municipio": "Melgar",
        "codigo_dane_departamento": pd.NA,
        "codigo_dane_municipio": pd.NA,
        "latitud": pd.NA,
        "longitud": pd.NA,
        "detalle": "Policia",
        "narrativa": "Desapareció presuntamente mientras ejercía sus labores como policía; caso sigue inconcluso ante las autoridades.",
    }])
    out["id_registro"] = "ENTREVISTA-" + out["id_original"]
    return out[COLUMNS]


# ---------------------------------------------------------------------------
# Consolidacion y reporte de cumplimiento
# ---------------------------------------------------------------------------
NUMERIC_VARS = ["num_personas", "anio", "mes", "latitud", "longitud", "edad"]
CATEGORICAL_VARS = [
    "fuente", "nivel_fuente", "unidad_de_analisis", "tipo_evento",
    "estado_victima", "sexo", "pais", "region", "departamento",
    "municipio", "codigo_dane_departamento", "codigo_dane_municipio", "detalle",
]
TEMPORAL_VARS = ["anio", "mes", "fecha"]
GEOGRAPHIC_VARS = [
    "pais", "region", "departamento", "municipio",
    "codigo_dane_departamento", "codigo_dane_municipio", "latitud", "longitud",
]


def main():
    print("Cargando y homologando fuentes...")
    partes = {
        "IOM Missing Migrants": load_iom(),
        "ACLED": load_acled(),
        "Medicina Legal (SIRDEC)": load_medicina_legal(),
        "SIEVCAC (CNMH)": load_sievcac(),
        "Encuesta propia de caracterizacion": load_encuesta(),
        "Entrevista familiar anonima": load_entrevista(),
    }
    for nombre, df in partes.items():
        print(f"  - {nombre}: {len(df):,} registros")

    dataset = pd.concat(partes.values(), ignore_index=True)
    dataset["codigo_dane_departamento"] = dataset["codigo_dane_departamento"].astype("Int64")
    dataset["codigo_dane_municipio"] = dataset["codigo_dane_municipio"].astype("Int64")
    dataset["anio"] = dataset["anio"].astype("Int64")
    dataset["mes"] = dataset["mes"].astype("Int64")
    dataset["edad"] = pd.to_numeric(dataset["edad"], errors="coerce").astype("Int64")

    csv_path = OUT_DIR / "dataset_consolidado.csv"
    dataset.to_csv(csv_path, index=False, encoding="utf-8-sig")

    parquet_path = OUT_DIR / "dataset_consolidado.parquet"
    dataset.to_parquet(parquet_path, index=False)

    # Muestra estratificada por fuente, para vistas previas ligeras (ej. en Flask)
    muestra = (
        dataset.groupby("fuente", group_keys=False)
        .apply(lambda g: g.sample(min(len(g), 75), random_state=42))
        .sample(frac=1, random_state=42)  # mezclar para que la vista previa no quede agrupada por fuente
        .reset_index(drop=True)
    )
    muestra.to_csv(OUT_DIR / "dataset_muestra.csv", index=False, encoding="utf-8-sig")

    # -----------------------------------------------------------------
    # Resumen de cumplimiento de minimos
    # -----------------------------------------------------------------
    resumen = {
        "total_registros": int(len(dataset)),
        "cumple_10000_registros": bool(len(dataset) >= 10_000),
        "total_variables": int(len(dataset.columns)),
        "cumple_10_variables": bool(len(dataset.columns) >= 10),
        "variables_numericas": NUMERIC_VARS,
        "cumple_3_numericas": bool(len(NUMERIC_VARS) >= 3),
        "variables_categoricas": CATEGORICAL_VARS,
        "cumple_3_categoricas": bool(len(CATEGORICAL_VARS) >= 3),
        "variables_temporales": TEMPORAL_VARS,
        "cumple_1_temporal": bool(len(TEMPORAL_VARS) >= 1),
        "variables_geograficas": GEOGRAPHIC_VARS,
        "cumple_1_geografica": bool(len(GEOGRAPHIC_VARS) >= 1),
        "registros_por_fuente": {k: int(len(v)) for k, v in partes.items()},
        "registros_por_nivel_fuente": dataset["nivel_fuente"].value_counts(dropna=False).astype(int).to_dict(),
        "registros_por_pais_top10": dataset["pais"].value_counts(dropna=False).head(10).astype(int).to_dict(),
        "rango_anios": [
            int(dataset["anio"].min()) if dataset["anio"].notna().any() else None,
            int(dataset["anio"].max()) if dataset["anio"].notna().any() else None,
        ],
        "columnas": [
            {"nombre": c, "tipo": (
                "numerica" if c in NUMERIC_VARS else
                "temporal" if c in TEMPORAL_VARS else
                "geografica" if c in GEOGRAPHIC_VARS else
                "categorica" if c in CATEGORICAL_VARS else
                "identificador/texto"
            )}
            for c in dataset.columns
        ],
    }
    with open(OUT_DIR / "dataset_resumen.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    # -----------------------------------------------------------------
    # Impresion del resumen final
    # -----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("RESUMEN DE CUMPLIMIENTO - Dataset consolidado (Etapa 1, Punto 4)")
    print("=" * 70)
    print(f"Registros totales: {resumen['total_registros']:,} "
          f"(minimo 10.000: {'OK' if resumen['cumple_10000_registros'] else 'FALTA'})")
    print(f"Variables totales: {resumen['total_variables']} "
          f"(minimo 10: {'OK' if resumen['cumple_10_variables'] else 'FALTA'})")
    print(f"Variables numericas ({len(NUMERIC_VARS)}, minimo 3): {NUMERIC_VARS}")
    print(f"Variables categoricas ({len(CATEGORICAL_VARS)}, minimo 3): {CATEGORICAL_VARS}")
    print(f"Variables temporales ({len(TEMPORAL_VARS)}, minimo 1): {TEMPORAL_VARS}")
    print(f"Variables geograficas ({len(GEOGRAPHIC_VARS)}, minimo 1): {GEOGRAPHIC_VARS}")
    print(f"\nRegistros por fuente: {resumen['registros_por_fuente']}")
    print(f"Registros por nivel: {resumen['registros_por_nivel_fuente']}")
    print(f"Rango de anios: {resumen['rango_anios']}")
    print(f"\nArchivos generados:")
    print(f"  - {csv_path}")
    print(f"  - {parquet_path}")
    print(f"  - {OUT_DIR / 'dataset_muestra.csv'}")
    print(f"  - {OUT_DIR / 'dataset_resumen.json'}")


if __name__ == "__main__":
    main()
