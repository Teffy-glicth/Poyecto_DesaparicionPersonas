import csv
import json
import os
from pathlib import Path

from flask import Flask, abort, render_template, send_from_directory

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

MUESTRA_MAX_FILAS = 50


@app.context_processor
def inject_menu():
    return {"etapa1_menu": ETAPA1_MENU, "current_slug": None}


@app.route("/")
def index():
    return render_template("index.html")


def render_problema():
    return render_template(
        "etapa1_problema.html",
        current_slug="problema",
    )


def render_preguntas():
    return render_template(
        "etapa1_preguntas.html",
        current_slug="preguntas",
    )

def render_necesidades():
    return render_template(
        "etapa1_necesidades.html",
        current_slug="necesidades",
    )


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


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
