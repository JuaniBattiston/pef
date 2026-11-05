# Plan — Tercer Parcial: documentación externa + CI

> Criterio rector (igual que en la parte 2): **simple y reproducible**.
> Cada control es **un comando** que corre igual en la máquina local y en el CI.
> El CI no tiene lógica propia: llama a `make <control>`. Si pasa local, pasa en CI.

---

## 0. Punto de partida (medido el 2026-11-05)

| Control | Estado actual | Qué falta |
|---|---|---|
| Repositorio | **no es un repo git**, `gh` no instalado | `git init`, repo en GitHub, rama `main` protegida |
| Pruebas | pytest, todo verde | reporte JUnit |
| Cobertura | **98 %** en `src/` | fijar umbral |
| Ruff | `All checks passed` | salida SARIF/JSON |
| Complejidad | promedio A (3.0); peores: `dijkstra_naive` C (13), `section_algorithms` C (14) | fijar umbral + gate |
| mypy | **4 errores** (`osm.py:92-93`, `parallel.py:105`, `archivos.py:71`) | corregirlos |
| Bandit | 1 Medium (B310 `data/fetch_cordoba.py:87`), 5 Low (B311 `random`) | todos falsos positivos → documentar |
| pip-audit | sin vulnerabilidades | dependencias **sin fijar** (`fastapi`, `uvicorn` sin versión) |
| Documentación | Sphinx (solo API) + README largo | sitio con las 9 secciones exigidas |
| Benchmark / memoria | scripts propios en `bench/` (cProfile + tracemalloc) | versión con umbral y línea base |

---

## 1. Decisiones (una herramienta por control)

| Tema | Elección | Por qué |
|---|---|---|
| Plataforma CI | **GitHub Actions** | gratis en repo público, integra Dependabot, CodeQL, SARIF y Pages |
| Documentación externa | **MkDocs + Material** publicada en **GitHub Pages** | Markdown en Git (se reutiliza README/EJECUCION), colaboración por PR, acceso por permisos del repo |
| API en la doc | **mkdocstrings[python]** (reemplaza Sphinx) | una sola herramienta; lee los docstrings Google que ya tenemos |
| Orquestación local | **Makefile** | `make ci` = el pipeline completo en local |
| Dependencias fijadas | **uv pip compile** → `requirements.lock` y `requirements-dev.lock` con hashes | instalación reproducible (`--require-hashes`) |

---

## 2. Matriz de controles (el centro del trabajo)

| Control | Herramienta | Comando (`make …`) | Reporte | Criterio de rechazo |
|---|---|---|---|---|
| Pruebas | pytest | `make test` | consola + `reports/junit.xml` | ≥ 1 test falla |
| Cobertura | pytest-cov | (dentro de `make test`) | `coverage.xml` + HTML | `--cov-fail-under=90` en `src/` |
| Análisis estático | Ruff (+ Pylint informativo) | `make lint` | consola + `reports/ruff.sarif` | cualquier error de ruff o `ruff format --check` falla; Pylint `--fail-under=9` |
| Complejidad | Radon (reporte) + Xenon (gate) | `make complexity` | `reports/radon_cc.txt`, `radon_mi.txt` | función > C (CC > 20) o promedio del módulo > A → rechaza. Advertencia en C (11-20) |
| Tipado | mypy | `make types` | consola + `reports/mypy.txt` | cualquier error en `src/` (`--disallow-untyped-defs`) |
| Seguridad del código | Bandit + CodeQL | `make sec-code` | `reports/bandit.sarif` + `.txt`; CodeQL en pestaña Security | Bandit: severidad **High** (confianza ≥ Medium) bloquea; Medium/Low se reportan |
| Secretos | Gitleaks | `make secrets` | `reports/gitleaks.sarif` | cualquier hallazgo bloquea (excepciones en `.gitleaks.toml`) |
| Dependencias | pip-audit + Dependabot | `make sec-deps` | `reports/pip-audit.json` + `.md` | vulnerabilidad con fix disponible o CVSS ≥ 7 bloquea; excepciones con `--ignore-vuln` documentadas |
| Documentación | MkDocs `--strict` + markdownlint-cli2 + Lychee | `make docs` | `site/` como artefacto | build falla, warning de mkdocs o enlace roto |
| Benchmark | pytest-benchmark | `make bench` | `reports/bench.json` + tabla comparativa | mediana > **+25 %** contra `main` medido en el **mismo runner** |
| Profiling CPU | pyinstrument (+ cProfile) | `make profile` | `reports/profile.html` + top-20 | **informativo** (no bloquea): se publica para revisar el cuello de botella |
| Memoria | tracemalloc (script propio) | `make memory` | `reports/memory.json` | pico > límite de `bench/memory_limits.json` (pico medido × 1,3) |

### Por qué estos umbrales
- **Cobertura 90 %**: hoy estamos en 98 %; 90 da margen sin permitir que se caiga.
- **CC ≤ 20**: `dijkstra_naive` (13) es el baseline a propósito y se queda; el
  límite atrapa funciones nuevas inmanejables sin forzar a "romper" el baseline.
- **Benchmark +25 %**: los runners de GitHub varían ±10-15 %. Para no comparar
  hardware distinto, el job corre el benchmark de `main` y del PR **en la misma
  máquina, en el mismo job** (`--benchmark-compare-fail=median:25%`).
- **Memoria con tracemalloc**: mide asignaciones de Python, es casi determinista
  (no depende del RSS del runner) → se puede usar un límite fijo con 30 % de margen.

---

## 3. Diseño del pipeline (`.github/workflows/ci.yml`)

Disparadores: `push` a `main` y `pull_request` hacia `main`. Rápido primero, caro al final.

```
            ┌─ lint ───────┐
            ├─ types ──────┤
 setup ─────┼─ complexity ─┼──► test+cov ──┬─ sec-deps ─┐
 (lock +    ├─ sec-code ───┤               ├─ docs ─────┼──► perf (bench,  ──► resultado
  caché)    └─ secrets ────┘               └────────────┘     memory, profile)   (resumen)
```

| Etapa | Jobs | Notas |
|---|---|---|
| 1. Integración | — | PR obligatorio a `main`, branch protection exige todos los checks |
| 2. Entorno | `setup` | Python 3.14, `pip install --require-hashes -r requirements-dev.lock`, caché pip |
| 3. Estática | `lint`, `types`, `complexity`, `sec-code`, `secrets` | en paralelo, ~1 min |
| 4. Pruebas | `test` (matriz 3.12 / 3.14) | `needs:` etapa 3 |
| 5. Deps + docs | `sec-deps`, `docs` | en paralelo |
| 6. Rendimiento | `perf` | solo si todo lo anterior pasó |
| 7. Resultado | `summary` (`if: always()`) | tabla aprobado/rechazado en `$GITHUB_STEP_SUMMARY`, sube `reports/` como artefacto |

Workflows aparte:
- `codeql.yml` (push/PR + semanal) → SARIF a la pestaña Security.
- `docs-deploy.yml` (push a `main`) → `mkdocs gh-deploy` a GitHub Pages.
- `.github/dependabot.yml` → `pip` y `github-actions`, semanal.
- Todos los SARIF (ruff, bandit, gitleaks) se suben con `github/codeql-action/upload-sarif`.

---

## 4. Política de seguridad (explícita y verificable)

| Fuente | Bloquea | Revisión antes de integrar | Solo se reporta |
|---|---|---|---|
| Bandit | High | Medium | Low |
| pip-audit | CVSS ≥ 7 o con fix disponible | resto | — |
| CodeQL | error | warning | note |
| Gitleaks | todo | — | — |

Excepciones: **solo** con `# nosec BXXX  # motivo` en la línea, o `--ignore-vuln ID`
en el Makefile, y cada una registrada en `docs/seguridad.md` (ID, motivo, fecha, quién).

Falsos positivos ya identificados (para documentar):
- **B311 × 5** (`random` en `graph.py`, `archivos.py`, `parallel.py`): genera
  grafos y consultas de prueba, no hay uso criptográfico → `# nosec B311`.
- **B310** (`data/fetch_cordoba.py:87`, `urlopen`): URL fija `https://` hacia
  Overpass, script offline de descarga → validar el esquema y `# nosec B310`.

---

## 5. Documentación externa (MkDocs) — estructura

```
docs/
  index.md               Descripción funcional: problema, alcance, requisitos
  arquitectura.md        módulos, responsabilidades, dependencias + diagrama Mermaid
  instalacion.md         dependencias, configuración, comandos
  diseno-tecnico.md      estructuras de datos, algoritmos, decisiones (sale del README §4-5)
  api.md                 mkdocstrings (src.graph, src.algorithms, src.cache, …) + ejemplos CLI/HTTP
  pruebas.md             estrategia, casos, resultados (cobertura del último CI)
  rendimiento.md         benchmarks, profiling, complejidad O(), memoria (parte 1 y 2)
  seguridad.md           riesgos, dependencias, política, falsos positivos, excepciones
  mantenimiento.md       cómo contribuir, `make ci` local, cómo resolver cada fallo del pipeline
```

`mantenimiento.md` cubre el **requisito adicional**: tabla "control → comando
local → qué significa el fallo → cómo arreglarlo" (p. ej. `make bench` falla →
correr `make bench-compare` contra `main`, revisar `reports/profile.html`).

---

## 6. Orden de trabajo

1. **Repo**: `git init`, `.gitignore` (agregar `reports/`, `site/`, `.benchmarks/`),
   primer commit, crear repo en GitHub, push. (Instalar `gh` o hacerlo por la web.)
2. **Dependencias fijadas**: `requirements*.in` → `.lock` con hashes; agregar
   mypy, xenon, bandit, pip-audit, pytest-benchmark, pyinstrument, mkdocs-material,
   mkdocstrings; sacar sphinx.
3. **Arreglar lo que rompería el CI**: 4 errores de mypy, `# nosec` justificados.
4. **Makefile** con un target por control + `make ci`. Verificar todo verde en local.
5. **Benchmarks y memoria**: `tests/bench/test_bench.py` (pytest-benchmark sobre
   heap/astar/bfs en grilla 200×200, caché hit/miss, lote paralelo) y
   `bench/check_memory.py` + `memory_limits.json`.
6. **Workflow CI** + CodeQL + Dependabot. Primer push → corregir lo que falle.
7. **Branch protection** en `main` (checks requeridos, PR obligatorio).
8. **Documentación MkDocs**: migrar contenido del README/EJECUCION/resultados-parte-2,
   escribir seguridad y mantenimiento, publicar en Pages.
9. **Evidencia**: PR de prueba que **rompa** a propósito cada gate (test que falla,
   cobertura baja, regresión de rendimiento con `time.sleep`, secreto falso) y
   capturas de cada rechazo → `resultados-parte-3/`.

---

## 7. Entregables

- URL del repo y de la documentación en GitHub Pages.
- `.github/workflows/*.yml`, `Makefile`, locks, configs (`pyproject.toml`, `.gitleaks.toml`, `dependabot.yml`).
- Corrida verde en `main` + PRs de demostración rechazados.
- `resultados-parte-3/`: capturas, reportes descargados (JUnit, SARIF, JSON), tabla de la matriz.

## 8. Riesgos / decisiones pendientes

- **Repo público o privado**: CodeQL, secret scanning y Pages son gratis solo en
  públicos (o con GitHub Pro / Education). Recomendado: **público**.
- **Python 3.14 en CI**: disponible en `setup-python`; si alguna herramienta no lo
  soporta (pasó con Scalene en la parte 2), se corre esa herramienta en 3.12.
- **Variabilidad del benchmark**: si la comparación en el mismo runner sigue
  siendo ruidosa, subir la tolerancia a 35 % o usar `--benchmark-min-rounds`.
