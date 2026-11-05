"""
Implementacion de referencia, independiente de las optimizadas.

Bellman-Ford es lento (O(V*E)) pero trivial de auditar: relaja todas las
aristas V-1 veces. Sirve como oraculo de correctitud. Cada algoritmo nuevo
se valida contra el mismo oraculo, asi que optimizar no puede introducir
errores silenciosos.
"""

from __future__ import annotations

from src.algorithms.base import INF
from src.graph import Graph


def bellman_ford(graph: Graph, source: int) -> list[float]:
    dist = [INF] * graph.n
    dist[source] = 0.0
    for _ in range(graph.n - 1):
        changed = False
        for u, v, w in graph.edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                changed = True
            if dist[v] + w < dist[u]:
                dist[u] = dist[v] + w
                changed = True
        if not changed:
            break
    return dist


def path_cost(graph: Graph, path: list[int]) -> float:
    """Suma real de los pesos del camino, validando que las aristas existan."""
    total = 0.0
    for u, v in zip(path, path[1:], strict=False):
        weights = [w for nb, w in graph.adj[u] if nb == v]
        if not weights:
            raise AssertionError(f"el camino usa una arista inexistente {u}->{v}")
        total += min(weights)
    return total
