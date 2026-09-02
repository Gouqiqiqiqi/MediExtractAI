.PHONY: dev build test clean preflight deploy

# Development
dev:
	docker compose up --build

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# Build
build:
	docker compose build

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

# Demo operations
# Run this before showing the demo to anyone: it exercises the whole path,
# including one real extraction, and says what is wrong rather than that
# something is.
preflight:
	./scripts/preflight.sh

deploy:
	ssh oracle 'cd /data/projects/MediExtractAI && git pull --ff-only && docker compose up -d --build'
	./scripts/preflight.sh

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.venv frontend/node_modules frontend/dist
