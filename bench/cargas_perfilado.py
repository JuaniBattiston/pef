"""Cargas de trabajo para los perfiladores externos (py-spy y Scalene).

Uso (desde la raiz del proyecto):
    py-spy record -r 200 -f raw -o resultados-parte-2/perfilado/pyspy_baseline.txt \
        -- python bench/cargas_perfilado.py baseline
    py-spy record -r 200 -o resultados-parte-2/perfilado/flamegraph.svg \
        -- python bench/cargas_perfilado.py archivo
    uvx --python 3.12 --from scalene==1.5.51 scalene --cli --cpu --profile-all \
        --profile-exclude threading bench/cargas_perfilado.py --- baseline
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # los perfiladores lo ejecutan como script

from src.algorithms.dijkstra_naive import dijkstra_naive  # noqa: E402
from src.archivos import generar_consultas, procesar_archivo  # noqa: E402
from src.graph import generate  # noqa: E402
from src.parallel import GraphSpec, make_queries  # noqa: E402


def baseline() -> None:
    """El baseline de la parte 1: ¿que linea concentra el tiempo?"""
    g = generate("grid", 2500)
    for s, t in make_queries(g.n, 20):
        dijkstra_naive(g, s, t)


def archivo() -> None:
    """Procesar un CSV de consultas: ¿pesa mas el I/O o el calculo?"""
    spec = GraphSpec("grid", 2000)
    with tempfile.TemporaryDirectory() as d:
        entrada = Path(d) / "q.csv"
        generar_consultas(entrada, spec.build().n, 20_000)
        procesar_archivo(entrada, Path(d) / "r.csv", spec, paralelo=False)


if __name__ == "__main__":
    {"baseline": baseline, "archivo": archivo}[sys.argv[1]]()
