PYTHON := python3
SRC_PATH := src
TEST_PATH := tests

.DEFAULT_GOAL := help

.PHONY: help
help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Environment ───────────────────────────────────────────────────────────────

.PHONY: install
install:  ## Install all dependencies (including dev) with uv
	uv sync --all-groups

.PHONY: install-prod
install-prod:  ## Install production dependencies only
	uv sync --no-dev

.PHONY: clean
clean:  ## Remove cache files and build artifacts
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/ .ruff_cache/ .mypy_cache/

# ── Code Quality ──────────────────────────────────────────────────────────────

.PHONY: format
format:  ## Format code with black and ruff
	uv run black $(SRC_PATH) $(TEST_PATH)
	uv run ruff check --select I --fix $(SRC_PATH) $(TEST_PATH)

.PHONY: lint
lint:  ## Run linting checks (ruff + black --check)
	uv run ruff check $(SRC_PATH) $(TEST_PATH)
	uv run black --check $(SRC_PATH) $(TEST_PATH)

.PHONY: type-check
type-check:  ## Run static type checking with mypy
	uv run mypy $(SRC_PATH) --ignore-missing-imports

# ── Testing ───────────────────────────────────────────────────────────────────

.PHONY: test
test:  ## Run tests
	uv run pytest $(TEST_PATH) --verbose

.PHONY: test-cov
test-cov:  ## Run tests with coverage report
	uv run pytest $(TEST_PATH) --verbose --cov=$(SRC_PATH) --cov-report=html --cov-report=term-missing

.PHONY: test-fast
test-fast:  ## Run tests without verbose output
	uv run pytest $(TEST_PATH) -q

# ── Combined Workflows ────────────────────────────────────────────────────────

.PHONY: check
check: lint test  ## Run all checks (lint + tests)

.PHONY: ci
ci: install lint test-cov  ## Full CI pipeline (install + lint + test with coverage)

# ── Build & Release ───────────────────────────────────────────────────────────

.PHONY: generate-man
generate-man:  ## Generate man pages from the CLI app definition
	PYTHONPATH=src uv run scripts/generate_man.py
	@echo "Man pages written to man/man1/"

.PHONY: install-man
install-man: generate-man  ## Generate and install man pages (requires sudo)
	@install -d $(DESTDIR)/usr/share/man/man1
	@for f in man/man1/*.1; do \
		install -m 644 "$$f" $(DESTDIR)/usr/share/man/man1/; \
		gzip -f "$(DESTDIR)/usr/share/man/man1/$$(basename $$f)"; \
	done
	@ln -sf todopro.1.gz $(DESTDIR)/usr/share/man/man1/tp.1.gz
	@mandb 2>/dev/null || true
	@echo "Man pages installed. Run: man todopro"

.PHONY: build
build: clean  ## Build distribution packages
	uv build

.PHONY: publish
publish: build  ## Publish package to PyPI
	uv publish
