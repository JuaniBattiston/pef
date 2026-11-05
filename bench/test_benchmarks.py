"""Benchmarks del CI (parte 3) con pytest-benchmark.

Operaciones representativas: una por decision de diseno que defendimos en las
partes 1 y 2. Si una de estas se vuelve mas lenta, se perdio una optimizacion.

  - Dijkstra con heap, A* y BFS sobre su familia de grafo natural.
  - Dijkstra ingenuo: el baseline. Se mide para que una "optimizacion" que en
    realidad empeora el baseline tambien se vea.
  - Arbol de caminos minimos (`dijkstra_tree`): el camino caliente de la cache.
  - Consulta resuelta por la cache (hit): lo que justifica la memoizacion.
  - Lote secuencial de consultas: el escenario del despachante.

No se mide el modo paralelo: el arranque de procesos en un runner compartido
varia demasiado para usarlo como umbral (se analizo en la parte 1).

Uso:  make bench            (corre y compara contra la linea base, si existe)
      make bench-baseline   (mide la linea base sobre otra rama, por defecto main)

Semillas fijas en grafos y consultas: cada corrida mide exactamente el mismo trabajo.
"""

from __future__ import annotations

import pytest

from src.algorithms import ALGORITHMS
from src.algorithms.dijkstra_heap import dijkstra_tree
from src.cache import RouteCache
from src.graph import Graph, generate
from src.parallel import make_queries, solve_sequential

V = 10_000  # nodos de los grafos medianos (~ el mapa real de Cordoba)
V_NAIVE = 1_000  # el baseline es O(V^2 + V*E): con V grande tarda segundos


@pytest.fixture(scope="module")
def grid() -> Graph:
    return generate("grid", V)


@pytest.fixture(scope="module")
def unweighted() -> Graph:
    return generate("unweighted", V)


@pytest.fixture(scope="module")
def grid_small() -> Graph:
    return generate("grid", V_NAIVE)


@pytest.mark.parametrize("algo", ["heap", "astar"])
def test_ruta_grid(benchmark, grid: Graph, algo: str) -> None:
    """Una consulta de punta a punta de la grilla (peor caso para Dijkstra)."""
    res = benchmark(ALGORITHMS[algo], grid, 0, grid.n - 1)
    assert res.reachable


def test_ruta_bfs(benchmark, unweighted: Graph) -> None:
    res = benchmark(ALGORITHMS["bfs"], unweighted, 0, unweighted.n - 1)
    assert res.reachable


def test_ruta_naive(benchmark, grid_small: Graph) -> None:
    res = benchmark(ALGORITHMS["naive"], grid_small, 0, grid_small.n - 1)
    assert res.reachable


def test_arbol_caminos_minimos(benchmark, grid: Graph) -> None:
    dist, _ = benchmark(dijkstra_tree, grid, 0)
    assert dist[grid.n - 1] < float("inf")


def test_cache_hit(benchmark, grid: Graph) -> None:
    cache = RouteCache(capacity=8)
    cache.route(grid, 0, grid.n - 1)  # llena la cache: lo medido son solo hits
    res = benchmark(cache.route, grid, 0, grid.n - 1)
    assert res.stats["cache"] == "hit"


def test_lote_secuencial(benchmark, grid: Graph) -> None:
    queries = make_queries(grid.n, 20)
    out = benchmark(solve_sequential, grid, queries, "astar")
    assert len(out) == len(queries)
