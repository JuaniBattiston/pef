"""Genera results/tablas.md a partir de results/results.csv.

Las tablas del informe se derivan del CSV y no se transcriben a mano: si se
vuelve a correr el benchmark en otra maquina, el informe se actualiza solo y
no queda desincronizado de las mediciones.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "results" / "results.csv"
OUT = ROOT / "results" / "tablas.md"


def load() -> list[dict]:
    with CSV.open() as fh:
        return list(csv.DictReader(fh))


def fnum(v, nd=2):
    try:
        return f"{float(v):,.{nd}f}"
    except (TypeError, ValueError):
        return "--"


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def section_summary(rows):
    names = {
        "1_baseline": "Implementación inicial",
        "2_estructuras": "Estructura optimizada",
        "3_algoritmo": "Algoritmo optimizado",
        "4_paralelismo": "Concurrencia / paralelismo",
        "5_final": "Versión final",
    }
    sel = [r for r in rows if r["experiment"] == "summary"]
    if not sel:
        return ""
    base = float(sel[0]["ms"])
    body = []
    for r in sel:
        obs = r["notes"].split(";")[0]
        body.append(
            [
                names.get(r["variant"], r["variant"]),
                fnum(r["ms"]) + " ms",
                fnum(r["mb"]) + " MB",
                f"{base / float(r['ms']):.1f}x",
                obs,
            ]
        )
    head = (
        "## Comparación obligatoria\n\n"
        f"Grafo `grid` V={sel[0]['V']}, E={sel[0]['E']}; "
        f"{sel[0]['queries']} consultas con 5 orígenes calientes. "
        "Todas las versiones resuelven exactamente la misma carga.\n\n"
    )
    return head + table(["Versión", "Tiempo", "Memoria (pico)", "Aceleración", "Observación"], body)


def section_algorithms(rows):
    sel = [r for r in rows if r["experiment"] == "algorithms" and r["ms"]]
    by_family = defaultdict(list)
    for r in sel:
        by_family[r["family"]].append(r)
    out = ["## Algoritmos por familia de grafo y tamaño\n"]
    out.append(
        "`ms/consulta` normaliza porque el baseline se corre con menos "
        "repeticiones. `expandidos` es la cantidad media de nodos cerrados: "
        "es la métrica que explica la diferencia entre Dijkstra y A*, que "
        "comparten cota asintótica.\n"
    )
    for family, items in by_family.items():
        body = []
        for r in items:
            pct = ""
            if r["expanded_avg"] and r["V"]:
                pct = f"{100 * float(r['expanded_avg']) / float(r['V']):.1f}%"
            body.append(
                [
                    r["V"],
                    r["E"],
                    f"`{r['variant']}`",
                    fnum(r["ms_per_query"], 2),
                    fnum(r["mb"]),
                    fnum(r["expanded_avg"], 0),
                    pct,
                ]
            )
        out.append(f"\n### Familia `{family}`\n")
        out.append(
            table(["V", "E", "Algoritmo", "ms/consulta", "MB", "Expandidos", "% del grafo"], body)
        )
    omitted = [r for r in rows if r["experiment"] == "algorithms" and not r["ms"]]
    if omitted:
        out.append(
            "\n**Casos donde el baseline no es ejecutable:** "
            + ", ".join(f"{r['family']} V={r['V']} ({r['notes']})" for r in omitted)
            + ". Que un algoritmo deje de ser viable a cierta escala es un "
            "resultado del análisis, no una omisión."
        )
    return "\n".join(out)


def section_cache(rows):
    sel = [r for r in rows if r["experiment"] == "cache"]
    if not sel:
        return ""
    body = [
        [
            r["notes"].split()[0],
            f"`{r['variant']}`",
            fnum(r["ms"]) + " ms",
            fnum(r["mb"]) + " MB",
            next((p.split("=")[1] for p in r["notes"].split() if p.startswith("hit_rate")), "--"),
        ]
        for r in sel
    ]
    return "## Caché: impacto y sensibilidad al patrón de consultas\n\n" + table(
        ["Escenario", "Variante", "Tiempo", "Memoria", "Tasa de aciertos"], body
    )


def section_parallel(rows):
    sel = [r for r in rows if r["experiment"] == "parallel"]
    if not sel:
        return ""
    by_batch = defaultdict(dict)
    for r in sel:
        by_batch[int(r["queries"])][r["variant"]] = r
    body = []
    for batch in sorted(by_batch):
        v = by_batch[batch]
        row = [batch]
        for name in ("secuencial", "hilos", "procesos"):
            r = v.get(name)
            row.append(fnum(r["ms"]) + " ms" if r else "--")
        for name in ("hilos", "procesos"):
            r = v.get(name)
            row.append(r["notes"].split("=")[1] if r else "--")
        body.append(row)
    return "## Concurrencia: barrido de tamaño de lote\n\n" + table(
        ["Consultas", "Secuencial", "Hilos", "Procesos", "Speedup hilos", "Speedup procesos"], body
    )


def main() -> None:
    if not CSV.exists():
        sys.exit(f"falta {CSV}; correr antes: python3 -m bench.run_bench")
    rows = load()
    doc = "\n\n".join(
        x
        for x in [
            "# Resultados de las mediciones\n\nGenerado por `bench/make_report.py` "
            "a partir de `results/results.csv`. No editar a mano.",
            section_summary(rows),
            section_algorithms(rows),
            section_cache(rows),
            section_parallel(rows),
        ]
        if x
    )
    OUT.write_text(doc + "\n")
    print(f"{len(rows)} mediciones -> {OUT}")


if __name__ == "__main__":
    main()
