.DEFAULT_GOAL := help

# Helper to ensure uv is available before running commands that need it
define ensure_uv
	@command -v uv >/dev/null 2>&1 || { echo "Error: 'uv' is required. Install: https://docs.astral.sh/uv/"; exit 1; }
endef

.PHONY: help setup sync install run lint format test build clean ci

help: ## Show this help message
	@printf "Common developer tasks:\n\n"
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_%-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Create or update local dev environment (includes dev dependencies)
	$(ensure_uv)
	uv sync --dev

sync: ## Sync runtime dependencies only (no dev extras)
	$(ensure_uv)
	uv sync

install: ## Alias for 'sync' (compatibility)
	@$(MAKE) sync

run: ## Run the CLI (pass ARGS="..."), e.g. ARGS="hello -n world -t 2"
	$(ensure_uv)
	uv run dev-digest $(ARGS)

lint: ## Run static checks (Ruff)
	$(ensure_uv)
	uv run ruff check .

lint-fix: ## Fix static checks (Ruff)
	$(ensure_uv)
	uv run ruff check --fix .

format: ## Format code (Ruff)
	$(ensure_uv)
	uv run ruff format

test: ## Run tests (pytest). Pass PYTEST_ARGS for customization
	$(ensure_uv)
	uv run pytest -q $(PYTEST_ARGS)

build: ## Build sdist and wheel
	$(ensure_uv)
	uv build

clean: ## Remove build, cache, and coverage artifacts
	rm -rf dist build .pytest_cache .ruff_cache .coverage htmlcov *.egg-info

ci: ## CI pipeline: setup, lint, test, build
	@$(MAKE) setup
	@$(MAKE) lint
	@$(MAKE) test
	@$(MAKE) build