#!/usr/bin/env bash
# Demostracion de la parte 2: corre cada punto en orden, con una pausa entre pasos.
# Uso (desde cualquier carpeta):  ./demo.sh
set -e
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

paso() { echo; echo "==== $1 ===="; }
pausa() { read -rp "  [Enter para seguir]" _; }

paso "Testing (punto 9): pytest"
pytest
pausa

paso "Archivos grandes (punto 4): generar 200.000 consultas"
python -m src.cli generar-consultas --size 2000 --n 200000 --salida "$TMP/consultas.csv"
pausa

paso "Archivos grandes (punto 4): resolverlas por lotes en paralelo"
python -m src.cli archivo --size 2000 --entrada "$TMP/consultas.csv" --salida "$TMP/respuestas.csv"
head -5 "$TMP/respuestas.csv"
pausa

paso "PEP 8 (punto 5): ruff"
ruff check .
ruff format --check .
pausa

paso "Documentacion (punto 6): Sphinx"
sphinx-build -q -b html docs docs/_build/html
echo "  -> docs/_build/html/index.html"
pausa

paso "APM (punto 3): Pyroscope"
if curl -s -o /dev/null http://localhost:4040/ready; then
    python -m bench.apm_pyroscope
else
    echo "  Pyroscope no esta corriendo. Levantarlo con:"
    echo "    docker start pyroscope-pef   (o: docker run -d --name pyroscope-pef -p 4040:4040 grafana/pyroscope)"
fi
pausa

paso "Framework (punto 10): visualizador FastAPI"
echo "  -> http://localhost:8000   y   http://localhost:8000/docs   (Ctrl+C para cortar)"
python -m viz.server
