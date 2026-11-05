"""OPTIMIZACION DE ALGORITMO (fila 3 de la tabla).

A* es Dijkstra guiado: en vez de ordenar la frontera por g(n) (costo
acumulado), la ordena por f(n) = g(n) + h(n), donde h estima lo que falta
hasta el destino. Con h = 0 degenera exactamente en Dijkstra.

Cota asintotica: la MISMA que Dijkstra, O((V+E) log V). La mejora no es
asintotica sino en el factor constante: A* expande menos nodos porque
descarta las direcciones que se alejan del destino. Por eso la metrica que
justifica esta optimizacion es `expanded`, no solo el reloj.

Condiciones que debe cumplir h (verificadas en tests/test_correctness.py):

  - Admisible: h(n) <= costo real de n al destino. Garantiza que la ruta
    devuelta es optima. Se cumple porque todo peso se genero como
    dist_euclidea * factor con factor >= 1.

  - Consistente: h(u) <= w(u,v) + h(v). Garantiza que un nodo cerrado no
    necesita reabrirse, y por lo tanto que el set de visitados es correcto.
    Se cumple por desigualdad triangular: la diferencia de distancias
    euclideas a un mismo destino nunca supera la distancia entre los nodos,
    que a su vez no supera el peso de la arista.

Cuando A* NO conviene (medido en el benchmark):
  - Grafo denso sin geometria util: h no informa, se paga su calculo de gratis.
  - Pesos de alta varianza (familia `highway`): h subestima mucho, el frente
    de busqueda se ensancha y A* tiende a Dijkstra.

`on_expand`: callback opcional, ver la convencion en `base.py`.
"""

from __future__ import annotations

import heapq

from ..graph import Graph
from .base import INF, SearchResult, rebuild_path


def astar(graph: Graph, source: int, target: int, on_expand=None) -> SearchResult:
    """A* de `source` a `target` con heuristica euclidea admisible."""
    g_score = [INF] * graph.n
    parent = [-1] * graph.n
    visited: set[int] = set()
    g_score[source] = 0.0
    h = graph.heuristic
    frontier = [(h(source, target), 0.0, source)]
    expanded = 0
    pushes = 1

    adj = graph.adj
    while frontier:
        _, g_u, u = heapq.heappop(frontier)
        if u in visited:
            continue
        visited.add(u)
        expanded += 1
        if on_expand is not None:
            on_expand(u)
        if u == target:
            break
        for v, w in adj[u]:
            ng = g_u + w
            if v not in visited and ng < g_score[v]:
                g_score[v] = ng
                parent[v] = u
                heapq.heappush(frontier, (ng + h(v, target), ng, v))
                pushes += 1

    return SearchResult(
        cost=g_score[target],
        path=rebuild_path(parent, source, target),
        expanded=expanded,
        algorithm="astar",
        stats={"pushes": pushes, "heap_peak": len(frontier)},
    )
