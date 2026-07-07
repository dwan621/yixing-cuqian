.PHONY: install test-backend test-frontend test dev-backend dev-frontend e2e

install:
	cd backend && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"
	cd frontend && npm install

test-backend:
	cd backend && pytest -v

test-frontend:
	cd frontend && npx vitest run

test: test-backend test-frontend

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

e2e:
	cd backend && pytest tests/test_e2e_ac.py -v
