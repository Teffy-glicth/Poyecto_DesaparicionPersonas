import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
SALIDA_DIR = BASE_DIR / "etapa6" / "youtube" / "datos"
ARCHIVO_ENV = BASE_DIR / ".env"

URL_VIDEO = "https://www.youtube.com/watch?v=V190AYPh-b0"
MAX_COMENTARIOS = 5000
INCLUIR_RESPUESTAS = True

API = "https://www.googleapis.com/youtube/v3"


def leer_env():
    if not ARCHIVO_ENV.exists():
        return
    for linea in ARCHIVO_ENV.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        nombre, valor = linea.split("=", 1)
        os.environ.setdefault(nombre.strip(), valor.strip().strip('"').strip("'"))


def obtener_clave():
    leer_env()
    clave = os.environ.get("YOUTUBE_API_KEY")
    return clave if clave else getpass("API key de YouTube: ")


def extraer_id(url):
    patron = r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})"
    coincidencia = re.search(patron, url)
    return coincidencia.group(1) if coincidencia else url.strip()


def consultar(recurso, parametros):
    url = f"{API}/{recurso}?{urllib.parse.urlencode(parametros)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        datos = json.loads(error.read().decode("utf-8") or "{}")
        detalle = datos.get("error", {})
        motivo = detalle.get("errors", [{}])[0].get("reason", "")
        raise RuntimeError(f"{error.code} {motivo}: {detalle.get('message')}") from None


def metadatos_video(clave, video_id):
    datos = consultar("videos", {
        "key": clave,
        "id": video_id,
        "part": "snippet,statistics,contentDetails",
    })
    if not datos.get("items"):
        raise RuntimeError("No se encontró el video. Revisa el enlace.")
    item = datos["items"][0]
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "titulo": item["snippet"]["title"],
        "canal": item["snippet"]["channelTitle"],
        "fecha_publicacion": item["snippet"]["publishedAt"],
        "duracion_iso8601": item["contentDetails"]["duration"],
        "idioma_audio": item["snippet"].get("defaultAudioLanguage"),
        "vistas": int(item["statistics"].get("viewCount", 0)),
        "likes": int(item["statistics"].get("likeCount", 0)),
        "comentarios_reportados": int(item["statistics"].get("commentCount", 0)),
    }


def formatear(snippet, id_hilo, es_respuesta):
    return {
        "id_hilo": id_hilo,
        "es_respuesta": es_respuesta,
        "texto": snippet["textDisplay"],
        "fecha": snippet["publishedAt"],
        "likes": snippet.get("likeCount", 0),
    }


def respuestas_completas(clave, parent_id, id_hilo):
    resultado = []
    pagina = None
    while True:
        parametros = {
            "key": clave,
            "part": "snippet",
            "parentId": parent_id,
            "maxResults": 100,
            "textFormat": "plainText",
        }
        if pagina:
            parametros["pageToken"] = pagina
        datos = consultar("comments", parametros)
        resultado.extend(formatear(c["snippet"], id_hilo, True) for c in datos.get("items", []))
        pagina = datos.get("nextPageToken")
        if not pagina:
            return resultado


def descargar_comentarios(clave, video_id, maximo):
    comentarios = []
    pagina = None
    id_hilo = 0
    while len(comentarios) < maximo:
        parametros = {
            "key": clave,
            "part": "snippet,replies" if INCLUIR_RESPUESTAS else "snippet",
            "videoId": video_id,
            "maxResults": 100,
            "textFormat": "plainText",
            "order": "time",
        }
        if pagina:
            parametros["pageToken"] = pagina
        datos = consultar("commentThreads", parametros)

        for hilo in datos.get("items", []):
            id_hilo += 1
            principal = hilo["snippet"]["topLevelComment"]
            comentarios.append(formatear(principal["snippet"], id_hilo, False))

            if not INCLUIR_RESPUESTAS:
                continue
            total_respuestas = hilo["snippet"].get("totalReplyCount", 0)
            incluidas = hilo.get("replies", {}).get("comments", [])
            if total_respuestas > len(incluidas):
                comentarios.extend(respuestas_completas(clave, principal["id"], id_hilo))
            else:
                comentarios.extend(formatear(r["snippet"], id_hilo, True) for r in incluidas)

        pagina = datos.get("nextPageToken")
        print(f"Descargados: {len(comentarios)}")
        if not pagina:
            break
    return comentarios[:maximo]


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else URL_VIDEO
    maximo = int(sys.argv[2]) if len(sys.argv) > 2 else MAX_COMENTARIOS

    clave = obtener_clave()
    video_id = extraer_id(url)
    fecha_extraccion = datetime.now(timezone.utc).isoformat(timespec="seconds")

    meta = metadatos_video(clave, video_id)
    print(f"{meta['titulo']} | {meta['canal']} | {meta['duracion_iso8601']} | "
          f"{meta['comentarios_reportados']} comentarios reportados")

    try:
        comentarios = descargar_comentarios(clave, video_id, maximo)
    except RuntimeError as error:
        if "commentsDisabled" in str(error):
            print("Este video tiene los comentarios desactivados.")
            return
        raise

    if not comentarios:
        print("No se descargaron comentarios.")
        return

    df = pd.DataFrame(comentarios)
    df.insert(0, "id_comentario", range(1, len(df) + 1))
    df.insert(1, "video_id", video_id)
    df["fecha_extraccion"] = fecha_extraccion

    meta["fecha_extraccion"] = fecha_extraccion
    meta["comentarios_descargados"] = int(len(df))
    meta["comentarios_principales"] = int((~df["es_respuesta"]).sum())
    meta["respuestas"] = int(df["es_respuesta"].sum())
    meta["max_comentarios_configurado"] = maximo

    SALIDA_DIR.mkdir(parents=True, exist_ok=True)
    archivo_csv = SALIDA_DIR / f"comentarios_{video_id}.csv"
    archivo_meta = SALIDA_DIR / f"metadatos_{video_id}.json"
    df.to_csv(archivo_csv, index=False, encoding="utf-8-sig")
    archivo_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Comentarios guardados: {len(df)} "
          f"({meta['comentarios_principales']} principales, {meta['respuestas']} respuestas)")
    print(f"CSV: {archivo_csv}")
    print(f"Metadatos: {archivo_meta}")
    print(df.head().to_string(index=False, max_colwidth=60))


if __name__ == "__main__":
    main()
