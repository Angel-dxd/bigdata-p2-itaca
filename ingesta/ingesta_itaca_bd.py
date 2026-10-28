"""Ingesta de las tablas académicas de ITACA (PostgreSQL) a la zona raw del proyecto."""

import os
import sys
import hmac
import json
import hashlib
import logging
from datetime import date
from pathlib import Path

import psycopg2
import psycopg2.extras
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingesta_itaca_bd")

# Modelo de datos del enunciado: tabla -> {campo del modelo: columna en la BD}.
# Solo se extraen estos campos (lista blanca), así ningún dato personal sale de la BD.
MODELO = {
    "alumnos": {
        "anyo": "anyo", "nia": "nia", "curso": "curso", "turno": "turno", "grupo": "grupo",
    },
    "contenidos": {
        "anyo": "anyo", "curso": "curso", "modulo": "codigo", "nombre_modulo": "nombre_cas",
    },
    "calificaciones": {
        "anyo": "anyo", "nia": "alumno", "curso": "curso", "modulo": "contenido",
        "nota": "nota_numerica", "evaluacion": "evaluacion",
    },
    "cursos": {
        "anyo": "anyo", "codigo": "codigo", "nombre_cas": "nombre_cas", "padre": "padre",
    },
}
TABLAS = list(MODELO)
VARIABLES_REQUERIDAS = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "NIA_SALT"]

# Campo del modelo que contiene el NIA (se sustituye por un hash)
CAMPO_NIA = "nia"

# data/raw relativo a la raíz del proyecto, no al directorio desde el que se ejecute
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ_PROYECTO / "data" / "raw"


def comprobar_entorno() -> None:
    faltan = [v for v in VARIABLES_REQUERIDAS if not os.getenv(v)]
    if faltan:
        raise RuntimeError(f"Faltan variables en .env: {', '.join(faltan)}")


def conectar():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=10,
    )


def extraer_tabla(conexion, tabla: str) -> list[dict]:
    # SELECT columna AS campo, ... con sql.Identifier, que escapa los nombres
    # (evita inyección SQL en vez de usar f-strings)
    campos = sql.SQL(", ").join(
        sql.SQL("{} AS {}").format(sql.Identifier(columna), sql.Identifier(campo))
        for campo, columna in MODELO[tabla].items()
    )
    consulta = sql.SQL("SELECT {} FROM {}").format(campos, sql.Identifier(tabla))
    with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(consulta)
        filas = [dict(fila) for fila in cur.fetchall()]
    logger.info("Extraídas %d filas de '%s'", len(filas), tabla)
    return filas


# Caché NIA original -> NIA anonimizado: cada NIA se calcula una vez y se reutiliza
# en todas las tablas, de modo que alumnos y calificaciones siguen cruzándose.
_nias_anonimizados: dict[str, str] = {}


def anonimizar_nia(nia: str) -> str:
    nia = str(nia).strip()
    if nia not in _nias_anonimizados:
        # HMAC-SHA256 con clave secreta: sin NIA_SALT no se puede revertir probando
        # todos los NIA posibles (un SHA-256 simple de 8 dígitos se rompe en segundos).
        clave = os.environ["NIA_SALT"].encode()
        digest = hmac.new(clave, nia.encode(), hashlib.sha256).hexdigest()
        _nias_anonimizados[nia] = digest[:10]
    return _nias_anonimizados[nia]


def anonimizar(datos: list[dict], tabla: str) -> list[dict]:
    if CAMPO_NIA not in MODELO[tabla]:
        return datos
    for fila in datos:
        fila[CAMPO_NIA] = anonimizar_nia(fila[CAMPO_NIA])
    logger.info("Anonimizado el NIA de %d filas de '%s'", len(datos), tabla)
    return datos


def guardar(datos: list[dict], nombre: str) -> Path:
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    ruta = DIR_RAW / f"{nombre}_{date.today().isoformat()}.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Guardados %d registros en %s", len(datos), ruta.relative_to(RAIZ_PROYECTO))
    return ruta


def main() -> int:
    try:
        comprobar_entorno()
    except RuntimeError as e:
        logger.error("Configuración incompleta: %s", e)
        return 1
    try:
        conexion = conectar()
    except psycopg2.OperationalError as e:
        logger.error("No se pudo conectar a la BD: %s", e)
        return 1

    errores = 0
    try:
        for tabla in TABLAS:
            try:
                guardar(anonimizar(extraer_tabla(conexion, tabla), tabla), tabla)
            except psycopg2.Error as e:
                logger.error("Error extrayendo '%s': %s", tabla, e)
                conexion.rollback()  # deja la conexión usable para la siguiente tabla
                errores += 1
    finally:
        conexion.close()

    if errores:
        logger.error("Ingesta terminada con %d tabla(s) fallida(s)", errores)
        return 1
    logger.info("Ingesta completada: %d tablas", len(TABLAS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
