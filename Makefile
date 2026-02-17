.PHONY: help install run dev docker-build docker-up docker-down docker-logs docker-shell lint format test clean

# ======================== HELP ========================
help:
	@echo "AegisRAG Backend - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install dependencies"
	@echo "  make setup            Copy .env.example to .env"
	@echo ""
	@echo "Running:"
	@echo "  make run              Run production server"
	@echo "  make dev              Run development server (with auto-reload)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     Build Docker image"
	@echo "  make docker-up        Start Docker containers"
	@echo "  make docker-down      Stop Docker containers"
	@echo "  make docker-logs      View Docker logs"
	@echo "  make docker-shell     Open shell in container"
	@echo ""
	@echo "Development:"
	@echo "  make format           Format code with black"
	@echo "  make lint             Lint code with flake8"
	@echo "  make test             Run tests"
	@echo "  make clean            Remove cache and temp files"
	@echo ""

# ======================== SETUP ========================
install:
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env created from .env.example"; \
	else \
		echo "⚠️  .env already exists"; \
	fi

# ======================== RUNNING ========================
run: setup
	python -m uvicorn api.server:app --host 0.0.0.0 --port 8000

dev: setup
	AEGIS_DEBUG=true AEGIS_LOG_LEVEL=DEBUG python run.py

# ======================== DOCKER ========================
docker-build:
	docker-compose build
	@echo "✅ Docker image built"

docker-up:
	docker-compose up -d
	@echo "✅ Containers started"
	@echo "📊 API available at http://localhost:8000"
	@echo "📖 Docs available at http://localhost:8000/docs"

docker-down:
	docker-compose down
	@echo "✅ Containers stopped"

docker-logs:
	docker-compose logs -f aegisrag

docker-shell:
	docker-compose exec aegisrag /bin/bash

# ======================== DEVELOPMENT ========================
format:
	black . --line-length=100
	@echo "✅ Code formatted"

lint:
	flake8 . --max-line-length=100 --ignore=E203,W503
	@echo "✅ Lint passed"

test:
	pytest tests/ -v --tb=short
	@echo "✅ Tests passed"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	@echo "✅ Cache cleaned"

# ======================== QUICK TEST ========================
test-health:
	curl http://localhost:8000/health | python -m json.tool

test-status:
	curl http://localhost:8000/status | python -m json.tool

test-query:
	curl -X POST "http://localhost:8000/query" \
		-H "Content-Type: application/json" \
		-d '{"question": "What is in the documents?", "top_k": 3}' | python -m json.tool
