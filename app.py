import csv
import io
import json
import os
import re
from urllib.parse import urlparse, parse_qs
from functools import lru_cache
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
ETAPA6_VIDEO_URL = "https://youtu.be/SiBh-1_yS-Q"
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

ETAPA6_MENU = [
    {"numero": 1, "slug": "sintesis", "titulo": "Síntesis, objetivo y datos"},
    {"numero": 2, "slug": "supervisado", "titulo": "Modelo supervisado (clasificación)"},
    {"numero": 3, "slug": "clustering", "titulo": "Agrupamiento de municipios"},
    {"numero": 4, "slug": "comentarios", "titulo": "Comentarios de YouTube"},
    {"numero": 5, "slug": "conclusiones", "titulo": "Conclusiones integradas"},
    {"numero": 6, "slug": "informe", "titulo": "Informe técnico (PDF)"},
    {"numero": 7, "slug": "video", "titulo": "Video de sustentación"},
]
ETAPA6_MENU_BY_SLUG = {item["slug"]: item for item in ETAPA6_MENU}

CONOCIMIENTO_OCULTO_PATH = DATA_DIR / "conocimiento_oculto.json"
ETAPA6_STATIC = BASE_DIR / "static" / "etapa6"
ETAPA6_INFORME = "informe_tecnico_oculto.pdf"
ETAPA6_VIDEO_LOCAL = "video_sustentacion.mp4"
ETAPA6_VIDEO_URL = os.environ.get("ETAPA6_VIDEO_URL", "https://youtu.be/SiBh-1_yS-Q")


@app.context_processor
def inject_menu():
    return {
        "etapa1_menu": ETAPA1_MENU,
        "etapa2_menu": ETAPA2_MENU,
        "etapa3_menu": ETAPA3_MENU,
        "etapa4_menu": ETAPA4_MENU,
        "etapa5_menu": ETAPA5_MENU,
        "etapa6_menu": ETAPA6_MENU,
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
# ---------- Vista 4 · Perfiles combinados ----------

VISTA4_PREGUNTA = (
    "¿Qué combinaciones de sexo, zona del hecho y departamento tienen la mayor "
    "proporción de personas sin resolver?"
)
MEDIDAS_VISTA4 = ["personas", "siguen_desaparecidas", "pct_siguen_desaparecidas"]
FILTROS_VISTA4 = ("fuente", "macro_region", "departamento", "zona_hecho", "sexo")
FILTROS_DICE_VISTA4 = ("macro_region", "departamento", "zona_hecho", "sexo")
# Nunca se suman fuentes: si no se elige una, se usa esta.
FUENTE_POR_DEFECTO_V4 = "Medicina Legal (SIRDEC)"
SIN_INFO = "Sin informacion"


def _opciones_vista4(columna, con):
    filas = olap.consultar([columna], ["personas"], con=con)["filas"]
    return [f[columna] for f in filas if f[columna] is not None]


def _clave_orden_v4(valor):
    # "Sin informacion" siempre al final, separado de las respuestas reales.
    return (valor == SIN_INFO, str(valor))


def _celda_v4(fila):
    personas = fila["personas"] or 0
    return {
        "personas": personas,
        "pct": fila["pct_siguen_desaparecidas"] or 0.0,
        "confiable": personas >= MIN_PERSONAS_CONFIABLE,
    }


def datos_vista4(args):
    # 1. Filtros: fuente (dimensión fuente) + los cortes del Dice
    #    (geografía, zona y víctima).
    filtros = {}
    for clave in FILTROS_VISTA4:
        valor = args.get(clave)
        if valor:
            filtros[clave] = valor
    filtros.setdefault("fuente", FUENTE_POR_DEFECTO_V4)
    fuente = filtros["fuente"]
    pivote = args.get("pivot") in ("1", "true", "True")
    n_dice = len([c for c in FILTROS_DICE_VISTA4 if c in filtros])

    con = olap.conectar()
    try:
        total = olap.consultar([], MEDIDAS_VISTA4, filtros, con=con)["filas"][0]
        base_fuente = olap.consultar([], MEDIDAS_VISTA4, {"fuente": fuente}, con=con)["filas"][0]

        combos = olap.consultar(["sexo", "zona_hecho"], MEDIDAS_VISTA4, filtros, con=con)["filas"]
        por_zona = olap.consultar(["zona_hecho", "grupo_desenlace"], ["personas"], filtros, con=con)["filas"]

        # Pivot: se vuelve a consultar el modelo con las dimensiones invertidas,
        # y los totales de fila se recalculan con SQL en ese nuevo nivel.
        dims = ["sexo", "zona_hecho"] if pivote else ["zona_hecho", "sexo"]
        celdas_res = olap.pivot(dims, MEDIDAS_VISTA4, filtros, con=con)
        totales_fila_res = olap.consultar([dims[0]], MEDIDAS_VISTA4, filtros, con=con)["filas"]

        top_res = olap.consultar(["sexo", "zona_hecho", "departamento"], MEDIDAS_VISTA4, filtros, con=con)["filas"]
        opciones = {c: _opciones_vista4(c, con) for c in FILTROS_VISTA4}
    finally:
        con.close()

    personas_sel = total["personas"] or 0
    pct_sel = total["pct_siguen_desaparecidas"] or 0.0
    personas_fuente = base_fuente["personas"] or 0
    pct_fuente = base_fuente["pct_siguen_desaparecidas"] or 0.0
    diferencia = pct_sel - pct_fuente

    indicadores = [
        {"etiqueta": "Personas en la combinación seleccionada",
         "valor": _formato_entero(personas_sel), "unidad": "", "denominador": None},
        {"etiqueta": "% sin resolver de la combinación",
         "valor": _formato_pct(pct_sel), "unidad": "%", "denominador": personas_sel},
        {"etiqueta": f"Diferencia frente al total de {fuente} ({_formato_pct(pct_fuente)} %)",
         "valor": f"{diferencia:+.1f}".replace(".", ","), "unidad": "pp",
         "denominador": personas_fuente},
    ]

    # Gráfica 1: % sin resolver por sexo + zona, de mayor a menor.
    # Las combinaciones con menos de 30 personas van al final y no se destacan.
    combos = sorted(combos, key=lambda f: ((f["personas"] or 0) < MIN_PERSONAS_CONFIABLE,
                                           -(f["pct_siguen_desaparecidas"] or 0)))
    barras_combos = [
        {"etiqueta": f"{f['sexo']} · {f['zona_hecho']}", "sexo": f["sexo"], **_celda_v4(f)}
        for f in combos
    ]

    # Matriz zona × sexo (o sexo × zona con Pivot): % sin resolver y personas por celda.
    filas_v = sorted({f[dims[0]] for f in celdas_res["filas"]}, key=_clave_orden_v4)
    cols_v = sorted({f[dims[1]] for f in celdas_res["filas"]}, key=_clave_orden_v4)
    por_celda = {(f[dims[0]], f[dims[1]]): f for f in celdas_res["filas"]}
    por_fila = {f[dims[0]]: f for f in totales_fila_res}
    matriz = {
        "fila_dim": dims[0],
        "columna_dim": dims[1],
        "filas": filas_v,
        "columnas": cols_v,
        "celdas": [[_celda_v4(por_celda[(fv, cv)]) if (fv, cv) in por_celda else None
                    for cv in cols_v] for fv in filas_v],
        "totales_fila": [_celda_v4(por_fila[fv]) for fv in filas_v],
    }

    # Ranking sexo + zona + departamento (solo n >= 30 y sin "Sin informacion").
    ranking = [
        f for f in top_res
        if (f["personas"] or 0) >= MIN_PERSONAS_CONFIABLE
        and SIN_INFO not in (f["sexo"], f["zona_hecho"], f["departamento"])
    ]
    ranking.sort(key=lambda f: f["pct_siguen_desaparecidas"] or 0, reverse=True)
    top_combinaciones = [
        {"combinacion": f"{f['sexo']} · {f['zona_hecho']} · {f['departamento']}", **_celda_v4(f)}
        for f in ranking[:10]
    ]

    aviso = None
    if personas_sel == 0:
        aviso = "La combinación elegida no tiene personas registradas."
    elif personas_sel < MIN_PERSONAS_CONFIABLE:
        aviso = (f"La selección tiene solo {personas_sel} personas (menos de "
                 f"{MIN_PERSONAS_CONFIABLE}): el % no es confiable.")

    return {
        "pregunta": VISTA4_PREGUNTA,
        "dimensiones": ["víctima (sexo)", "zona (zona del hecho)",
                        "geografía (macrorregión › departamento)", "estado (desenlace)", "fuente"],
        "medidas": ["Personas registradas", "Personas que siguen desaparecidas",
                    "% que siguen desaparecidas"],
        "jerarquias": ["geografía: macro_region → departamento", "estado: grupo_desenlace → estado_victima"],
        "filtros_aplicados": filtros,
        "pivote": pivote,
        "n_dice": n_dice,
        "min_personas_confiable": MIN_PERSONAS_CONFIABLE,
        "opciones_filtros": opciones,
        "indicadores": indicadores,
        "grafica_combos": barras_combos,
        "grafica_zonas": por_zona,
        "matriz": matriz,
        "top_combinaciones": top_combinaciones,
        "aviso": aviso,
        "denominador_total": personas_sel,
        "sql": celdas_res.get("sql"),
        "conocimientos": conocimientos_de_vista("vista4"),
    }

# ---------- Operaciones, validaciones y conclusiones ----------

FUENTE_ML = "Medicina Legal (SIRDEC)"
FUENTE_SIEVCAC = "SIEVCAC (CNMH)"
FUENTES_MODELO = (FUENTE_ML, FUENTE_SIEVCAC)
PERIODO_DESPUES = "Despues (2017-2025)"
ANIO_EJEMPLO = 2017
MEDIDAS_OP = ["personas", "siguen_desaparecidas", "pct_siguen_desaparecidas"]
TRATADO_CSV = PROCESSED_DIR / "dataset_tratado.csv"
CARGA_RESUMEN_PATH = DATA_DIR / "olap" / "carga_resumen.json"

CONDICIONES_ANALISIS = [
    ("Granularidad consistente",
     "Cada fila de fact_desaparicion es una persona registrada por una fuente. El script de carga comprueba que el número de filas no cambie y que id_registro sea único."),
    ("Relaciones que no multiplican valores",
     "Las seis dimensiones se unen por una clave primaria única y cada hecho tiene una sola clave por dimensión, así que los JOIN no repiten filas. La página de validaciones lo comprueba."),
    ("Registros, entidades únicas y sumas",
     "Las personas son la suma de num_personas (un registro por persona y fuente) y los municipios afectados se cuentan con COUNT(DISTINCT). Una misma persona puede estar en las dos fuentes, por eso los filtros de fuente advierten cuando se eligen todas."),
    ("Denominador de los porcentajes",
     "Cada porcentaje indica sobre qué se calcula: las personas del grupo que se está mostrando."),
    ("Recalcular al cambiar de nivel",
     "Los porcentajes se definen como cociente de sumas (siguen desaparecidas ÷ personas) y se recalculan en SQL en cada nivel de la jerarquía."),
    ("No sumar ni promediar porcentajes",
     "Al cambiar de nivel, la vista de territorio contrasta el porcentaje ponderado con el promedio simple de los niveles inferiores, y la de tiempo verifica que la suma de las filas iguale el total de la selección."),
    ("Periodos equivalentes",
     "La serie comparable usa 2007-2025 (2026 llega hasta junio). Como 2007-2016 tiene 10 años y 2017-2025 tiene 9, se comparan promedios anuales y no totales."),
    ("Faltantes, desconocidos y negativos",
     "'Sin informacion' se conserva como categoría propia y no se mezcla con 'Sin resolver': la primera indica que se desconoce el estado y la segunda que la persona sigue desaparecida."),
    ("Jerarquías válidas",
     "Geografía: macrorregión → departamento → municipio. Tiempo: año → trimestre → mes. Estado: grupo de desenlace → estado. Fuente: fuente → tipo de evento. Cada nivel pertenece a un único nivel superior."),
    ("Asociación y causalidad",
     "Los hallazgos describen asociaciones entre dimensiones. Ninguno prueba que una variable cause a otra."),
    ("Hipótesis",
     "Las explicaciones que los datos no permiten comprobar, como la presencia de grupos armados o diferencias de registro entre fuentes, se presentan como hipótesis."),
]


def _tabla_medidas(titulo, titulo_dim, filas, etiqueta):
    return {
        "titulo": titulo,
        "columnas": [titulo_dim, "Personas", "Siguen desaparecidas", "% que siguen desaparecidas"],
        "filas": [[etiqueta(f), _formato_entero(f["personas"]), _formato_entero(f["siguen_desaparecidas"]),
                   _formato_pct(f["pct_siguen_desaparecidas"]) + " %"] for f in filas],
    }


def _tabla_matriz(titulo, titulo_fila, m):
    filas = []
    for nombre, valores in zip(m["filas"], m["celdas"]):
        filas.append([nombre] + [_formato_entero(v) for v in valores]
                     + [_formato_entero(sum(v or 0 for v in valores))])
    return {"titulo": titulo,
            "columnas": [titulo_fila] + [str(c) for c in m["columnas"]] + ["Total fila"],
            "filas": filas}


def _extremos(filas):
    validas = [f for f in filas if (f["personas"] or 0) >= MIN_PERSONAS_CONFIABLE
               and f["pct_siguen_desaparecidas"] is not None]
    if len(validas) < 2:
        return None
    return (min(validas, key=lambda f: f["pct_siguen_desaparecidas"]),
            max(validas, key=lambda f: f["pct_siguen_desaparecidas"]))


def _pct_fila(m, fila, columna):
    if fila not in m["filas"] or columna not in m["columnas"]:
        return None
    celdas = m["celdas"][m["filas"].index(fila)]
    total = sum(v or 0 for v in celdas)
    return 100 * (celdas[m["columnas"].index(columna)] or 0) / total if total else None


def _op(numero, nombre, definicion, vista, dimensiones, medidas, nivel_filtros,
        procedimiento, tablas, interpretacion, sql):
    return {
        "numero": numero, "nombre": nombre, "definicion": definicion,
        "vista_slug": vista, "vista_titulo": ETAPA5_MENU_BY_SLUG[vista]["titulo"],
        "dimensiones": dimensiones, "medidas": medidas, "nivel_filtros": nivel_filtros,
        "procedimiento": procedimiento, "tablas": tablas,
        "interpretacion": interpretacion, "sql": sql,
    }


def datos_operaciones():
    con = olap.conectar()
    try:
        # 1. Drill-down: macrorregión -> departamento (Sur, Medicina Legal)
        macro = olap.consultar(["macro_region"], MEDIDAS_OP, {"fuente": FUENTE_ML}, con=con)["filas"]
        drill = olap.drill_down("geografia", "macro_region", MEDIDAS_OP,
                                {"fuente": FUENTE_ML, "macro_region": "Sur"}, con=con)
        deps = sorted(drill["filas"], key=lambda f: f["siguen_desaparecidas"] or 0, reverse=True)
        sur = next((f for f in macro if f["macro_region"] == "Sur"), None)
        interp1 = []
        if sur:
            interp1.append(
                f"En el nivel de macrorregión, el Sur reúne {_formato_entero(sur['personas'])} personas de "
                f"Medicina Legal y {_formato_pct(sur['pct_siguen_desaparecidas'])} % siguen desaparecidas "
                f"(denominador: personas del Sur).")
        ext = _extremos(deps)
        if ext:
            bajo, alto = ext
            interp1.append(
                f"Al bajar a departamento, el porcentaje va de {_formato_pct(bajo['pct_siguen_desaparecidas'])} % "
                f"en {bajo['departamento']} a {_formato_pct(alto['pct_siguen_desaparecidas'])} % en "
                f"{alto['departamento']} (solo grupos con al menos {MIN_PERSONAS_CONFIABLE} personas): "
                f"el promedio de la macrorregión resume situaciones distintas.")
        interp1.append("Cada porcentaje se recalcula con SQL en el nivel mostrado (siguen desaparecidas ÷ "
                       "personas del grupo); no es el promedio de los porcentajes del nivel inferior.")

        # 2. Roll-up: mes -> trimestre (2017, Medicina Legal)
        filtros_r = {"fuente": FUENTE_ML, "anio": ANIO_EJEMPLO}
        meses = sorted(olap.consultar(["mes"], MEDIDAS_OP, filtros_r, con=con)["filas"],
                       key=lambda f: _orden_tiempo("mes", f["mes"]))
        roll = olap.roll_up("tiempo", "mes", MEDIDAS_OP, filtros_r, con=con)
        trims = sorted(roll["filas"], key=lambda f: _orden_tiempo("trimestre", f["trimestre"]))
        total_anio = olap.consultar([], MEDIDAS_OP, filtros_r, con=con)["filas"][0]
        pcts_m = [f["pct_siguen_desaparecidas"] for f in meses if f["pct_siguen_desaparecidas"] is not None]
        interp2 = [
            f"Los meses de {ANIO_EJEMPLO} suman {_formato_entero(sum(f['personas'] or 0 for f in meses))} personas, "
            f"los trimestres suman {_formato_entero(sum(f['personas'] or 0 for f in trims))} y el año completo "
            f"tiene {_formato_entero(total_anio['personas'])}: al subir de nivel no se pierden ni se duplican registros.",
        ]
        if pcts_m and total_anio["pct_siguen_desaparecidas"] is not None:
            interp2.append(
                f"El porcentaje del año ({_formato_pct(total_anio['pct_siguen_desaparecidas'])} %) se calcula con las "
                f"personas del año; el promedio simple de los porcentajes mensuales daría "
                f"{_formato_pct(sum(pcts_m) / len(pcts_m))} %, que no es el valor correcto.")
        interp2.append("Los registros sin mes aparecen como 'Mes desconocido' y no se reparten entre trimestres.")

        # 3. Slice: fuente = SIEVCAC, agrupado por calidad de la víctima
        sl = olap.consultar(["calidad_victima"], MEDIDAS_OP, {"fuente": FUENTE_SIEVCAC}, con=con)
        filas_s = sorted(sl["filas"], key=lambda f: f["personas"] or 0, reverse=True)
        total_s = sum(f["personas"] or 0 for f in filas_s)
        tabla_s = {
            "titulo": "Resultado del slice (fuente = SIEVCAC)",
            "columnas": ["Calidad de la víctima", "Personas",
                         f"% de las personas de SIEVCAC (denominador: {_formato_entero(total_s)})",
                         "% que siguen desaparecidas"],
            "filas": [[f["calidad_victima"], _formato_entero(f["personas"]),
                       _formato_pct(100 * (f["personas"] or 0) / total_s if total_s else 0) + " %",
                       _formato_pct(f["pct_siguen_desaparecidas"]) + " %"] for f in filas_s],
        }
        interp3 = []
        if filas_s and total_s:
            top = filas_s[0]
            interp3.append(
                f"Con la fuente fijada en SIEVCAC quedan {_formato_entero(total_s)} personas; la categoría más "
                f"frecuente es '{top['calidad_victima']}' con {_formato_entero(top['personas'])} "
                f"({_formato_pct(100 * top['personas'] / total_s)} %).")
        interp3.append("La calidad de la víctima (civil o combatiente) solo se registra en SIEVCAC, por eso este "
                       "análisis necesita el slice y no puede extenderse a Medicina Legal.")

        # 4. Dice: fuente + periodo + macrorregión, agrupado por sexo
        filtros_d = {"fuente": FUENTE_ML, "periodo_acuerdo": PERIODO_DESPUES, "macro_region": "Sur"}
        dice = olap.consultar(["sexo"], MEDIDAS_OP, filtros_d, con=con)
        tot_d = olap.consultar([], MEDIDAS_OP, filtros_d, con=con)["filas"][0]
        tot_ml = olap.consultar([], MEDIDAS_OP, {"fuente": FUENTE_ML}, con=con)["filas"][0]
        interp4 = []
        if tot_d["personas"] and tot_ml["personas"]:
            interp4.append(
                f"La combinación de tres filtros (fuente, periodo y macrorregión) deja "
                f"{_formato_entero(tot_d['personas'])} de las {_formato_entero(tot_ml['personas'])} personas de "
                f"Medicina Legal ({_formato_pct(100 * tot_d['personas'] / tot_ml['personas'])} %). De ellas, "
                f"{_formato_pct(tot_d['pct_siguen_desaparecidas'])} % siguen desaparecidas, frente a "
                f"{_formato_pct(tot_ml['pct_siguen_desaparecidas'])} % en toda la fuente.")
        interp4.append("Diferencia con el slice: aquí se restringen varias dimensiones a la vez, así que el "
                       "resultado describe un subconjunto concreto y no debe leerse como el comportamiento general.")

        # 5. Pivot: sexo x desenlace, dos disposiciones del mismo resultado
        piv = olap.pivot(["sexo", "grupo_desenlace"], ["personas"], {"fuente": FUENTE_ML}, con=con)
        m_a = olap.como_matriz(piv, "sexo", "grupo_desenlace", "personas")
        m_b = olap.como_matriz(piv, "grupo_desenlace", "sexo", "personas")
        pa = _pct_fila(m_a, "Mujer", "Sin resolver")
        pb = _pct_fila(m_b, "Sin resolver", "Mujer")
        interp5 = []
        if pa is not None and pb is not None:
            interp5.append(
                f"Con el sexo en las filas se lee: del total de mujeres registradas, {_formato_pct(pa)} % siguen "
                f"sin resolver. Con el desenlace en las filas se lee: del total de personas sin resolver, "
                f"{_formato_pct(pb)} % son mujeres.")
        interp5.append("Las dos proporciones responden preguntas distintas porque cambia el denominador "
                       "(mujeres registradas frente a personas sin resolver). El pivot cambia la perspectiva "
                       "de lectura sin cambiar los datos.")
    finally:
        con.close()

    return [
        _op(1, "Drill-down",
            "Bajar de un nivel general a uno más detallado dentro de una jerarquía.",
            "vista2", "Geografía (macrorregión → departamento), Fuente",
            "Personas, personas que siguen desaparecidas, % que siguen desaparecidas",
            "Nivel: de macrorregión a departamento · Filtros: fuente = Medicina Legal, macrorregión = Sur",
            "olap.drill_down('geografia', 'macro_region', medidas, filtros) agrupa por el siguiente nivel y "
            "mantiene el filtro del valor elegido. Las medidas se recalculan con SQL.",
            [_tabla_medidas("Nivel general: macrorregión", "Macrorregión", macro, lambda f: f["macro_region"]),
             _tabla_medidas("Nivel detallado: departamentos del Sur", "Departamento", deps, lambda f: f["departamento"])],
            interp1, drill["sql"]),
        _op(2, "Roll-up",
            "Agrupar los resultados en un nivel superior de la jerarquía.",
            "vista3", "Tiempo (mes → trimestre), Fuente",
            "Personas, personas que siguen desaparecidas, % que siguen desaparecidas",
            f"Nivel: de mes a trimestre · Filtros: fuente = Medicina Legal, año = {ANIO_EJEMPLO}",
            "olap.roll_up('tiempo', 'mes', medidas, filtros) agrupa por el nivel superior (trimestre). Las "
            "sumas se vuelven a calcular en la base de datos, no se suman porcentajes.",
            [_tabla_medidas(f"Nivel detallado: meses de {ANIO_EJEMPLO}", "Mes", meses, lambda f: _etiqueta_tiempo("mes", f["mes"])),
             _tabla_medidas(f"Nivel superior: trimestres de {ANIO_EJEMPLO}", "Trimestre", trims, lambda f: _etiqueta_tiempo("trimestre", f["trimestre"]))],
            interp2, roll["sql"]),
        _op(3, "Slice",
            "Seleccionar un valor de una dimensión para estudiar un subconjunto.",
            "vista1", "Fuente (valor fijo), Víctima (calidad)",
            "Personas, participación dentro de la fuente, % que siguen desaparecidas",
            "Filtro: fuente = SIEVCAC (CNMH) · Agrupación: calidad de la víctima",
            "olap.consultar(['calidad_victima'], medidas, {'fuente': 'SIEVCAC (CNMH)'}) fija una sola dimensión "
            "y agrupa por otra.",
            [tabla_s], interp3, sl["sql"]),
        _op(4, "Dice",
            "Seleccionar un subconjunto combinando filtros de dos o más dimensiones.",
            "vista2", "Fuente, Tiempo (periodo frente al Acuerdo), Geografía (macrorregión), Víctima (sexo)",
            "Personas, personas que siguen desaparecidas, % que siguen desaparecidas",
            "Filtros: fuente = Medicina Legal, periodo = 2017-2025, macrorregión = Sur · Agrupación: sexo",
            "olap.consultar(['sexo'], medidas, filtros) con tres filtros simultáneos sobre dimensiones distintas.",
            [_tabla_medidas("Resultado del dice, por sexo", "Sexo", dice["filas"], lambda f: f["sexo"])],
            interp4, dice["sql"]),
        _op(5, "Pivot",
            "Cambiar la disposición de las dimensiones en una matriz para ver los resultados desde otra perspectiva.",
            "vista3", "Víctima (sexo), Estado (grupo de desenlace), Fuente",
            "Personas (con total por fila)",
            "Filtro: fuente = Medicina Legal · Matriz A: sexo × desenlace · Matriz B: desenlace × sexo",
            "olap.pivot(['sexo', 'grupo_desenlace'], medidas, filtros) y olap.como_matriz con filas y columnas "
            "intercambiadas. Es la misma consulta con otra disposición.",
            [_tabla_matriz("Matriz A: sexo en filas, desenlace en columnas", "Sexo", m_a),
             _tabla_matriz("Matriz B: desenlace en filas, sexo en columnas", "Desenlace", m_b)],
            interp5, piv["sql"]),
    ]


@lru_cache(maxsize=1)
def resumen_tratado():
    """Conteos del dataset tratado, con el mismo filtro con que se carga el modelo."""
    if not TRATADO_CSV.exists():
        return None
    total, elegibles, por_fuente, por_estado = 0, 0, {}, {}
    with open(TRATADO_CSV, encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            total += 1
            if fila.get("fuente") in FUENTES_MODELO and fila.get("unidad_de_analisis") == "persona":
                elegibles += 1
                por_fuente[fila["fuente"]] = por_fuente.get(fila["fuente"], 0) + 1
                estado = fila.get("estado_victima") or "Sin informacion"
                por_estado[estado] = por_estado.get(estado, 0) + 1
    return {"total": total, "elegibles": elegibles, "por_fuente": por_fuente, "por_estado": por_estado}


DIMENSIONES_FK = [
    ("dim_tiempo", "id_tiempo", "Tiempo"),
    ("dim_geografia", "id_geografia", "Geografía"),
    ("dim_zona", "id_zona", "Zona del hecho"),
    ("dim_victima", "id_victima", "Víctima"),
    ("dim_estado", "id_estado", "Estado"),
    ("dim_fuente", "id_fuente", "Fuente"),
]
FALTANTES = [
    ("Tiempo: sin año", "dim_tiempo", "id_tiempo", "d.anio IS NULL"),
    ("Tiempo: año conocido, mes desconocido", "dim_tiempo", "id_tiempo", "d.anio IS NOT NULL AND d.mes IS NULL"),
    ("Geografía: departamento sin información", "dim_geografia", "id_geografia", "d.departamento = 'Sin informacion'"),
    ("Geografía: municipio sin información", "dim_geografia", "id_geografia", "d.municipio = 'Sin informacion'"),
    ("Zona del hecho: sin información", "dim_zona", "id_zona", "d.zona_hecho = 'Sin informacion'"),
    ("Víctima: sexo sin información", "dim_victima", "id_victima", "d.sexo = 'Sin informacion'"),
    ("Víctima: calidad sin información", "dim_victima", "id_victima", "d.calidad_victima = 'Sin informacion'"),
    ("Estado: sin información", "dim_estado", "id_estado", "d.estado_victima = 'Sin informacion'"),
]
ESTADOS_COMPARAR = [
    ("Siguen desaparecidas", "flag_sigue_desaparecida", "Desaparecido"),
    ("Aparecidas con vida", "flag_aparecio_viva", "Aparecido con vida"),
    ("Aparecidas sin vida", "flag_aparecio_sin_vida", "Aparecido sin vida"),
]


def _fila_comparacion(nombre, modelo, esperado):
    if esperado is None:
        return {"celdas": [nombre, _formato_entero(modelo), "No disponible"], "ok": None}
    return {"celdas": [nombre, _formato_entero(modelo), _formato_entero(esperado)], "ok": modelo == esperado}


def datos_validaciones():
    tratado = resumen_tratado()
    carga = {}
    if CARGA_RESUMEN_PATH.exists():
        with open(CARGA_RESUMEN_PATH, encoding="utf-8") as f:
            carga = json.load(f)

    con = olap.conectar()
    try:
        un = lambda sql, p=(): con.execute(sql, p).fetchone()[0]
        total = un("SELECT COUNT(*) FROM fact_desaparicion")
        personas_total = un("SELECT SUM(num_personas) FROM fact_desaparicion") or 0

        unicidad = []
        for tabla, pk, nombre in DIMENSIONES_FK:
            filas, distintas = con.execute(f"SELECT COUNT(*), COUNT(DISTINCT {pk}) FROM {tabla}").fetchone()
            unicidad.append({"celdas": [f"{tabla}.{pk}", _formato_entero(filas), _formato_entero(distintas)],
                             "ok": filas == distintas})

        huerfanas = []
        for tabla, pk, nombre in DIMENSIONES_FK:
            n = un(f"SELECT COUNT(*) FROM fact_desaparicion f LEFT JOIN {tabla} d ON f.{pk} = d.{pk} "
                   f"WHERE d.{pk} IS NULL")
            huerfanas.append({"celdas": [f"fact_desaparicion.{pk} → {tabla}", _formato_entero(n), "0"], "ok": n == 0})

        distintos = un("SELECT COUNT(DISTINCT id_registro) FROM fact_desaparicion")
        multi = un("SELECT COUNT(*) FROM fact_desaparicion WHERE flag_sigue_desaparecida + "
                   "flag_aparecio_viva + flag_aparecio_sin_vida > 1")
        duplicados = [
            {"celdas": ["Filas frente a id_registro distintos", _formato_entero(total), _formato_entero(distintos)],
             "ok": total == distintos},
            {"celdas": ["SUM(num_personas) frente a filas (una persona por fila)",
                        _formato_entero(personas_total), _formato_entero(total)], "ok": personas_total == total},
            {"celdas": ["Filas con más de un estado marcado", _formato_entero(multi), "0"], "ok": multi == 0},
        ]

        faltantes = []
        for nombre, tabla, pk, cond in FALTANTES:
            n = un(f"SELECT COUNT(*) FROM fact_desaparicion f JOIN {tabla} d ON f.{pk} = d.{pk} WHERE {cond}")
            faltantes.append({"celdas": [nombre, _formato_entero(n),
                                         _formato_pct(100 * n / total if total else 0) + " %"], "ok": None})

        origen = "dataset_tratado.csv" if tratado else "carga_resumen.json (conteos registrados al cargar el modelo)"
        esp_total = tratado["elegibles"] if tratado else carga.get("registros_cargados")
        esp_fuente = tratado["por_fuente"] if tratado else carga.get("por_fuente", {})
        comparaciones = [_fila_comparacion("Total de personas (Medicina Legal + SIEVCAC, unidad persona)", total, esp_total)]
        for fuente in FUENTES_MODELO:
            n = un("SELECT COUNT(*) FROM fact_desaparicion f JOIN dim_fuente d ON f.id_fuente = d.id_fuente "
                   "WHERE d.fuente = ?", (fuente,))
            comparaciones.append(_fila_comparacion(f"Personas de {fuente}", n,
                                                   esp_fuente.get(fuente) if esp_fuente else None))
        if tratado:
            for nombre, flag, valor in ESTADOS_COMPARAR:
                n = un(f"SELECT SUM({flag}) FROM fact_desaparicion") or 0
                comparaciones.append(_fila_comparacion(nombre, n, tratado["por_estado"].get(valor, 0)))

        niveles = []
        for nombre, dims in [("Suma por macrorregión", ["macro_region"]),
                             ("Suma por departamento", ["departamento"]),
                             ("Suma por departamento y municipio", ["departamento", "municipio"]),
                             ("Suma por año", ["anio"]),
                             ("Suma por año y trimestre", ["anio", "trimestre"])]:
            suma = sum(f["personas"] or 0 for f in olap.consultar(dims, ["personas"], con=con)["filas"])
            niveles.append({"celdas": [nombre, _formato_entero(suma), _formato_entero(personas_total)],
                            "ok": suma == personas_total})
    finally:
        con.close()

    nota_dif = ("No hay conjunto tratado disponible para comparar en este entorno; se usan los conteos "
                "registrados al cargar el modelo.")
    if tratado:
        nota_dif = (f"El conjunto tratado completo tiene {_formato_entero(tratado['total'])} filas y "
                    f"{_formato_entero(tratado['elegibles'])} entran al modelo. Las "
                    f"{_formato_entero(tratado['total'] - tratado['elegibles'])} restantes corresponden a IOM o ACLED "
                    f"(eventos agregados) o a una unidad de análisis distinta de persona, y se excluyen para "
                    f"mantener la granularidad de la tabla de hechos.")

    secciones = [
        {"titulo": "1. Unicidad de las claves de las dimensiones",
         "descripcion": "Cada clave primaria debe aparecer una sola vez en su dimensión.",
         "columnas": ["Clave primaria", "Filas", "Claves distintas"], "filas": unicidad, "nota": None},
        {"titulo": "2. Correspondencia de las claves foráneas",
         "descripcion": "Todo hecho debe tener su registro en cada dimensión relacionada.",
         "columnas": ["Relación", "Hechos sin registro relacionado", "Esperado"], "filas": huerfanas, "nota": None},
        {"titulo": "3. Duplicaciones en la tabla de hechos",
         "descripcion": "Verifica que la granularidad sea una persona por fila y que ninguna persona tenga dos estados.",
         "columnas": ["Comprobación", "Obtenido", "Esperado"], "filas": duplicados, "nota": None},
        {"titulo": "4. Valores faltantes y categorías desconocidas",
         "descripcion": f"Cuántos hechos tienen un atributo sin información (denominador: {_formato_entero(total)} hechos).",
         "columnas": ["Atributo", "Hechos", "% de los hechos"], "filas": faltantes,
         "nota": ("Los desconocidos se conservan como la categoría 'Sin informacion' y no se eliminan ni se reparten. "
                  "Tampoco se confunden con una respuesta negativa: 'Sin resolver' es un desenlace conocido. "
                  "La zona del hecho solo existe en Medicina Legal y la calidad de la víctima solo en SIEVCAC, "
                  "por eso aparecen como 'Sin informacion' en la otra fuente.")},
        {"titulo": "5. Comparación con los datos tratados",
         "descripcion": f"Conteos del modelo frente a los datos tratados (origen de la comparación: {origen}).",
         "columnas": ["Comparación", "Modelo", "Datos tratados"], "filas": comparaciones, "nota": nota_dif},
        {"titulo": "6. Coherencia entre niveles de las jerarquías",
         "descripcion": "La suma de cualquier nivel debe igualar el total de personas del modelo.",
         "columnas": ["Agrupación", "Suma de personas", "Total del modelo"], "filas": niveles, "nota": None},
    ]
    evaluadas = [r for s in secciones for r in s["filas"] if r["ok"] is not None]
    return {
        "secciones": secciones,
        "total_comprobaciones": len(evaluadas),
        "coinciden": sum(1 for r in evaluadas if r["ok"]),
        "total_hechos": total,
    }


def datos_conclusiones():
    todos = cargar_conocimientos_multidimensionales().get("conocimientos", [])
    vistas = [{"slug": v["slug"], "titulo": v["titulo"],
               "conocimientos": [c for c in todos if c.get("vista") == v["slug"]]}
              for v in ETAPA5_MENU if v["slug"].startswith("vista")]
    return vistas, len(todos)


def render_operaciones():
    try:
        operaciones = datos_operaciones()
    except FileNotFoundError as exc:
        abort(500, description=str(exc))
    return render_template("etapa5_operaciones.html", current_slug="operaciones",
                           operaciones=operaciones, condiciones=CONDICIONES_ANALISIS)


def render_validaciones():
    try:
        datos = datos_validaciones()
    except FileNotFoundError as exc:
        abort(500, description=str(exc))
    return render_template("etapa5_validaciones.html", current_slug="validaciones", datos=datos)


def render_conclusiones():
    vistas, total = datos_conclusiones()
    return render_template("etapa5_conclusiones.html", current_slug="conclusiones",
                           vistas=vistas, total_conocimientos=total)
VISTA_API = {
    "vista1": datos_vista1,
    "vista2": datos_vista2,
    "vista3": datos_vista3,
    "vista4": datos_vista4,
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
# Dirección de la vista 3: Evolución temporal
def render_vista3():
    return render_template(
        "etapa5_vista_tiempo.html",
        current_slug="vista3",
        conocimientos=conocimientos_de_vista("vista3"),
    )
def render_vista4():
    return render_template(
        "etapa5_vista_perfiles.html",
        current_slug="vista4",
        conocimientos=conocimientos_de_vista("vista4"),
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


def render_modelo():
    return render_template("etapa5_modelo.html", current_slug="modelo")


@app.route("/etapa5/<slug>")
def etapa5_pagina(slug):
    if slug not in ETAPA5_MENU_BY_SLUG:
        abort(404)

    if slug == "proposito":
        return render_proposito()

    if slug == "modelo":
        return render_modelo()

    if slug == "vista1":
        return render_vista1()

    if slug == "vista2":
        return render_vista2()

    if slug == "vista3":
        return render_vista3()

    if slug == "vista4":
        return render_vista4()

    if slug == "operaciones":
        return render_operaciones()

    if slug == "validaciones":
        return render_validaciones()

    if slug == "conclusiones":
        return render_conclusiones()


    item = ETAPA5_MENU_BY_SLUG[slug]
    return render_template(
        "etapa1_placeholder.html",
        numero=item["numero"],
        titulo=item["titulo"],
        current_slug=slug,
    )


# ---------- Etapa 6 ----------

@lru_cache(maxsize=1)
def cargar_conocimiento_oculto():
    if not CONOCIMIENTO_OCULTO_PATH.exists():
        abort(500, description="Falta data/conocimiento_oculto.json.")
    with open(CONOCIMIENTO_OCULTO_PATH, encoding="utf-8") as f:
        return json.load(f)


@app.route("/etapa6/informe/pdf")
def etapa6_informe_pdf():
    if not (ETAPA6_STATIC / ETAPA6_INFORME).exists():
        abort(404)
    return send_from_directory(ETAPA6_STATIC, ETAPA6_INFORME, mimetype="application/pdf")


def render_etapa6_sintesis():
    return render_template(
        "etapa6_sintesis.html",
        datos=cargar_conocimiento_oculto(),
        current_slug="sintesis",
    )


def render_etapa6_supervisado():
    return render_template(
        "etapa6_supervisado.html",
        datos=cargar_conocimiento_oculto()["supervisado"],
        current_slug="supervisado",
    )


def render_etapa6_clustering():
    return render_template(
        "etapa6_clustering.html",
        datos=cargar_conocimiento_oculto()["clustering"],
        current_slug="clustering",
    )


def render_etapa6_comentarios():
    return render_template(
        "etapa6_comentarios.html",
        datos=cargar_conocimiento_oculto()["comentarios"],
        current_slug="comentarios",
    )


def render_etapa6_conclusiones():
    return render_template(
        "etapa6_conclusiones.html",
        datos=cargar_conocimiento_oculto()["conclusiones"],
        referencias=cargar_conocimiento_oculto()["referencias"],
        current_slug="conclusiones",
    )


def render_etapa6_informe():
    return render_template(
        "etapa6_informe.html",
        hay_informe=(ETAPA6_STATIC / ETAPA6_INFORME).exists(),
        informe_url=url_for("etapa6_informe_pdf"),
        repo_url=REPO_URL,
        app_url=APP_URL,
        current_slug="informe",
    )



def render_etapa6_video():
    video_local = (ETAPA6_STATIC / ETAPA6_VIDEO_LOCAL).exists()
    return render_template(
        "etapa6_video.html",
        video_url=ETAPA6_VIDEO_URL,
        video_embed=video_embed_url(ETAPA6_VIDEO_URL),
        video_local_url=url_for("static", filename=f"etapa6/{ETAPA6_VIDEO_LOCAL}") if video_local else None,
        current_slug="video",
    )


ETAPA6_RENDER = {
    "sintesis": render_etapa6_sintesis,
    "supervisado": render_etapa6_supervisado,
    "clustering": render_etapa6_clustering,
    "comentarios": render_etapa6_comentarios,
    "conclusiones": render_etapa6_conclusiones,
    "informe": render_etapa6_informe,
    "video": render_etapa6_video,
}


@app.route("/etapa6/<slug>")
def etapa6_pagina(slug):
    if slug not in ETAPA6_MENU_BY_SLUG:
        abort(404)
    return ETAPA6_RENDER[slug]()


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
