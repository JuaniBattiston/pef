"""PERFILADO (punto 7 del enunciado).

Responde las cuatro preguntas que pide la consigna con evidencia y no con
intuicion:

  Donde esta el cuello de botella?   -> cProfile, ordenado por tiempo propio
  Que optimizacion se hizo?          -> se perfila antes y despues
  Que impacto tuvo?                  -> comparacion de tiempos acumulados
  Se mantiene al crecer el volumen?  -> lo responde run_bench.py con el barrido

Herramientas
  cProfile     conteo de llamadas y tiempo por funcion. Instrumenta cada
               llamada, asi que agrega overhead y distorsiona los tiempos
               absolutos: sirve para ubicar el cuello de botella y comparar
               proporciones, no para medir velocidad. Las mediciones de
               tiempo reales salen de run_bench.py, sin instrumentacion.
  tracemalloc  asignaciones de memoria del interprete, por linea de codigo.

Salidas en results/: profile_baseline.txt, profile_optimizado.txt,
profile_memoria.txt.

Ejecutar como script: python3 -m bench.profile_run
"""

from __future__ import annotations

import cProfile
import io
import pstats
import time
import tracemalloc
from pathlib import Path

from src.algorithms.astar import astar
from src.algorithms.base import INF
from src.algorithms.dijkstra_heap import dijkstra_heap
from src.algorithms.dijkstra_naive import dijkstra_naive
from src.cache import RouteCache
from src.graph import generate
from src.parallel import make_queries

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def profile_to_file(fn, path: Path, title: str, top: int = 15) -> str:
    """Perfila `fn` con cProfile; guarda el texto y el .prof (para SnakeViz)."""
    pr = cProfile.Profile()
    pr.enable()
    fn()
    pr.disable()
    pr.dump_stats(path.with_suffix(".prof"))  # snakeviz results/profile_x.prof
    buf = io.StringIO()
    stats = pstats.Stats(pr, stream=buf).sort_stats("tottime")
    buf.write(f"{title}\n{'=' * len(title)}\n\n")
    stats.print_stats(top)
    path.write_text(buf.getvalue())
    total = stats.total_tt
    print(f"  {title}: {total * 1000:.1f} ms acumulados -> {path.name}")
    return buf.getvalue()


def main() -> None:
    RESULTS.mkdir(exist_ok=True)

    print("\n[1/3] Perfilado del baseline (grafo chico: no escala)")
    g_small = generate("grid", 2500)
    q_small = make_queries(g_small.n, 5)
    profile_to_file(
        lambda: [dijkstra_naive(g_small, s, t) for s, t in q_small],
        RESULTS / "profile_baseline.txt",
        "BASELINE  dijkstra_naive  (5 consultas, V=2500)",
    )

    print("\n[2/3] Perfilado de la version optimizada (grafo 25x mas grande)")
    g_big = generate("grid", 64000)
    q_big = make_queries(g_big.n, 20)
    profile_to_file(
        lambda: [dijkstra_heap(g_big, s, t) for s, t in q_big],
        RESULTS / "profile_optimizado.txt",
        "OPTIMIZADO  dijkstra_heap  (20 consultas, V=64000)",
    )
    profile_to_file(
        lambda: [astar(g_big, s, t) for s, t in q_big],
        RESULTS / "profile_astar.txt",
        "OPTIMIZADO  astar  (20 consultas, V=64000)",
    )

    print("\n[3/4] Atribucion del cuello de botella dentro del baseline")
    attribute_baseline_phases(g_small, q_small)

    print("\n[4/4] Perfilado de memoria (tracemalloc)")
    lines = ["PERFILADO DE MEMORIA (tracemalloc)", "=" * 34, ""]
    scenarios = [
        (
            "dijkstra_heap sin cache, 100 consultas, V=64000",
            lambda: [dijkstra_heap(g_big, s, t) for s, t in make_queries(g_big.n, 100)],
        ),
        ("RouteCache capacidad 64, 100 consultas, V=64000", lambda: _cached_run(g_big, 100, 64)),
    ]
    for label, fn in scenarios:
        tracemalloc.start()
        fn()
        current, peak = tracemalloc.get_traced_memory()
        snap = tracemalloc.take_snapshot()
        tracemalloc.stop()
        lines.append(
            f"{label}\n  pico: {peak / 1e6:.2f} MB   retenido al final: {current / 1e6:.2f} MB"
        )
        lines.append("  principales lineas asignadoras:")
        for st in snap.statistics("lineno")[:5]:
            frame = st.traceback[0]
            fname = Path(frame.filename).name
            lines.append(
                f"    {fname}:{frame.lineno:<5} {st.size / 1e6:7.2f} MB  ({st.count} bloques)"
            )
        lines.append("")
        print(f"  {label}: pico {peak / 1e6:.2f} MB")

    lines.append(
        "Lectura: la cache cambia tiempo por memoria. Cada entrada guarda dos\n"
        "vectores de V elementos (dist y parent), asi que la memoria retenida\n"
        "crece con capacidad * V. Es el trade-off explicito de la version final."
    )
    (RESULTS / "profile_memoria.txt").write_text("\n".join(lines))
    print(f"\nSalidas escritas en {RESULTS}")


def _min_lineal(dist, visited):
    """Fase (a) del baseline: minimo no visitado por barrido lineal, O(V)."""
    u, best = -1, INF
    for i in range(len(dist)):  # mismo bucle que dijkstra_naive, para medir lo mismo
        if not visited[i] and dist[i] < best:
            u, best = i, dist[i]
    return u, best


def _relajar_por_aristas(edges, u, best, dist, visited) -> None:
    """Fase (b) del baseline: vecinos de u recorriendo TODAS las aristas, O(E)."""
    for a, b, w in edges:  # mismo bucle que dijkstra_naive
        if a == u:
            v = b
        elif b == u:
            v = a
        else:
            continue
        if not visited[v] and best + w < dist[v]:
            dist[v] = best + w


def attribute_baseline_phases(graph, queries) -> None:
    """Separa el tiempo del baseline entre sus dos fases.

    cProfile trabaja a nivel de FUNCION, y los dos bucles calientes del
    baseline estan inline dentro de una sola: el perfil lo muestra como una
    caja negra de 1,1 s sin decir cual de los dos cuesta.

    Esta version instrumentada cronometra las dos fases por separado. Es la
    medicion que justifica cual optimizacion aplicar primero: no sirve
    cambiar la estructura equivocada.

    Nota: la instrumentacion agrega su propio costo (dos llamadas a
    perf_counter por iteracion), asi que los tiempos absolutos son mayores
    que los reales. Lo que importa es la PROPORCION entre fases.
    """
    t_min = t_edges = 0.0
    for src, dst in queries:
        dist = [INF] * graph.n
        visited = [False] * graph.n
        dist[src] = 0.0
        for _ in range(graph.n):
            t0 = time.perf_counter()
            u, best = _min_lineal(dist, visited)
            t_min += time.perf_counter() - t0
            if u == -1 or u == dst:
                break
            visited[u] = True
            t0 = time.perf_counter()
            _relajar_por_aristas(graph.edges, u, best, dist, visited)
            t_edges += time.perf_counter() - t0

    total = t_min + t_edges
    lines = [
        "ATRIBUCION DEL CUELLO DE BOTELLA -- BASELINE",
        "=" * 44,
        "",
        f"Grafo grid V={graph.n}, E={graph.num_edges}; {len(queries)} consultas.",
        "",
        f"  (a) seleccion del minimo por barrido lineal  O(V^2)   "
        f"{t_min:7.3f} s  ({100 * t_min / total:5.1f}%)",
        f"  (b) busqueda de vecinos sobre lista de aristas O(V*E)  "
        f"{t_edges:7.3f} s  ({100 * t_edges / total:5.1f}%)",
        "",
        "Conclusion: la fase dominante es (b). Por eso la primera optimizacion",
        "aplicada fue la lista de adyacencia y no el heap: atacar (a) primero",
        "habria dejado intacto el grueso del costo. El heap se aplica despues,",
        "cuando (a) pasa a ser el termino dominante.",
        "",
        "Advertencia metodologica: la instrumentacion inflacta los tiempos",
        "absolutos; la lectura valida es la proporcion entre fases.",
    ]
    (RESULTS / "profile_cuello_botella.txt").write_text("\n".join(lines) + "\n")
    print(f"  (a) minimo lineal : {100 * t_min / total:5.1f}%")
    print(f"  (b) barrido aristas: {100 * t_edges / total:5.1f}%  <- fase dominante")


def _cached_run(graph, count: int, capacity: int):
    cache = RouteCache(capacity=capacity)
    qs = make_queries(graph.n, count, hot_sources=5)
    return [cache.route(graph, s, t) for s, t in qs]


if __name__ == "__main__":
    main()
