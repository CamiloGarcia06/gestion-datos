#!/usr/bin/env python3
"""
ETL: Carga el CSV ConsumerComplaints a Postgres usando SQLAlchemy.

Origen:
  - data/ConsumerComplaints.csv (ruta relativa a este script)

Destino (tabla):
  - postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}
  - tabla: consumer_complaints (reemplaza si existe)

Variables de entorno esperadas (con valores por defecto razonables):
  DB_HOST=postgres
  DB_PORT=5432
  DB_NAME=etl
  DB_USER=etl
  DB_PASSWORD=etl
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import pandas as pd
from sqlalchemy import create_engine, text


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_CSV = SCRIPT_DIR / "data" / "ConsumerComplaints.csv"


def get_database_url() -> str:
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = int(os.getenv("DB_PORT", "5432"))
    db_name = os.getenv("DB_NAME", "etl")
    db_user = os.getenv("DB_USER", "etl")
    db_password = os.getenv("DB_PASSWORD", "etl")
    return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def make_safe_column_names(columns: pd.Index) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for col in columns:
        safe = str(col).strip().lower()
        # Reemplazar separadores y caracteres no alfanuméricos por '_'
        safe = safe.replace("/", " ")
        safe = safe.replace("-", " ")
        safe = safe.replace(".", " ")
        safe = "".join(ch if ch.isalnum() else "_" for ch in safe)
        while "__" in safe:
            safe = safe.replace("__", "_")
        safe = safe.strip("_")
        if not safe:
            safe = "col"
        mapping[col] = safe
    return mapping


def load_csv(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo CSV: {csv_path}")
    # Leer todo como texto para evitar sorpresas de tipos
    df = pd.read_csv(csv_path, dtype=str)
    # Normalizar nombres de columna para SQL
    rename_map = make_safe_column_names(df.columns)
    df = df.rename(columns=rename_map)
    return df


def write_dataframe_to_postgres(df: pd.DataFrame, table_name: str) -> None:
    database_url = get_database_url()
    engine = create_engine(database_url)
    # Escribir en reemplazo, en lotes para eficiencia
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=1000,
        method="multi",
    )


def normalize_and_load(df: pd.DataFrame) -> None:
    """Normaliza a tablas relacionales y crea índices y agregados.

    - Crea staging: stg_consumer_complaints (todas las columnas originales)
    - Dimensiones: dim_product, dim_channel
    - Hechos: fact_complaint (complaint_id, product_id, channel_id, date_received opcional)
    - Índices: sobre claves foráneas y nombres
    - Agregado: agg_complaints_by_product_channel (cuentas por producto y canal)
    """
    database_url = get_database_url()
    engine = create_engine(database_url)

    # 1) Staging completo
    df.to_sql(
        name="stg_consumer_complaints",
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=1000,
        method="multi",
    )

    # 2) Dimensiones a partir de columnas normalizadas
    # Detectar columnas estandarizadas tras make_safe_column_names
    product_col = None
    for candidate in ["product", "product_name"]:
        if candidate in df.columns:
            product_col = candidate
            break
    channel_col = "submitted_via" if "submitted_via" in df.columns else None

    if product_col is None or channel_col is None:
        missing = []
        if product_col is None:
            missing.append("product/product_name")
        if channel_col is None:
            missing.append("submitted_via")
        raise ValueError(
            f"Columnas requeridas ausentes para normalización: {', '.join(missing)}"
        )

    products = (
        df[[product_col]]
        .dropna()
        .drop_duplicates()
        .rename(columns={product_col: "name"})
        .reset_index(drop=True)
    )
    products.insert(0, "id", products.index + 1)

    channels = (
        df[[channel_col]]
        .dropna()
        .drop_duplicates()
        .rename(columns={channel_col: "name"})
        .reset_index(drop=True)
    )
    channels.insert(0, "id", channels.index + 1)

    products.to_sql("dim_product", engine, if_exists="replace", index=False)
    channels.to_sql("dim_channel", engine, if_exists="replace", index=False)

    # Añadir PK e índices
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE dim_product ADD PRIMARY KEY (id)"))
        conn.execute(text("ALTER TABLE dim_channel ADD PRIMARY KEY (id)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uidx_dim_product_name ON dim_product(name)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uidx_dim_channel_name ON dim_channel(name)"))

    # 3) Hechos: asignar IDs por mapeo
    product_map = dict(zip(products["name"], products["id"]))
    channel_map = dict(zip(channels["name"], channels["id"]))

    fact = pd.DataFrame()
    if "complaint_id" in df.columns:
        fact["complaint_id"] = df["complaint_id"].astype(str)
    else:
        # Generar clave si no existe
        fact["complaint_id"] = (df.reset_index().index + 1).astype(str)

    # Mapear dimensiones; valores faltantes como None
    fact["product_id"] = df[product_col].map(product_map)
    fact["channel_id"] = df[channel_col].map(channel_map)

    if "date_received" in df.columns:
        fact["date_received"] = df["date_received"]

    fact.to_sql("fact_complaint", engine, if_exists="replace", index=False)

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE fact_complaint ADD PRIMARY KEY (complaint_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fact_complaint_product ON fact_complaint(product_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fact_complaint_channel ON fact_complaint(channel_id)"))

    # 4) Agregado por producto y canal (con nombres para consulta directa)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS agg_complaints_by_product_channel"))
        conn.execute(
            text(
                """
                CREATE TABLE agg_complaints_by_product_channel AS
                SELECT dp.id AS product_id,
                       dp.name AS product,
                       dc.id AS channel_id,
                       dc.name AS channel,
                       COUNT(*) AS complaints_count
                FROM fact_complaint f
                JOIN dim_product dp ON dp.id = f.product_id
                JOIN dim_channel dc ON dc.id = f.channel_id
                GROUP BY dp.id, dp.name, dc.id, dc.name
                ORDER BY dp.name, dc.name
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agg_prod ON agg_complaints_by_product_channel(product_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agg_chan ON agg_complaints_by_product_channel(channel_id)"))


def main() -> None:
    print(f"Leyendo CSV desde: {DATA_CSV}")
    df = load_csv(DATA_CSV)
    print(f"Filas: {len(df):,}  Columnas: {len(df.columns)}")
    # Carga normalizada con staging, dimensiones, hechos e índices
    normalize_and_load(df)
    print("Carga y normalización completadas. Tablas: stg_consumer_complaints, dim_product, dim_channel, fact_complaint, agg_complaints_by_product_channel")


if __name__ == "__main__":
    main()




