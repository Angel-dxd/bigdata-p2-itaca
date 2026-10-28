"""Ingesta de las tablas académicas de ITACA (PostgreSQL) a la zona raw del proyecto."""

import os
import sys
import json
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

TABLAS = ["alumnos", "contenidos", "calificaciones", "cursos"]
VARIABLES_BD = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]

# data/raw relativo a la raíz del proyecto, no al directorio desde el que se ejecute
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ_PROYECTO / "data" / "raw"


def conectar():
    faltan = [v for v in VARIABLES_BD if not os.getenv(v)]
    if faltan:
        raise RuntimeError(f"Faltan variables en .env: {', '.join(faltan)}")
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=10,
    )


def extraer_tabla(conexion, tabla: str) -> list[dict]:
    # sql.Identifier escapa el nombre de la tabla (evita inyección SQL en vez de usar f-strings)
    consulta = sql.SQL("SELECT * FROM {}").format(sql.Identifier(tabla))
    with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(consulta)
        filas = [dict(fila) for fila in cur.fetchall()]
    logger.info("Extraídas %d filas de '%s'", len(filas), tabla)
    return filas


def guardar(datos: list[dict], nombre: str) -> Path:
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    ruta = DIR_RAW / f"{nombre}_{date.today().isoformat()}.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Guardados %d registros en %s", len(datos), ruta.relative_to(RAIZ_PROYECTO))
    return ruta


def main() -> int:
    try:
        conexion = conectar()
    except (RuntimeError, psycopg2.OperationalError) as e:
        logger.error("No se pudo conectar a la BD: %s", e)
        return 1

    errores = 0
    try:
        for tabla in TABLAS:
            try:
                guardar(extraer_tabla(conexion, tabla), tabla)
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
