.DEFAULT_GOAL := help
COMPOSE := docker compose

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Build images and start Postgres + API (detached)
	$(COMPOSE) up -d --build

down: ## Stop and remove containers
	$(COMPOSE) down

logs: ## Tail all service logs
	$(COMPOSE) logs -f

build: ## Build the backend image
	$(COMPOSE) build

migrate: ## Apply database migrations (alembic upgrade head)
	$(COMPOSE) run --rm api alembic upgrade head

makemigration: ## Autogenerate a migration: make makemigration m="message"
	$(COMPOSE) run --rm api alembic revision --autogenerate -m "$(m)"

test: ## Run the test suite
	$(COMPOSE) run --rm --no-deps api pytest

lint: ## Lint with ruff
	$(COMPOSE) run --rm --no-deps api ruff check .

fmt: ## Auto-format with ruff
	$(COMPOSE) run --rm --no-deps api ruff format .

ingest: ## Run one ingest+analyze cycle (implemented in Phase 1)
	@echo "ingest: implemented in Phase 1"

demo: ## Replay a curated escalation event (implemented in Phase 6)
	@echo "demo: implemented in Phase 6"

.PHONY: help up down logs build migrate makemigration test lint fmt ingest demo
