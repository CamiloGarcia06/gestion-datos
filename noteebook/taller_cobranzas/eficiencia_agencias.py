import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection


def open_connection() -> PGConnection:
    host = os.environ.get("PGHOST", "localhost")
    port = int(os.environ.get("PGPORT", "5432"))
    user = os.environ.get("PGUSER", "odoo")
    password = os.environ.get("PGPASSWORD", "odoo")
    dbname = os.environ.get("PGDATABASE", "cobranzas")
    conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
    conn.autocommit = True
    return conn


def main() -> int:
    out_dir = os.environ.get("OUTPUT_DIR", "/app/output")
    out_path = os.path.join(out_dir, "eficiencia_agencias.txt")
    os.makedirs(out_dir, exist_ok=True)

    sql = """
    WITH cierre_ok AS (
      SELECT pr.id AS proceso_id,
             pr.receptor,
             COALESCE(pr.fecradicac, pr.fechainic) AS fecha_inicio,
             MIN(b.fecha) AS fecha_cierre
      FROM procesos pr
      JOIN bitacora b ON b.proceso = pr.id
      JOIN estados es ON es.id = b.estado
      WHERE es.nombre_es = 'Cerrado. OBLIGACION CANCELADA en su TOTALIDAD.'
      GROUP BY pr.id, pr.receptor
    ),
    promedio AS (
      SELECT ep.id AS receptor_id,
             ep.notas_conf AS agencia,
             AVG((c.fecha_cierre - c.fecha_inicio))::numeric AS dias_promedio,
             COUNT(*) AS procesos_cerrados
      FROM cierre_ok c
      JOIN empresas ep ON ep.id = c.receptor
      WHERE c.fecha_inicio IS NOT NULL AND c.fecha_cierre IS NOT NULL
      GROUP BY ep.id, ep.notas_conf
      ORDER BY dias_promedio ASC NULLS LAST, procesos_cerrados DESC
    ),
    top_ok AS (
      SELECT ep.id AS receptor_id, ep.notas_conf AS agencia, COUNT(*) AS procesos_cerrados_ok
      FROM procesos pr
      JOIN empresas ep ON ep.id = pr.receptor
      WHERE EXISTS (
        SELECT 1 FROM bitacora b JOIN estados es ON es.id=b.estado
        WHERE b.proceso = pr.id AND es.nombre_es = 'Cerrado. OBLIGACION CANCELADA en su TOTALIDAD.'
      )
      GROUP BY ep.id, ep.notas_conf
      ORDER BY procesos_cerrados_ok DESC, agencia ASC
      LIMIT 10
    ),
    top_no_ok AS (
      SELECT ep.id AS receptor_id, ep.notas_conf AS agencia, COUNT(*) AS procesos_cerrados_no_ok
      FROM procesos pr
      JOIN empresas ep ON ep.id = pr.receptor
      WHERE pr.cerrado = TRUE
        AND NOT EXISTS (
          SELECT 1 FROM bitacora b JOIN estados es ON es.id=b.estado
          WHERE b.proceso = pr.id AND es.nombre_es = 'Cerrado. OBLIGACION CANCELADA en su TOTALIDAD.'
        )
      GROUP BY ep.id, ep.notas_conf
      ORDER BY procesos_cerrados_no_ok DESC, agencia ASC
      LIMIT 10
    )
    SELECT (
      'Cuánto es el tiempo promedio que demoran los receptores en cerrar los procesos (de menor a mayor, más rápidas primero):' || E'\n' ||
      COALESCE(
        (
          SELECT string_agg(
                   format('%s: %s días (procesos %s)',
                          COALESCE(agencia, '(sin nombre)'),
                          trim(to_char(dias_promedio, 'FM999999999.99')),
                          procesos_cerrados
                   ), E'\n'
                 )
          FROM promedio
        ), '(sin datos)'
      )
    ) || E'\n\n' || (
      'Top 10 de las agencias que han cerrado la mayor cantidad de procesos con el estado “Cerrado. OBLIGACION CANCELADA en su TOTALIDAD.”:' || E'\n' ||
      COALESCE(
        (
          SELECT string_agg(
                   format('%s) %s: %s procesos', rn, COALESCE(agencia, '(sin nombre)'), procesos_cerrados_ok), E'\n')
          FROM (
            SELECT row_number() over (ORDER BY procesos_cerrados_ok DESC, agencia ASC) AS rn,
                   agencia, procesos_cerrados_ok
            FROM top_ok
          ) t
        ), '(sin datos)'
      )
    ) || E'\n\n' || (
      'Top 10 de las agencias que han cerrado la mayor cantidad de procesos con estados diferentes a “Cerrado. OBLIGACION CANCELADA en su TOTALIDAD.”:' || E'\n' ||
      COALESCE(
        (
          SELECT string_agg(
                   format('%s) %s: %s procesos', rn, COALESCE(agencia, '(sin nombre)'), procesos_cerrados_no_ok), E'\n')
          FROM (
            SELECT row_number() over (ORDER BY procesos_cerrados_no_ok DESC, agencia ASC) AS rn,
                   agencia, procesos_cerrados_no_ok
            FROM top_no_ok
          ) t
        ), '(sin datos)'
      )
    ) AS informe;
    """

    conn = open_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
            informe = row[0] if row and row[0] is not None else ''
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(informe)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

