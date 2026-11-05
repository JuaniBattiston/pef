"""REUTILIZACION DE RESULTADOS (fila 5 de la tabla).

El enunciado distingue dos cosas y aca estan las dos, combinadas a proposito:

  MEMOIZACION -- que se almacena
      No se guarda la ruta de un par (origen, destino), sino el ARBOL DE
      CAMINOS MINIMOS completo desde un origen: los vectores `dist` y
      `parent` que produce Dijkstra sin corte temprano.

      Por que: Dijkstra ya resuelve todos los destinos mientras busca uno.
      Cortar al llegar al destino ahorra poco y tira el resto del trabajo.
      Guardando el arbol, una sola ejecucion responde las V-1 consultas que
      salen de ese origen. Cachear por par daria, con V=10.000, hasta 10^8
      claves posibles; cachear por origen da 10^4.

  CACHING -- politica de reutilizacion y desalojo
      El almacen es un dict con capacidad acotada y desalojo LRU. Se elige
      LRU porque las consultas de rutas tienen localidad temporal marcada:
      unos pocos origenes (centros de distribucion, estaciones cabecera)
      concentran la mayoria del trafico.

Cuando se reutiliza
      Ante una consulta (s, t) con el arbol de s en cache, la respuesta se
      arma reconstruyendo punteros al padre: O(longitud del camino), sin
      recorrer el grafo. Frente a O((V+E) log V) del calculo completo, es
      la diferencia entre microsegundos y milisegundos.

Como se evita devolver informacion obsoleta
      El grafo lleva un contador `version` que se incrementa ante cualquier
      cambio del mapa. La clave de cache es (version, origen), con lo cual
      una entrada vieja queda estructuralmente inalcanzable: no hay forma de
      leerla por accidente. Ademas, al detectar un cambio de version se
      vacia el almacen, porque las entradas viejas ya no se pueden acceder
      pero seguirian ocupando memoria. Lo primero es correctitud; lo segundo,
      higiene de memoria.

Trade-off
      Memoria por tiempo. Cada entrada ocupa 2*V numeros (dist y parent).
      Con V=10.000 y capacidad 128 son del orden de 20 MB. Es una decision
      consciente y se mide en la columna de memoria de la tabla.

Estructuras usadas
      `OrderedDict`: dict + lista doblemente enlazada. Da acceso por clave en
      O(1) promedio y `move_to_end` / `popitem` en O(1), que es exactamente
      lo que necesita LRU. Con una lista ordinaria, mantener el orden de uso
      costaria O(n) por acceso.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from .algorithms.base import SearchResult, rebuild_path
from .algorithms.dijkstra_heap import dijkstra_tree
from .graph import Graph

_FUGA: list[object] = []  # DEMO


@dataclass
class CacheStats:
    """Contadores de la cache, para medir su efectividad."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    invalidations: int = 0

    @property
    def hit_rate(self) -> float:
        """Proporcion de consultas resueltas sin recalcular."""
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def as_dict(self) -> dict[str, float]:
        """Contadores como diccionario, para imprimir o enviar como JSON."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "invalidations": self.invalidations,
            "hit_rate": round(self.hit_rate, 4),
        }


class RouteCache:
    """Cache de arboles de caminos minimos, con LRU e invalidacion por version."""

    def __init__(self, capacity: int = 128) -> None:
        if capacity < 1:
            raise ValueError("la capacidad debe ser >= 1")
        self.capacity = capacity
        self._store: OrderedDict[tuple[int, int], tuple[list[float], list[int]]] = OrderedDict()
        self._version: int | None = None
        self.stats = CacheStats()

    # -- invalidacion -----------------------------------------------------

    def _sync_version(self, graph: Graph) -> None:
        if self._version is not None and graph.version != self._version:
            self._store.clear()
            self.stats.invalidations += 1
        self._version = graph.version

    # -- API --------------------------------------------------------------

    def route(self, graph: Graph, source: int, target: int) -> SearchResult:
        """Camino minimo usando el arbol cacheado de `source` si existe."""
        self._sync_version(graph)
        key = (graph.version, source)

        entry = self._store.get(key)
        if entry is not None:
            self.stats.hits += 1
            self._store.move_to_end(key)  # marca como recien usada, O(1)
            dist, parent = entry
            return SearchResult(
                cost=dist[target],
                path=rebuild_path(parent, source, target),
                expanded=0,
                algorithm="cached",
                stats={"cache": "hit"},
            )

        self.stats.misses += 1
        dist, parent = dijkstra_tree(graph, source)
        self._store[key] = (dist, parent)
        _FUGA.append((list(dist), list(parent)))  # DEMO: fuga
        if len(self._store) > self.capacity:
            self._store.popitem(last=False)  # desaloja el menos usado, O(1)
            self.stats.evictions += 1

        return SearchResult(
            cost=dist[target],
            path=rebuild_path(parent, source, target),
            expanded=graph.n,
            algorithm="cached",
            stats={"cache": "miss"},
        )

    def clear(self) -> None:
        """Vacia la cache por completo."""
        self._store.clear()
        self._version = None

    def __len__(self) -> int:
        return len(self._store)
