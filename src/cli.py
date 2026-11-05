"""Interfaz de linea de comandos del planificador.

Es la parte "aplicacion" del trabajo: permite demostrar en vivo una consulta
de ruta, comparar algoritmos sobre el mismo par origen-destino, y simular un
cambio en el mapa para mostrar la invalidacion de la cache (punto 9 de la
presentacion: demostracion del codigo).

Uso:
    python3 -m src.cli ruta      --family grid --size 16000 --origen 0 --destino 15999
    python3 -m src.cli comparar  --family highway --size 16000
    python3 -m src.cli simular   --family grid --size 4000
    python3 -m src.cli lote      --family grid --size 16000 --n 200 --modo procesos
    python3 -m src.cli generar-consultas --size 4000 --n 1000000 --salida consultas.csv
    python3 -m src.cli archivo   --size 4000 --entrada consultas.csv --salida respuestas.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.algorithms import ALGORITHMS
from src.archivos import generar_consultas, procesar_archivo
from src.cache import RouteCache
from src.graph import FAMILIES, generate
from src.parallel import GraphSpec, make_queries, solve_processes, solve_sequential, solve_threads
from src.timing import timed_ms


def _extremos(args, g) -> tuple[int, int]:
    """Origen y destino pedidos, o por defecto el primer y el ultimo nodo."""
    src = args.origen if args.origen is not None else 0
    dst = args.destino if args.destino is not None else g.n - 1
    return src, dst


def cmd_ruta(args) -> None:
    """Resuelve una consulta y muestra costo, camino y nodos expandidos."""
    g = generate(args.family, args.size, seed=args.seed)
    src, dst = _extremos(args, g)
    algo = ALGORITHMS[args.algo]
    res, ms = timed_ms(lambda: algo(g, src, dst))
    print(f"\n{g}")
    print(f"Consulta {src} -> {dst} con {args.algo}")
    if not res.reachable:
        print("  sin ruta")
        return
    print(f"  costo           : {res.cost:.4f}")
    print(f"  saltos          : {len(res.path) - 1}")
    print(f"  nodos expandidos: {res.expanded}  ({100 * res.expanded / g.n:.1f}% del grafo)")
    print(f"  tiempo          : {ms:.2f} ms")
    head = " -> ".join(map(str, res.path[:8]))
    print(f"  camino          : {head}{' -> ...' if len(res.path) > 8 else ''}")


def cmd_comparar(args) -> None:
    """Corre todos los algoritmos aplicables sobre el mismo par origen-destino."""
    g = generate(args.family, args.size, seed=args.seed)
    src, dst = _extremos(args, g)
    print(f"\n{g}\nComparacion sobre {src} -> {dst}\n")
    print(f"{'algoritmo':16s} {'tiempo':>12s} {'expandidos':>12s} {'% grafo':>9s} {'costo':>12s}")
    print("-" * 66)
    names = ["heap", "astar"]
    if g.n * (g.n + g.num_edges) <= 4e7:
        names.insert(0, "naive")
    if not g.weighted:
        names.append("bfs")
    for name in names:
        res, ms = timed_ms(lambda a=ALGORITHMS[name]: a(g, src, dst))
        pct = 100 * res.expanded / g.n
        print(f"{name:16s} {ms:10.2f}ms {res.expanded:12d} {pct:8.1f}% {res.cost:12.4f}")
    print("\nLos costos deben coincidir: todos resuelven el camino minimo.")
    print("La diferencia esta en cuantos nodos hace falta expandir para hallarlo.")


def cmd_simular(args) -> None:
    """Demuestra la invalidacion de cache ante un cambio del mapa."""
    g = generate(args.family, args.size, seed=args.seed)
    cache = RouteCache(capacity=32)
    src, dst = 0, g.n - 1

    print(f"\n{g}\n")
    r1, ms1 = timed_ms(lambda: cache.route(g, src, dst))
    print(f"1. Primera consulta (miss) : costo {r1.cost:8.4f}  {ms1:8.3f} ms")
    r2, ms2 = timed_ms(lambda: cache.route(g, src, dst))
    print(
        f"2. Repetida       (hit)    : costo {r2.cost:8.4f}  {ms2:8.3f} ms  "
        f"-> {ms1 / ms2:.0f}x mas rapido"
    )

    u, v = r1.path[len(r1.path) // 2], r1.path[len(r1.path) // 2 + 1]
    w = min(x for nb, x in g.adj[u] if nb == v)
    g.update_weight(u, v, w * 1000)
    print(
        f"\n3. Se corta la calle {u}-{v} (peso {w:.2f} -> {w * 1000:.2f}); "
        f"version {g.version - 1} -> {g.version}"
    )

    r3, ms3 = timed_ms(lambda: cache.route(g, src, dst))
    print(f"4. Nueva consulta (miss)   : costo {r3.cost:8.4f}  {ms3:8.3f} ms")
    print(f"\nEstadisticas de cache: {cache.stats.as_dict()}")
    if r3.cost > r1.cost:
        print("La ruta se encarecio: la cache NO devolvio el resultado obsoleto.")
    else:
        print("Se encontro un desvio del mismo costo; la cache igual se invalido.")


def cmd_lote(args) -> None:
    """Resuelve un lote de consultas en el modo de ejecucion elegido."""
    spec = GraphSpec(args.family, args.size, args.seed)
    g = spec.build()
    queries = make_queries(g.n, args.n, hot_sources=args.calientes)
    print(f"\n{g}\nLote de {args.n} consultas, modo={args.modo}, algoritmo={args.algo}")
    if args.modo == "secuencial":
        _, ms = timed_ms(lambda: solve_sequential(g, queries, args.algo))
    elif args.modo == "hilos":
        _, ms = timed_ms(lambda: solve_threads(g, queries, args.algo))
    elif args.modo == "procesos":
        _, ms = timed_ms(lambda: solve_processes(spec, queries, args.algo))
    else:
        cache = RouteCache(capacity=64)
        _, ms = timed_ms(lambda: [cache.route(g, s, t) for s, t in queries])
        print(f"  cache: {cache.stats.as_dict()}")
    print(f"  tiempo total : {ms:.2f} ms")
    print(f"  por consulta : {ms / args.n:.3f} ms")


def cmd_generar_consultas(args) -> None:
    """Escribe un CSV grande de consultas para probar `archivo`."""
    g = generate(args.family, args.size, seed=args.seed)
    _, ms = timed_ms(lambda: generar_consultas(Path(args.salida), g.n, args.n))
    print(f"{args.n} consultas -> {args.salida}  ({ms:.0f} ms)")


def cmd_archivo(args) -> None:
    """Resuelve un CSV de consultas por lotes y escribe las respuestas."""
    spec = GraphSpec(args.family, args.size, args.seed)
    _, ms = timed_ms(
        lambda: procesar_archivo(
            Path(args.entrada), Path(args.salida), spec, args.algo, args.lote, args.paralelo
        )
    )
    modo = "procesos" if args.paralelo else "secuencial"
    print(f"{args.entrada} -> {args.salida}  lote={args.lote} modo={modo}  {ms:.0f} ms")


def main(argv=None) -> None:
    """Arma los subcomandos y ejecuta el elegido."""
    p = argparse.ArgumentParser(description="Planificador inteligente de rutas")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--family", default="grid", choices=sorted(FAMILIES))
        sp.add_argument("--size", type=int, default=4000)
        sp.add_argument("--seed", type=int, default=42)
        sp.add_argument("--origen", type=int, default=None)
        sp.add_argument("--destino", type=int, default=None)
        return sp

    sp = common(sub.add_parser("ruta", help="resolver una consulta"))
    sp.add_argument("--algo", default="astar", choices=sorted(ALGORITHMS))
    sp.set_defaults(func=cmd_ruta)

    common(sub.add_parser("comparar", help="comparar algoritmos")).set_defaults(func=cmd_comparar)
    common(sub.add_parser("simular", help="cambiar el mapa e invalidar cache")).set_defaults(
        func=cmd_simular
    )

    sp = common(sub.add_parser("lote", help="resolver muchas consultas"))
    sp.add_argument("--n", type=int, default=200)
    sp.add_argument(
        "--modo", default="procesos", choices=["secuencial", "hilos", "procesos", "cache"]
    )
    sp.add_argument("--algo", default="astar", choices=sorted(ALGORITHMS))
    sp.add_argument(
        "--calientes",
        type=int,
        default=5,
        help="cantidad de origenes que concentran el trafico (0 = uniforme)",
    )
    sp.set_defaults(func=cmd_lote)

    sp = common(sub.add_parser("generar-consultas", help="crear un CSV grande de consultas"))
    sp.add_argument("--n", type=int, default=1_000_000)
    sp.add_argument("--salida", default="consultas.csv")
    sp.set_defaults(func=cmd_generar_consultas)

    sp = common(sub.add_parser("archivo", help="resolver un CSV de consultas por lotes"))
    sp.add_argument("--entrada", required=True)
    sp.add_argument("--salida", default="respuestas.csv")
    sp.add_argument("--lote", type=int, default=10_000)
    sp.add_argument("--algo", default="astar", choices=sorted(ALGORITHMS))
    sp.add_argument("--secuencial", dest="paralelo", action="store_false")
    sp.set_defaults(func=cmd_archivo)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
