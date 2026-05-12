.PHONY: setup dev verify test

setup:
	python3 -m venv .venv
	.venv/bin/pip install -q -r requirements.txt
	@[ -f .env ] || cp .env.example .env && echo "Created .env from .env.example — fill in your keys."

dev:
	@echo "Starting backend and frontend..."
	RIFTBUDDY_TEST_MODE=1 LLM_PROVIDER=mock .venv/bin/python -m uvicorn backend.main:app --reload --port 8001 &
	cd frontend && npm run dev

verify:
	RIFTBUDDY_TEST_MODE=1 LLM_PROVIDER=mock .venv/bin/python -m pytest backend/tests/ -q --no-header
	cd frontend && npm test --silent
	RIFTBUDDY_TEST_MODE=1 LLM_PROVIDER=mock .venv/bin/python evals/run_evals.py
