"""CONCURRENCIA Y PARALELISMO (fila 4 de la tabla).

Que tareas se ejecutan simultaneamente
    Consultas de rutas distintas de un mismo lote. Un despachante que recibe
    200 pedidos de ruta puede resolverlos en cualquier orden.

Por que son independientes
    Cada consulta solo LEE el grafo; ninguna lo modifica. No hay estado
    compartido mutable, por lo tanto no hay condiciones de carrera ni hace
    falta sincronizacion. Los vectores dist/parent son locales a cada
    invocacion. Es paralelismo de datos puro (embarazosamente paralelo).

Que mecanismo usa el lenguaje, y por que este y no otro
    `concurrent.futures`, con las dos implementaciones para poder comparar:

      ThreadPoolExecutor  -- NO deberia acelerar. Dijkstra es CPU-bound puro
          y el GIL (Global Interpreter Lock) permite ejecutar bytecode de
          Python en un solo hilo a la vez. Se mide igual, porque mostrar que
          los hilos no ayudan es parte del analisis: el error tipico es
          asumir que "usar threads" es optimizar.

      ProcessPoolExecutor -- si acelera. Cada proceso tiene su propio
          interprete y su propio GIL, asi que los nucleos se usan de verdad.

Que problemas pueden aparecer
    1. Costo de serializacion. Enviar el grafo a cada worker en cada tarea lo
       serializa una y otra vez, y para V=10.000 eso puede costar mas que el
       calculo. Solucion aplicada: `initializer`, que construye el grafo UNA
       vez por proceso. Como la generacion es determinista a partir de
       (familia, tamano, semilla), se manda esa especificacion de tres campos
       en lugar del grafo entero.
       En Python 3.14 esto es obligatorio y no una mejora: el metodo de
       arranque por defecto en Linux ya no es fork, asi que los workers no
       heredan la memoria del padre.
    2. Overhead de arranque. Crear procesos cuesta decenas de milisegundos.
       Con lotes chicos ese costo domina y la version paralela sale PEOR que
       la secuencial. El benchmark barre tamanos de lote justamente para
       encontrar el punto de cruce.
    3. Granularidad. Una tarea por consulta genera mucho ida y vuelta entre
       procesos. Se usa `chunksize` para agrupar consultas por envio.
    4. Payload de vuelta. Se devuelve solo el costo y la longitud del camino,
       no el camino completo, para no serializar listas largas de nodos.

Lo que NO se paralelizo, y por que
    Un solo Dijkstra. Es inherentemente secuencial: cada extraccion del
    minimo depende de las relajaciones de la anterior. Paralelizarlo requiere
    algoritmos distintos (delta-stepping) y sincronizacion, con lo cual el
    costo de coordinacion se comeria la ganancia a esta escala.
"""

from __future__ import annotations

import os
import random
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass

from .algorithms import ALGORITHMS
from .algorithms.base import Algorithm
from .graph import Graph, generate

Query = tuple[int, int]
Answer = tuple[float, int]  # (costo, cantidad de nodos del camino)


@dataclass(frozen=True)
class GraphSpec:
    """Receta reproducible de un grafo. Barata de serializar: 3 campos."""

    family: str
    size: int
    seed: int = 42

    def build(self) -> Graph:
        """Construye el grafo descripto por esta receta."""
        # El mapa real entra por la misma puerta que los sinteticos: los
        # workers lo reconstruyen desde el JSON en vez de recibirlo serializado.
        if self.family == "cordoba":
            from .osm import cargar_cordoba

            return cargar_cordoba()
        return generate(self.family, self.size, seed=self.seed)


# --- estado por worker -----------------------------------------------------
# Un unico grafo por proceso, construido en el initializer. Es de solo
# lectura, asi que compartirlo entre tareas del mismo worker es seguro.

_WORKER_GRAPH: Graph | None = None
_WORKER_ALGO: Algorithm | None = None


def _init_worker(spec: GraphSpec, algo_name: str) -> None:
    global _WORKER_GRAPH, _WORKER_ALGO
    _WORKER_GRAPH = spec.build()
    _WORKER_ALGO = ALGORITHMS[algo_name]


def _answer(algo: Algorithm, graph: Graph, query: Query) -> Answer:
    """Resuelve una consulta y devuelve solo (costo, nodos del camino)."""
    res = algo(graph, query[0], query[1])
    return (res.cost, len(res.path))


def _solve_in_worker(query: Query) -> Answer:
    if _WORKER_ALGO is None or _WORKER_GRAPH is None:  # pragma: no cover
        raise RuntimeError("worker sin inicializar: usar process_pool()")
    return _answer(_WORKER_ALGO, _WORKER_GRAPH, query)


# --- estrategias -----------------------------------------------------------


def solve_sequential(graph: Graph, queries: list[Query], algo_name: str = "heap") -> list[Answer]:
    """Resuelve el lote en el hilo actual, una consulta tras otra."""
    algo = ALGORITHMS[algo_name]
    return [_answer(algo, graph, q) for q in queries]


def solve_threads(
    graph: Graph, queries: list[Query], algo_name: str = "heap", workers: int | None = None
) -> list[Answer]:
    """Hilos. Se espera que NO mejore.

    La carga es CPU-bound y el GIL serializa la ejecucion de bytecode.
    Se mide para documentarlo con numeros.
    """
    algo = ALGORITHMS[algo_name]
    workers = workers or (os.cpu_count() or 1)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda q: _answer(algo, graph, q), queries))


def process_pool(
    spec: GraphSpec, algo_name: str = "heap", workers: int | None = None
) -> ProcessPoolExecutor:
    """Crea un pool de procesos donde cada worker ya tiene el grafo construido.

    Se puede reutilizar para muchos lotes seguidos (ver `src/archivos.py`):
    el arranque de los procesos se paga una sola vez.
    """
    return ProcessPoolExecutor(
        max_workers=workers or os.cpu_count() or 1,
        initializer=_init_worker,
        initargs=(spec, algo_name),
    )


def solve_in_pool(pool: ProcessPoolExecutor, queries: list[Query]) -> list[Answer]:
    """Reparte un lote entre los workers, agrupando consultas por envio."""
    chunksize = max(1, len(queries) // ((os.cpu_count() or 1) * 4))
    return list(pool.map(_solve_in_worker, queries, chunksize=chunksize))


def solve_processes(
    spec: GraphSpec, queries: list[Query], algo_name: str = "heap", workers: int | None = None
) -> list[Answer]:
    """Procesos. Recibe la ESPECIFICACION del grafo, no el grafo.

    Cada worker lo reconstruye una sola vez en su initializer.
    """
    with process_pool(spec, algo_name, workers) as pool:
        return solve_in_pool(pool, queries)


def make_queries(n_nodes: int, count: int, seed: int = 11, hot_sources: int = 0) -> list[Query]:
    """Genera un lote de consultas.

    `hot_sources > 0` simula la carga real de un despachante: unos pocos
    origenes concentran el trafico. Es el escenario donde la cache rinde.
    Con hot_sources = 0 los origenes son uniformes: el peor caso para cachear.
    """
    # Datos de prueba reproducibles, sin uso criptografico (ver docs/seguridad.md).
    rng = random.Random(seed)  # nosec B311
    if hot_sources:
        sources = [rng.randrange(n_nodes) for _ in range(hot_sources)]
        return [(rng.choice(sources), rng.randrange(n_nodes)) for _ in range(count)]
    return [(rng.randrange(n_nodes), rng.randrange(n_nodes)) for _ in range(count)]
