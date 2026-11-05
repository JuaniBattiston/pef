"""Mediciones de archivos grandes: batching, buffer y paralelo (parte 2).

Tres experimentos, cada uno aisla una variable:

  1. I/O puro. El "calculo" es trivial, asi que solo se mide leer y escribir.
     Compara la version ingenua (todo a memoria, flush por linea) contra la
     version por lotes con buffer, para archivos de 100k, 500k y 1M filas.
  2. I/O + calculo real de rutas (A*). Muestra donde esta el cuello de botella
     cuando el trabajo por fila es caro, y cuanto aporta el paralelismo.
  3. Tamano de lote. Barrido para ver el trade-off overhead vs memoria.

Uso:  python3 -m bench.bench_archivos
Salida: resultados-parte-2/archivos/{archivos.csv, tablas.md}
"""

from __future__ import annotations

import csv
import tempfile
import time
import tracemalloc
from pathlib import Path

from src.archivos import generar_consultas, procesar_ingenuo, procesar_por_lotes
from src.parallel import GraphSpec, process_pool, solve_in_pool, solve_sequential

OUT = Path(__file__).resolve().parents[1] / "resultados-parte-2" / "archivos"
SPEC = GraphSpec("grid", 2000)
LOTE = 10_000
SALIDA = "respuestas.csv"  # archivo temporal de salida


def medir(fn, repeat: int = 1, memoria: bool = True) -> tuple[float, float]:
    """Devuelve (mejor tiempo en ms, pico de memoria en MB) en pasadas separadas."""
    best = float("inf")
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t0)
    peak = 0.0
    if memoria:
        tracemalloc.start()
        fn()
        peak = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()
    return best * 1000, peak


def trivial(lote):
    """Resolver que no calcula nada: deja solo el costo de I/O."""
    return [(0.0, 0)] * len(lote)


def exp_io_puro(tmp: Path, rows: list[dict]) -> None:
    for filas in [100_000, 500_000, 1_000_000]:
        entrada = tmp / f"q{filas}.csv"
        generar_consultas(entrada, SPEC.build().n, filas)
        variantes = {
            "ingenuo": lambda e=entrada: procesar_ingenuo(e, tmp / SALIDA, trivial),
            "lotes+buffer": lambda e=entrada: procesar_por_lotes(e, tmp / SALIDA, trivial, LOTE),
        }
        for nombre, fn in variantes.items():
            ms, mb = medir(fn, repeat=3)
            rows.append({"exp": "io_puro", "variante": nombre, "filas": filas, "ms": ms, "mb": mb})
            print(f"  io_puro  {filas:>9} filas  {nombre:14s} {ms:9.1f} ms  {mb:7.1f} MB")


def exp_con_calculo(tmp: Path, rows: list[dict]) -> None:
    filas = 50_000
    entrada = tmp / "q_calc.csv"
    graph = SPEC.build()
    generar_consultas(entrada, graph.n, filas)

    def secuencial(lote):
        return solve_sequential(graph, lote, "astar")

    with process_pool(SPEC, "astar") as pool:
        solve_in_pool(pool, [(0, 1)] * 100)  # calentamiento: arranca los workers
        variantes = {
            "ingenuo": lambda: procesar_ingenuo(entrada, tmp / SALIDA, secuencial),
            "lotes+buffer": lambda: procesar_por_lotes(entrada, tmp / SALIDA, secuencial, LOTE),
            "lotes+buffer+procesos": lambda: procesar_por_lotes(
                entrada, tmp / SALIDA, lambda lote: solve_in_pool(pool, lote), LOTE
            ),
        }
        for nombre, fn in variantes.items():
            ms, mb = medir(fn, memoria=False)
            rows.append(
                {"exp": "con_calculo", "variante": nombre, "filas": filas, "ms": ms, "mb": mb}
            )
            print(f"  calculo  {filas:>9} filas  {nombre:22s} {ms:9.1f} ms")


def exp_tamano_lote(tmp: Path, rows: list[dict]) -> None:
    filas = 50_000
    entrada = tmp / "q_lote.csv"
    generar_consultas(entrada, SPEC.build().n, filas)
    with process_pool(SPEC, "astar") as pool:
        solve_in_pool(pool, [(0, 1)] * 100)
        for lote in [10, 100, 1_000, 10_000, 50_000]:
            ms, _ = medir(
                lambda n=lote: procesar_por_lotes(
                    entrada, tmp / SALIDA, lambda q: solve_in_pool(pool, q), n
                ),
                memoria=False,
            )
            # La memoria se mide con el resolver trivial: con procesos, tracemalloc
            # solo ve al proceso principal.
            _, mb = medir(
                lambda n=lote: procesar_por_lotes(entrada, tmp / SALIDA, trivial, n),
            )
            rows.append(
                {
                    "exp": "tamano_lote",
                    "variante": f"lote={lote}",
                    "filas": filas,
                    "ms": ms,
                    "mb": mb,
                }
            )
            print(f"  lote {lote:>7}  {ms:9.1f} ms  {mb:7.2f} MB")


def escribir_tablas(rows: list[dict]) -> None:
    lineas = ["# Archivos grandes: batching, buffer y paralelo", ""]
    titulos = {
        "io_puro": "## 1. Solo I/O (calculo trivial)",
        "con_calculo": f"## 2. I/O + calculo real (A*, {SPEC.family} V~{SPEC.size})",
        "tamano_lote": "## 3. Tamano de lote (procesos)",
    }
    for exp, titulo in titulos.items():
        lineas += [titulo, "", "| Variante | Filas | Tiempo (ms) | Memoria pico (MB) |"]
        lineas += ["|---|---|---|---|"]
        for r in rows:
            if r["exp"] == exp:
                mb = f"{r['mb']:.2f}" if r["mb"] else "-"
                lineas.append(f"| {r['variante']} | {r['filas']:,} | {r['ms']:.1f} | {mb} |")
        lineas.append("")
    (OUT / "tablas.md").write_text("\n".join(lineas))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        print("[1/3] I/O puro")
        exp_io_puro(tmp, rows)
        print("[2/3] I/O + calculo")
        exp_con_calculo(tmp, rows)
        print("[3/3] Tamano de lote")
        exp_tamano_lote(tmp, rows)
    with open(OUT / "archivos.csv", "w", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=["exp", "variante", "filas", "ms", "mb"])
        escritor.writeheader()
        escritor.writerows(rows)
    escribir_tablas(rows)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
