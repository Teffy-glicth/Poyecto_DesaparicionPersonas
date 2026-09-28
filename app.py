import csv
import io
import json
import os
import re
from pathlib import Path

from flask import Flask, Response, abort, render_template, send_from_directory, url_for

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
PRIMARIAS_DIR = DATA_DIR / "Primarias"

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
# Enlace publico del video (YouTube "no listado" o Google Drive con permiso
# "cualquier persona con el enlace"). Se puede definir aqui o con la variable
# de entorno ETAPA3_VIDEO_URL en el servicio donde se publique la app.
ETAPA3_VIDEO_URL = os.environ.get("ETAPA3_VIDEO_URL", "https://www.youtube.com/watch?v=A8Gn9X58u3g")
REPO_URL = os.environ.get("REPO_URL", "")

MUESTRA_MAX_FILAS = 50


@app.context_processor
def inject_menu():
    return {
        "etapa1_menu": ETAPA1_MENU,
        "etapa2_menu": ETAPA2_MENU,
        "etapa3_menu": ETAPA3_MENU,
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


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
