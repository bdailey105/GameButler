PYTHON ?= python3
VENV := .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
FRONTEND_DIR := frontend

.PHONY: help setup setup-backend setup-frontend verify test lint build up down restart logs health backup restore compose-config clean

help:
	@echo "GameButler local commands"
	@echo ""
	@echo "  make setup          Install backend and frontend dependencies"
	@echo "  make verify         Run backend tests, frontend lint, frontend build, and compose config validation"
	@echo "  make up             Build and start the local Docker deployment"
	@echo "  make health         Check the running local deployment"
	@echo "  make backup         Back up data/gamebutler.db into backups/"
	@echo "  make restore BACKUP=path/to/file.db"
	@echo "  make down           Stop the local Docker deployment"
	@echo "  make logs           Tail Docker Compose logs"
	@echo "  make clean          Remove local build/test artifacts"

setup: setup-backend setup-frontend

setup-backend:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -r requirements.txt

setup-frontend:
	cd $(FRONTEND_DIR) && npm ci

verify: test lint build compose-config

test:
	$(PYTEST)

lint:
	cd $(FRONTEND_DIR) && npm run lint

build:
	cd $(FRONTEND_DIR) && npm run build

compose-config:
	docker compose config

up:
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

health:
	sh scripts/local-health.sh

backup:
	sh scripts/backup-db.sh

restore:
	sh scripts/restore-db.sh "$(BACKUP)"

clean:
	rm -rf .pytest_cache frontend/dist
