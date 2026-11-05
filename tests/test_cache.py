"""Memoizacion de arboles + cache LRU con invalidacion por version."""

import random

import pytest

from src.cache import RouteCache
from tests.reference import bellman_ford


def test_cache_returns_same_results(grid400):
    """La cache no puede cambiar la respuesta, solo el tiempo."""
    cache = RouteCache(capacity=8)
    rng = random.Random(3)
    hot = [0, 7, 21]
    refs = {s: bellman_ford(grid400, s) for s in hot}
    for _ in range(30):
        s, t = rng.choice(hot), rng.randrange(grid400.n)
        assert cache.route(grid400, s, t).cost == pytest.approx(refs[s][t])
    assert cache.stats.hits >= 27


def test_cache_invalidates_on_map_change(grid400):
    """No devolver informacion obsoleta: si se corta una calle, el costo sube."""
    cache = RouteCache()
    src, dst = 0, grid400.n - 1
    before = cache.route(grid400, src, dst)
    u, v = before.path[0], before.path[1]
    w = min(w for nb, w in grid400.adj[u] if nb == v)
    grid400.update_weight(u, v, w * 1000)

    after = cache.route(grid400, src, dst)
    assert cache.stats.invalidations == 1
    assert after.cost == pytest.approx(bellman_ford(grid400, src)[dst])
    assert after.cost > before.cost


def test_cache_respects_capacity(grid400):
    """LRU acotada: la memoria no crece sin limite."""
    cache = RouteCache(capacity=4)
    for s in range(20):
        cache.route(grid400, s, grid400.n - 1)
    assert len(cache) == 4
    assert cache.stats.evictions == 16


def test_lru_keeps_recently_used(grid400):
    cache = RouteCache(capacity=2)
    cache.route(grid400, 1, 0)
    cache.route(grid400, 2, 0)
    cache.route(grid400, 1, 0)  # 1 pasa a ser el mas reciente
    cache.route(grid400, 3, 0)  # desaloja al 2
    cache.route(grid400, 1, 0)
    assert cache.stats.hits == 2


def test_invalid_capacity():
    with pytest.raises(ValueError):
        RouteCache(capacity=0)
