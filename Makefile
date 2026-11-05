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
GITLEAKS_IMAGE := docker.io/zricethezav/gitleaks:v8.30.1
LYCHEE_IMAGE   := docker.io/lycheeverse/lychee:0.24.2
MDLINT         := npx --yes markdownlint-cli2@0.24.0

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
# Benchmark: % de empeoramiento de la MEDIANA contra la linea base que rechaza.
BENCH_REGRESION := 25
# Rama/commit contra el que se compara el benchmark (el CI pasa origin/main).
BASE_REF ?= main

# --- rendimiento ---------------------------------------------------------------
PY_ABS := $(if $(findstring /,$(PY)),$(abspath $(PY)),$(PY))
BENCH_OPTS := bench/test_benchmarks.py -p no:cacheprovider --benchmark-only \
  --benchmark-disable-gc --benchmark-min-rounds=10 --benchmark-sort=name \
  --benchmark-columns=min,median,iqr,rounds --benchmark-storage="file://$(CURDIR)/.benchmarks"
# Carga que se perfila: un lote de consultas sobre una grilla de 16.000 nodos.
PROFILE_ARGS := -m src.cli lote --family grid --size 16000 --n 100 --modo secuencial

.PHONY: help setup lock ci lint types complexity test sec-code secrets sec-deps \
  docs bench bench-baseline memory profile clean

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

secrets: | $(REPORTS) ## Gitleaks sobre todo el historial que llega al commit actual
	@# --log-opts HEAD: se escanea el historial del commit que se integra, no las demas
	@# ramas del repo (con --all, un secreto en una rama ajena rechazaria cualquier PR).
	@if command -v gitleaks >/dev/null; then \
	  gitleaks git . --no-banner --redact -v --log-opts="--full-history HEAD" \
	    --report-format sarif --report-path $(REPORTS)/gitleaks.sarif; \
	else \
	  $(CONTAINER) run --rm -v "$$PWD":/repo:Z -w /repo $(GITLEAKS_IMAGE) \
	    git /repo --no-banner --redact -v --log-opts="--full-history HEAD" \
	    --report-format sarif --report-path /repo/$(REPORTS)/gitleaks.sarif; \
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

# --- etapa 5: documentacion ---------------------------------------------------

docs: | $(REPORTS) ## MkDocs --strict + markdownlint-cli2 + Lychee (enlaces)
	$(PY) -m mkdocs build --strict --site-dir site
	$(MDLINT)
	@if command -v lychee >/dev/null; then \
	  lychee --config lychee.toml --no-progress --format markdown --output $(REPORTS)/lychee.md docs README.md \
	    && st=0 || st=$$?; \
	else \
	  $(CONTAINER) run --rm -v "$$PWD":/repo:Z -w /repo $(LYCHEE_IMAGE) \
	    --config lychee.toml --no-progress --format markdown --output $(REPORTS)/lychee.md docs README.md \
	    && st=0 || st=$$?; \
	fi; cat $(REPORTS)/lychee.md; exit $$st

# --- etapa 6: rendimiento y memoria -------------------------------------------

bench-baseline: ## Mide la linea base en BASE_REF (default main) con los benchmarks actuales
	@rm -rf .benchmarks; tmp=$$(mktemp -d); \
	git worktree add -q --detach "$$tmp" $(BASE_REF); \
	cp bench/test_benchmarks.py "$$tmp/bench/"; \
	echo "==> linea base: $(BASE_REF) ($$(git rev-parse --short $(BASE_REF)))"; \
	(cd "$$tmp" && "$(PY_ABS)" -m pytest $(BENCH_OPTS) --benchmark-save=base) && st=0 || st=$$?; \
	git worktree remove --force "$$tmp"; exit $$st

bench: | $(REPORTS) ## pytest-benchmark; falla si la mediana empeora > BENCH_REGRESION % vs la base
	@cmp=""; \
	if ls .benchmarks/*/*_base.json >/dev/null 2>&1; then \
	  cmp="--benchmark-compare --benchmark-compare-fail=median:$(BENCH_REGRESION)%"; \
	else echo "==> sin linea base (make bench-baseline): se mide sin comparar"; fi; \
	$(PY) -m pytest $(BENCH_OPTS) --benchmark-json=$(REPORTS)/bench.json $$cmp

memory: | $(REPORTS) ## Pico de memoria (tracemalloc) contra bench/memory_limits.json
	$(PY) -m bench.check_memory

profile: | $(REPORTS) ## Perfil de CPU (pyinstrument + cProfile). Informativo, no bloquea
	$(PY) -m pyinstrument -r session -o $(REPORTS)/profile.pyisession $(PROFILE_ARGS)
	$(PY) -m pyinstrument --load $(REPORTS)/profile.pyisession -r html -o $(REPORTS)/profile.html
	$(PY) -m pyinstrument --load $(REPORTS)/profile.pyisession -r text -o $(REPORTS)/profile.txt
	$(PY) -m cProfile -o $(REPORTS)/profile.prof $(PROFILE_ARGS) > /dev/null
	$(PY) -c "import pstats; pstats.Stats('$(REPORTS)/profile.prof').sort_stats('tottime').print_stats(20)" \
	  > $(REPORTS)/profile_top20.txt
	@grep -A12 "ncalls" $(REPORTS)/profile_top20.txt

# --- todo junto ----------------------------------------------------------------

ci: lint types complexity sec-code secrets test sec-deps docs bench memory profile ## Todos los controles, en orden
	@echo; echo "==> make ci: todos los controles aprobados"

clean: ## Borra reportes y caches
	rm -rf $(REPORTS) .benchmarks .coverage .mypy_cache .ruff_cache .pytest_cache .benchmarks site
