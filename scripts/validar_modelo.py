import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cargar_modelo_estrella import FUENTES_INCLUIDAS, UNIDAD_INCLUIDA

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OLAP_SQL_DIR = BASE_DIR / "etl" / "olap"
OLAP_DATA_DIR = BASE_DIR / "data" / "olap"

ENTRADA_CSV = PROCESSED_DIR / "dataset_tratado.csv"
BASE_DB = OLAP_DATA_DIR / "modelo_estrella.db"
SALIDA_JSON = OLAP_DATA_DIR / "validaciones.json"

DIMENSIONES = [
    ("dim_tiempo", "id_tiempo"),
    ("dim_geografia", "id_geografia"),
    ("dim_zona", "id_zona"),
    ("dim_victima", "id_victima"),
    ("dim_estado", "id_estado"),
    ("dim_fuente", "id_fuente"),
]


def validar_unicidad_claves(con):
    resultado = {}
    for tabla, clave in DIMENSIONES:
        cur = con.execute(
            f"SELECT {clave}, COUNT(*) c FROM {tabla} GROUP BY {clave} HAVING c > 1"
        )
        repetidas = cur.fetchall()
        resultado[tabla] = {"ok": len(repetidas) == 0, "claves_repetidas": repetidas}
    return resultado


def validar_fk_huerfanas(con):
    resultado = {}
    for tabla, clave in DIMENSIONES:
        cur = con.execute(
            f"""SELECT COUNT(*) FROM fact_desaparicion f
                LEFT JOIN {tabla} d ON f.{clave} = d.{clave}
                WHERE d.{clave} IS NULL"""
        )
        resultado[clave] = cur.fetchone()[0]
    return resultado


def validar_duplicados_hechos(con):
    cur = con.execute(
        "SELECT id_registro, COUNT(*) c FROM fact_desaparicion GROUP BY id_registro HAVING c > 1"
    )
    duplicados = cur.fetchall()
    return {"ok": len(duplicados) == 0, "cantidad": len(duplicados)}


def contar_clave_cero(con):
    resultado = {}
    for _, clave in DIMENSIONES:
        cur = con.execute(f"SELECT COUNT(*) FROM fact_desaparicion WHERE {clave} = 0")
        resultado[clave] = cur.fetchone()[0]
    return resultado


def comparaciones_contra_csv(con):
    df = pd.read_csv(ENTRADA_CSV, low_memory=False)
    df = df[df["fuente"].isin(FUENTES_INCLUIDAS) & (df["unidad_de_analisis"] == UNIDAD_INCLUIDA)]

    comparaciones = []

    csv_por_fuente = df["fuente"].value_counts().to_dict()
    cur = con.execute(
        "SELECT fuente, COUNT(*) FROM fact_desaparicion f JOIN dim_fuente d USING(id_fuente) GROUP BY fuente"
    )
    modelo_por_fuente = dict(cur.fetchall())
    for fuente in FUENTES_INCLUIDAS:
        valor_csv = int(csv_por_fuente.get(fuente, 0))
        valor_modelo = int(modelo_por_fuente.get(fuente, 0))
        comparaciones.append({
            "nombre": f"Personas registradas — {fuente}",
            "valor_csv_tratado": valor_csv,
            "valor_modelo": valor_modelo,
            "coincide": valor_csv == valor_modelo,
            "explicacion": (
                "Coincide: num_personas=1 por fila y el filtro de carga es el mismo "
                "que se aplico aqui sobre el CSV (fuente + unidad_de_analisis='persona')."
                if valor_csv == valor_modelo else
                "Diferencia: revisar el filtro de carga en scripts/cargar_modelo_estrella.py."
            ),
        })

    ml = df[df["fuente"] == "Medicina Legal (SIRDEC)"]
    hombres_csv = int((ml["sexo"].astype(str).str.strip().str.title() == "Hombre").sum())
    cur = con.execute(
        """SELECT COUNT(*) FROM fact_desaparicion f
           JOIN dim_victima v USING(id_victima) JOIN dim_fuente d USING(id_fuente)
           WHERE d.fuente='Medicina Legal (SIRDEC)' AND v.sexo='Hombre'"""
    )
    hombres_modelo = cur.fetchone()[0]
    comparaciones.append({
        "nombre": "Hombres en Medicina Legal (SIRDEC)",
        "valor_csv_tratado": hombres_csv,
        "valor_modelo": hombres_modelo,
        "coincide": hombres_csv == hombres_modelo,
        "explicacion": (
            "Coincide: dim_victima.sexo aplica la misma normalizacion (str.title()) "
            "que esta comparacion sobre el CSV."
            if hombres_csv == hombres_modelo else
            "Diferencia: revisar normalizar_departamento/sexo en el script de carga."
        ),
    })

    cur = con.execute(
        """SELECT d.fuente, SUM(f.flag_sigue_desaparecida)*100.0/COUNT(*)
           FROM fact_desaparicion f JOIN dim_fuente d USING(id_fuente)
           GROUP BY d.fuente"""
    )
    pct_modelo = dict(cur.fetchall())
    for fuente in FUENTES_INCLUIDAS:
        sub = df[df["fuente"] == fuente]
        pct_csv = round(float(100.0 * (sub["estado_victima"] == "Desaparecido").sum() / len(sub)), 2)
        valor_modelo = round(float(pct_modelo.get(fuente, 0.0)), 2)
        comparaciones.append({
            "nombre": f"% que siguen desaparecidas — {fuente}",
            "valor_csv_tratado": pct_csv,
            "valor_modelo": valor_modelo,
            "coincide": bool(abs(pct_csv - valor_modelo) < 0.05),
            "explicacion": (
                "Coincide (margen de redondeo < 0.05 pp): "
                "SUM(flag_sigue_desaparecida)*100.0/COUNT(*) sobre el grupo filtrado, "
                "el mismo denominador que esta comparacion."
                if abs(pct_csv - valor_modelo) < 0.05 else
                "Diferencia: revisar el calculo de flag_sigue_desaparecida en la carga."
            ),
        })

    return comparaciones


def main():
    if not BASE_DB.exists():
        raise SystemExit(
            f"Falta {BASE_DB}. Ejecuta 'python scripts/cargar_modelo_estrella.py' primero."
        )
    if not ENTRADA_CSV.exists():
        raise SystemExit(f"Falta {ENTRADA_CSV}.")

    con = sqlite3.connect(BASE_DB)
    try:
        unicidad = validar_unicidad_claves(con)
        fk_huerfanas = validar_fk_huerfanas(con)
        duplicados = validar_duplicados_hechos(con)
        clave_cero = contar_clave_cero(con)
        comparaciones = comparaciones_contra_csv(con)
    finally:
        con.close()

    ok_general = (
        all(v["ok"] for v in unicidad.values())
        and all(v == 0 for v in fk_huerfanas.values())
        and duplicados["ok"]
        and all(c["coincide"] for c in comparaciones)
    )

    resultado = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ok_general": ok_general,
        "unicidad_claves": unicidad,
        "fk_huerfanas": fk_huerfanas,
        "duplicados_hechos": duplicados,
        "hechos_en_clave_0_por_dimension": clave_cero,
        "comparaciones_con_csv_tratado": comparaciones,
    }

    OLAP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SALIDA_JSON.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"ok_general: {ok_general}")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
