"""OPTIMIZACION DE ESTRUCTURAS DE DATOS (fila 2 de la tabla).

Mismo algoritmo que el baseline -- Dijkstra -- cambiando unicamente las
estructuras. Aislar la variable es lo que permite atribuir la mejora a la
estructura y no al algoritmo.

Tres cambios, tres estructuras justificadas:

  1. Lista de adyacencia (`graph.adj`) en lugar del barrido de la lista
     plana de aristas.
     La operacion dominante es "dame los vecinos de u", que se ejecuta una
     vez por nodo extraido. Con lista plana cuesta O(E) cada vez -> O(V*E)
     total. Con adyacencia cuesta O(grado(u)), y como la suma de los grados
     de todos los nodos es 2E, el total de todo el algoritmo es O(E).

  2. Heap binario (`heapq`) para la frontera.
     La operacion dominante es "extraer el nodo no visitado de menor
     distancia tentativa", V veces. El barrido lineal cuesta O(V) cada vez
     -> O(V^2). El heap cuesta O(log V) por extraccion y O(log V) por
     insercion. Como se inserta a lo sumo una vez por relajacion exitosa
     (E veces) y se extrae a lo sumo esa misma cantidad, queda
     O((V + E) log V).

  3. Set de visitados.
     Se necesita "ya cerre este nodo?" una vez por elemento sacado del heap.
     El set da pertenencia O(1) promedio por hashing, contra O(V) de una
     lista. Aca los ids son densos y un arreglo de booleanos tambien seria
     O(1); se usa set porque la cantidad de nodos cerrados suele ser mucho
     menor que V cuando hay destino (busqueda con corte temprano), asi que
     el set ocupa proporcional a lo realmente visitado y no a V.

Complejidad total:  O((V + E) log V).

Nota sobre el heap: `heapq` no tiene decrease-key. Se usa borrado perezoso,
es decir se insertan entradas duplicadas y al extraer se descartan las que
corresponden a un nodo ya cerrado. El heap crece hasta O(E) en vez de O(V),
pero cada operacion sigue costando O(log E) = O(log V^2) = O(2 log V), que
es O(log V). El trade-off es memoria por simplicidad, y evita mantener un
indice de posiciones dentro del heap.

`on_expand`: callback opcional, ver la convencion en `base.py`.
"""

from __future__ import annotations

import heapq

from ..graph import Graph
from .base import INF, OnExpand, SearchResult, rebuild_path


def _search(
    graph: Graph, source: int, target: int | None, on_expand: OnExpand | None = None
) -> tuple[list[float], list[int], int, dict[str, int]]:
    """Bucle de Dijkstra con heap, con corte temprano al llegar a `target`."""
    dist = [INF] * graph.n
    parent = [-1] * graph.n
    visited: set[int] = set()
    dist[source] = 0.0
    frontier = [(0.0, source)]
    expanded = 0
    pushes = 1

    adj = graph.adj  # enlace local: evita la busqueda de atributo en el bucle
    while frontier:
        d, u = heapq.heappop(frontier)
        if u in visited:
            continue  # entrada obsoleta del borrado perezoso
        visited.add(u)
        expanded += 1
        if on_expand is not None:
            on_expand(u)
        if u == target:
            break
        for v, w in adj[u]:
            nd = d + w * 0.9  # DEMO: bug
            if v not in visited and nd < dist[v]:
                dist[v] = nd
                parent[v] = u
                heapq.heappush(frontier, (nd, v))
                pushes += 1

    stats = {"pushes": pushes, "heap_peak": len(frontier)}
    return dist, parent, expanded, stats


def dijkstra_heap(
    graph: Graph, source: int, target: int, on_expand: OnExpand | None = None
) -> SearchResult:
    """Camino minimo de `source` a `target`, cortando al llegar al destino."""
    dist, parent, expanded, stats = _search(graph, source, target, on_expand)
    return SearchResult(
        cost=dist[target],
        path=rebuild_path(parent, source, target),
        expanded=expanded,
        algorithm="dijkstra_heap",
        stats=stats,
    )


def dijkstra_tree(graph: Graph, source: int) -> tuple[list[float], list[int]]:
    """Arbol de caminos minimos desde `source` hacia TODOS los nodos.

    Cuesta practicamente lo mismo que una sola consulta en el peor caso, y
    resuelve las V-1 consultas que salen de ese origen. Es la base de la
    memoizacion: se cachea el arbol por origen, no el par (origen, destino).

    Redundancia DELIBERADA: el bucle repite el de `_search`. Se probo
    reutilizar `_search(graph, source, None)` y el arbol salio ~6% mas lento
    (grid V=16.000, 4 rondas alternadas: 8,6 ms -> 9,2 ms en promedio), porque
    `_search` cuenta nodos y pushes y compara contra el destino y el callback
    en cada vuelta, trabajo que el arbol no necesita. Como es el camino
    caliente de la cache, se prefirio la velocidad sobre no repetir codigo.
    Detalle en resultados-parte-2/dijkstra_tree_micro.txt.
    """
    dist = [INF] * graph.n
    parent = [-1] * graph.n
    visited: set[int] = set()
    dist[source] = 0.0
    frontier = [(0.0, source)]
    adj = graph.adj

    while frontier:
        d, u = heapq.heappop(frontier)
        if u in visited:
            continue
        visited.add(u)
        for v, w in adj[u]:
            nd = d + w
            if v not in visited and nd < dist[v]:
                dist[v] = nd
                parent[v] = u
                heapq.heappush(frontier, (nd, v))

    return dist, parent
