"""Runner de mediciones.

Produce results/results.csv, que es la fuente de la tabla comparativa obligatoria
y de los graficos de escalabilidad.

Metodologia
  - Semilla fija en grafos y consultas: las corridas son comparables entre si
    y entre integrantes del grupo.
  - Una corrida de calentamiento antes de medir, para no contaminar con el
    costo de importar modulos y llenar caches del interprete.
  - `time.perf_counter`, que es el reloj monotono de mayor resolucion.
  - Memoria con `tracemalloc`: mide asignaciones del interprete, no RSS del
    proceso, asi que no incluye ruido del sistema operativo.
  - El baseline O(V^2+V*E) se saltea por encima de cierto tamano porque no
    termina en tiempo razonable. Eso tambien es un resultado a reportar.

IMPORTANTE: debe ejecutarse como script (python3 -m bench.run_bench) y no de
forma interactiva. Desde Python 3.14 el metodo de arranque de procesos en
Linux es forkserver, que necesita reimportar el modulo principal desde un
archivo real.
"""

from __future__ import annotations

import csv
import time
import tracemalloc
from pathlib import Path

from src.algorithms.astar import astar
from src.algorithms.bfs import bfs
from src.algorithms.dijkstra_heap import dijkstra_heap
from src.algorithms.dijkstra_naive import dijkstra_naive
from src.cache import RouteCache
from src.graph import generate
from src.parallel import (
    GraphSpec,
    make_queries,
    solve_processes,
    solve_sequential,
    solve_threads,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
# El baseline cuesta O(V^2 + V*E) POR CONSULTA. Se acota por trabajo estimado
# y no por cantidad de nodos, porque en la familia densa E crece con V^2 y
# 2000 nodos ya implican 4*10^8 operaciones por consulta. Que el baseline sea
# inejecutable a cierta escala es, en si mismo, un resultado a reportar.
BASELINE_MAX_WORK = 4e7
BASELINE_QUERIES = 5  # menos repeticiones; se compara por ms/consulta


def timed(fn, *args, repeat: int = 1, warmup: bool = True, **kwargs):
    """Devuelve (mejor tiempo en ms, pico de memoria en MB, resultado).

    TIEMPO Y MEMORIA SE MIDEN EN PASADAS SEPARADAS, a proposito.

    `tracemalloc` intercepta cada asignacion de memoria del interprete, y eso
    cuesta caro: medir las dos cosas a la vez inflaba los tiempos al doble
    (dijkstra_heap sobre V=16.000 daba 25 ms con el trazador activo y 12,6 ms
    sin el). Cronometrar con el medidor de memoria encendido es medir el
    medidor, no el algoritmo.

    Entonces: primera pasada limpia para el reloj, segunda pasada instrumentada
    para el pico de memoria. Cuesta el doble de trabajo y da numeros que
    significan lo que dicen.

    Se toma el minimo de las repeticiones y no el promedio: el ruido del
    planificador del sistema operativo solo puede agregar tiempo, nunca
    quitarlo, asi que el minimo es la estimacion mas cercana al costo real.
    """
    if warmup:
        fn(*args, **kwargs)  # calentamiento

    best = float("inf")
    out = None
    for _ in range(repeat):
        t0 = time.perf_counter()
        out = fn(*args, **kwargs)
        best = min(best, time.perf_counter() - t0)

    tracemalloc.start()
    fn(*args, **kwargs)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    return best * 1000, peak / 1e6, out


# ---------------------------------------------------------------------------
# Experimento 1: algoritmos por familia y por tamano
# ---------------------------------------------------------------------------


def _omitted_baseline_row(family: str, g, work: float) -> dict:
    """Fila del CSV para un baseline que no se corre por ser inejecutable."""
    return {
        "experiment": "algorithms",
        "family": family,
        "V": g.n,
        "E": g.num_edges,
        "variant": "dijkstra_naive",
        "queries": 0,
        "ms": "",
        "ms_per_query": "",
        "mb": "",
        "expanded_avg": "",
        "notes": f"omitido: trabajo estimado {work:.1e} operaciones",
    }


def _candidates(family: str, g, rows: list[dict]) -> list:
    """Algoritmos a medir en este grafo; registra el baseline si se omite."""
    candidates = [("dijkstra_heap", dijkstra_heap), ("astar", astar)]
    work = g.n * (g.n + g.num_edges)
    if work <= BASELINE_MAX_WORK:
        candidates.insert(0, ("dijkstra_naive", dijkstra_naive))
    else:
        rows.append(_omitted_baseline_row(family, g, work))
        print(f"  {family:11s} V={g.n:6d} dijkstra_naive  OMITIDO (trabajo {work:.1e})")
    if not g.weighted:
        candidates.append(("bfs", bfs))
    return candidates


def bench_algorithms(rows: list[dict]) -> None:
    plan = [
        ("grid", [1000, 4000, 16000, 64000]),
        ("highway", [1000, 4000, 16000]),
        ("dense", [500, 1000, 2000]),
        ("unweighted", [1000, 4000, 16000]),
    ]
    for family, sizes in plan:
        for size in sizes:
            g = generate(family, size)
            queries = make_queries(g.n, 20)

            for name, algo in _candidates(family, g, rows):
                qs = queries[:BASELINE_QUERIES] if name == "dijkstra_naive" else queries

                def run_batch(algo=algo, g=g, qs=qs):
                    return [algo(g, s, t) for s, t in qs]

                ms, mb, res = timed(run_batch, warmup=(name != "dijkstra_naive"))
                expanded = sum(r.expanded for r in res) / len(res)
                rows.append(
                    {
                        "experiment": "algorithms",
                        "family": family,
                        "V": g.n,
                        "E": g.num_edges,
                        "variant": name,
                        "queries": len(qs),
                        "ms": round(ms, 3),
                        "ms_per_query": round(ms / len(qs), 4),
                        "mb": round(mb, 3),
                        "expanded_avg": round(expanded, 1),
                        "notes": "",
                    }
                )
                print(
                    f"  {family:11s} V={g.n:6d} E={g.num_edges:8d} {name:15s} "
                    f"{ms / len(qs):9.2f} ms/consulta  {mb:7.2f} MB  exp={expanded:9.1f}"
                )


# ---------------------------------------------------------------------------
# Experimento 2: cache -- impacto y sensibilidad al patron de consultas
# ---------------------------------------------------------------------------


def bench_cache(rows: list[dict]) -> None:
    g = generate("grid", 16000)
    for label, hot in [("origenes_calientes", 5), ("origenes_uniformes", 0)]:
        queries = make_queries(g.n, 200, hot_sources=hot)

        ms_no, mb_no, _ = timed(solve_sequential, g, queries, "heap")

        def with_cache(g=g, queries=queries):
            c = RouteCache(capacity=64)
            out = [c.route(g, s, t) for s, t in queries]
            return c, out

        ms_yes, mb_yes, (cache, _) = timed(with_cache)
        st = cache.stats.as_dict()
        for variant, ms, mb, note in [
            ("sin_cache", ms_no, mb_no, label),
            ("con_cache", ms_yes, mb_yes, f"{label} hit_rate={st['hit_rate']}"),
        ]:
            rows.append(
                {
                    "experiment": "cache",
                    "family": "grid",
                    "V": g.n,
                    "E": g.num_edges,
                    "variant": variant,
                    "queries": len(queries),
                    "ms": round(ms, 3),
                    "ms_per_query": round(ms / len(queries), 4),
                    "mb": round(mb, 3),
                    "expanded_avg": "",
                    "notes": note,
                }
            )
            print(f"  cache {variant:10s} {label:20s} {ms:10.2f} ms  {mb:7.2f} MB  {note}")


# ---------------------------------------------------------------------------
# Experimento 3: concurrencia -- barrido de tamano de lote para hallar el cruce
# ---------------------------------------------------------------------------


def bench_parallel(rows: list[dict]) -> None:
    spec = GraphSpec("grid", 16000)
    g = spec.build()
    for batch in [10, 50, 200, 800]:
        queries = make_queries(g.n, batch)
        variants = [
            ("secuencial", lambda q=queries: solve_sequential(g, q, "heap")),
            ("hilos", lambda q=queries: solve_threads(g, q, "heap")),
            ("procesos", lambda q=queries: solve_processes(spec, q, "heap")),
        ]
        base_ms = None
        for name, fn in variants:
            ms, mb, _ = timed(fn)
            if name == "secuencial":
                base_ms = ms
            speedup = base_ms / ms if ms else 0
            rows.append(
                {
                    "experiment": "parallel",
                    "family": "grid",
                    "V": g.n,
                    "E": g.num_edges,
                    "variant": name,
                    "queries": batch,
                    "ms": round(ms, 3),
                    "ms_per_query": round(ms / batch, 4),
                    "mb": round(mb, 3),
                    "expanded_avg": "",
                    "notes": f"speedup={speedup:.2f}x",
                }
            )
            print(f"  paralelo lote={batch:4d} {name:11s} {ms:10.2f} ms  speedup={speedup:.2f}x")


# ---------------------------------------------------------------------------
# Experimento 4: las cinco filas de la tabla comparativa obligatoria
# ---------------------------------------------------------------------------


def bench_summary_table(rows: list[dict]) -> None:
    """Misma carga de trabajo para las cinco versiones, cambiando una cosa por vez.

    Es la tabla que pide el enunciado.

    Tamano elegido para que el baseline todavia termine: es la restriccion
    real de la comparacion, y se documenta como tal.
    """
    spec = GraphSpec("grid", 2500)
    g = spec.build()
    queries = make_queries(g.n, 50, hot_sources=5)

    def v_cache():
        c = RouteCache(capacity=64)
        return [c.route(g, s, t) for s, t in queries]

    versions = [
        ("1_baseline", "Implementacion inicial", lambda: solve_sequential(g, queries, "naive")),
        ("2_estructuras", "Adyacencia + heap + set", lambda: solve_sequential(g, queries, "heap")),
        (
            "3_algoritmo",
            "A* con heuristica euclidea",
            lambda: solve_sequential(g, queries, "astar"),
        ),
        ("4_paralelismo", "ProcessPoolExecutor", lambda: solve_processes(spec, queries, "astar")),
        ("5_final", "A* + cache LRU por origen", v_cache),
    ]
    base_ms = None
    for key, desc, fn in versions:
        ms, mb, _ = timed(fn, warmup=(key != "1_baseline"))
        if base_ms is None:
            base_ms = ms
        rows.append(
            {
                "experiment": "summary",
                "family": "grid",
                "V": g.n,
                "E": g.num_edges,
                "variant": key,
                "queries": len(queries),
                "ms": round(ms, 3),
                "ms_per_query": round(ms / len(queries), 4),
                "mb": round(mb, 3),
                "expanded_avg": "",
                "notes": f"{desc}; {base_ms / ms:.1f}x vs baseline",
            }
        )
        print(f"  tabla {key:15s} {ms:11.2f} ms  {mb:7.2f} MB  {base_ms / ms:7.1f}x")


def main() -> None:
    rows: list[dict] = []
    print("\n[1/4] Algoritmos por familia y tamano")
    bench_algorithms(rows)
    print("\n[2/4] Cache")
    bench_cache(rows)
    print("\n[3/4] Concurrencia")
    bench_parallel(rows)
    print("\n[4/4] Tabla comparativa")
    bench_summary_table(rows)

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "results.csv"
    fields = [
        "experiment",
        "family",
        "V",
        "E",
        "variant",
        "queries",
        "ms",
        "ms_per_query",
        "mb",
        "expanded_avg",
        "notes",
    ]
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n{len(rows)} mediciones -> {out}")


if __name__ == "__main__":
    main()
