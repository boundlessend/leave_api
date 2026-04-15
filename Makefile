COMPOSE=docker compose

.PHONY: help install run up down logs migrate makemigrations seed test

help:
	@echo "install            install dependencies"
	@echo "run                run app locally"
	@echo "up                 start app, postgres and redis"
	@echo "down               stop containers"
	@echo "logs               show compose logs"
	@echo "migrate            apply alembic migrations"
	@echo "makemigrations     create alembic migration"
	@echo "seed               create demo users"
	@echo "test               run pytest"

install:
	python -m pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f

migrate:
	alembic upgrade head

makemigrations:
	alembic revision --autogenerate -m "$(m)"

seed:
	python -m app.seed

test:
	pytest -q
