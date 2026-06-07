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
	$(COMPOSE) run --rm api pytest

lint: ## Lint with ruff
	$(COMPOSE) run --rm --no-deps api ruff check .

fmt: ## Auto-format with ruff
	$(COMPOSE) run --rm --no-deps api ruff format .

seed: ## Seed the source rows (GDELT + RSS + EIA)
	$(COMPOSE) run --rm api python -m worker.seeds

ingest: ## Run one ingest cycle (GDELT + RSS + EIA) once
	$(COMPOSE) run --rm api python -m worker.run_ingest

analyze: ## Analyze un-analyzed articles (prefilter -> triage -> extract -> score)
	$(COMPOSE) run --rm api python -m worker.run_analyze

eval: ## Run the golden-set evaluation harness
	$(COMPOSE) run --rm api python -m eval.run_eval

alert: ## Backfill alerts for relevant analyses (match -> dedup -> deliver)
	$(COMPOSE) run --rm api python -m worker.run_alerting

worker: ## Start the continuous ingestion worker (APScheduler)
	$(COMPOSE) --profile worker up -d --build worker

demo: ## Replay a curated escalation event (implemented in Phase 6)
	@echo "demo: implemented in Phase 6"

.PHONY: help up down logs build migrate makemigration test lint fmt seed ingest analyze eval alert worker demo
