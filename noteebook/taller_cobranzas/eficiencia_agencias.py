import json
import os
import psycopg2
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


def dump_json(path: str, rows, headers):
    data = []
    for row in rows:
        obj = {}
        for idx, col in enumerate(headers):
            val = row[idx]
            obj[col] = val if isinstance(val, (str, int, float, bool, list, dict)) or val is None else str(val)
        data.append(obj)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch(conn: PGConnection, query: str, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params or [])
        rows = cur.fetchall()
        headers = [d[0] for d in cur.description]
    return rows, headers


def main() -> int:
    out_dir = os.environ.get("OUTPUT_DIR", "/app/output")
    conn = open_connection()
    try:
        # 1) Tiempo promedio en cerrar procesos por receptor (agencia receptora)
        q_promedio = """
        WITH cierre AS (
          SELECT pr.id AS proceso_id,
                 pr.receptor,
                 COALESCE(pr.fecradicac, pr.fechainic) AS fecha_inicio,
                 MIN(b.fecha) AS fecha_cierre
          FROM procesos pr
          JOIN bitacora b ON b.proceso = pr.id
          JOIN estados es ON es.id = b.estado
          WHERE es.nombre_es = 'Cerrado. OBLIGACION CANCELADA en su TOTALIDAD.'
          GROUP BY pr.id, pr.receptor
        )
        SELECT ep.id AS receptor_id,
               ep.notas_conf AS agencia,
               AVG((cierre.fecha_cierre - cierre.fecha_inicio))::numeric AS dias_promedio,
               COUNT(*) AS procesos_cerrados
        FROM cierre
        JOIN empresas ep ON ep.id = cierre.receptor
        WHERE cierre.fecha_inicio IS NOT NULL AND cierre.fecha_cierre IS NOT NULL
        GROUP BY ep.id, ep.notas_conf
        ORDER BY dias_promedio ASC NULLS LAST, procesos_cerrados DESC;
        """
        rows1, headers1 = fetch(conn, q_promedio)
        dump_json(os.path.join(out_dir, "agencias_tiempo_promedio_cierre.json"), rows1, headers1)

        # 2) Top 10 agencias con más cierres en estado exacto CANCELADA TOTALIDAD
        q_top_ok = """
        WITH cierre_ok AS (
          SELECT pr.receptor, pr.id
          FROM procesos pr
          WHERE EXISTS (
            SELECT 1 FROM bitacora b JOIN estados es ON es.id=b.estado
            WHERE b.proceso = pr.id AND es.nombre_es = 'Cerrado. OBLIGACION CANCELADA en su TOTALIDAD.'
          )
        )
        SELECT ep.id AS receptor_id, ep.notas_conf AS agencia, COUNT(*) AS procesos_cerrados_ok
        FROM cierre_ok c
        JOIN empresas ep ON ep.id = c.receptor
        GROUP BY ep.id, ep.notas_conf
        ORDER BY procesos_cerrados_ok DESC, agencia ASC
        LIMIT 10;
        """
        rows2, headers2 = fetch(conn, q_top_ok)
        dump_json(os.path.join(out_dir, "top10_agencias_cerrados_ok.json"), rows2, headers2)

        # 3) Top 10 agencias con más cierres en estados diferentes a CANCELADA TOTALIDAD
        q_top_not_ok = """
        WITH cierre_not_ok AS (
          SELECT pr.receptor, pr.id
          FROM procesos pr
          WHERE pr.cerrado = TRUE
            AND NOT EXISTS (
              SELECT 1 FROM bitacora b JOIN estados es ON es.id=b.estado
              WHERE b.proceso = pr.id AND es.nombre_es = 'Cerrado. OBLIGACION CANCELADA en su TOTALIDAD.'
            )
        )
        SELECT ep.id AS receptor_id, ep.notas_conf AS agencia, COUNT(*) AS procesos_cerrados_no_ok
        FROM cierre_not_ok c
        JOIN empresas ep ON ep.id = c.receptor
        GROUP BY ep.id, ep.notas_conf
        ORDER BY procesos_cerrados_no_ok DESC, agencia ASC
        LIMIT 10;
        """
        rows3, headers3 = fetch(conn, q_top_not_ok)
        dump_json(os.path.join(out_dir, "top10_agencias_cerrados_no_ok.json"), rows3, headers3)

    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
