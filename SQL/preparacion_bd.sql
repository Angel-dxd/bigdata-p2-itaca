-- Preparación de la BD para la ingesta (P2).
-- Ejecutar como superusuario, pasando la contraseña como variable:
--   docker exec -i bigdata-postgres psql -U itaca -d itaca -v pwd="LA_CONTRASEÑA" < SQL/preparacion_bd.sql

\set ON_ERROR_STOP on

BEGIN;

-- 1. Reconstruir la tabla unificada de calificaciones a partir de las tablas anuales
--    (la versión cargada inicialmente era un recorte de ~11.000 filas).
TRUNCATE calificaciones;
INSERT INTO calificaciones
    SELECT * FROM calificaciones_2021_22
    UNION ALL SELECT * FROM calificaciones_2022_23
    UNION ALL SELECT * FROM calificaciones_2023_24
    UNION ALL SELECT * FROM calificaciones_2024_25
    UNION ALL SELECT * FROM calificaciones_2025_26;

-- 2. Usuario de solo lectura para la ingesta (principio de mínimo privilegio).
SELECT format('CREATE ROLE lectura_bigdata LOGIN PASSWORD %L', :'pwd')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lectura_bigdata') \gexec
ALTER ROLE lectura_bigdata PASSWORD :'pwd';

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM lectura_bigdata;
GRANT CONNECT ON DATABASE itaca TO lectura_bigdata;
GRANT USAGE ON SCHEMA public TO lectura_bigdata;
GRANT SELECT ON alumnos, contenidos, calificaciones, cursos TO lectura_bigdata;

COMMIT;
