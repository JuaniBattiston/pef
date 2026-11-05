"""Datos compartidos por todos los tests."""

import random

import pytest

from src.graph import FAMILIES, generate

EPS = 1e-9
SIZES = {"grid": 100, "highway": 100, "dense": 120, "unweighted": 100}


def pairs(g, k=8, seed=7):
    """Pares (origen, destino) reproducibles para un grafo."""
    rng = random.Random(seed)
    return [(rng.randrange(g.n), rng.randrange(g.n)) for _ in range(k)]


@pytest.fixture(params=sorted(FAMILIES))
def graph(request):
    """Un grafo chico de cada familia: cada test corre una vez por familia."""
    return generate(request.param, SIZES[request.param])


@pytest.fixture
def grid400():
    return generate("grid", 400)
