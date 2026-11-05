import csv
import io
import json
import os
import re
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, send_from_directory, url_for

import olap

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
PRIMARIAS_DIR = DATA_DIR / "Primarias"
REPO_URL = "https://github.com/Teffy-glicth/Poyecto_DesaparicionPersonas"
APP_URL = "https://poyecto-desaparicionpersonas-kefg.onrender.com"
POWERBI_URL = (
    "https://app.powerbi.com/view?r="
    "eyJrIjoiZmNhMGZjOGQtZjA2OC00ZjhlLWI2OWEtN2I3N2QyOGVjZWQ0IiwidCI6IjA3ZGE2N2EwLTFmNDMtNGU4Yy05NzdmLTVmODhiNjQ3MGVlNiIsImMiOjR9"
    "&pageName=9897ca544da6e7d48a25"
)
PBIX_URL = "https://github.com/Teffy-glicth/Poyecto_DesaparicionPersonas/blob/ec1f4c07430488bac30d513a98e0622aaf3a605a/powerbi/ConocimientoEvidente_Final.pbix"  

ETAPA1_MENU = [
    {"numero": 1, "slug": "problema", "titulo": "Problema y contexto"},
    {"numero": 2, "slug": "preguntas", "titulo": "Pregunta principal y preguntas secundarias"},
    {"numero": 3, "slug": "necesidades", "titulo": "Necesidades de información"},
    {"numero": 4, "slug": "fuentes", "titulo": "Fuentes de datos"},
    {"numero": 5, "slug": "dataset", "titulo": "Dataset"},
    {"numero": 6, "slug": "diccionario", "titulo": "Diccionario de datos"},
    {"numero": 7, "slug": "calidad", "titulo": "Calidad inicial de los datos"},
    {"numero": 8, "slug": "limitaciones", "titulo": "Limitaciones y consideraciones"},
]
ETAPA1_MENU_BY_SLUG = {item["slug"]: item for item in ETAPA1_MENU}

ETAPA2_MENU = [
    {"numero": 1, "slug": "descripcion", "titulo": "Descripción del conjunto de datos"},
    {"numero": 2, "slug": "perfilamiento", "titulo": "Resultados del perfilamiento"},
    {"numero": 3, "slug": "dimensiones", "titulo": "Dimensiones y métricas evaluadas"},
    {"numero": 4, "slug": "problemas", "titulo": "Problemas identificados"},
    {"numero": 5, "slug": "tratamiento", "titulo": "Acciones de tratamiento aplicadas"},
]
ETAPA2_MENU_BY_SLUG = {item["slug"]: item for item in ETAPA2_MENU}

ETAPA3_MENU = [
    {"numero": 1, "slug": "reglas", "titulo": "Reglas de tratamiento"},
    {"numero": 2, "slug": "diseno", "titulo": "Diseño del ETL en SSIS"},
    {"numero": 3, "slug": "iteraciones", "titulo": "Resultados de las tres iteraciones"},
    {"numero": 4, "slug": "informe", "titulo": "Informe técnico (PDF)"},
    {"numero": 5, "slug": "video", "titulo": "Video de demostración"},
]
ETAPA3_MENU_BY_SLUG = {item["slug"]: item for item in ETAPA3_MENU}

ETAPA3_STATIC = BASE_DIR / "static" / "etapa3"
ETAPA3_INFORME = "informe_tecnico_etl.pdf"
ETAPA3_VIDEO_LOCAL = "video_demostracion.mp4"
RESULTADOS_ETL_PATH = BASE_DIR / "etl" / "resultados" / "iteraciones.json"

ETAPA3_VIDEO_URL = os.environ.get("ETAPA3_VIDEO_URL", "https://www.youtube.com/watch?v=A8Gn9X58u3g")
REPO_URL = os.environ.get("REPO_URL", "")

ETAPA4_MENU = [
    {"numero": 1, "slug": "continuidad", "titulo": "Continuidad del proyecto"},
    {"numero": 2, "slug": "preguntas", "titulo": "Preguntas de análisis"},
    {"numero": 3, "slug": "tablero", "titulo": "Tablero de Power BI"},
    {"numero": 4, "slug": "conocimientos", "titulo": "Conocimientos evidentes"},
    {"numero": 5, "slug": "informe", "titulo": "Informe técnico (PDF)"},
]
ETAPA4_MENU_BY_SLUG = {item["slug"]: item for item in ETAPA4_MENU}

ETAPA4_DIR = BASE_DIR / "etapa4"
ETAPA4_INFORME = "Etapa4_Informe.pdf"
APP_URL = os.environ.get("APP_URL", "https://poyecto-desaparicionpersonas-kefg.onrender.com/")

CONOCIMIENTOS_PATH = DATA_DIR / "conocimientos.json"
POWERBI_REPORT_URL = os.environ.get("POWERBI_REPORT_URL", "")

ELEMENTOS_CONOCIMIENTO = [
    ("pregunta", "Pregunta"),
    ("variables", "Variables"),
    ("procedimiento", "Procedimiento"),
    ("evidencia", "Evidencia"),
    ("hallazgo", "Hallazgo"),
    ("interpretacion", "Interpretación"),
    ("utilidad", "Utilidad"),
    ("limitacion", "Limitación"),
]

MUESTRA_MAX_FILAS = 50

ETAPA5_MENU = [
    {"numero": 1, "slug": "proposito", "titulo": "Propósito y modelo estrella"},
    {"numero": 2, "slug": "modelo", "titulo": "Modelo multidimensional"},
    {"numero": 3, "slug": "vista1", "titulo": "Vista 1 · Perfil y desenlace"},
    {"numero": 4, "slug": "vista2", "titulo": "Vista 2 · Territorio"},
    {"numero": 5, "slug": "vista3", "titulo": "Vista 3 · Evolución temporal"},
    {"numero": 6, "slug": "vista4", "titulo": "Vista 4 · Perfiles combinados"},
    {"numero": 7, "slug": "operaciones", "titulo": "Operaciones multidimensionales"},
    {"numero": 8, "slug": "validaciones", "titulo": "Validaciones del modelo"},
    {"numero": 9, "slug": "conclusiones", "titulo": "Conocimientos y conclusiones"},
]
ETAPA5_MENU_BY_SLUG = {item["slug"]: item for item in ETAPA5_MENU}

CONOCIMIENTOS_MULTIDIM_PATH = DATA_DIR / "conocimientos_multidimensionales.json"


@app.context_processor
def inject_menu():
    return {
        "etapa1_menu": ETAPA1_MENU,
        "etapa2_menu": ETAPA2_MENU,
        "etapa3_menu": ETAPA3_MENU,
        "etapa4_menu": ETAPA4_MENU,
        "etapa5_menu": ETAPA5_MENU,
        "current_slug": None,
    }


@app.route("/")
def index():
    return render_template("index.html")


# ---------- Etapa 1 ----------

def render_problema():
    return render_template("etapa1_problema.html", current_slug="problema")


def render_preguntas():
    return render_template("etapa1_preguntas.html", current_slug="preguntas")


def render_necesidades():
    return render_template("etapa1_necesidades.html", current_slug="necesidades")


def render_fuentes():
    with open(DATA_DIR / "fuentes.json", encoding="utf-8") as f:
        data = json.load(f)
    return render_template(
        "etapa1_fuentes.html",
        fuentes=data["fuentes"],
        justificacion_general=data["justificacion_general"],
        limitaciones=data["limitaciones_conocidas"],
        current_slug="fuentes",
    )


def render_diccionario():
    diccionario_path = DATA_DIR / "diccionario_datos.json"
    if not diccionario_path.exists():
        abort(500, description="Falta el archivo data/diccionario_datos.json.")

    with open(diccionario_path, encoding="utf-8") as f:
        diccionario = json.load(f)

    return render_template(
        "etapa1_diccionario.html",
        diccionario=diccionario,
        current_slug="diccionario",
    )


def render_dataset():
    resumen_path = PROCESSED_DIR / "dataset_resumen.json"
    muestra_path = PROCESSED_DIR / "dataset_muestra.csv"
    if not resumen_path.exists() or not muestra_path.exists():
        abort(500, description=(
            "Faltan los artefactos del dataset consolidado. "
            "Ejecuta 'python scripts/build_dataset.py' antes de iniciar la app."
        ))

    with open(resumen_path, encoding="utf-8") as f:
        resumen = json.load(f)

    with open(muestra_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        muestra_columnas = reader.fieldnames
        muestra_filas = [row for _, row in zip(range(MUESTRA_MAX_FILAS), reader)]

    return render_template(
        "etapa1_dataset.html",
        resumen=resumen,
        muestra_columnas=muestra_columnas,
        muestra_filas=muestra_filas,
        current_slug="dataset",
    )

def render_calidad():
    return render_template(
        "etapa1_calidad.html",
        current_slug="calidad",
    )

def render_limitaciones():
    return render_template(
        "etapa1_limitaciones.html",
        current_slug="limitaciones",
    )

@app.route("/etapa1/fuentes/entrevista-audio")
def entrevista_audio():
    audio_path = PRIMARIAS_DIR / "entrevista_audio.mp4"
    if not audio_path.exists():
        abort(404)
    return send_from_directory(PRIMARIAS_DIR, "entrevista_audio.mp4", mimetype="audio/mp4")

@app.route("/etapa1/dataset/descargar")
def descargar_dataset():
    csv_path = PROCESSED_DIR / "dataset_consolidado.csv"
    if not csv_path.exists():
        abort(500, description=(
            "Falta el dataset consolidado. "
            "Ejecuta 'python scripts/build_dataset.py' antes de iniciar la app."
        ))
    return send_from_directory(
        PROCESSED_DIR, "dataset_consolidado.csv",
        as_attachment=True, download_name="dataset_consolidado.csv",
    )


@app.route("/etapa1/<slug>")
def etapa1_pagina(slug):
    if slug not in ETAPA1_MENU_BY_SLUG:
        abort(404)
    if slug == "problema":
        return render_problema()
    if slug == "preguntas":
        return render_preguntas()
    if slug == "necesidades":
        return render_necesidades()
    if slug == "fuentes":
        return render_fuentes()
    if slug == "dataset":
        return render_dataset()
    if slug == "diccionario":
        return render_diccionario()
    if slug == "calidad":
        return render_calidad()
    if slug == "limitaciones":
        return render_limitaciones()

    item = ETAPA1_MENU_BY_SLUG[slug]
    return render_template(
        "etapa1_placeholder.html",
        numero=item["numero"],
        titulo=item["titulo"],
        current_slug=slug,
    )


# ---------- Etapa 2 ----------
def render_perfilamiento():
    return render_template(
        "etapa2_perfilamiento.html",
        current_slug="perfilamiento",
    )
def render_tratamiento():
    resumen_path = PROCESSED_DIR / "tratamiento_resumen.json"
    if not resumen_path.exists():
        abort(500, description=(
            "Falta data/processed/tratamiento_resumen.json. "
            "Ejecuta 'python scripts/aplicar_tratamiento.py' antes de iniciar la app "
            "(requiere que ya exista dataset_consolidado.csv)."
        ))

    with open(resumen_path, encoding="utf-8") as f:
        resumen = json.load(f)

    return render_template(
        "etapa2_tratamiento.html",
        resumen=resumen,
        current_slug="tratamiento",
    )


@app.route("/etapa2/<slug>")

def etapa2_pagina(slug):
    if slug not in ETAPA2_MENU_BY_SLUG:
        abort(404)
    if slug == "descripcion":
        return render_template(
            "etapa2_descripcion.html",
            current_slug="descripcion",
        )

    if slug == "perfilamiento":
        return render_template(
            "etapa2_perfilamiento.html",
            current_slug="perfilamiento",
        )

    if slug == "dimensiones":
        return render_template(
            "etapa2_dimensiones.html",
            current_slug="dimensiones",
        )

    if slug == "problemas":
        return render_template(
            "etapa2_problemas.html",
            current_slug="problemas",
        )

    if slug == "tratamiento":
        return render_tratamiento()

    item = ETAPA2_MENU_BY_SLUG[slug]
    return render_template(
        "etapa1_placeholder.html",
        numero=item["numero"],
        titulo=item["titulo"],
        current_slug=slug,
    )

# ---------- Etapa 3 ----------

def video_embed_url(url):
    """Convierte un enlace de YouTube o Google Drive en su URL de inserción."""
    if not url:
        return None
    m = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([\w-]{11})", url)
    if m:
        return f"https://www.youtube.com/embed/{m.group(1)}"
    m = re.search(r"drive\.google\.com/file/d/([\w-]+)", url)
    if m:
        return f"https://drive.google.com/file/d/{m.group(1)}/preview"
    return url


def cargar_resultados_etl():
    if not RESULTADOS_ETL_PATH.exists():
        abort(500, description="Falta etl/resultados/iteraciones.json.")
    with open(RESULTADOS_ETL_PATH, encoding="utf-8") as f:
        return json.load(f)


@app.route("/etapa3/iteraciones.csv")
def descargar_iteraciones():
    datos = cargar_resultados_etl()
    campos = ["id_carga", "iteracion", "ejecucion", "flujo", "recibidos", "aceptados",
              "duplicados", "revision", "ya_existian"]
    salida = io.StringIO()
    writer = csv.DictWriter(salida, fieldnames=campos, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(datos["ejecuciones"])
    return Response(
        "\ufeff" + salida.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=iteraciones_etl.csv"},
    )


@app.route("/etapa3/<slug>")
def etapa3_pagina(slug):
    if slug not in ETAPA3_MENU_BY_SLUG:
        abort(404)

    if slug in ("reglas", "diseno"):
        return render_template(f"etapa3_{slug}.html", current_slug=slug)

    if slug == "informe":
        return render_template(
            "etapa3_informe.html",
            hay_informe=(ETAPA3_STATIC / ETAPA3_INFORME).exists(),
            informe_url=url_for("static", filename=f"etapa3/{ETAPA3_INFORME}"),
            repo_url=REPO_URL,
            current_slug=slug,
        )

    if slug == "iteraciones":
        return render_template(
            "etapa3_iteraciones.html",
            datos=cargar_resultados_etl(),
            current_slug=slug,
        )

    video_local = (ETAPA3_STATIC / ETAPA3_VIDEO_LOCAL).exists()
    return render_template(
        "etapa3_video.html",
        video_url=ETAPA3_VIDEO_URL,
        video_embed=video_embed_url(ETAPA3_VIDEO_URL),
        video_local_url=url_for("static", filename=f"etapa3/{ETAPA3_VIDEO_LOCAL}") if video_local else None,
        current_slug=slug,
    )


# ---------- Etapa 4 ----------

@app.route("/etapa4/informe/pdf")
def etapa4_informe_pdf():
    if not (ETAPA4_DIR / ETAPA4_INFORME).exists():
        abort(404)
    return send_from_directory(ETAPA4_DIR, ETAPA4_INFORME, mimetype="application/pdf")


@app.route("/etapa4/<slug>")
def etapa4_pagina(slug):
    if slug not in ETAPA4_MENU_BY_SLUG:
        abort(404)

    if slug == "conocimientos":
        return render_conocimientos()
    if slug == "informe":
        return render_informe()

    return render_template(f"etapa4_{slug}.html", current_slug=slug)


def render_conocimientos():
    if not CONOCIMIENTOS_PATH.exists():
        abort(500, description="Falta el archivo data/conocimientos.json.")
    with open(CONOCIMIENTOS_PATH, encoding="utf-8") as f:
        datos = json.load(f)
    return render_template(
        "etapa4_conocimientos.html",
        datos=datos,
        elementos=ELEMENTOS_CONOCIMIENTO,
        informe_url=POWERBI_REPORT_URL,
        current_slug="conocimientos",
    )


def render_informe():
    return render_template(
        "etapa4_informe.html",
        hay_informe=(ETAPA4_DIR / ETAPA4_INFORME).exists(),
        informe_url=url_for("etapa4_informe_pdf"),
        repo_url=REPO_URL,
        app_url=APP_URL,
        powerbi_url=POWERBI_URL,
        pbix_url=PBIX_URL,
        current_slug="informe",
    )

    return render_template(f"etapa4_{slug}.html", current_slug=slug)


# ---------- Etapa 5 ----------

def cargar_conocimientos_multidimensionales():
    if not CONOCIMIENTOS_MULTIDIM_PATH.exists():
        return {"conocimientos": []}
    with open(CONOCIMIENTOS_MULTIDIM_PATH, encoding="utf-8") as f:
        return json.load(f)


def conocimientos_de_vista(slug_vista):
    datos = cargar_conocimientos_multidimensionales()
    return [c for c in datos.get("conocimientos", []) if c.get("vista") == slug_vista]


VISTA1_PREGUNTA = (
    "¿Cómo cambia la brecha de desenlace entre hombres y mujeres según la fuente, "
    "la calidad de la víctima y el periodo frente al Acuerdo de Paz?"
)


def datos_vista1(args):
    filtros = {}
    fuente = args.get("fuente")
    if fuente:
        filtros["fuente"] = fuente
    periodo_acuerdo = args.get("periodo_acuerdo")
    if periodo_acuerdo:
        filtros["periodo_acuerdo"] = periodo_acuerdo

    pivote = args.get("pivot") in ("1", "true", "True")
    slice_fuente_sievcac = args.get("slice_sievcac") in ("1", "true", "True")
    if slice_fuente_sievcac:
        filtros["fuente"] = "SIEVCAC (CNMH)"

    con = olap.conectar()
    try:
        por_sexo = olap.consultar(
            ["sexo"], ["personas", "pct_aparecidas_con_vida"],
            filtros=filtros, con=con,
        )
        filas_sexo = {f["sexo"]: f for f in por_sexo["filas"]}
        mujeres = filas_sexo.get("Mujer", {})
        hombres = filas_sexo.get("Hombre", {})
        pct_mujeres = mujeres.get("pct_aparecidas_con_vida", 0.0) or 0.0
        pct_hombres = hombres.get("pct_aparecidas_con_vida", 0.0) or 0.0

        indicadores = [
            {
                "etiqueta": "Mujeres aparecidas con vida",
                "valor": round(pct_mujeres, 1),
                "unidad": "%",
                "denominador": mujeres.get("personas", 0),
            },
            {
                "etiqueta": "Hombres aparecidos con vida",
                "valor": round(pct_hombres, 1),
                "unidad": "%",
                "denominador": hombres.get("personas", 0),
            },
            {
                "etiqueta": "Brecha mujeres − hombres",
                "valor": round(pct_mujeres - pct_hombres, 1),
                "unidad": "pp",
                "denominador": None,
            },
        ]

        dims_cruce = ["estado_victima", "sexo"] if pivote else ["sexo", "estado_victima"]
        grafica_barras = olap.consultar(
            dims_cruce, ["personas"], filtros={**filtros, "sexo": ["Hombre", "Mujer", "Sin informacion"]}, con=con
        )

        filtros_lineas = dict(filtros)
        filtros_lineas["sexo"] = ["Hombre", "Mujer"]
        grafica_lineas = olap.consultar(
            ["anio", "sexo"], ["personas", "pct_aparecidas_con_vida"], filtros=filtros_lineas, con=con
        )
        grafica_lineas["filas"] = [f for f in grafica_lineas["filas"] if f["anio"] is not None]

        matriz_res = olap.consultar(dims_cruce, ["personas"], filtros=filtros, con=con)
        matriz = olap.como_matriz(matriz_res, dims_cruce[0], dims_cruce[1], "personas")
        matriz["totales_fila"] = [sum(c for c in fila if c) for fila in matriz["celdas"]]

        opciones_fuente = [f["fuente"] for f in olap.consultar(["fuente"], ["personas"], con=con)["filas"]]
        opciones_periodo = [
            f["periodo_acuerdo"] for f in olap.consultar(["periodo_acuerdo"], ["personas"], con=con)["filas"]
        ]

        return {
            "pregunta": VISTA1_PREGUNTA,
            "dimensiones": ["víctima (sexo, calidad)", "estado (desenlace)", "fuente", "tiempo (periodo_acuerdo)"],
            "medidas": ["Personas registradas", "% aparecidas con vida"],
            "jerarquias": ["estado: grupo_desenlace → estado_victima", "fuente: fuente → tipo_evento"],
            "filtros_aplicados": filtros,
            "pivote": pivote,
            "opciones_filtros": {"fuente": opciones_fuente, "periodo_acuerdo": opciones_periodo},
            "indicadores": indicadores,
            "grafica_barras": grafica_barras,
            "grafica_lineas": grafica_lineas,
            "matriz": matriz,
            "denominador_total": por_sexo["denominador_total"],
            "conocimientos": conocimientos_de_vista("vista1"),
        }
    finally:
        con.close()
VISTA2_PREGUNTA = (
    "¿Qué departamentos y municipios concentran a las personas que siguen "
    "desaparecidas y cómo cambia el porcentaje al bajar de macrorregión a municipio?"
)

# Jerarquía geográfica definida por el Integrante 1 en olap.JERARQUIAS:
# macro_region -> departamento -> municipio
NIVELES_GEO = olap.JERARQUIAS["geografia"]
NOMBRE_NIVEL_GEO = {
    "macro_region": "Macrorregión",
    "departamento": "Departamento",
    "municipio": "Municipio",
}
# Categorías que existen en dim_geografia pero no son un municipio real.
GEO_NO_MUNICIPIO = {"Sin informacion", "Desaparecidos En El Extranjero"}
# Por debajo de este número de personas el % de un grupo no es confiable.
MIN_PERSONAS_CONFIABLE = 30
MEDIDAS_VISTA2 = ["personas", "siguen_desaparecidas", "pct_siguen_desaparecidas"]
ORDEN_DESENLACE = ["Sin resolver", "Resuelto", "Sin informacion"]


def _formato_entero(valor):
    return f"{int(valor or 0):,}".replace(",", ".")


def _formato_pct(valor):
    return f"{(valor or 0):.1f}".replace(".", ",")


def datos_vista2(args):
    # 1. Filtros de las dos dimensiones distintas a la geografía.
    filtros = {}
    for clave in ("fuente", "periodo_acuerdo"):
        valor = args.get(clave)
        if valor:
            filtros[clave] = valor

    # 2. Ruta dentro de la jerarquía geográfica (ej.: Sur > Huila).
    ruta = {}
    for nivel_ruta in NIVELES_GEO[:-1]:
        valor = args.get(nivel_ruta)
        if not valor:
            break
        ruta[nivel_ruta] = valor
    profundidad = len(ruta)
    nivel = NIVELES_GEO[profundidad]
    filtros_sel = {**filtros, **ruta}
    op = args.get("op", "")

    con = olap.conectar()
    try:
        # 3. Operación OLAP: se vuelve a consultar el modelo en el nivel pedido.
        #    Drill-down: del nivel padre al siguiente nivel, filtrando por el valor elegido.
        #    Roll-up: del nivel hijo al nivel superior (las medidas se recalculan con SQL).
        if op == "roll_up" and profundidad < len(NIVELES_GEO) - 1:
            res = olap.roll_up("geografia", NIVELES_GEO[profundidad + 1],
                               MEDIDAS_VISTA2, filtros_sel, con=con)
        elif profundidad > 0 and op != "roll_up":
            res = olap.drill_down("geografia", NIVELES_GEO[profundidad - 1],
                                  MEDIDAS_VISTA2, filtros_sel, con=con)
        else:
            res = olap.consultar([nivel], MEDIDAS_VISTA2, filtros_sel, con=con)
            res["operacion"] = op or "consulta"

        filas = sorted(res["filas"], key=lambda f: f["siguen_desaparecidas"] or 0, reverse=True)
        for f in filas:
            f["etiqueta"] = f[nivel]
            f["confiable"] = (f["personas"] or 0) >= MIN_PERSONAS_CONFIABLE

        # 4. Totales de la selección completa (no se suman ni promedian % de los grupos).
        total = olap.consultar([], MEDIDAS_VISTA2, filtros_sel, con=con)["filas"][0]
        personas_sel = total["personas"] or 0
        sin_resolver_sel = total["siguen_desaparecidas"] or 0
        pct_sel = total["pct_siguen_desaparecidas"] or 0.0

        # Municipios afectados = conteo DISTINTO de municipios (departamento + municipio)
        # con al menos un registro, sin contar "Sin informacion" ni "Desaparecidos en el extranjero".
        munis = olap.consultar(["departamento", "municipio"], ["personas"], filtros_sel, con=con)["filas"]
        municipios_afectados = sum(1 for m in munis if m["municipio"] not in GEO_NO_MUNICIPIO)

        indicadores = [
            {
                "etiqueta": "Personas que siguen desaparecidas",
                "valor": _formato_entero(sin_resolver_sel),
                "unidad": "",
                "denominador": personas_sel,
            },
            {
                "etiqueta": "% que siguen desaparecidas",
                "valor": _formato_pct(pct_sel),
                "unidad": "%",
                "denominador": personas_sel,
            },
            {
                "etiqueta": "Municipios afectados (conteo distinto)",
                "valor": _formato_entero(municipios_afectados),
                "unidad": "",
                "denominador": None,
            },
        ]

        # 5. Comprobación de recálculo: % del grupo padre (ponderado por personas)
        #    frente al promedio simple de los % de sus hijos (lo que NO se debe hacer).
        comprobacion = None
        if profundidad > 0 and filas:
            promedio_simple = sum(f["pct_siguen_desaparecidas"] or 0 for f in filas) / len(filas)
            comprobacion = {
                "grupo": " › ".join(ruta.values()),
                "pct_ponderado": _formato_pct(pct_sel),
                "promedio_simple_hijos": _formato_pct(promedio_simple),
                "hijos": len(filas),
                "nivel_hijos": NOMBRE_NIVEL_GEO[nivel].lower(),
            }

        # 6. Matriz: nivel geográfico actual x grupo_desenlace (personas; el % por fila lo calcula olap.js).
        matriz_res = olap.consultar([nivel, "grupo_desenlace"], ["personas"], filtros_sel, con=con)
        matriz = olap.como_matriz(matriz_res, nivel, "grupo_desenlace", "personas")
        orden_filas = [f[nivel] for f in filas]
        idx = {v: i for i, v in enumerate(matriz["filas"])}
        columnas = [c for c in ORDEN_DESENLACE if c in matriz["columnas"]]
        idx_col = {c: j for j, c in enumerate(matriz["columnas"])}
        celdas = [[matriz["celdas"][idx[v]][idx_col[c]] for c in columnas] for v in orden_filas if v in idx]
        matriz = {
            "filas": [v for v in orden_filas if v in idx],
            "columnas": columnas,
            "celdas": celdas,
            "totales_fila": [sum(c or 0 for c in fila) for fila in celdas],
        }

        opciones_fuente = [f["fuente"] for f in olap.consultar(["fuente"], ["personas"], con=con)["filas"]]
        opciones_periodo = [
            f["periodo_acuerdo"] for f in olap.consultar(["periodo_acuerdo"], ["personas"], con=con)["filas"]
        ]

        return {
            "pregunta": VISTA2_PREGUNTA,
            "dimensiones": ["geografía (macrorregión › departamento › municipio)", "estado (desenlace)",
                            "fuente", "tiempo (periodo_acuerdo)"],
            "medidas": ["Personas registradas", "Personas que siguen desaparecidas",
                        "% que siguen desaparecidas", "Municipios afectados"],
            "jerarquias": ["geografía: macro_region → departamento → municipio"],
            "filtros_aplicados": filtros,
            "ruta": [{"nivel": k, "nombre_nivel": NOMBRE_NIVEL_GEO[k], "valor": v} for k, v in ruta.items()],
            "nivel": nivel,
            "nombre_nivel": NOMBRE_NIVEL_GEO[nivel],
            "nivel_siguiente": NIVELES_GEO[profundidad + 1] if profundidad + 1 < len(NIVELES_GEO) else None,
            "operacion": res.get("operacion", "consulta"),
            "min_personas_confiable": MIN_PERSONAS_CONFIABLE,
            "opciones_filtros": {"fuente": opciones_fuente, "periodo_acuerdo": opciones_periodo},
            "indicadores": indicadores,
            "filas": filas,
            "top10": filas[:10],
            "matriz": matriz,
            "comprobacion": comprobacion,
            "denominador_total": personas_sel,
            "pct_seleccion": round(pct_sel, 1),
            "sql": res.get("sql"),
            "conocimientos": conocimientos_de_vista("vista2"),
        }
    finally:
        con.close()

# ---------- Vista 3 · Evolución temporal ----------

VISTA3_PREGUNTA = (
    "¿Cómo evolucionaron las personas registradas y el porcentaje que sigue desaparecido "
    "entre 2007 y 2025, y cambia ese patrón entre el periodo anterior y el posterior al "
    "Acuerdo de Paz según la fuente y el sexo?"
)

NIVELES_TIEMPO = olap.JERARQUIAS["tiempo"]  # anio -> trimestre -> mes
NOMBRE_NIVEL_TIEMPO = {"anio": "Año", "trimestre": "Trimestre", "mes": "Mes"}
ANIOS_COMPARABLES = list(range(2007, 2026))  # 2026 llega hasta junio: se excluye
# 2007-2016 tiene 10 años y 2017-2025 tiene 9: se comparan promedios anuales, no totales.
ANIOS_POR_PERIODO = {"Antes (2007-2016)": 10, "Despues (2017-2025)": 9}
MEDIDAS_VISTA3 = ["personas", "siguen_desaparecidas", "pct_siguen_desaparecidas"]
COLUMNAS_MATRIZ_V3 = ("grupo_desenlace", "sexo", "fuente")
MESES_ORDEN = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
               "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _formato_decimal(valor):
    texto = f"{(valor or 0):,.1f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _entero_opcional(valor, nombre):
    if valor in (None, ""):
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise olap.ConsultaInvalida(f"{nombre} no es un número válido: {valor!r}")


def _etiqueta_tiempo(nivel, valor):
    if valor is None:
        return "Mes desconocido"
    if nivel == "anio":
        return str(int(valor))
    if nivel == "trimestre":
        return f"T{int(valor)}"
    return str(valor).capitalize()


def _orden_tiempo(nivel, valor):
    # olap ordena los meses por nombre; aquí se ordenan por calendario.
    if valor is None:
        return 99
    if nivel == "mes":
        return MESES_ORDEN.index(valor) if valor in MESES_ORDEN else 98
    return int(valor)


def _matriz_tiempo(filas, nivel, columna, transponer):
    tiempos = sorted({f[nivel] for f in filas}, key=lambda v: _orden_tiempo(nivel, v))
    if columna == "grupo_desenlace":
        otros = sorted({f[columna] for f in filas},
                       key=lambda v: ORDEN_DESENLACE.index(v) if v in ORDEN_DESENLACE else 99)
    else:
        otros = sorted({f[columna] for f in filas}, key=str)
    celda = {(f[nivel], f[columna]): f["personas"] for f in filas}
    etiquetas_tiempo = [_etiqueta_tiempo(nivel, t) for t in tiempos]
    if transponer:
        nombres_filas, nombres_cols = otros, etiquetas_tiempo
        celdas = [[celda.get((t, o)) for t in tiempos] for o in otros]
    else:
        nombres_filas, nombres_cols = etiquetas_tiempo, otros
        celdas = [[celda.get((t, o)) for o in otros] for t in tiempos]
    return {
        "filas": nombres_filas,
        "columnas": nombres_cols,
        "celdas": celdas,
        "totales_fila": [sum(c or 0 for c in fila) for fila in celdas],
    }


def datos_vista3(args):
    op = args.get("op", "")
    fuente = args.get("fuente") or None
    sexo = args.get("sexo") or None
    columna = args.get("columna") if args.get("columna") in COLUMNAS_MATRIZ_V3 else "grupo_desenlace"
    transponer = args.get("transponer") in ("1", "true", "True")

    anio = _entero_opcional(args.get("anio"), "anio")
    trimestre = _entero_opcional(args.get("trimestre"), "trimestre")
    if anio not in ANIOS_COMPARABLES:
        anio = None
    if anio is None or trimestre not in (1, 2, 3, 4):
        trimestre = None

    # Filtros de las dimensiones fuente y víctima (sexo), más el rango comparable.
    base = {"anio": ANIOS_COMPARABLES}
    filtros_aplicados = {}
    if fuente:
        base["fuente"] = fuente
        filtros_aplicados["fuente"] = fuente
    if sexo:
        base["sexo"] = sexo
        filtros_aplicados["sexo"] = sexo

    # Ruta dentro de la jerarquía de tiempo (ej.: 2017 > T1).
    filtros_sel = dict(base)
    ruta = []
    if anio is not None:
        filtros_sel["anio"] = anio
        ruta.append({"nivel": "anio", "nombre_nivel": "Año", "valor": str(anio)})
    if trimestre is not None:
        filtros_sel["trimestre"] = trimestre
        ruta.append({"nivel": "trimestre", "nombre_nivel": "Trimestre", "valor": f"T{trimestre}"})
    profundidad = len(ruta)
    nivel = NIVELES_TIEMPO[profundidad]

    con = olap.conectar()
    try:
        # Operación OLAP: se vuelve a consultar el modelo en el nivel pedido.
        if op == "roll_up" and profundidad < len(NIVELES_TIEMPO) - 1:
            res = olap.roll_up("tiempo", NIVELES_TIEMPO[profundidad + 1],
                               MEDIDAS_VISTA3, filtros_sel, con=con)
        elif op == "drill_down" and profundidad > 0:
            res = olap.drill_down("tiempo", NIVELES_TIEMPO[profundidad - 1],
                                  MEDIDAS_VISTA3, filtros_sel, con=con)
        else:
            res = olap.consultar([nivel], MEDIDAS_VISTA3, filtros_sel, con=con)
            res["operacion"] = "pivot" if op == "pivot" else "consulta"

        total = olap.consultar([], MEDIDAS_VISTA3, filtros_sel, con=con)["filas"][0]
        por_periodo = olap.consultar(["periodo_acuerdo"], ["personas"], base, con=con)["filas"]
        matriz_res = olap.consultar([nivel, columna], ["personas"], filtros_sel, con=con)
        opciones_fuente = [f["fuente"] for f in olap.consultar(["fuente"], ["personas"], con=con)["filas"]]
        opciones_sexo = [f["sexo"] for f in olap.consultar(["sexo"], ["personas"], con=con)["filas"]]
    finally:
        con.close()

    serie = []
    for f in sorted(res["filas"], key=lambda f: _orden_tiempo(nivel, f[nivel])):
        clave = f[nivel]
        anio_fila = int(clave) if nivel == "anio" else anio
        serie.append({
            "etiqueta": _etiqueta_tiempo(nivel, clave),
            "clave": int(clave) if nivel == "anio" else clave,
            "personas": f["personas"],
            "siguen_desaparecidas": f["siguen_desaparecidas"],
            "pct_siguen_desaparecidas": f["pct_siguen_desaparecidas"],
            "confiable": (f["personas"] or 0) >= MIN_PERSONAS_CONFIABLE,
            "periodo": "Antes (2007-2016)" if anio_fila <= 2016 else "Despues (2017-2025)",
        })

    personas_sel = total["personas"] or 0
    pct_sel = total["pct_siguen_desaparecidas"] or 0.0

    # Promedio anual por periodo (periodos de distinta duración).
    promedio = {p["periodo_acuerdo"]: (p["personas"] or 0) / ANIOS_POR_PERIODO[p["periodo_acuerdo"]]
                for p in por_periodo if p["periodo_acuerdo"] in ANIOS_POR_PERIODO}
    antes, despues = promedio.get("Antes (2007-2016)"), promedio.get("Despues (2017-2025)")
    if antes and despues is not None:
        variacion = f"{100 * (despues - antes) / antes:+.1f}".replace(".", ",")
        valor_promedio = f"{_formato_decimal(antes)} → {_formato_decimal(despues)} ({variacion} %)"
    else:
        valor_promedio = "Sin datos"

    indicadores = [
        {"etiqueta": "Personas registradas en la selección",
         "valor": _formato_entero(personas_sel), "unidad": "", "denominador": None},
        {"etiqueta": "% que siguen desaparecidas",
         "valor": _formato_pct(pct_sel), "unidad": "%", "denominador": personas_sel},
        {"etiqueta": "Promedio anual de personas: 2007-2016 → 2017-2025",
         "valor": valor_promedio, "unidad": "personas por año", "denominador": None},
    ]

    suma_filas = sum(f["personas"] or 0 for f in serie)
    comprobacion = {
        "nivel": NOMBRE_NIVEL_TIEMPO[nivel].lower(),
        "filas": len(serie),
        "total_seleccion": personas_sel,
        "suma_filas": suma_filas,
        "coincide": suma_filas == personas_sel,
    }

    return {
        "pregunta": VISTA3_PREGUNTA,
        "dimensiones": ["tiempo (año › trimestre › mes, periodo_acuerdo)", "estado (desenlace)",
                        "fuente", "víctima (sexo)"],
        "medidas": ["Personas registradas", "Personas que siguen desaparecidas",
                    "% que siguen desaparecidas", "Promedio anual de personas por periodo"],
        "jerarquias": ["tiempo: año → trimestre → mes"],
        "filtros_aplicados": filtros_aplicados,
        "ruta": ruta,
        "nivel": nivel,
        "nombre_nivel": NOMBRE_NIVEL_TIEMPO[nivel],
        "nivel_siguiente": NIVELES_TIEMPO[profundidad + 1] if profundidad + 1 < len(NIVELES_TIEMPO) else None,
        "operacion": res.get("operacion", "consulta"),
        "min_personas_confiable": MIN_PERSONAS_CONFIABLE,
        "opciones_filtros": {"fuente": opciones_fuente, "sexo": opciones_sexo},
        "indicadores": indicadores,
        "serie": serie,
        "matriz": _matriz_tiempo(matriz_res["filas"], nivel, columna, transponer),
        "comprobacion": comprobacion,
        "denominador_total": personas_sel,
        "pct_seleccion": round(pct_sel, 1),
        "sql": res.get("sql"),
        "conocimientos": conocimientos_de_vista("vista3"),
    }

VISTA_API = {
    "vista1": datos_vista1,
    "vista2": datos_vista2,
    "vista3": datos_vista3,
}


@app.route("/api/etapa5/<vista>")
def api_etapa5(vista):
    handler = VISTA_API.get(vista)
    if handler is None:
        abort(404, description=f"La vista {vista!r} todavía no tiene API (la arma su dueño en su turno).")
    try:
        return jsonify(handler(request.args))
    except olap.ConsultaInvalida as exc:
        abort(400, description=str(exc))
    except FileNotFoundError as exc:
        abort(500, description=str(exc))


def render_vista1():
    return render_template("etapa5_vista_perfil.html", current_slug="vista1")

def render_vista2():
    return render_template(
        "etapa5_vista_territorio.html",
        current_slug="vista2",
        conocimientos=conocimientos_de_vista("vista2"),
    )
 //Dirección de la vista 3: Evolución temporal
def render_vista3():
    return render_template(
        "etapa5_vista_tiempo.html",
        current_slug="vista3",
        conocimientos=conocimientos_de_vista("vista3"),
    )
# Qué tablero de conocimiento evidente (Etapa 4) profundiza cada vista de esta etapa.
ETAPA5_TABLERO_A_VISTA = {
    "poblacion": "vista1",
    "territorio": "vista2",
    "tiempo": "vista3",
    "perfiles": "vista4",
}


def render_proposito():
    conocimiento_evidente = {}
    if CONOCIMIENTOS_PATH.exists():
        with open(CONOCIMIENTOS_PATH, encoding="utf-8") as f:
            conocimiento_evidente = json.load(f)

    relacion = []
    for tablero in conocimiento_evidente.get("tableros", []):
        vista_slug = ETAPA5_TABLERO_A_VISTA.get(tablero["slug"])
        vista_item = ETAPA5_MENU_BY_SLUG.get(vista_slug)
        relacion.append({
            "tablero": tablero,
            "vista_slug": vista_slug,
            "vista_titulo": vista_item["titulo"] if vista_item else None,
        })

    return render_template(
        "etapa5_proposito.html",
        current_slug="proposito",
        fuente=conocimiento_evidente.get("fuente"),
        periodo=conocimiento_evidente.get("periodo"),
        base=conocimiento_evidente.get("base"),
        relacion=relacion,
        vistas=[v for v in ETAPA5_MENU if v["slug"].startswith("vista")],
    )


@app.route("/etapa5/<slug>")
def etapa5_pagina(slug):
    if slug not in ETAPA5_MENU_BY_SLUG:
        abort(404)

    if slug == "proposito":
        return render_proposito()

    if slug == "vista1":
        return render_vista1()

    if slug == "vista2":
        return render_vista2()

    if slug == "vista3":
        return render_vista3()

    item = ETAPA5_MENU_BY_SLUG[slug]
    return render_template(
        "etapa1_placeholder.html",
        numero=item["numero"],
        titulo=item["titulo"],
        current_slug=slug,
    )

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
