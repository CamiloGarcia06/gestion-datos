import argparse
import json
import os
import sys
from typing import Iterable, List

import psycopg2
from psycopg2.extensions import connection as PGConnection


QUERY = """
SELECT 
        pr.id id_proceso,
        dla.nombre nombre_acreedor,
        psa.nombre_es pais_acreedor,
        dld.nombre nombre_deudor,
        psd.nombre_es pais_deudor,
        erpr.notas_conf agencia_remitente,
        eppr.notas_conf agencia_receptora,
        sum(cp.monto) monto_total,
        COALESCE(
        array_agg(
            format('%s, [%s, %s], %s',
            tcp.nombre_es,
            trim(to_char(cp.monto, 'FM999999999.######')),
            COALESCE(dv.nombre_es, ''),
            to_char(cp.fecha, 'DD-MM-YYYY')
            )
            ORDER BY cp.fecha NULLS LAST, cp.tipo
        ) FILTER (WHERE cp.id IS NOT NULL),
        ARRAY[]::text[]
        ) AS componentes                
    FROM
        procesos pr
        INNER JOIN datosloc dla ON pr.acreedor = dla.id 
        INNER JOIN zonas zna ON dla.zona = zna.id
        INNER JOIN paises psa ON zna.pais = psa.id
        INNER JOIN datosloc dld ON pr.deudorpos = dld.id
        INNER JOIN zonas znd ON dld.zona = znd.id
        INNER JOIN paises psd ON znd.pais = psd.id
        INNER JOIN empresas erpr ON pr.remitente = erpr.id
        INNER JOIN empresas eppr ON pr.receptor = eppr.id
        INNER JOIN componentes cp ON pr.id = cp.proceso
        INNER JOIN tiposcomp tcp ON cp.tipo = tcp.id 
        INNER JOIN divisas dv ON cp.divisa = dv.id
    GROUP BY  
        pr.id, dla.nombre, psa.nombre_es, dld.nombre, psd.nombre_es, erpr.notas_conf, eppr.notas_conf
    ORDER BY pr.id; 
"""


def open_connection() -> PGConnection:
    host = os.environ.get("PGHOST", "localhost")
    port = int(os.environ.get("PGPORT", "5432"))
    user = os.environ.get("PGUSER", "odoo")
    password = os.environ.get("PGPASSWORD", "odoo")
    dbname = os.environ.get("PGDATABASE", "cobranzas")
    conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
    conn.autocommit = True
    return conn


def write_json(rows: Iterable[tuple], headers: List[str], output_path: str | None, pretty: bool = False) -> None:
    records = []
    for row in rows:
        obj = {}
        for idx, col in enumerate(headers):
            obj[col] = _jsonify(row[idx])
        records.append(obj)
    if pretty:
        data = json.dumps(records, ensure_ascii=False, indent=2)
    else:
        data = json.dumps(records, ensure_ascii=False)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(data)
    else:
        sys.stdout.write(data)


def _jsonify(value):
    if value is None:
        return None
    if isinstance(value, (list, dict, int, float, str, bool)):
        return value
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cobranzas consulta and output as JSON")
    parser.add_argument("--output", dest="output", help="Path to JSON output file (defaults to stdout)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output with indentation")
    args = parser.parse_args()

    conn = open_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(QUERY)
            rows = cur.fetchall()
            headers = [d[0] for d in cur.description]
        write_json(rows, headers, args.output, pretty=args.pretty)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


