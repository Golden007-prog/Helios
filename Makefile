# Helios — repo-wide convenience targets.
#
# Designed for Linux/macOS bash. Windows users should use `make` from a Bash
# shell (Git Bash, WSL) or run the equivalent commands directly.
#
# Conventions:
#   `make`              shows this help
#   `make dev`          runs backend + frontend concurrently
#   `make test`         runs backend + frontend test suites
#   `make typegen`      regenerates shared OpenAPI + TS types + constants
#   `make seed`         seeds Cloudant with the MeridianBank demo corpus
#   targets prefixed `deploy:` are gated on IBM Cloud creds.

PYTHON ?= python
PIP ?= $(PYTHON) -m pip

.DEFAULT_GOAL := help

.PHONY: help
help:
	@grep -E '^[a-zA-Z][^:]*:.*##' $(MAKEFILE_LIST) | sort | sed -E 's/:.*##/ — /'

# ---- install --------------------------------------------------------------

.PHONY: install
install: install.backend install.mcp install.frontend ## Install every workspace's deps

.PHONY: install.backend
install.backend: ## pip install -e backend (with dev extras)
	$(PIP) install -e "backend[dev]"

.PHONY: install.mcp
install.mcp: ## pip install -e mcp-servers (with dev extras)
	$(PIP) install -e "mcp-servers[dev]"

.PHONY: install.frontend
install.frontend: ## npm install in frontend/
	cd frontend && npm install

# ---- dev ------------------------------------------------------------------

.PHONY: dev
dev: ## Run backend + frontend concurrently
	@echo "→ backend on :8080  /  frontend on :3000"
	@( \
		($(PYTHON) -m uvicorn app.main:app --reload --port 8080 --app-dir backend &); \
		(cd frontend && npm run dev); \
	)

# ---- lint / format / typecheck -------------------------------------------

.PHONY: lint
lint: lint.backend lint.frontend ## ruff + eslint

.PHONY: lint.backend
lint.backend:
	cd backend && $(PYTHON) -m ruff check .
	cd backend && $(PYTHON) -m mypy app

.PHONY: lint.frontend
lint.frontend:
	cd frontend && npm run typecheck && npm run lint

.PHONY: format
format: ## ruff format + prettier
	cd backend && $(PYTHON) -m ruff format .
	cd frontend && npm run format

# ---- tests ---------------------------------------------------------------

.PHONY: test
test: test.backend test.mcp test.frontend ## pytest + vitest

.PHONY: test.backend
test.backend:
	cd backend && $(PYTHON) -m pytest

.PHONY: test.mcp
test.mcp:
	cd mcp-servers && $(PYTHON) -m pytest

.PHONY: test.frontend
test.frontend:
	cd frontend && npm test

.PHONY: test.e2e
test.e2e: ## Playwright e2e against the static export
	cd frontend && npm run test:e2e

# ---- codegen --------------------------------------------------------------

.PHONY: typegen
typegen: ## OpenAPI dump + Pydantic→TS + constants → frontend/src/lib/api/*.gen.ts
	$(PYTHON) -m shared.codegen.dump_openapi
	$(PYTHON) -m shared.codegen.pydantic_to_typescript
	$(PYTHON) -m shared.codegen.dump_constants

# ---- data ----------------------------------------------------------------

.PHONY: indexes
indexes: ## Idempotently apply Cloudant indexes
	cd backend && $(PYTHON) -m migrations.apply_indexes

.PHONY: migrate
migrate: indexes ## Alias for indexes (kept for parity with future schema migrations)

.PHONY: migrate-rollback
migrate-rollback: ## Delete every Mango design doc owned by the migration (no data loss)
	cd backend && $(PYTHON) -m migrations.apply_indexes --rollback

.PHONY: seed
seed: migrate seed-bankdemo seed-omp seed-cobolcheck ## Apply indexes + seed all 3 datasets into shop meridianbank.demo

.PHONY: seed-legacy
seed-legacy: migrate ## Seed the legacy abstract MeridianBank corpus (shop meridianbank)
	cd backend && $(PYTHON) -m migrations.seed_demo

.PHONY: seed-bankdemo
seed-bankdemo: ## Seed only the BankDemo dataset (Rocket EULA)
	cd backend && $(PYTHON) -m migrations.seed_corpus --pack bankdemo

.PHONY: seed-omp
seed-omp: ## Seed only the OMP COBOL Course dataset (CC-BY-4.0)
	cd backend && $(PYTHON) -m migrations.seed_corpus --pack omp_course

.PHONY: seed-cobolcheck
seed-cobolcheck: ## Seed only the cobol-check dataset (Apache 2.0)
	cd backend && $(PYTHON) -m migrations.seed_corpus --pack cobol_check

.PHONY: seed-reset
seed-reset: ## Wipe shop meridianbank.demo and re-seed all 3 datasets
	cd backend && $(PYTHON) -m migrations.seed_corpus --reset

.PHONY: verify-corpus
verify-corpus: ## Run the end-to-end corpus assertions in backend/tests/test_corpus_e2e.py
	cd backend && $(PYTHON) -m pytest tests/test_corpus_e2e.py -v --tb=short

.PHONY: calibrate
calibrate: ## Run the Confidence Score calibration bench across all scenarios
	$(PYTHON) -m bench.calibrate_confidence

.PHONY: calibrate-report
calibrate-report: calibrate ## Regenerate docs/CALIBRATION_REPORT.md (gitignored)
	@echo "→ docs/CALIBRATION_REPORT.md updated"

# ---- docker --------------------------------------------------------------

.PHONY: docker.build
docker.build: ## Build the backend image
	docker build -t helios-backend:dev backend

.PHONY: docker.run
docker.run: ## Run the backend image (env from .env)
	docker run --rm -p 8080:8080 --env-file .env helios-backend:dev

# ---- deploy --------------------------------------------------------------

.PHONY: deploy.backend
deploy.backend: ## Push image + apply Code Engine spec (requires IBM creds)
	bash backend/deploy/deploy.sh

.PHONY: deploy.frontend
deploy.frontend: ## Static-export the frontend for GitHub Pages
	cd frontend && GITHUB_PAGES=true PAGES_BASE_PATH=/Helios npm run build
	@echo "→ frontend/out is ready for GitHub Pages upload"

# ---- demo / abend smoke + benchmark --------------------------------------

.PHONY: demo-smoke
demo-smoke: ## 8-step round-trip per docs/TESTING.md §2 (xfail-graceful when Bob stubs)
	cd backend && $(PYTHON) -m pytest tests/test_demo_smoke.py -v --tb=short

.PHONY: abend-smoke
abend-smoke: ## ABEND analyzer happy path with seeded S0C7 (xfail until Bob lands classifier)
	cd backend && $(PYTHON) -m pytest tests/test_abend_smoke.py::test_seeded_s0c7_match_confirmed -v --tb=short

.PHONY: abend-smoke-degraded
abend-smoke-degraded: ## ABEND analyzer degraded path (novel pattern → unfamiliar tier)
	cd backend && $(PYTHON) -m pytest tests/test_abend_smoke.py::test_novel_pattern_degraded -v --tb=short

.PHONY: benchmark
benchmark: ## Performance budgets per docs/TESTING.md §5; writes to bench/results/<date>.json
	cd backend && $(PYTHON) -m pytest tests/test_benchmark.py -v --tb=short

.PHONY: lint.audit
lint.audit: ## tools/lint_audit_calls.py — wired into pre-commit, runnable here too
	$(PYTHON) tools/lint_audit_calls.py
