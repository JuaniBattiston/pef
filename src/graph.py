"""Representacion de la red y generadores de grafos sinteticos.

Decisiones de diseno relevantes para el analisis de eficiencia:

1. Doble representacion. El grafo expone las aristas de dos formas:

   - `edges`: lista plana de tuplas (u, v, w). Es la representacion
     "ingenua" que usa la implementacion baseline.
   - `adj`: lista de listas de adyacencia, `adj[u] -> [(v, w), ...]`.

   Tener las dos permite medir el impacto de la estructura de datos
   sin cambiar el algoritmo.

2. `adj` es una lista indexada por entero y no un dict. Los ids de nodo
   son 0..n-1 densos, asi que la lista da acceso O(1) real (indexacion
   directa en memoria contigua) sin costo de hashing ni overhead por
   entrada. El dict se reserva para donde las claves son dispersas:
   la cache de rutas.

3. Coordenadas. Todo nodo tiene (x, y). Sin coordenadas no hay heuristica
   y por lo tanto no hay A*.

4. Admisibilidad. El peso de cada arista se genera como
   ``w = dist_euclidea(u, v) * factor``, con ``factor >= 1.0``.
   Asi la distancia euclidea nunca sobreestima el costo real de un camino
   y h(n) = dist(n, destino) es una heuristica admisible: A* devuelve el
   optimo. En la familia sin pesos (todas las aristas valen 1) esto no se
   cumple, por eso el grafo lleva `heuristic_scale`: el costo real en saltos
   entre u y destino es al menos dist(u, destino) / longitud_maxima_arista,
   de modo que escalando la heuristica se recupera la admisibilidad.

5. `version`. Contador que se incrementa ante cualquier modificacion del
   mapa. Es la base de la invalidacion de la cache: una entrada calculada
   con la version k deja de ser alcanzable apenas el grafo pasa a k+1.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Graph:
    """Red no dirigida con coordenadas, lista de adyacencia y version."""

    n: int
    coords: list[tuple[float, float]]
    adj: list[list[tuple[int, float]]] = field(default_factory=list)
    edges: list[tuple[int, int, float]] = field(default_factory=list)
    version: int = 0
    weighted: bool = True
    heuristic_scale: float = 1.0
    family: str = "custom"
    # Solo para mapas reales (src/osm.py): coordenadas geograficas y nombre.
    latlon: list[tuple[float, float]] | None = None
    ciudad: str | None = None

    def __post_init__(self) -> None:
        if not self.adj:
            self.adj = [[] for _ in range(self.n)]

    # -- construccion -----------------------------------------------------

    def add_edge(self, u: int, v: int, w: float) -> None:
        """Agrega una arista no dirigida. O(1) amortizado."""
        self.adj[u].append((v, w))
        self.adj[v].append((u, w))
        self.edges.append((u, v, w))

    # -- modificacion del mapa (invalida cache) ---------------------------

    def update_weight(self, u: int, v: int, new_w: float) -> bool:
        """Cambia el peso de una arista existente (calle cortada, congestion).

        Incrementa `version`, que es lo que invalida la cache.

        O(grado(u) + grado(v) + E) por el barrido de `edges`. Es una
        operacion poco frecuente frente a las consultas, asi que no
        justifica mantener un indice adicional.
        """
        if not _set_weight(self.adj[u], v, new_w):
            return False
        _set_weight(self.adj[v], u, new_w)
        for i, (a, b, _) in enumerate(self.edges):
            if (a, b) in ((u, v), (v, u)):
                self.edges[i] = (a, b, new_w)
                break
        self.version += 1
        return True

    # -- consultas --------------------------------------------------------

    @property
    def num_edges(self) -> int:
        """Cantidad de aristas."""
        return len(self.edges)

    def euclid(self, u: int, v: int) -> float:
        """Distancia en linea recta entre dos nodos."""
        (x1, y1), (x2, y2) = self.coords[u], self.coords[v]
        return math.hypot(x1 - x2, y1 - y2)

    def heuristic(self, u: int, goal: int) -> float:
        """Heuristica admisible para A*."""
        return self.euclid(u, goal) * self.heuristic_scale

    def __repr__(self) -> str:
        return (
            f"Graph(family={self.family!r}, V={self.n}, E={self.num_edges}, "
            f"weighted={self.weighted}, version={self.version})"
        )


def _set_weight(neighbors: list[tuple[int, float]], node: int, new_w: float) -> bool:
    """Cambia el peso hacia `node` en una lista de vecinos. True si lo encontro."""
    for i, (nb, _) in enumerate(neighbors):
        if nb == node:
            neighbors[i] = (node, new_w)
            return True
    return False


# ---------------------------------------------------------------------------
# Generadores
# ---------------------------------------------------------------------------
#
# Cada familia esta elegida para que gane un algoritmo distinto. Ese es el
# punto: el desafio del enunciado pide decidir que algoritmo conviene segun
# el tamano y las caracteristicas del grafo, y eso solo se puede responder
# midiendo sobre topologias diferentes.


def _grid_coords(side: int, rng: random.Random, jitter: float = 0.25) -> list[tuple[float, float]]:
    """Grilla side x side con ruido, para que no sea perfectamente regular."""
    return [
        (x + rng.uniform(-jitter, jitter), y + rng.uniform(-jitter, jitter))
        for y in range(side)
        for x in range(side)
    ]


def _side_for(n_target: int) -> int:
    return max(2, int(round(math.sqrt(n_target))))


def grid(n_target: int, seed: int = 42, factor_range: tuple[float, float] = (1.0, 1.2)) -> Graph:
    """Malla urbana. Planar, grado <= 4, E ~ 2V.

    Heuristica euclidea muy informativa -> es donde A* deberia brillar.
    """
    # Datos de prueba reproducibles, sin uso criptografico (ver docs/seguridad.md).
    rng = random.Random(seed)  # nosec B311
    side = _side_for(n_target)
    n = side * side
    g = Graph(n=n, coords=_grid_coords(side, rng), family="grid")
    lo, hi = factor_range
    for y in range(side):
        for x in range(side):
            u = y * side + x
            if x + 1 < side:
                v = u + 1
                g.add_edge(u, v, g.euclid(u, v) * rng.uniform(lo, hi))
            if y + 1 < side:
                v = u + side
                g.add_edge(u, v, g.euclid(u, v) * rng.uniform(lo, hi))
    return g


def highway(n_target: int, seed: int = 42, shortcut_ratio: float = 0.05) -> Graph:
    """Malla + aristas de largo alcance y pesos de alta varianza (factor hasta 4).

    Los pesos dispersos hacen que la distancia euclidea siga siendo admisible
    (factor >= 1) pero mucho menos informativa: subestima fuerte. A* deberia
    degradarse hacia Dijkstra. Es el caso interesante para la presentacion.
    """
    # Datos de prueba reproducibles, sin uso criptografico (ver docs/seguridad.md).
    rng = random.Random(seed)  # nosec B311
    g = grid(n_target, seed=seed, factor_range=(1.0, 4.0))
    g.family = "highway"
    extra = int(g.n * shortcut_ratio)
    for _ in range(extra):
        u = rng.randrange(g.n)
        v = rng.randrange(g.n)
        if u != v:
            g.add_edge(u, v, g.euclid(u, v) * rng.uniform(1.0, 1.3))
    return g


def dense(n_target: int, seed: int = 42, avg_degree: float | None = None) -> Graph:
    """Aleatorio denso sin estructura geometrica util.

    Con E -> V^2 el termino O(E log V) del heap supera a O(V^2) del barrido
    lineal: es el escenario donde se espera que el baseline "ingenuo" gane.
    La heuristica euclidea existe pero no informa nada, asi que A* ~ Dijkstra.

    Ojo con el tamano: E crece con V^2, no lo uses por encima de ~5k nodos.
    """
    # Datos de prueba reproducibles, sin uso criptografico (ver docs/seguridad.md).
    rng = random.Random(seed)  # nosec B311
    n = n_target
    coords = [(rng.uniform(0, math.sqrt(n)), rng.uniform(0, math.sqrt(n))) for _ in range(n)]
    g = Graph(n=n, coords=coords, family="dense")
    if avg_degree is None:
        avg_degree = n / 10.0

    # Camino hamiltoniano aleatorio: garantiza conectividad por construccion,
    # asi ningun benchmark se arruina por un par (origen, destino) sin ruta.
    order = list(range(n))
    rng.shuffle(order)
    for a, b in zip(order, order[1:], strict=False):
        g.add_edge(a, b, g.euclid(a, b) * rng.uniform(1.0, 2.0))

    target_edges = int(n * avg_degree / 2)
    seen = {(min(a, b), max(a, b)) for a, b, _ in g.edges}
    while len(g.edges) < target_edges:
        u, v = rng.randrange(n), rng.randrange(n)
        if u == v:
            continue
        key = (min(u, v), max(u, v))
        if key in seen:
            continue
        seen.add(key)
        g.add_edge(u, v, g.euclid(u, v) * rng.uniform(1.0, 2.0))
    return g


def unweighted(n_target: int, seed: int = 42) -> Graph:
    """Topologia de malla con todas las aristas de peso 1.

    Aca BFS es correcto y corre en O(V+E) sin heap ni log V: es la
    justificacion de por que BFS entra en la comparacion.

    La heuristica euclidea cruda dejaria de ser admisible (una arista de
    longitud 1.3 cuesta 1), asi que se escala por 1/longitud_maxima.
    """
    g = grid(n_target, seed=seed)
    g.family = "unweighted"
    g.weighted = False
    max_len = 0.0
    for i, (u, v, _) in enumerate(g.edges):
        d = g.euclid(u, v)
        max_len = max(max_len, d)
        g.edges[i] = (u, v, 1.0)
    for u in range(g.n):
        g.adj[u] = [(v, 1.0) for v, _ in g.adj[u]]
    g.heuristic_scale = 1.0 / max_len
    return g


FAMILIES: dict[str, Callable[..., Graph]] = {
    "grid": grid,
    "highway": highway,
    "dense": dense,
    "unweighted": unweighted,
}


def generate(family: str, n_target: int, seed: int = 42) -> Graph:
    """Punto de entrada unico. Semilla fija => mediciones reproducibles."""
    if family not in FAMILIES:
        raise ValueError(f"familia desconocida: {family!r}; opciones: {sorted(FAMILIES)}")
    return FAMILIES[family](n_target, seed=seed)
