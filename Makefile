.PHONY: install dev test lint format clean help docker docker-down

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies for all services"
	@echo "  make dev          - Run payments service locally"
	@echo "  make test         - Run all tests"
	@echo "  make lint         - Check code quality"
	@echo "  make format       - Format code"
	@echo "  make docker       - Build and run with docker-compose"
	@echo "  make docker-down  - Stop and remove docker containers"
	@echo "  make clean        - Remove build artifacts"

install:
	uv sync --all-extras

dev: install
	uv run -p payments uvicorn payments.main:app --reload --host 0.0.0.0 --port 8000

test: install
	uv run pytest -v --cov=src --cov-report=html

lint: install
	uv run ruff check src/
	uv run mypy src/

format: install
	uv run black src/
	uv run ruff check --fix src/

docker:
	docker-compose up --build

docker-down: clean
	docker-compose down -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	rm -rf .coverage htmlcov dist build *.egg-info
