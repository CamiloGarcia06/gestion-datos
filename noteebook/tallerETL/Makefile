SHELL := /bin/bash

# Variables
PROJECT_DIR := $(shell pwd)
COMPOSE := docker compose

.PHONY: help up build run logs psql load down reset

help:
	@echo "Targets disponibles:"
	@echo "  up      : Levanta Postgres y la app (construye si es necesario)"
	@echo "  build   : Construye la imagen de la app"
	@echo "  run     : Ejecuta el ETL (requiere servicios arriba)"
	@echo "  logs    : Muestra logs de servicios"
	@echo "  psql    : Abre psql contra la base"
	@echo "  load    : Levanta todo y corre el ETL"
	@echo "  down    : Detiene y elimina servicios"
	@echo "  reset   : Borra datos de Postgres y reinicia"

up:
	$(COMPOSE) up -d --build postgres
	$(COMPOSE) up -d app

build:
	$(COMPOSE) build app

run:
	$(COMPOSE) run --rm app python etl_consumer_complaints.py

logs:
	$(COMPOSE) logs -f --tail=200

psql:
	$(COMPOSE) exec postgres psql -U etl -d etl

load: up run

down:
	$(COMPOSE) down

reset:
	$(COMPOSE) down -v
	$(COMPOSE) up -d --build postgres
