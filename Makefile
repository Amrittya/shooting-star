# =========================================================================
# Shooting Star — developer task runner
# Run `make help` to see all available targets.
# =========================================================================
.DEFAULT_GOAL := help
.PHONY: help sync lint fmt fmt-check type test test-fast cov audit ci clean docker-up docker-down docker-logs

PY := uv run

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

sync: ## Install/sync all workspace dependencies
	uv sync

lint: ## Run ruff check
	$(PY) ruff check .

fmt: ## Auto-format with ruff
	$(PY) ruff format .
	$(PY) ruff check --fix .

fmt-check: ## Verify formatting without changes
	$(PY) ruff format --check .

type: ## Run mypy in strict mode
	$(PY) mypy packages

test: ## Run all tests
	$(PY) pytest

test-fast: ## Run only fast tests
	$(PY) pytest -m "not slow"

cov: ## Run tests with coverage report
	$(PY) pytest --cov --cov-report=term-missing --cov-report=html

audit: ## Security + supply-chain audit
	@# --skip-editable ignores workspace packages that aren't on PyPI.
	@# Not --strict because workspace packages can't be resolved on PyPI (that's expected).
	$(PY) pip-audit --skip-editable
	@echo "Rust:"; (command -v cargo >/dev/null && cargo audit 2>/dev/null || echo "  cargo-audit not installed; skipping")

ci: lint fmt-check type test audit ## Run all CI gates (what pre-commit + CI enforces)

clean: ## Remove caches and build artifacts
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache -o -name .coverage -o -name htmlcov -o -name '*.egg-info' -o -name 'dist' -o -name 'build' \) -prune -exec rm -rf {} +
	rm -f .coverage

docker-up: ## Start local infra (Redis)
	docker compose up -d
	@echo "Redis:  redis://localhost:6379"

docker-down: ## Stop local infra
	docker compose down

docker-logs: ## Tail infra logs
	docker compose logs -f
