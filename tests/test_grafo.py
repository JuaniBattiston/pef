"""Generacion de grafos y cambios del mapa."""

import pytest

from src.graph import FAMILIES, generate
from tests.conftest import SIZES


def test_version_changes_on_map_update():
    """La invalidacion de cache depende de que version se incremente."""
    g = generate("grid", 100)
    u, v, w = g.edges[0]
    assert g.update_weight(u, v, w * 10)
    assert g.version == 1
    assert g.edges[0][2] == w * 10
    assert (v, w * 10) in g.adj[u]
    assert (u, w * 10) in g.adj[v]


def test_missing_edge_does_not_touch_version():
    g = generate("grid", 100)
    assert g.update_weight(0, g.n - 1, 1.0) is False
    assert g.version == 0


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_generation_is_reproducible(family):
    """Semilla fija => mismo grafo. Sin esto las mediciones no son comparables."""
    a = generate(family, SIZES[family], seed=42)
    b = generate(family, SIZES[family], seed=42)
    assert a.edges == b.edges


def test_unknown_family_is_rejected():
    with pytest.raises(ValueError):
        generate("marte", 100)
