"""Procesamiento de archivos grandes de consultas (parte 2).

Escenario: el despachante recibe un CSV con muchas consultas
``origen,destino`` y tiene que devolver otro CSV con las respuestas.

Tres tecnicas, cada una en pocas lineas:

  BATCHING   `leer_lotes` es un generador: lee de a `tam_lote` filas y nunca
             tiene el archivo entero en memoria. La memoria queda constante
             aunque el archivo crezca.

  BUFFER     Los archivos se abren con un buffer de 1 MB y se escribe con
             `writerows` una vez por lote, no una vez por fila. Menos llamadas
             al sistema operativo.

  PARALELO   Cada lote se reparte entre procesos con un pool que se crea UNA
             sola vez para todo el archivo (`process_pool`).

`procesar_ingenuo` queda a proposito como linea base para comparar, igual que
`dijkstra_naive` en la parte 1.
"""

from __future__ import annotations

import csv
import random
from collections.abc import Callable, Iterator
from itertools import islice
from pathlib import Path

from .parallel import Answer, GraphSpec, Query, process_pool, solve_in_pool, solve_sequential

BUFFER = 1 << 20  # 1 MB
CABECERA_ENTRADA = ["origen", "destino"]
CABECERA_SALIDA = ["origen", "destino", "costo", "nodos_camino"]

# Recibe una lista de consultas y devuelve sus respuestas, en el mismo orden.
Resolver = Callable[[list[Query]], list[Answer]]


def generar_consultas(
    ruta: Path, n_nodos: int, cantidad: int, seed: int = 11, calientes: int = 5
) -> None:
    """Escribe un CSV de consultas sin armar la lista entera en memoria."""
    # Datos de prueba reproducibles, sin uso criptografico (ver docs/seguridad.md).
    rng = random.Random(seed)  # nosec B311
    fuentes = [rng.randrange(n_nodos) for _ in range(calientes)]

    def origen() -> int:
        return rng.choice(fuentes) if fuentes else rng.randrange(n_nodos)

    filas = ((origen(), rng.randrange(n_nodos)) for _ in range(cantidad))
    with open(ruta, "w", newline="", buffering=BUFFER) as f:
        escritor = csv.writer(f)
        escritor.writerow(CABECERA_ENTRADA)
        escritor.writerows(filas)  # consume el generador de a una fila


def leer_lotes(ruta: Path, tam_lote: int) -> Iterator[list[Query]]:
    """Devuelve las consultas de a `tam_lote` por vez (batching)."""
    with open(ruta, newline="", buffering=BUFFER) as f:
        lector = csv.reader(f)
        next(lector)  # cabecera
        while lote := list(islice(lector, tam_lote)):
            yield [(int(s), int(t)) for s, t in lote]


def procesar_ingenuo(entrada: Path, salida: Path, resolver: Resolver) -> None:
    """Linea base: todo a memoria y una escritura (con flush) por fila."""
    lineas = Path(entrada).read_text().splitlines()[1:]
    consultas = [(int(s), int(t)) for s, t in (linea.split(",") for linea in lineas)]
    respuestas = resolver(consultas)
    with open(salida, "w", buffering=1) as f:  # buffering=1: flush en cada linea
        f.write(",".join(CABECERA_SALIDA) + "\n")
        for (s, t), (costo, nodos) in zip(consultas, respuestas, strict=True):
            f.write(f"{s},{t},{costo},{nodos}\n")


def procesar_por_lotes(entrada: Path, salida: Path, resolver: Resolver, tam_lote: int) -> None:
    """Version optimizada: lee por lotes y escribe con buffer, un lote a la vez."""
    with open(salida, "w", newline="", buffering=BUFFER) as f:
        escritor = csv.writer(f)
        escritor.writerow(CABECERA_SALIDA)
        for lote in leer_lotes(entrada, tam_lote):
            respuestas = resolver(lote)
            escritor.writerows(
                (s, t, costo, nodos)
                for (s, t), (costo, nodos) in zip(lote, respuestas, strict=True)
            )


def procesar_archivo(
    entrada: Path,
    salida: Path,
    spec: GraphSpec,
    algo_name: str = "astar",
    tam_lote: int = 10_000,
    paralelo: bool = True,
) -> None:
    """Punto de entrada de la CLI: lotes + buffer, en secuencial o en procesos."""
    if paralelo:
        with process_pool(spec, algo_name) as pool:
            procesar_por_lotes(entrada, salida, lambda lote: solve_in_pool(pool, lote), tam_lote)
        return

    graph = spec.build()
    procesar_por_lotes(
        entrada, salida, lambda lote: solve_sequential(graph, lote, algo_name), tam_lote
    )
