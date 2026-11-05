"""IMPLEMENTACION BASELINE (fila 1 de la tabla comparativa).

Deliberadamente ingenua, pero correcta. Es la linea base contra la que se
miden todas las optimizaciones, asi que no se toca: las versiones mejoradas
viven en modulos aparte.

Dos ineficiencias intencionales, cada una atacada por una optimizacion
posterior distinta:

  (a) Seleccion del minimo por barrido lineal sobre el arreglo de distancias.
      Se ejecuta V veces y cada una recorre V nodos  ->  O(V^2).
      Lo ataca el heap binario:  O(log V) por extraccion  ->  O(V log V).

  (b) Busqueda de vecinos recorriendo la lista plana de aristas. Por cada
      nodo extraido se recorren las E aristas para ver cuales lo tocan
      ->  O(V * E).
      Lo ataca la lista de adyacencia: O(grado(u)) por nodo, y la suma de
      los grados es 2E  ->  O(E) en todo el algoritmo.

Complejidad total del baseline:  O(V^2 + V*E).
En una malla urbana E ~ 2V, con lo cual queda O(V^2), y el termino que
domina en la practica es (b) por la constante alta del barrido de aristas.

`on_expand`: callback opcional, ver la convencion en `base.py`.
"""

from __future__ import annotations

from ..graph import Graph
from .base import INF, SearchResult, rebuild_path


def dijkstra_naive(graph: Graph, source: int, target: int, on_expand=None) -> SearchResult:
    """Dijkstra baseline: minimo por barrido lineal y vecinos por lista plana."""
    n = graph.n
    dist = [INF] * n
    parent = [-1] * n
    visited = [False] * n
    dist[source] = 0.0
    expanded = 0

    for _ in range(n):
        # (a) minimo por barrido lineal: O(V)
        u, best = -1, INF
        for i in range(n):
            if not visited[i] and dist[i] < best:
                u, best = i, dist[i]
        if u == -1:
            break

        visited[u] = True
        expanded += 1
        if on_expand is not None:
            on_expand(u)
        if u == target:
            break

        # (b) vecinos recorriendo TODAS las aristas: O(E)
        for a, b, w in graph.edges:
            if a == u:
                v = b
            elif b == u:
                v = a
            else:
                continue
            if not visited[v] and best + w < dist[v]:
                dist[v] = best + w
                parent[v] = u

    return SearchResult(
        cost=dist[target],
        path=rebuild_path(parent, source, target),
        expanded=expanded,
        algorithm="dijkstra_naive",
    )
