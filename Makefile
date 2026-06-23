API := services/api
COMPOSE := deploy/compose.yaml

.PHONY: install dev lint typecheck test fmt up down migrate revision run

install:  ## Create venv and install api + dev deps
	cd $(API) && python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -e '.[dev]'

run:  ## Run the API locally (needs a reachable database)
	cd $(API) && .venv/bin/uvicorn app.main:app --reload --port 8000

lint:
	cd $(API) && .venv/bin/ruff check .

fmt:
	cd $(API) && .venv/bin/ruff check --fix . && .venv/bin/ruff format .

typecheck:
	cd $(API) && .venv/bin/mypy app

test:
	cd $(API) && .venv/bin/pytest

up:  ## Start Postgres + Redis + API via Compose
	docker compose -f $(COMPOSE) up --build

down:
	docker compose -f $(COMPOSE) down -v

migrate:  ## Apply migrations against CHESS_DATABASE_URL
	cd $(API) && .venv/bin/alembic upgrade head

revision:  ## make revision m="message"
	cd $(API) && .venv/bin/alembic revision --autogenerate -m "$(m)"
