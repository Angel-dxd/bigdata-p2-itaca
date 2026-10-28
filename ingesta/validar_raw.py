"""Validación de los ficheros generados por la ingesta en data/raw (paso 5 de la P2)."""

import sys
import json
import logging

from ingesta_itaca_bd import MODELO, TABLAS, CAMPO_NIA, DIR_RAW, comprobar_entorno, conectar

logger = logging.getLogger("validar_raw")


def cargar_ultimo(tabla: str) -> list[dict]:
    ficheros = sorted(DIR_RAW.glob(f"{tabla}_*.json"))
    if not ficheros:
        raise FileNotFoundError(f"No hay ficheros de '{tabla}' en {DIR_RAW}")
    with open(ficheros[-1], encoding="utf-8") as f:
        datos = json.load(f)
    logger.info("Cargado %s (%d filas)", ficheros[-1].name, len(datos))
    return datos


def consultar_bd(consulta: str) -> list[tuple]:
    conexion = conectar()
    try:
        with conexion.cursor() as cur:
            cur.execute(consulta)
            return cur.fetchall()
    finally:
        conexion.close()


def huerfanos(hijos: list[dict], padres: list[dict], claves_hijo: tuple, claves_padre: tuple) -> int:
    existentes = {tuple(str(p[c]) for c in claves_padre) for p in padres}
    return sum(1 for h in hijos if tuple(str(h[c]) for c in claves_hijo) not in existentes)


def main() -> int:
    fallos = 0

    def comprobar(ok: bool, mensaje: str) -> None:
        nonlocal fallos
        logger.info("%s %s", "OK   " if ok else "FALLO", mensaje)
        fallos += not ok

    comprobar_entorno()
    datos = {t: cargar_ultimo(t) for t in TABLAS}
    comprobar(len(datos) == len(TABLAS), f"Generadas las {len(TABLAS)} tablas: {', '.join(datos)}")

    # 1. Cada tabla tiene exactamente los campos del modelo (ningún dato personal extra)
    for tabla, campos in MODELO.items():
        reales = set(datos[tabla][0])
        comprobar(reales == set(campos), f"'{tabla}' tiene solo los campos del modelo: {', '.join(campos)}")

    # 2. Ningún NIA real en la zona raw
    originales = {fila[0] for fila in consultar_bd(
        "SELECT DISTINCT trim(nia) FROM alumnos UNION SELECT DISTINCT trim(alumno) FROM calificaciones")}
    for tabla in (t for t, campos in MODELO.items() if CAMPO_NIA in campos):
        filtrados = {str(f[CAMPO_NIA]) for f in datos[tabla]} & originales
        comprobar(not filtrados, f"'{tabla}.{CAMPO_NIA}' no contiene ningún NIA real ({len(filtrados)} encontrados)")

    # 3. NIA anonimizado consistente: los cruces dan lo mismo que en la BD origen
    sin_alumno = huerfanos(datos["calificaciones"], datos["alumnos"], ("nia", "anyo"), ("nia", "anyo"))
    sin_alumno_bd = consultar_bd(
        "SELECT count(*) FROM calificaciones c WHERE NOT EXISTS "
        "(SELECT 1 FROM alumnos a WHERE a.nia = c.alumno AND a.anyo = c.anyo)")[0][0]
    comprobar(sin_alumno == sin_alumno_bd,
              f"NIA consistente alumnos<->calificaciones: {sin_alumno} calificaciones sin alumno "
              f"en raw, {sin_alumno_bd} en la BD origen")

    # 4. Integridad referencial de las claves compuestas
    comprobar(huerfanos(datos["calificaciones"], datos["contenidos"],
                        ("modulo", "curso", "anyo"), ("modulo", "curso", "anyo")) == 0,
              "Todo módulo de calificaciones existe en contenidos (modulo+curso+anyo)")
    for tabla in ("alumnos", "contenidos", "calificaciones"):
        comprobar(huerfanos(datos[tabla], datos["cursos"], ("curso", "anyo"), ("codigo", "anyo")) == 0,
                  f"Todo curso de '{tabla}' existe en cursos (curso+anyo)")

    if fallos:
        logger.error("Validación con %d fallo(s)", fallos)
        return 1
    logger.info("Validación superada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
