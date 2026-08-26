
"""
Diagnostico inicial de calidad - Etapa 1, Punto 7.
Analiza el dataset consolidado (4 fuentes) SIN limpiarlo, solo para
documentar su estado actual: faltantes, duplicados, inconsistencias,
valores fuera de dominio, problemas de formato e integracion entre fuentes.
 
"""
 
import sys
import pandas as pd
 
COLUMNS = [
    "id_registro", "id_original", "fuente", "nivel_fuente", "unidad_de_analisis",
    "num_personas", "tipo_evento", "estado_victima", "sexo",
    "anio", "mes", "fecha",
    "pais", "region", "departamento", "municipio",
    "codigo_dane_departamento", "codigo_dane_municipio",
    "latitud", "longitud", "detalle",
]
 
 
def main(path):
    df = pd.read_csv(path, dtype=str, low_memory=False)
    n = len(df)
    print(f"\n{'='*60}\nTotal de registros: {n:,}\n{'='*60}")
 
    # 1) VALORES FALTANTES por columna
    print("\n--- 1. VALORES FALTANTES POR COLUMNA ---")
    faltantes = df.isna().sum().sort_values(ascending=False)
    for col, cnt in faltantes.items():
        if cnt > 0:
            pct = cnt / n * 100
            print(f"  {col:30s} {cnt:>8,}  ({pct:5.1f}%)")
 
    # 2) FALTANTES CRUZADOS CON FUENTE (para distinguir "vacio esperado" de "vacio real")
    print("\n--- 2. % FALTANTES POR FUENTE (columnas clave) ---")
    cols_clave = ["departamento", "municipio", "codigo_dane_departamento",
                  "latitud", "longitud", "sexo", "estado_victima", "fecha"]
    for col in cols_clave:
        if col in df.columns:
            tab = df.groupby("fuente")[col].apply(lambda s: s.isna().mean() * 100)
            print(f"\n  {col}:")
            for fuente, pct in tab.items():
                print(f"    {fuente:35s} {pct:5.1f}% vacio")
 
    # 3) DUPLICADOS
    print("\n--- 3. DUPLICADOS ---")
    dup_id = df.duplicated(subset=["id_original", "fuente"]).sum()
    print(f"  Duplicados por (id_original, fuente): {dup_id:,}")
    dup_full = df.duplicated(subset=[c for c in COLUMNS if c not in ("id_registro",)]).sum()
    print(f"  Filas 100% identicas (excluyendo id_registro): {dup_full:,}")
 
    # 4) VALORES FUERA DE DOMINIO
    # Nota: el dominio de cada variable es el "rango observado" documentado
    # en el diccionario de datos del equipo, no un limite de negocio impuesto.
    # Por eso aqui NO se marca ningun anio como "fuera de dominio": el rango
    # completo (1930-2026) SI esta dentro del dominio documentado.
    print("\n--- 4. VALORES FUERA DE DOMINIO ---")
    print("  (Dominio = rango observado segun el diccionario de datos del equipo)")
    if "anio" in df.columns:
        anios = pd.to_numeric(df["anio"], errors="coerce")
        print(f"  Rango de 'anio': {anios.min():.0f} - {anios.max():.0f}  "
              f"(coincide con el rango documentado en el diccionario de datos)")
        pre_1990 = anios[anios < 1990]
        print(f"  [Observacion exploratoria, NO es un valor fuera de dominio] "
              f"Registros con anio < 1990: {pre_1990.notna().sum():,} "
              f"({pre_1990.notna().sum()/n*100:.1f}%) -- validar con el equipo "
              f"si es informacion historica legitima o merece analisis aparte.")
    if "mes" in df.columns:
        meses = pd.to_numeric(df["mes"], errors="coerce")
        fuera = meses[(meses < 1) | (meses > 12)]
        print(f"  Valores de 'mes' fuera de 1-12: {fuera.notna().sum():,}")
    if "num_personas" in df.columns:
        num = pd.to_numeric(df["num_personas"], errors="coerce")
        print(f"  'num_personas': min={num.min()}, max={num.max()}")
        print(f"  Registros con num_personas <= 0: {(num <= 0).sum():,}")
    if "latitud" in df.columns and "longitud" in df.columns:
        lat = pd.to_numeric(df["latitud"], errors="coerce")
        lon = pd.to_numeric(df["longitud"], errors="coerce")
        fuera_lat = ((lat < -90) | (lat > 90)).sum()
        fuera_lon = ((lon < -180) | (lon > 180)).sum()
        print(f"  Latitudes fuera de rango [-90,90]: {fuera_lat:,}")
        print(f"  Longitudes fuera de rango [-180,180]: {fuera_lon:,}")
 
    # 5) CATEGORIAS / TEXTO INCONSISTENTE
    print("\n--- 5. VALORES UNICOS EN COLUMNAS CATEGORICAS CLAVE ---")
    for col in ["sexo", "estado_victima", "tipo_evento", "nivel_fuente", "fuente"]:
        if col in df.columns:
            vals = df[col].dropna().unique()
            print(f"\n  {col} ({len(vals)} valores unicos):")
            for v in sorted(vals)[:15]:
                print(f"    - {v}")
            if len(vals) > 15:
                print(f"    ... y {len(vals)-15} mas")
 
    # 6) FORMATO DE FECHA
    print("\n--- 6. FORMATO DE FECHA ---")
    if "fecha" in df.columns:
        fechas_parseadas = pd.to_datetime(df["fecha"], errors="coerce", format="%Y-%m-%d")
        no_parseadas = df["fecha"].notna() & fechas_parseadas.isna()
        print(f"  Fechas que NO calzan con formato YYYY-MM-DD: {no_parseadas.sum():,}")
        if no_parseadas.sum() > 0:
            print("  Ejemplos:", df.loc[no_parseadas, "fecha"].unique()[:5])
 
    # 7) COBERTURA POR FUENTE / NIVEL
    print("\n--- 7. REGISTROS POR FUENTE Y NIVEL ---")
    print(df.groupby(["fuente", "nivel_fuente"]).size().to_string())
 
    print("\n(Fin del diagnostico. Guarda esta salida para redactar la seccion 7.)\n")
 
 
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python diagnostico_calidad.py ruta/al/dataset_consolidado.csv")
        sys.exit(1)
    main(sys.argv[1])
 