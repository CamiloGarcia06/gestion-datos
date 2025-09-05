import json
import os
from typing import Any, List, Sequence

import psycopg2
from psycopg2.extensions import connection as PGConnection
import xml.etree.ElementTree as ET


def open_connection() -> PGConnection:
    host = os.environ.get("PGHOST", "localhost")
    port = int(os.environ.get("PGPORT", "5432"))
    user = os.environ.get("PGUSER", "odoo")
    password = os.environ.get("PGPASSWORD", "odoo")
    dbname = os.environ.get("PGDATABASE", "cobranzas")
    conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
    conn.autocommit = True
    return conn


def fetch_all(conn: PGConnection, query: str, params: Sequence[Any] | None = None) -> tuple[list[tuple], list[str]]:
    with conn.cursor() as cur:
        cur.execute(query, params or [])
        rows = cur.fetchall()
        headers = [d[0] for d in cur.description]
    return rows, headers


def write_json(path: str, rows: list[tuple], headers: list[str]) -> None:
    records = []
    for row in rows:
        obj = {}
        for idx, col in enumerate(headers):
            obj[col] = _jsonify(row[idx])
        records.append(obj)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def _jsonify(value):
    if value is None:
        return None
    if isinstance(value, (list, dict, int, float, str, bool)):
        return value
    return str(value)


def write_xml_top_componentes(path: str, rows: list[tuple], headers: list[str]) -> None:
    # Expected headers: pais_deudor, tipo, cnt
    idx_pais = headers.index("pais_deudor")
    idx_tipo = headers.index("tipo")
    idx_cnt = headers.index("cnt")

    root = ET.Element("componentes_por_pais")
    current_country = None
    country_el: ET.Element | None = None
    for row in rows:
        pais = str(row[idx_pais]) if row[idx_pais] is not None else ""
        tipo = str(row[idx_tipo]) if row[idx_tipo] is not None else ""
        cnt = str(row[idx_cnt])
        if pais != current_country:
            country_el = ET.SubElement(root, "pais", nombre=pais)
            current_country = pais
        assert country_el is not None
        ET.SubElement(country_el, "componente", nombre=tipo, frecuencia=cnt)

    tree = ET.ElementTree(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Pretty print (Python 3.9+)
    try:
        ET.indent(tree, space="  ", level=0)  # type: ignore[attr-defined]
    except Exception:
        pass
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main() -> int:
    output_dir = os.environ.get("OUTPUT_DIR", "/app/output")
    conn = open_connection()
    try:
        # 1) Países con mayor cantidad de deudores en incumplimiento (Promesa rota o Proceso judicial)
        q_incumplimientos = """
        SELECT
          psd.nombre_es AS pais_deudor,
          COUNT(DISTINCT pr.deudorpos) AS num_deudores,
          SUM(cp.monto) AS monto_total
        FROM procesos pr
        JOIN datosloc dld ON pr.deudorpos = dld.id
        JOIN zonas znd ON dld.zona = znd.id
        JOIN paises psd ON znd.pais = psd.id
        JOIN componentes cp ON cp.proceso = pr.id
        WHERE EXISTS (
          SELECT 1
          FROM bitacora b
          JOIN estados es ON es.id = b.estado
          WHERE b.proceso = pr.id AND es.clase_es IN ('PROMESA ROTA', 'PROCESO JUDICIAL')
        )
        GROUP BY psd.nombre_es
        ORDER BY num_deudores DESC, monto_total DESC;
        """
        rows1, headers1 = fetch_all(conn, q_incumplimientos)
        write_json(os.path.join(output_dir, "incumplimientos_por_pais.json"), rows1, headers1)

        # 2) Países cuyos deudores cumplidos tardan más en llegar a CERRADO. OBLIGACION CANCELADA...
        q_demoras = """
        WITH cierre AS (
          SELECT pr.id AS proceso_id,
                 COALESCE(pr.fecradicac, pr.fechainic) AS fecha_inicio,
                 MIN(b.fecha) AS fecha_cierre
          FROM procesos pr
          JOIN bitacora b ON b.proceso = pr.id
          JOIN estados es ON es.id = b.estado
          WHERE es.nombre_es = 'Cerrado. OBLIGACION CANCELADA en su TOTALIDAD.'
          GROUP BY pr.id
        ), procesos_con_pais AS (
          SELECT pr.id, psd.nombre_es AS pais_deudor
          FROM procesos pr
          JOIN datosloc dld ON pr.deudorpos = dld.id
          JOIN zonas znd ON dld.zona = znd.id
          JOIN paises psd ON znd.pais = psd.id
        )
        SELECT pcp.pais_deudor,
               AVG((cierre.fecha_cierre - cierre.fecha_inicio))::numeric AS dias_promedio
        FROM cierre
        JOIN procesos_con_pais pcp ON pcp.id = cierre.proceso_id
        WHERE cierre.fecha_inicio IS NOT NULL AND cierre.fecha_cierre IS NOT NULL
        GROUP BY pcp.pais_deudor
        ORDER BY dias_promedio DESC;
        """
        rows2, headers2 = fetch_all(conn, q_demoras)
        write_json(os.path.join(output_dir, "demoras_por_pais.json"), rows2, headers2)

        # 3) XML: Para cada país (deudor), tipos de componentes más frecuentes
        q_componentes_top = """
        WITH base AS (
          SELECT psd.nombre_es AS pais_deudor,
                 tcp.nombre_es AS tipo,
                 COUNT(*) AS cnt
          FROM procesos pr
          JOIN datosloc dld ON pr.deudorpos = dld.id
          JOIN zonas znd ON dld.zona = znd.id
          JOIN paises psd ON znd.pais = psd.id
          JOIN componentes cp ON cp.proceso = pr.id
          JOIN tiposcomp tcp ON tcp.id = cp.tipo
          GROUP BY psd.nombre_es, tcp.nombre_es
        ), maxes AS (
          SELECT pais_deudor, MAX(cnt) AS max_cnt
          FROM base
          GROUP BY pais_deudor
        )
        SELECT b.pais_deudor, b.tipo, b.cnt
        FROM base b
        JOIN maxes m ON m.pais_deudor = b.pais_deudor AND m.max_cnt = b.cnt
        ORDER BY b.pais_deudor, b.tipo;
        """
        rows3, headers3 = fetch_all(conn, q_componentes_top)
        write_xml_top_componentes(os.path.join(output_dir, "top_componentes_por_pais.xml"), rows3, headers3)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


