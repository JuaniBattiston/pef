# Controles de calidad y eficiencia (parte 3).
#
# El CI (.github/workflows/ci.yml) llama a estos mismos targets: lo que pasa
# con `make ci` en local pasa en el CI, y lo que falla, falla igual.
#
#   make setup       crea .venv e instala las dependencias fijadas (con hashes)
#   make ci          corre todos los controles en el orden del pipeline
#   make help        lista los targets
#
# Cada target deja su reporte en reports/ y termina con codigo != 0 si el
# control rechaza el cambio. Los umbrales estan definidos abajo, en un solo lugar.

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

# --- entorno ----------------------------------------------------------------
# Usa .venv si existe; en el CI las herramientas estan en el Python del runner.
PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python)
REPORTS := reports

# Herramientas que no son de Python: binario local si existe, si no, contenedor.
CONTAINER ?= $(shell command -v podman || command -v docker)
GITLEAKS_IMAGE := docker.io/zricethezav/gitleaks:v8.21.2

# --- umbrales (politica de aprobacion / rechazo) -----------------------------
COV_MIN        := 90   # % minimo de cobertura de src/
PYLINT_MIN     := 9.5  # puntaje minimo de pylint (hoy 9.71)
XENON_ABSOLUTE := C    # peor rango permitido para una funcion (C = CC <= 20)
XENON_MODULES  := C    # peor rango permitido para un modulo
XENON_AVERAGE  := A    # rango promedio del proyecto (A = CC <= 5)
BANDIT_SEV     := high   # severidad minima que bloquea
BANDIT_CONF    := medium # confianza minima que bloquea
# Vulnerabilidades aceptadas explicitamente (ver docs/seguridad.md). Ej: --ignore-vuln GHSA-xxxx
PIP_AUDIT_IGNORE :=

.PHONY: help setup lock ci lint types complexity test sec-code secrets sec-deps clean

help: ## Lista los targets disponibles
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

$(REPORTS):
	@mkdir -p $(REPORTS)

# --- entorno reproducible ------------------------------------------------------

setup: ## Crea .venv e instala dependencias fijadas (pip --require-hashes)
	python3 -m venv .venv
	.venv/bin/pip install -q --upgrade pip
	.venv/bin/pip install -q --require-hashes -r requirements-dev.txt

lock: ## Regenera requirements*.txt desde los .in (requiere uv)
	uv pip compile requirements.in --universal --python-version 3.12 --generate-hashes -q -o requirements.txt
	uv pip compile requirements-dev.in --universal --python-version 3.12 --generate-hashes -q -o requirements-dev.txt

# --- etapa 3: calidad estatica -------------------------------------------------

lint: | $(REPORTS) ## Ruff (estilo + errores) y Pylint
	$(PY) -m ruff check --output-format sarif -o $(REPORTS)/ruff.sarif --exit-zero .
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .
	$(PY) -m pylint src --fail-under=$(PYLINT_MIN) | tee $(REPORTS)/pylint.txt

types: | $(REPORTS) ## mypy sobre src/ (config en pyproject.toml)
	$(PY) -m mypy | tee $(REPORTS)/mypy.txt

complexity: | $(REPORTS) ## Radon (reporte) + Xenon (umbral de complejidad ciclomatica)
	$(PY) -m radon cc src -s -a > $(REPORTS)/radon_cc.txt
	$(PY) -m radon mi src -s > $(REPORTS)/radon_mi.txt
	@tail -1 $(REPORTS)/radon_cc.txt
	$(PY) -m xenon src --max-absolute $(XENON_ABSOLUTE) --max-modules $(XENON_MODULES) --max-average $(XENON_AVERAGE)

sec-code: | $(REPORTS) ## Bandit: reportes completos + bloqueo por severidad
	$(PY) -m bandit -q -r src viz bench data -f sarif -o $(REPORTS)/bandit.sarif --exit-zero
	$(PY) -m bandit -q -r src viz bench data -f txt -o $(REPORTS)/bandit.txt --exit-zero
	$(PY) -m bandit -q -r src viz bench data -f txt -o $(REPORTS)/bandit_nosec.txt --ignore-nosec --exit-zero
	$(PY) -m bandit -q -r src viz bench data --severity-level $(BANDIT_SEV) --confidence-level $(BANDIT_CONF)

secrets: | $(REPORTS) ## Gitleaks sobre todo el historial de git
	@if command -v gitleaks >/dev/null; then \
	  gitleaks git . --no-banner --redact -v --report-format sarif --report-path $(REPORTS)/gitleaks.sarif; \
	else \
	  $(CONTAINER) run --rm -v "$$PWD":/repo:Z -w /repo $(GITLEAKS_IMAGE) \
	    git /repo --no-banner --redact -v --report-format sarif --report-path /repo/$(REPORTS)/gitleaks.sarif; \
	fi

# --- etapa 4: pruebas y cobertura ----------------------------------------------

test: | $(REPORTS) ## pytest + cobertura minima de src/
	$(PY) -m pytest \
	  --junitxml=$(REPORTS)/junit.xml \
	  --cov=src --cov-report=term --cov-report=xml:$(REPORTS)/coverage.xml \
	  --cov-report=html:$(REPORTS)/htmlcov --cov-fail-under=$(COV_MIN)

# --- etapa 5: seguridad de dependencias ----------------------------------------

sec-deps: | $(REPORTS) ## pip-audit sobre las dependencias fijadas
	$(PY) -m pip_audit -r requirements-dev.txt --require-hashes --disable-pip $(PIP_AUDIT_IGNORE) \
	  -f json -o $(REPORTS)/pip-audit.json || true
	$(PY) -m pip_audit -r requirements-dev.txt --require-hashes --disable-pip $(PIP_AUDIT_IGNORE) \
	  -f markdown --desc | tee $(REPORTS)/pip-audit.md

# --- todo junto ----------------------------------------------------------------

ci: lint types complexity sec-code secrets test sec-deps ## Todos los controles, en orden
	@echo; echo "==> make ci: todos los controles aprobados"

clean: ## Borra reportes y caches
	rm -rf $(REPORTS) .coverage .mypy_cache .ruff_cache .pytest_cache .benchmarks site
