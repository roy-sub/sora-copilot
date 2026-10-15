# SORA Copilot backend. One command per task; `make dev` is the one the README names.
.DEFAULT_GOAL := help
VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip
PORT ?= 8000

$(VENV)/bin/activate: pyproject.toml
	python3 -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -e ".[dev]"
	@touch $(VENV)/bin/activate

.PHONY: install
install: $(VENV)/bin/activate ## Create the venv and install the project

.PHONY: dev
dev: install ## Run the API with reload on $(PORT)
	$(VENV)/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port $(PORT)

.PHONY: serve
serve: install ## Run the API without reload (production shape)
	$(VENV)/bin/uvicorn app.main:app --host 0.0.0.0 --port $(PORT)

.PHONY: test
test: install ## Run the test suite
	$(VENV)/bin/pytest

.PHONY: lint
lint: install ## Ruff + mypy
	$(VENV)/bin/ruff check app tests scripts
	$(VENV)/bin/mypy app

.PHONY: fmt
fmt: install ## Apply ruff fixes and formatting
	$(VENV)/bin/ruff check --fix app tests scripts
	$(VENV)/bin/ruff format app tests scripts

.PHONY: rulebase
rulebase: install ## Regenerate .lp fact files from the transcribed CSV tables
	$(PY) scripts/build_rulebase.py

.PHONY: openapi
openapi: install ## Write the OpenAPI schema to openapi.json (frontend client input)
	$(PY) scripts/export_openapi.py

.PHONY: docker
docker: ## Build the production image
	docker build -t sora-copilot-backend .

.PHONY: clean
clean: ## Remove the venv and caches
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

.PHONY: help
help:
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'
