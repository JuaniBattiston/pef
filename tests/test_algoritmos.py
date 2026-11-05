"""Correctitud de los algoritmos contra el oraculo Bellman-Ford.

Una optimizacion que cambia el resultado no es una optimizacion, es un bug.
"""

import pytest

from src.algorithms import ALGORITHMS
from src.algorithms.astar import astar
from src.algorithms.base import INF
from src.algorithms.bfs import bfs
from src.algorithms.dijkstra_heap import dijkstra_heap, dijkstra_tree
from src.graph import generate
from tests.conftest import EPS, SIZES, pairs
from tests.reference import bellman_ford, path_cost

# BFS solo vale sin pesos: tiene sus propios tests.
WEIGHTED_ALGOS = ["naive", "heap", "astar"]


@pytest.mark.parametrize("name", WEIGHTED_ALGOS)
def test_costs_match_reference(graph, name):
    for s, t in pairs(graph):
        assert ALGORITHMS[name](graph, s, t).cost == pytest.approx(bellman_ford(graph, s)[t])


@pytest.mark.parametrize("name", WEIGHTED_ALGOS)
def test_path_is_valid_and_consistent(graph, name):
    for s, t in pairs(graph):
        res = ALGORITHMS[name](graph, s, t)
        assert res.path[0] == s
        assert res.path[-1] == t
        assert path_cost(graph, res.path) == pytest.approx(res.cost)


def test_heuristic_is_admissible(graph):
    """Si h sobreestima, A* devuelve rutas suboptimas y la comparacion se cae."""
    goal = graph.n - 1
    real = bellman_ford(graph, goal)
    for u in range(graph.n):
        if real[u] < INF:
            assert graph.heuristic(u, goal) <= real[u] + EPS


def test_tree_matches_single_queries(graph):
    """El arbol de caminos minimos (base de la memoizacion) coincide."""
    dist, _ = dijkstra_tree(graph, 0)
    assert dist == pytest.approx(bellman_ford(graph, 0))


def test_bfs_matches_on_unweighted():
    g = generate("unweighted", SIZES["unweighted"])
    for s, t in pairs(g):
        assert bfs(g, s, t).cost == pytest.approx(bellman_ford(g, s)[t])


def test_bfs_rejects_weighted_graphs():
    """Precondicion explicita en vez de un resultado incorrecto en silencio."""
    pesado = generate("grid", 100)
    with pytest.raises(ValueError):
        bfs(pesado, 0, 1)


def test_astar_expands_no_more_than_dijkstra_on_grid(grid400):
    for s, t in pairs(grid400):
        assert astar(grid400, s, t).expanded <= dijkstra_heap(grid400, s, t).expanded


def test_same_source_and_target(grid400):
    for name in WEIGHTED_ALGOS:
        res = ALGORITHMS[name](grid400, 5, 5)
        assert res.cost == 0
        assert res.path == [5]


def test_on_expand_reports_every_expanded_node(grid400):
    seen = []
    res = astar(grid400, 0, grid400.n - 1, on_expand=seen.append)
    assert len(seen) == res.expanded
    assert seen[0] == 0


def test_mapa_real_cordoba():
    """La heuristica calculada de los datos reales es consistente y A* es optimo."""
    from src.osm import cargar_cordoba, nodo_mas_cercano

    try:
        g = cargar_cordoba()
    except FileNotFoundError:
        pytest.skip("falta data/cordoba.json")

    assert g.n > 1000
    assert 0 < g.heuristic_scale <= 1.0
    for u, v, w in g.edges:
        assert g.euclid(u, v) * g.heuristic_scale <= w + EPS
    for s, t in pairs(g, k=10, seed=5):
        assert astar(g, s, t).cost == pytest.approx(dijkstra_heap(g, s, t).cost)
    assert nodo_mas_cercano(g, *g.coords[42]) == 42
