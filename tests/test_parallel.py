"""Los tres modos de ejecucion deben dar exactamente las mismas respuestas."""

from src.parallel import (
    GraphSpec,
    make_queries,
    solve_processes,
    solve_sequential,
    solve_threads,
)


def test_all_modes_agree():
    spec = GraphSpec("grid", 400)
    g = spec.build()
    queries = make_queries(g.n, 40)
    expected = solve_sequential(g, queries, "astar")
    assert solve_threads(g, queries, "astar") == expected
    assert solve_processes(spec, queries, "astar", workers=2) == expected


def test_hot_sources_concentrate_origins():
    queries = make_queries(1000, 500, hot_sources=3)
    assert len({s for s, _ in queries}) <= 3


def test_queries_are_reproducible():
    """Misma semilla -> mismo lote; otra semilla -> otro lote."""
    primera = make_queries(1000, 50, seed=1)
    segunda = make_queries(1000, 50, seed=1)
    otra = make_queries(1000, 50, seed=2)
    assert primera == segunda
    assert primera != otra
