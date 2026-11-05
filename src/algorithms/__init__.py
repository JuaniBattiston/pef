"""Algoritmos de camino minimo y registro unico por nombre."""

from .astar import astar
from .base import Algorithm
from .bfs import bfs
from .dijkstra_heap import dijkstra_heap
from .dijkstra_naive import dijkstra_naive

# Unico lugar donde se asocia un nombre corto con su funcion. Lo usan la CLI,
# el paralelismo, el procesamiento de archivos y el visualizador.
ALGORITHMS: dict[str, Algorithm] = {
    "naive": dijkstra_naive,
    "heap": dijkstra_heap,
    "astar": astar,
    "bfs": bfs,
}
