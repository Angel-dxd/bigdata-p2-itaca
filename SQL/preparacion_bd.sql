-- Preparación de la BD para la ingesta (P2): usuario de solo lectura.
--
-- Montar la BD desde cero con los ficheros del docente (zip de la web del centro):
--   for t in alumnos contenidos calificaciones cursos; do
--     docker exec -i bigdata-postgres psql -U itaca -d itaca -q < SQL/$t.sql
--   done
--
-- Después, ejecutar este script como superusuario, pasando la contraseña como variable:
--   docker exec -i bigdata-postgres psql -U itaca -d itaca -v pwd="LA_CONTRASEÑA" < SQL/preparacion_bd.sql

\set ON_ERROR_STOP on

BEGIN;

-- Usuario de solo lectura para la ingesta (principio de mínimo privilegio).
SELECT format('CREATE ROLE lectura_bigdata LOGIN PASSWORD %L', :'pwd')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lectura_bigdata') \gexec
ALTER ROLE lectura_bigdata PASSWORD :'pwd';

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM lectura_bigdata;
GRANT CONNECT ON DATABASE itaca TO lectura_bigdata;
GRANT USAGE ON SCHEMA public TO lectura_bigdata;
GRANT SELECT ON alumnos, contenidos, calificaciones, cursos TO lectura_bigdata;

COMMIT;
