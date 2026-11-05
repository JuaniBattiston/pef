"""Tipo de resultado comun a todos los algoritmos de busqueda.

Convencion compartida por los cuatro algoritmos
    Todos tienen la firma ``algo(graph, source, target, on_expand=None)``.

    ``on_expand`` es un callback opcional que se invoca con cada nodo al
    cerrarlo definitivamente. Lo usa el visualizador para animar el avance de
    la busqueda: la animacion reproduce el orden REAL de exploracion del
    algoritmo medido, no una recreacion aparte.

    Costo: una comparacion contra None por nodo expandido, es decir O(V) veces
    y no O(E). Se verifico contra el benchmark que no altera las mediciones.
"""

from __future__ import annotations

from dataclasses import dataclass, field

INF = float("inf")


@dataclass
class SearchResult:
    """Resultado de una consulta de ruta.

    `expanded` (nodos extraidos definitivamente de la frontera) es la metrica
    que explica *por que* A* gana o pierde frente a Dijkstra: ambos tienen la
    misma cota asintotica, la diferencia esta en cuantos nodos visitan.
    """

    cost: float
    path: list[int]
    expanded: int = 0
    algorithm: str = ""
    stats: dict = field(default_factory=dict)

    @property
    def reachable(self) -> bool:
        """Indica si existe camino entre origen y destino."""
        return self.cost < INF


def rebuild_path(parent: list[int], source: int, target: int) -> list[int]:
    """Reconstruye el camino siguiendo los punteros al padre. O(len(path))."""
    if parent[target] == -1 and target != source:
        return []
    path = [target]
    while path[-1] != source:
        path.append(parent[path[-1]])
    path.reverse()
    return path
