<<<<<<< HEAD
from flask import Flask, render_template

app = Flask(__name__)

=======
import csv
import json
from pathlib import Path

from flask import Flask, abort, render_template, send_from_directory

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

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

>>>>>>> feature/etapa-1-upload

@app.route("/")
def index():
    return render_template("index.html")


<<<<<<< HEAD
if __name__ == "__main__":
    app.run(debug=True)
=======
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
    if slug == "fuentes":
        return render_fuentes()
    if slug == "dataset":
        return render_dataset()

    item = ETAPA1_MENU_BY_SLUG[slug]
    return render_template(
        "etapa1_placeholder.html",
        numero=item["numero"],
        titulo=item["titulo"],
        current_slug=slug,
    )


if __name__ == "__main__":
    import os
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
>>>>>>> feature/etapa-1-upload
