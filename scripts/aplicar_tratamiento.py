"""
Aplica el plan de tratamiento de calidad sobre el dataset consolidado
(Etapa 2 - Calidad de Datos) y genera:
  - data/processed/dataset_tratado.csv
  - data/processed/tratamiento_resumen.json  (métricas antes/después)

Uso:
    python scripts/aplicar_tratamiento.py

Requiere que ya exista data/processed/dataset_consolidado.csv
(generado por scripts/build_dataset.py).
"""
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

try:
    from unidecode import unidecode
except ImportError as exc:
    raise SystemExit(
        "Falta la dependencia 'unidecode'. Instálala con: pip install unidecode"
    ) from exc

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
ENTRADA = PROCESSED_DIR / "dataset_consolidado.csv"
SALIDA_CSV = PROCESSED_DIR / "dataset_tratado.csv"
SALIDA_RESUMEN = PROCESSED_DIR / "tratamiento_resumen.json"

# Caracteres invisibles / espacios especiales detectados en el perfilamiento
#  y variantes de codificación 
CARACTERES_INVISIBLES = re.compile(r"[\u00a0\u200b\u200c\u200d\ufeff]")
ESPACIOS_MULTIPLES = re.compile(r"\s+")

# Columnas cuyo vacío es estructural (no aplica según el diseño de la fuente,
# no es un dato faltante por error de captura) se documentan explícitamente
# como "No aplica" en vez de dejarse como nulo silencioso.
COLUMNAS_NO_APLICA_POR_DISENO = {
    # region solo aplica a registros de fuentes globales
    "region": lambda df: df["nivel_fuente"] != "Global",
    # codigo_dane_* solo aplica a registros de nivel nacional
    "codigo_dane_departamento": lambda df: df["nivel_fuente"] == "Global",
    "codigo_dane_municipio": lambda df: df["nivel_fuente"] == "Global",
}


def limpiar_texto(valor):
    """Corrige codificación, espacios invisibles y espacios múltiples."""
    if pd.isna(valor):
        return valor
    texto = unicodedata.normalize("NFKC", str(valor))
    texto = CARACTERES_INVISIBLES.sub("", texto)
    texto = ESPACIOS_MULTIPLES.sub(" ", texto).strip()
    return texto


def homologar_categorias(serie: pd.Series) -> pd.Series:
    """
    Agrupa valores que representan la misma categoría pero difieren solo
    por acentos, mayúsculas o espacios. Conserva como etiqueta canónica la variante más frecuente
    dentro de cada grupo, para no inventar redacciones nuevas.
    """
    limpio = serie.apply(limpiar_texto)
    clave = limpio.apply(lambda s: unidecode(s).lower().strip() if pd.notna(s) else s)
    canonico_por_clave = limpio.groupby(clave).agg(lambda s: s.value_counts().index[0])
    return clave.map(canonico_por_clave)


def marcar_valores_no_aplica(df: pd.DataFrame) -> pd.DataFrame:
    for columna, condicion in COLUMNAS_NO_APLICA_POR_DISENO.items():
        if columna not in df.columns:
            continue
        mascara_no_aplica = condicion(df) & df[columna].isna()
        if mascara_no_aplica.any():
            # convierte a texto antes de insertar la etiqueta, para no romper
            # columnas numéricas 
            df[columna] = df[columna].astype("object")
            df.loc[mascara_no_aplica, columna] = "No aplica"
    return df


def detectar_atipicos_iqr(serie: pd.Series):
    q1, q3 = serie.quantile([0.25, 0.75])
    iqr = q3 - q1
    limite_inferior, limite_superior = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mascara = (serie < limite_inferior) | (serie > limite_superior)
    return mascara, (float(limite_inferior), float(limite_superior))


def completitud_pct(df: pd.DataFrame) -> float:
    total_celdas = df.shape[0] * df.shape[1]
    nulos = df.isna().sum().sum()
    return round((1 - nulos / total_celdas) * 100, 2) if total_celdas else 0.0


def main():
    if not ENTRADA.exists():
        raise SystemExit(
            f"No se encontró {ENTRADA}. Ejecuta primero scripts/build_dataset.py."
        )

    df = pd.read_csv(ENTRADA, encoding="utf-8-sig")
    if "fuente" not in df.columns:
        df["fuente"] = df["id_registro"].astype(str).str.split("-").str[0]

    #Métricas ANTES 
    antes = {
        "registros": int(len(df)),
        "duplicados": int(df.duplicated(subset=["id_original", "fuente"]).sum()),
        "categorias_tipo_evento": int(df["tipo_evento"].nunique(dropna=True)),
        "completitud_pct": completitud_pct(df),
    }
    if "num_personas" in df.columns:
        mascara_atip_antes, limites = detectar_atipicos_iqr(df["num_personas"])
        antes["atipicos_num_personas"] = int(mascara_atip_antes.sum())

    # Tratamiento
    # 1 Eliminar duplicados exactos por id_original + fuente (conserva el primero)
    df_tratado = df.drop_duplicates(subset=["id_original", "fuente"], keep="first").copy()

    # 2 Homologar tipo_evento (codificación, espacios invisibles, variantes)
    df_tratado["tipo_evento"] = homologar_categorias(df_tratado["tipo_evento"])

    # 3 Marcar nulos estructurales explícitamente como "No aplica"
    df_tratado = marcar_valores_no_aplica(df_tratado)

    # 4 Marcar valores atípicos de num_personas y anio para revisión manual,
    #    siguiendo la recomendación del perfilamiento de no tratarlos como error automático.
    if "num_personas" in df_tratado.columns:
        mascara_atip, limites = detectar_atipicos_iqr(df_tratado["num_personas"])
        df_tratado["num_personas_atipico"] = mascara_atip
    if "anio" in df_tratado.columns:
        mascara_atip_anio, limites_anio = detectar_atipicos_iqr(df_tratado["anio"].dropna())
        df_tratado["anio_atipico"] = False
        df_tratado.loc[df_tratado["anio"].notna(), "anio_atipico"] = mascara_atip_anio.values

    # Métricas DESPUÉS 
    despues = {
        "registros": int(len(df_tratado)),
        "duplicados": int(df_tratado.duplicated(subset=["id_original", "fuente"]).sum()),
        "categorias_tipo_evento": int(df_tratado["tipo_evento"].nunique(dropna=True)),
        "completitud_pct": completitud_pct(df_tratado.drop(
            columns=[c for c in ("num_personas_atipico", "anio_atipico") if c in df_tratado.columns]
        )),
    }
    if "num_personas_atipico" in df_tratado.columns:
        despues["atipicos_num_personas_marcados"] = int(df_tratado["num_personas_atipico"].sum())

    resumen = {
        "antes": antes,
        "despues": despues,
        "acciones_aplicadas": [
            "Eliminación de registros duplicados exactos.",
            "Corrección de codificación de texto y eliminación de espacios invisibles en tipo_evento.",
            "Homologar de categorías de tipo_evento equivalentes tras la limpieza de texto.",
            "Marcado explícito de nulos estructurales como 'No aplica' en vez de vacío.",
            "Marcado de valores atípicos en num_personas y anio para revisión manual, "
            "dado que varios corresponden a eventos agregados legítimos según la fuente.",
        ],
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_tratado.to_csv(SALIDA_CSV, index=False, encoding="utf-8-sig")
    with open(SALIDA_RESUMEN, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print(f"Dataset tratado guardado en: {SALIDA_CSV}")
    print(f"Resumen antes/después guardado en: {SALIDA_RESUMEN}")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()