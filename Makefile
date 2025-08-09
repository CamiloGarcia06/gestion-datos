# DO NOT CHANGE
MAIN_DIR := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
DOCKER_DIR := $(MAIN_DIR)
PROJECT_NAME ?= introduccion

# docker compose apuntando al compose especifico
COMPOSE := docker compose -f $(DOCKER_DIR)/docker-compose.yml --project-name $(PROJECT_NAME)
SERVICE := $(PROJECT_NAME)-notebook

.PHONY: help requirements build up down restart logs shell notebook rm

help: ## Muestra los comandos disponibles
	@grep -E '^[^[:space:]]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*## "} {printf "make %-12s # %s\n", $$1, $$2}'

requirements: ## Genera requirements.txt con librerías para análisis de datos y Jupyter
	@echo "Generando requirements.txt en $(DOCKER_DIR)..."
	echo "jupyterlab" > $(DOCKER_DIR)/requirements.txt
	echo "notebook" >> $(DOCKER_DIR)/requirements.txt
	echo "ipykernel" >> $(DOCKER_DIR)/requirements.txt
	echo "ipywidgets" >> $(DOCKER_DIR)/requirements.txt
	echo "numpy" >> $(DOCKER_DIR)/requirements.txt
	echo "pandas" >> $(DOCKER_DIR)/requirements.txt
	echo "scipy" >> $(DOCKER_DIR)/requirements.txt
	echo "scikit-learn" >> $(DOCKER_DIR)/requirements.txt
	echo "matplotlib" >> $(DOCKER_DIR)/requirements.txt
	echo "seaborn" >> $(DOCKER_DIR)/requirements.txt
	echo "plotly" >> $(DOCKER_DIR)/requirements.txt
	echo "statsmodels" >> $(DOCKER_DIR)/requirements.txt
	echo "xgboost" >> $(DOCKER_DIR)/requirements.txt
	echo "pyarrow" >> $(DOCKER_DIR)/requirements.txt
	echo "openpyxl" >> $(DOCKER_DIR)/requirements.txt
	echo "polars" >> $(DOCKER_DIR)/requirements.txt
	echo "duckdb" >> $(DOCKER_DIR)/requirements.txt
	echo "SQLAlchemy" >> $(DOCKER_DIR)/requirements.txt
	echo "psycopg2-binary" >> $(DOCKER_DIR)/requirements.txt

build: down requirements ## Reconstruir dependencias e imagen y levantar en background
	$(COMPOSE) up --build -d

up: ## Levantar contenedores en background
	$(COMPOSE) up -d

down: ## Parar y eliminar contenedores y redes
	$(COMPOSE) down -v --remove-orphans

restart: ## Reiniciar contenedores
	$(COMPOSE) restart

logs: ## Seguir logs del servicio
	$(COMPOSE) logs -f

shell: ## Abrir shell dentro del contenedor principal
	$(COMPOSE) exec $(SERVICE) bash || (echo "El contenedor no está arriba. Ejecuta 'make up'" && false)

notebook: ## Mostrar URL de Jupyter
	@echo "Abre en navegador: http://localhost:8888"

rm: ## Eliminar contenedores, redes y limpiar imágenes no usadas
	@read -p "¿Eliminar todos los recursos Docker para $(PROJECT_NAME)? (y/n) " resp; \
	if [ "$$resp" = "y" ]; then \
		echo "Deteniendo y removiendo contenedores y redes..."; \
		$(COMPOSE) down -v --remove-orphans; \
		echo "Limpiando imágenes no usadas..."; \
		docker image prune -a -f; \
		echo "Operación completada."; \
	else \
		echo "Operación cancelada."; \
	fi

