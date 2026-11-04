import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "olap" / "modelo_estrella.db"

COLUMNAS = {
    "anio": "t.anio",
    "semestre": "t.semestre",
    "trimestre": "t.trimestre",
    "mes": "t.nombre_mes",
    "periodo_acuerdo": "t.periodo_acuerdo",
    "macro_region": "g.macro_region",
    "departamento": "g.departamento",
    "municipio": "g.municipio",
    "zona_hecho": "z.zona_hecho",
    "sexo": "v.sexo",
    "calidad_victima": "v.calidad_victima",
    "grupo_desenlace": "e.grupo_desenlace",
    "estado_victima": "e.estado_victima",
    "fuente": "f.fuente",
    "tipo_evento": "f.tipo_evento",
}

JERARQUIAS = {
    "tiempo": ["anio", "trimestre", "mes"],
    "geografia": ["macro_region", "departamento", "municipio"],
    "estado": ["grupo_desenlace", "estado_victima"],
    "fuente": ["fuente", "tipo_evento"],
}

MEDIDAS = {
    "personas": "SUM(h.num_personas)",
    "siguen_desaparecidas": "SUM(h.flag_sigue_desaparecida)",
    "aparecidas_con_vida": "SUM(h.flag_aparecio_viva)",
    "aparecidas_sin_vida": "SUM(h.flag_aparecio_sin_vida)",
    "pct_siguen_desaparecidas": "SUM(h.flag_sigue_desaparecida) * 100.0 / SUM(h.num_personas)",
    "pct_aparecidas_con_vida": "SUM(h.flag_aparecio_viva) * 100.0 / SUM(h.num_personas)",
    "pct_aparecidas_sin_vida": "SUM(h.flag_aparecio_sin_vida) * 100.0 / SUM(h.num_personas)",
    "municipios_afectados": "COUNT(DISTINCT h.id_geografia)",
}

FROM_JOIN = """
FROM fact_desaparicion h
JOIN dim_tiempo t    ON h.id_tiempo = t.id_tiempo
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_zona z      ON h.id_zona = z.id_zona
JOIN dim_victima v   ON h.id_victima = v.id_victima
JOIN dim_estado e    ON h.id_estado = e.id_estado
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
"""


def conectar():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Falta {DB_PATH}. Ejecuta 'python scripts/cargar_modelo_estrella.py'."
        )
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    return con


class ConsultaInvalida(ValueError):
    pass


def _validar_columnas(claves, etiqueta):
    for clave in claves:
        if clave not in COLUMNAS:
            raise ConsultaInvalida(f"{etiqueta} desconocida: {clave!r}")


def _validar_medidas(claves):
    for clave in claves:
        if clave not in MEDIDAS:
            raise ConsultaInvalida(f"Medida desconocida: {clave!r}")


def _where_de(filtros):
    if not filtros:
        return "", []
    condiciones = []
    params = []
    for clave, valor in filtros.items():
        if clave not in COLUMNAS:
            raise ConsultaInvalida(f"Filtro de columna desconocida: {clave!r}")
        columna = COLUMNAS[clave]
        if isinstance(valor, (list, tuple, set)):
            valores = list(valor)
            marcadores = ", ".join("?" for _ in valores)
            condiciones.append(f"{columna} IN ({marcadores})")
            params.extend(valores)
        else:
            condiciones.append(f"{columna} = ?")
            params.append(valor)
    return "WHERE " + " AND ".join(condiciones), params


def denominador_total(con, filtros=None):
    where_sql, params = _where_de(filtros)
    sql = f"SELECT SUM(h.num_personas) {FROM_JOIN} {where_sql}"
    fila = con.execute(sql, params).fetchone()
    return fila[0] or 0


def consultar(dimensiones, medidas, filtros=None, con=None, orden=None):
    dimensiones = list(dimensiones or [])
    medidas = list(medidas or ["personas"])
    filtros = dict(filtros or {})

    _validar_columnas(dimensiones, "Dimension")
    _validar_medidas(medidas)

    cerrar_al_final = con is None
    con = con or conectar()
    try:
        columnas_select = [f"{COLUMNAS[d]} AS {d}" for d in dimensiones]
        medidas_select = [f"{MEDIDAS[m]} AS {m}" for m in medidas]
        select_sql = ", ".join(columnas_select + medidas_select) or "1"

        where_sql, params = _where_de(filtros)

        if orden is None:
            orden = dimensiones
        _validar_columnas([c for c in orden if c in COLUMNAS], "Columna de orden")
        order_sql = ""
        if dimensiones:
            order_cols = ", ".join(COLUMNAS[d] for d in orden if d in dimensiones) or ", ".join(
                COLUMNAS[d] for d in dimensiones
            )
            order_sql = f"ORDER BY {order_cols}"

        group_sql = ""
        if dimensiones:
            group_sql = "GROUP BY " + ", ".join(COLUMNAS[d] for d in dimensiones)

        sql = f"SELECT {select_sql} {FROM_JOIN} {where_sql} {group_sql} {order_sql}".strip()
        cur = con.execute(sql, params)
        columnas_resultado = [c[0] for c in cur.description]
        filas = [dict(zip(columnas_resultado, fila)) for fila in cur.fetchall()]

        return {
            "dimensiones": dimensiones,
            "medidas": medidas,
            "filtros": filtros,
            "filas": filas,
            "denominador_total": denominador_total(con, filtros),
            "sql": " ".join(sql.split()),
        }
    finally:
        if cerrar_al_final:
            con.close()


def _nivel_de(jerarquia, nivel_actual):
    niveles = JERARQUIAS.get(jerarquia)
    if niveles is None:
        raise ConsultaInvalida(f"Jerarquia desconocida: {jerarquia!r}")
    if nivel_actual not in niveles:
        raise ConsultaInvalida(f"Nivel {nivel_actual!r} no existe en la jerarquia {jerarquia!r}")
    return niveles, niveles.index(nivel_actual)


def drill_down(jerarquia, nivel_actual, medidas, filtros=None, con=None, dimensiones_extra=None):
    niveles, i = _nivel_de(jerarquia, nivel_actual)
    if i >= len(niveles) - 1:
        raise ConsultaInvalida(f"{nivel_actual!r} ya es el nivel mas detallado de {jerarquia!r}")
    siguiente = niveles[i + 1]
    dimensiones = [siguiente] + list(dimensiones_extra or [])
    resultado = consultar(dimensiones, medidas, filtros, con=con)
    resultado["nivel"] = siguiente
    resultado["operacion"] = "drill_down"
    return resultado


def roll_up(jerarquia, nivel_actual, medidas, filtros=None, con=None, dimensiones_extra=None):
    niveles, i = _nivel_de(jerarquia, nivel_actual)
    if i <= 0:
        raise ConsultaInvalida(f"{nivel_actual!r} ya es el nivel mas general de {jerarquia!r}")
    anterior = niveles[i - 1]
    dimensiones = [anterior] + list(dimensiones_extra or [])
    resultado = consultar(dimensiones, medidas, filtros, con=con)
    resultado["nivel"] = anterior
    resultado["operacion"] = "roll_up"
    return resultado


def pivot(dimensiones, medidas, filtros=None, con=None):
    resultado = consultar(dimensiones, medidas, filtros, con=con)
    resultado["operacion"] = "pivot"
    return resultado


def como_matriz(resultado, fila_dim, columna_dim, medida):
    filas_valores = []
    columnas_valores = []
    celda = {}
    for fila in resultado["filas"]:
        fv, cv = fila[fila_dim], fila[columna_dim]
        if fv not in filas_valores:
            filas_valores.append(fv)
        if cv not in columnas_valores:
            columnas_valores.append(cv)
        celda[(fv, cv)] = fila.get(medida)
    return {
        "filas": filas_valores,
        "columnas": columnas_valores,
        "celdas": [[celda.get((fv, cv)) for cv in columnas_valores] for fv in filas_valores],
    }
