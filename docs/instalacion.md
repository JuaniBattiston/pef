# Instalación y ejecución

## Requisitos

| Requisito | Versión | Para qué |
| --- | --- | --- |
| Python | 3.12 o superior (el CI usa 3.12 y 3.14) | todo |
| Git | cualquiera reciente | clonar; `make bench-baseline` usa `git worktree` |
| GNU Make | cualquiera | correr los controles |
| Node.js | 18 o superior | solo `make docs` (markdownlint-cli2 por `npx`) |
| Podman o Docker | opcional | `make secrets` y `make docs` si no están instalados `gitleaks` o `lychee` |

## Instalación

```bash
git clone git@github.com:JuaniBattiston/pef.git
cd pef
make setup                 # crea .venv e instala requirements-dev.txt con --require-hashes
source .venv/bin/activate
```

`make setup` equivale a:

```bash
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements-dev.txt
```

`--require-hashes` hace que pip rechace cualquier paquete cuyo hash no coincida con el
lock. Así la instalación es idéntica en cualquier máquina y en el CI.

Si solo se quiere usar la aplicación (sin herramientas de desarrollo):

```bash
pip install --require-hashes -r requirements.txt
```

## Configuración

El proyecto no usa variables de entorno ni archivos de configuración propios. Los
parámetros se pasan por línea de comandos. La configuración de las herramientas está
centralizada en:

| Archivo | Configura |
| --- | --- |
| `pyproject.toml` | pytest, coverage, ruff, mypy |
| `Makefile` | umbrales de aprobación de todos los controles |
| `bench/memory_limits.json` | límites de memoria por escenario |
| `mkdocs.yml`, `.markdownlint-cli2.yaml`, `lychee.toml` | documentación |
| `.github/` | pipeline de CI, CodeQL y Dependabot |

## Ejecución

Siempre desde la raíz del proyecto.

### CLI

```bash
python -m src.cli ruta     --family grid --size 16000 --origen 100 --destino 15000 --algo astar
python -m src.cli comparar --family highway --size 16000
python -m src.cli simular  --family grid --size 4000
python -m src.cli lote     --family grid --size 16000 --n 200 --modo procesos
python -m src.cli generar-consultas --size 2000 --n 1000000 --salida consultas.csv
python -m src.cli archivo  --size 2000 --entrada consultas.csv --salida respuestas.csv
```

Opciones completas en [API y contratos](api.md#cli).

### Visualizador web

```bash
python data/fetch_cordoba.py   # solo si falta data/cordoba.json (~25 s)
python -m viz.server           # http://localhost:8000  (documentación interactiva en /docs)
python -m viz.server 8080      # otro puerto
```

### Controles de calidad

```bash
make help    # lista todos los targets
make ci      # corre todos los controles, igual que el pipeline
```

Detalle de cada control en [Integración continua](ci.md) y cómo resolver fallos en
[Mantenimiento](mantenimiento.md).

### Documentación

```bash
mkdocs serve   # http://127.0.0.1:8000 con recarga automática
make docs      # build estricto + estilo + enlaces (lo mismo que el CI)
```

### Scripts de mediciones de las partes 1 y 2

```bash
python -m bench.run_bench       # tabla comparativa -> results/
python -m bench.make_report
python -m bench.profile_run
python -m bench.bench_archivos  # batching / buffer / paralelo
```

Los resultados de esas entregas están en `results/` y `resultados-parte-2/`.
