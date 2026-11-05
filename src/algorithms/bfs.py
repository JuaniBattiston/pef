"""BFS: el caso especial que gana cuando el grafo no tiene pesos (fila 3 alt).

Si todas las aristas cuestan lo mismo, la cola FIFO ya visita los nodos en
orden de costo creciente: la primera vez que se alcanza un nodo es por el
camino minimo. No hace falta ordenar la frontera, y desaparece el factor
log V del heap.

  Dijkstra con heap : O((V + E) log V)
  BFS               : O(V + E)

Estructura: `collections.deque`, que es una lista doblemente enlazada por
bloques. Da popleft() en O(1), contra O(n) de una lista de Python, que al
sacar del frente tiene que desplazar todos los elementos restantes. Usar
`list.pop(0)` convertiria el algoritmo en O(V^2 + E).

Aplicabilidad: solo es correcto con pesos uniformes. Aplicarlo a un grafo
pesado devuelve el camino con menos saltos, que no es el mas barato. Por eso
el algoritmo valida la precondicion en vez de dar un resultado incorrecto en
silencio.

`on_expand`: callback opcional, ver la convencion en `base.py`.
"""

from __future__ import annotations

from collections import deque

from ..graph import Graph
from .base import INF, SearchResult, rebuild_path


def bfs(graph: Graph, source: int, target: int, on_expand=None) -> SearchResult:
    """BFS de `source` a `target`. Solo valido si todas las aristas pesan igual."""
    if graph.weighted:
        raise ValueError(
            "BFS solo es correcto con pesos uniformes; este grafo es pesado. "
            "Usar dijkstra_heap o astar."
        )

    parent = [-1] * graph.n
    dist = [INF] * graph.n
    dist[source] = 0.0
    queue = deque([source])
    expanded = 0
    adj = graph.adj

    while queue:
        u = queue.popleft()
        expanded += 1
        if on_expand is not None:
            on_expand(u)
        if u == target:
            break
        du = dist[u]
        for v, w in adj[u]:
            if dist[v] == INF:
                dist[v] = du + w
                parent[v] = u
                queue.append(v)

    return SearchResult(
        cost=dist[target],
        path=rebuild_path(parent, source, target),
        expanded=expanded,
        algorithm="bfs",
    )
