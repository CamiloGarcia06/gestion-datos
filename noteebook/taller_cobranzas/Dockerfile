FROM python:3.11-slim

# Avoid writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install PostgreSQL client tools (psql, pg_restore) and CA certs
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Minimal runtime deps for DB connectivity from Python
RUN pip install --no-cache-dir psycopg2-binary

# The loader script will be bind-mounted by the Makefile when executed
CMD ["python", "/app/load_dump.py", "--help"]


