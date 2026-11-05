"""Control de memoria del CI (parte 3): pico de memoria con tracemalloc.

Por que tracemalloc y no RSS
    tracemalloc cuenta las asignaciones del interprete de Python. No incluye
    el ruido del sistema operativo ni del allocator, asi que con la misma
    version de Python el pico es practicamente determinista (varia < 1 %).
    Eso permite usar un limite fijo, cosa que con RSS no seria justo.

Escenarios (los mismos que defendimos en las partes 1 y 2)
    grafo_grid        construir un grafo de V=10.000 (listas de adyacencia).
    dijkstra_heap     una consulta: vectores dist/parent + heap.
    cache_32          la cache llena con 32 arboles: el trade-off memoria/tiempo.
    archivo_lotes     procesar 50.000 consultas por lotes: memoria ACOTADA.
    archivo_ingenuo   lo mismo leyendo todo a memoria: linea base de la parte 2.

Limites
    bench/memory_limits.json guarda, por escenario, el pico medido y el limite
    (= medido x MARGEN). Si un cambio supera el limite, el control falla.
    Un aumento justificado se acepta regenerando los limites con --update y
    explicando el motivo en el PR.

Uso:  python -m bench.check_memory            (verifica; exit 1 si se supera un limite)
      python -m bench.check_memory --update   (vuelve a medir y reescribe los limites)
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import tracemalloc
from collections.abc import Callable
from pathlib import Path

from src.algorithms.dijkstra_heap import dijkstra_heap
from src.archivos import generar_consultas, procesar_ingenuo, procesar_por_lotes
from src.cache import RouteCache
from src.graph import generate

ROOT = Path(__file__).resolve().parents[1]
LIMITS = ROOT / "bench" / "memory_limits.json"
REPORT = ROOT / "reports" / "memory.json"
MARGEN = 1.3  # 30 % sobre lo medido
MIB = 1024 * 1024
V = 10_000
N_CONSULTAS = 50_000


def pico_mib(fn: Callable[[], object]) -> float:
    """Ejecuta fn() y devuelve el pico de memoria asignada durante la llamada."""
    tracemalloc.start()
    try:
        fn()
        return tracemalloc.get_traced_memory()[1] / MIB
    finally:
        tracemalloc.stop()


def escenarios(tmp: Path) -> dict[str, Callable[[], object]]:
    """Cada escenario mide SOLO su operacion: lo que prepara queda afuera."""
    g = generate("grid", V)
    entrada = tmp / "consultas.csv"
    generar_consultas(entrada, g.n, N_CONSULTAS)

    def resolver(qs: list[tuple[int, int]]) -> list[tuple[float, int]]:
        # Respuesta trivial del mismo tamano que la real: los escenarios de
        # archivo miden la lectura/escritura, no el algoritmo (ya medido arriba).
        return [(float(s + t), 2) for s, t in qs]

    def llenar_cache() -> RouteCache:
        cache = RouteCache(capacity=32)
        for s in range(32):
            cache.route(g, s * 300, g.n - 1)
        return cache

    return {
        "grafo_grid": lambda: generate("grid", V),
        "dijkstra_heap": lambda: dijkstra_heap(g, 0, g.n - 1),
        "cache_32": llenar_cache,
        "archivo_lotes": lambda: procesar_por_lotes(entrada, tmp / "a.csv", resolver, 1_000),
        "archivo_ingenuo": lambda: procesar_ingenuo(entrada, tmp / "b.csv", resolver),
    }


def main(argv: list[str] | None = None) -> int:
    """Mide todos los escenarios y compara contra los limites guardados."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--update", action="store_true", help="reescribe memory_limits.json")
    args = p.parse_args(argv)

    with tempfile.TemporaryDirectory() as d:
        medidos = {nombre: round(pico_mib(fn), 2) for nombre, fn in escenarios(Path(d)).items()}

    if args.update:
        limites = {
            k: {"medido_mib": v, "limite_mib": round(v * MARGEN, 2)} for k, v in medidos.items()
        }
        LIMITS.write_text(json.dumps(limites, indent=2) + "\n")
        print(f"limites reescritos en {LIMITS.relative_to(ROOT)} (margen x{MARGEN})")

    limites = json.loads(LIMITS.read_text())
    filas, fallas = [], []
    print(f"{'escenario':18s} {'pico MiB':>10s} {'limite MiB':>11s} {'uso':>6s}  estado")
    for nombre, pico in medidos.items():
        limite = limites[nombre]["limite_mib"]
        ok = pico <= limite
        estado = "OK" if ok else "EXCEDE"
        print(f"{nombre:18s} {pico:10.2f} {limite:11.2f} {pico / limite:6.0%}  {estado}")
        filas.append({"escenario": nombre, "pico_mib": pico, "limite_mib": limite, "ok": ok})
        if not ok:
            fallas.append(nombre)

    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(filas, indent=2) + "\n")
    if fallas:
        print(f"\nRECHAZADO: se supero el limite de memoria en {', '.join(fallas)}")
        return 1
    print("\nmemoria dentro de los limites")
    return 0


if __name__ == "__main__":
    sys.exit(main())
