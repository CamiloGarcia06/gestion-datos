COMPOSE_PROJECT_NAME ?= taller_cobranzas
DOCKER_COMPOSE = COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT_NAME) docker compose -f docker-compose.yml

DB_SERVICE = db
DB_NAME ?= cobranzas
DB_USER ?= odoo
DB_PASSWORD ?= odoo
DB_HOST ?= db
DB_PORT ?= 5432

LOADER_IMAGE = taller_cobranzas_loader:latest
NETWORK = $(COMPOSE_PROJECT_NAME)_default

.PHONY: up down restart logs status psql build-loader load shell-loader run-python run-consulta run-reportes run-eficiencia

up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

restart:
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE) up -d

logs:
	$(DOCKER_COMPOSE) logs -f $(DB_SERVICE) | cat

status:
	$(DOCKER_COMPOSE) ps | cat

# Open psql connected to the running DB (auto starts stack if needed)
psql:
	# Modes:
	# 1) Interactive: make psql
	# 2) Inline query: make psql Q="SELECT now();"
	# 3) From file: make psql FILE=queries/init.sql
	@$(DOCKER_COMPOSE) up -d > /dev/null
	@if [ -n "$(Q)" ]; then \
		$(DOCKER_COMPOSE) exec -T -e PGPASSWORD=$(DB_PASSWORD) $(DB_SERVICE) \
		  psql -U $(DB_USER) -d $(DB_NAME) -c "$(Q)"; \
	elif [ -n "$(FILE)" ]; then \
		cat "$(FILE)" | $(DOCKER_COMPOSE) exec -T -e PGPASSWORD=$(DB_PASSWORD) $(DB_SERVICE) \
		  psql -U $(DB_USER) -d $(DB_NAME); \
	else \
		$(DOCKER_COMPOSE) exec -e PGPASSWORD=$(DB_PASSWORD) -it $(DB_SERVICE) \
		  psql -U $(DB_USER) -d $(DB_NAME); \
	fi

# Build a lightweight Python image that has psycopg2 and pg_restore/psql
build-loader:
	docker build -t $(LOADER_IMAGE) .

# Restore the dump file and demonstrate a DB cursor execution
load: build-loader
	docker run --rm --network $(NETWORK) \
	  -e PGHOST=$(DB_HOST) -e PGPORT=$(DB_PORT) \
	  -e PGUSER=$(DB_USER) -e PGPASSWORD=$(DB_PASSWORD) -e PGDATABASE=$(DB_NAME) \
	  -v $(CURDIR)/data:/app/data \
	  -v $(CURDIR)/load_dump.py:/app/load_dump.py \
	  $(LOADER_IMAGE) python /app/load_dump.py --dump /app/data/taller_cobranzas.dump

shell-loader: build-loader
	docker run --rm -it --network $(NETWORK) \
	  -e PGHOST=$(DB_HOST) -e PGPORT=$(DB_PORT) \
	  -e PGUSER=$(DB_USER) -e PGPASSWORD=$(DB_PASSWORD) -e PGDATABASE=$(DB_NAME) \
	  -v $(CURDIR)/data:/app/data \
	  -v $(CURDIR)/load_dump.py:/app/load_dump.py \
	  $(LOADER_IMAGE) /bin/bash

run-python: build-loader
	@$(DOCKER_COMPOSE) up -d > /dev/null
	docker run --rm --network $(NETWORK) \
	  -e PGHOST=$(DB_HOST) -e PGPORT=$(DB_PORT) \
	  -e PGUSER=$(DB_USER) -e PGPASSWORD=$(DB_PASSWORD) -e PGDATABASE=$(DB_NAME) \
	  -v $(CURDIR)/data:/app/data \
	  -v $(CURDIR)/load_dump.py:/app/load_dump.py \
	  $(LOADER_IMAGE) python /app/load_dump.py $(if $(DUMP),--dump $(DUMP),) $(if $(SKIP_RESTORE),--skip-restore,) $(if $(RESET_PUBLIC),--reset-public,) $(if $(CONTINUE_ON_ERROR),--continue-on-error,) $(ARGS)


run-consulta: build-loader
	@$(DOCKER_COMPOSE) up -d > /dev/null
	docker run --rm --network $(NETWORK) \
	  -e PGHOST=$(DB_HOST) -e PGPORT=$(DB_PORT) \
	  -e PGUSER=$(DB_USER) -e PGPASSWORD=$(DB_PASSWORD) -e PGDATABASE=$(DB_NAME) \
	  -v $(CURDIR)/run_consulta.py:/app/run_consulta.py \
	  -v $(CURDIR)/output:/app/output \
	  $(LOADER_IMAGE) bash -lc "mkdir -p /app/output && python /app/run_consulta.py $(if $(OUTPUT),--output /app/output/consulta.json,) $(ARGS)"

run-reportes: build-loader
	@$(DOCKER_COMPOSE) up -d > /dev/null
	docker run --rm --network $(NETWORK) \
	  -e PGHOST=$(DB_HOST) -e PGPORT=$(DB_PORT) \
	  -e PGUSER=$(DB_USER) -e PGPASSWORD=$(DB_PASSWORD) -e PGDATABASE=$(DB_NAME) \
	  -e OUTPUT_DIR=/app/output \
	  -v $(CURDIR)/reportes.py:/app/reportes.py \
	  -v $(CURDIR)/output:/app/output \
	  $(LOADER_IMAGE) bash -lc "mkdir -p /app/output && python /app/reportes.py"

run-eficiencia: build-loader
	@$(DOCKER_COMPOSE) up -d > /dev/null
	docker run --rm --network $(NETWORK) \
	  -e PGHOST=$(DB_HOST) -e PGPORT=$(DB_PORT) \
	  -e PGUSER=$(DB_USER) -e PGPASSWORD=$(DB_PASSWORD) -e PGDATABASE=$(DB_NAME) \
	  -e OUTPUT_DIR=/app/output \
	  -v $(CURDIR)/eficiencia_agencias.py:/app/eficiencia_agencias.py \
	  -v $(CURDIR)/output:/app/output \
	  $(LOADER_IMAGE) bash -lc "mkdir -p /app/output && python /app/eficiencia_agencias.py"


