.PHONY: dev build test clean

# Development
dev:
	docker compose -f infra/docker-compose.yml up --build

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# Build
build:
	docker compose -f infra/docker-compose.yml build

# Test
test-backend:
	cd backend && pytest -v

test-frontend:
	cd frontend && npm test

test: test-backend test-frontend

# Lint
lint-backend:
	cd backend && ruff check app/ tests/

lint-frontend:
	cd frontend && npm run lint

lint: lint-backend lint-frontend

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.venv frontend/node_modules frontend/dist
