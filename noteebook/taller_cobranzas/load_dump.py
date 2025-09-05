import argparse
import os
import sys
import time
import subprocess
from typing import Optional

import psycopg2
from psycopg2.extensions import connection as PGConnection


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name, default)
    return value


def wait_for_db(host: str, port: int, user: str, password: str, dbname: str, timeout_seconds: int = 60) -> None:
    start = time.time()
    while True:
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=dbname,
                connect_timeout=3,
            )
            conn.close()
            print("Database is ready.")
            return
        except Exception as exc:  # noqa: BLE001 - broad for retry loop
            if time.time() - start > timeout_seconds:
                raise RuntimeError(f"Timed out waiting for database: {exc}") from exc
            print("Waiting for database to be ready...")
            time.sleep(2)


def is_custom_pg_dump(dump_path: str) -> bool:
    # Custom-format pg_dump files start with magic header 'PGDMP'
    try:
        with open(dump_path, "rb") as f:
            magic = f.read(5)
            return magic == b"PGDMP"
    except Exception:
        return False


def restore_with_pg_restore(
    dump_path: str,
    host: str,
    port: int,
    user: str,
    password: str,
    dbname: str,
    strict: bool = True,
) -> None:
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    cmd = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "--host",
        host,
        "--port",
        str(port),
        "--username",
        user,
        "--dbname",
        dbname,
        dump_path,
    ]
    if strict:
        cmd.insert(1, "--exit-on-error")
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, env=env)


def restore_with_psql_sqlfile(
    dump_path: str,
    host: str,
    port: int,
    user: str,
    password: str,
    dbname: str,
    on_error_stop: bool = True,
) -> None:
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    cmd = [
        "psql",
        "-v",
        f"ON_ERROR_STOP={'1' if on_error_stop else '0'}",
        "-h",
        host,
        "-p",
        str(port),
        "-U",
        user,
        "-d",
        dbname,
        "-f",
        dump_path,
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, env=env)


def extract_roles_from_sql_dump(dump_path: str) -> Set[str]:
    """Scan a plain SQL dump and collect role names referenced in OWNER TO clauses.

    Handles quoted identifiers like "652_gramo" or unquoted names.
    """
    roles: Set[str] = set()
    # Regex to capture: OWNER TO <role>;
    # Matches OWNER TO "name"; or OWNER TO name;
    owner_regex = re.compile(r"OWNER\s+TO\s+([\"A-Za-z0-9_@.%\-]+)\s*;", re.IGNORECASE)
    try:
        with open(dump_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "OWNER TO" not in line:
                    continue
                m = owner_regex.search(line)
                if not m:
                    continue
                raw = m.group(1).strip()
                # Strip quotes if present
                role = raw[1:-1] if raw.startswith('"') and raw.endswith('"') else raw
                if role:
                    roles.add(role)
    except Exception:
        # If scanning fails for any reason, proceed without role pre-creation
        return set()
    return roles


def ensure_roles_exist(conn: PGConnection, roles: Set[str]) -> None:
    """Create any missing roles found in the dump as NOLOGIN roles.

    This avoids failures when applying ALTER ... OWNER TO statements.
    """
    if not roles:
        return
    with conn.cursor() as cur:
        for role in roles:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", (role,))
            exists = cur.fetchone() is not None
            if exists:
                continue
            # Quote identifier safely by using double quotes around role name
            # Role names may require quoting (e.g., starting with digits)
            quoted = '"' + role.replace('"', '""') + '"'
            print(f"Creating missing role {quoted} (NOLOGIN)...")
            cur.execute(f"CREATE ROLE {quoted} NOLOGIN;")


def open_connection(host: str, port: int, user: str, password: str, dbname: str) -> PGConnection:
    conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
    conn.autocommit = True
    return conn


def run_demo_queries(conn: PGConnection) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"PostgreSQL version: {version}")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public';
        """)
        table_count = cur.fetchone()[0]
        print(f"Public tables: {table_count}")

    if table_count:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                LIMIT 5;
                """
            )
            sample = [r[0] for r in cur.fetchall()]
            print(f"Sample tables: {', '.join(sample)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a PostgreSQL dump and open a DB cursor.")
    parser.add_argument("--dump", dest="dump_path", default=os.environ.get("DUMP_FILE", "/app/data/taller_cobranzas.dump"), help="Path to the dump file (.sql or custom .dump)")
    parser.add_argument("--skip-restore", action="store_true", help="Skip restoring the dump and only open a DB connection")
    parser.add_argument("--reset-public", action="store_true", help="Drop and recreate schema public before restore")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue on errors during restore (do not stop on first error)")

    args = parser.parse_args()

    host = get_env("PGHOST", "localhost")
    port = int(get_env("PGPORT", "5432"))
    user = get_env("PGUSER", "odoo")
    password = get_env("PGPASSWORD", "odoo")
    dbname = get_env("PGDATABASE", "taller_cobranzas")

    print(f"Connecting to postgresql://{user}:****@{host}:{port}/{dbname}")
    wait_for_db(host, port, user, password, dbname, timeout_seconds=120)

    if not args.skip_restore:
        if not os.path.exists(args.dump_path):
            print(f"Dump file not found: {args.dump_path}", file=sys.stderr)
            return 2

        if args.reset_public:
            print("Resetting schema public (DROP CASCADE + CREATE)...")
            conn_reset = open_connection(host, port, user, password, dbname)
            try:
                with conn_reset.cursor() as cur:
                    cur.execute("DROP SCHEMA IF EXISTS public CASCADE;")
                    cur.execute("CREATE SCHEMA public;")
                    cur.execute("GRANT ALL ON SCHEMA public TO public;")
            finally:
                conn_reset.close()

        try:
            if is_custom_pg_dump(args.dump_path):
                print("Detected custom-format dump. Using pg_restore...")
                restore_with_pg_restore(
                    args.dump_path,
                    host,
                    port,
                    user,
                    password,
                    dbname,
                    strict=not args.continue_on_error,
                )
            else:
                print("Detected plain SQL dump. Using psql -f ...")
                # Pre-create any roles referenced as owners in the dump to avoid failures
                roles_in_dump = extract_roles_from_sql_dump(args.dump_path)
                if roles_in_dump:
                    conn_roles = open_connection(host, port, user, password, dbname)
                    try:
                        ensure_roles_exist(conn_roles, roles_in_dump)
                    finally:
                        conn_roles.close()
                if args.continue_on_error:
                    restore_with_psql_sqlfile(
                        args.dump_path, host, port, user, password, dbname, on_error_stop=False
                    )
                else:
                    restore_with_psql_sqlfile(
                        args.dump_path, host, port, user, password, dbname, on_error_stop=True
                    )
            print("Restore completed successfully.")
        except subprocess.CalledProcessError as exc:
            print(f"Restore failed with exit code {exc.returncode}", file=sys.stderr)
            return exc.returncode or 1

    # Open a cursor to allow further manipulation
    conn = open_connection(host, port, user, password, dbname)
    try:
        print("Opened a connection and cursor to the database. Running demo queries...")
        run_demo_queries(conn)
        print("You can import and extend this script to run your own SQL using psycopg2.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


