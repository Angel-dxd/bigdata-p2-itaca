## Fuentes de datos

### Mecanismo de acceso
Las cuatro tablas se extraen de una base de datos **PostgreSQL 16** (réplica de ejemplo de ITACA,
CIPFP Mislata) que corre en Docker (`bigdata-postgres`, puerto 5432). La conexión se hace desde
Python con el driver `psycopg2` (el equivalente en Python a un conector JDBC): una consulta
`SELECT` por tabla.

### Autenticación
- Usuario dedicado **`lectura_bigdata`** con permiso **solo de `SELECT`** sobre las 4 tablas
  (principio de mínimo privilegio: la ingesta no puede modificar ni borrar datos).
- Las credenciales se leen del fichero `.env` (no versionado). Plantilla en `.env.example`.

### Tablas y campos

| Tabla | Clave | Campos principales | Contiene datos personales |
|---|---|---|---|
| `alumnos` | `nia` + `anyo` | nia, curso, grupo, turno, ensenanza, repite, estado_matricula, anyo (+ nombre, apellidos, documento, email, teléfonos, sip, fecha_nac...) | **Sí** |
| `contenidos` (módulos) | `codigo` + `curso` + `anyo` | codigo, nombre_cas, nombre_val, ensenanza, curso, anyo | No |
| `calificaciones` | `alumno` + `contenido` + `evaluacion` + `anyo` | evaluacion, alumno (=NIA), curso, contenido, nota_numerica, tipo_nota, anyo | **Sí** (NIA) |
| `cursos` | `codigo` + `anyo` | codigo, nombre_cas, nombre_val, abreviatura, padre, anyo | No |

Relaciones: `calificaciones.alumno → alumnos.nia`, `calificaciones.contenido → contenidos.codigo`,
`alumnos.curso / contenidos.curso / calificaciones.curso → cursos.codigo`,
`cursos.padre → cursos.codigo` (jerarquía ciclo → curso).

Datos disponibles: cursos 2021-22 a 2025-26.

### Frecuencia de actualización
- `alumnos`, `cursos`, `contenidos`: cambian al **inicio de cada curso** (matrícula, septiembre),
  con ajustes puntuales. Ingesta **anual**, más alguna recarga en octubre.
- `calificaciones`: cambian **después de cada evaluación** (01, 02, FI, EX). Ingesta **por evaluación**
  (unas 4 veces al año).


## Fuentes de datos

### Mecanismo de acceso
Las cuatro tablas se extraen de una base de datos **PostgreSQL 16** (réplica de ejemplo de ITACA,
CIPFP Mislata) que corre en Docker (`bigdata-postgres`, puerto 5432). La conexión se hace desde
Python con el driver `psycopg2` (el equivalente en Python a un conector JDBC): una consulta
`SELECT` por tabla.

### Autenticación
- Usuario dedicado **`lectura_bigdata`** con permiso **solo de `SELECT`** sobre las 4 tablas
  (principio de mínimo privilegio: la ingesta no puede modificar ni borrar datos).
- Las credenciales se leen del fichero `.env` (no versionado). Plantilla en `.env.example`.

### Tablas y campos

| Tabla | Clave | Campos principales | Contiene datos personales |
|---|---|---|---|
| `alumnos` | `nia` + `anyo` | nia, curso, grupo, turno, ensenanza, repite, estado_matricula, anyo (+ nombre, apellidos, documento, email, teléfonos, sip, fecha_nac...) | **Sí** |
| `contenidos` (módulos) | `codigo` + `curso` + `anyo` | codigo, nombre_cas, nombre_val, ensenanza, curso, anyo | No |
| `calificaciones` | `alumno` + `contenido` + `evaluacion` + `anyo` | evaluacion, alumno (=NIA), curso, contenido, nota_numerica, tipo_nota, anyo | **Sí** (NIA) |
| `cursos` | `codigo` + `anyo` | codigo, nombre_cas, nombre_val, abreviatura, padre, anyo | No |

Relaciones: `calificaciones.alumno → alumnos.nia`, `calificaciones.contenido → contenidos.codigo`,
`alumnos.curso / contenidos.curso / calificaciones.curso → cursos.codigo`,
`cursos.padre → cursos.codigo` (jerarquía ciclo → curso).

Datos disponibles: cursos 2021-22 a 2025-26.

### Frecuencia de actualización
- `alumnos`, `cursos`, `contenidos`: cambian al **inicio de cada curso** (matrícula, septiembre),
  con ajustes puntuales. Ingesta **anual**, más alguna recarga en octubre.
- `calificaciones`: cambian **después de cada evaluación** (01, 02, FI, EX). Ingesta **por evaluación**
  (unas 4 veces al año).
