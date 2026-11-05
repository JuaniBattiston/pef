"""Servidor del visualizador, hecho con FastAPI.

La idea de fondo: el navegador dibuja, pero NO calcula nada. Cada ruta que se
ve animarse la resolvio el mismo codigo Python que medimos en el benchmark
(`src/algorithms/`), sobre el mapa real de Cordoba cargado por `src/osm.py`.
El orden en que se pintan las intersecciones es el orden REAL de expansion del
algoritmo, capturado con el callback `on_expand`. No hay ninguna reimplementacion
en JavaScript: si el visualizador muestra que A* explora menos, es porque
explora menos.

Que aporta FastAPI frente al `http.server` de la parte 1:
    - ruteo con decoradores, en vez de un `if url.path == ...` por endpoint;
    - validacion por tipos: `desde: int` o `algo: Algoritmo` se chequean solos
      y un parametro invalido devuelve 422 sin escribir codigo de validacion;
    - documentacion interactiva generada sola en /docs (Swagger UI);
    - los endpoints `def` corren en un pool de hilos, igual que el
      `ThreadingHTTPServer` anterior (son CPU-bound, no ganan nada con async);
    - `TestClient` para testear la API sin levantar el servidor.

Endpoints (ver http://localhost:8000/docs)
    GET /                      la pagina
    GET /api/mapa              intersecciones y cuadras para dibujar
    GET /api/ruta              resuelve una consulta y devuelve la traza
    GET /api/cortar            corta una calle (sube la version, invalida cache)
    GET /api/reset             restaura el mapa original
    GET /api/lote              resuelve un lote secuencial / hilos / procesos

Uso:
    python3 -m viz.server            y abrir http://localhost:8000
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from enum import StrEnum
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from src.algorithms import ALGORITHMS
from src.cache import RouteCache
from src.osm import cargar_cordoba
from src.parallel import GraphSpec, make_queries, solve_processes, solve_sequential, solve_threads
from src.timing import timed_ms

Algoritmo = StrEnum("Algoritmo", {nombre: nombre for nombre in ALGORITHMS})

# Estado del servidor. Un solo grafo compartido, de solo lectura salvo cuando
# se corta una calle explicitamente.
MAPA = None
CACHE = RouteCache(capacity=32)
PESOS_ORIGINALES: dict[tuple[int, int], float] = {}


def iniciar_mapa() -> None:
    """Carga el mapa de Cordoba una sola vez al arrancar."""
    global MAPA
    MAPA, ms = timed_ms(cargar_cordoba)
    print(f"Mapa cargado: {MAPA.n} intersecciones, {MAPA.num_edges} cuadras ({ms:.0f} ms)")
    print(f"Margen de heuristica calculado de los datos: {100 * (1 - MAPA.heuristic_scale):.2f}%")


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    """Carga el mapa antes de atender el primer request."""
    if MAPA is None:
        iniciar_mapa()
    yield


app = FastAPI(
    title="Planificador de rutas — Córdoba",
    description="API del visualizador. Todos los cálculos los hace `src/`.",
    lifespan=ciclo_de_vida,
)


class ApiError(Exception):
    """Error esperado (consulta invalida); se devuelve como `{"error": ...}`."""

    def __init__(self, msg: str, codigo: int = 400):
        self.msg, self.codigo = msg, codigo


# El frontend lee `res.error`: todos los errores salen con esa forma.
@app.exception_handler(ApiError)
async def _error_api(_req: Request, e: ApiError) -> JSONResponse:
    return JSONResponse({"error": e.msg}, status_code=e.codigo)


@app.exception_handler(RequestValidationError)
async def _error_validacion(_req: Request, e: RequestValidationError) -> JSONResponse:
    detalle = "; ".join(f"{'.'.join(map(str, err['loc'][1:]))}: {err['msg']}" for err in e.errors())
    return JSONResponse({"error": f"parametro invalido: {detalle}"}, status_code=422)


@app.get("/", include_in_schema=False)
def pagina() -> FileResponse:
    """La pagina del visualizador."""
    return FileResponse(Path(__file__).parent / "index.html")


@app.get("/api/mapa")
def api_mapa() -> dict:
    """Manda las coordenadas proyectadas (metros) y las cuadras.

    Se envia una sola vez al abrir la pagina: son 0,4 MB y el navegador los guarda.
    """
    return {
        "ciudad": MAPA.ciudad,
        "n": MAPA.n,
        "x": [round(x, 1) for x, _ in MAPA.coords],
        "y": [round(y, 1) for _, y in MAPA.coords],
        "edges": [[u, v] for u, v, _ in MAPA.edges],
        "version": MAPA.version,
    }


@app.get("/api/ruta")
def api_ruta(
    desde: int = Query(ge=0, description="nodo de origen"),
    hasta: int = Query(ge=0, description="nodo de destino"),
    algo: Algoritmo = Algoritmo.astar,
    cache: bool = Query(False, description="usar la cache LRU (siempre con A*)"),
) -> dict:
    """Resuelve una consulta y devuelve la traza de expansion."""
    if max(desde, hasta) >= MAPA.n:
        raise ApiError(f"el mapa tiene {MAPA.n} nodos")
    if algo == "naive" and MAPA.n > 3000:
        raise ApiError(
            f"El baseline necesita del orden de {MAPA.n * (MAPA.n + MAPA.num_edges):.0e} "
            "operaciones sobre este mapa. Es justamente el punto: no escala."
        )

    if cache:
        res, ms = timed_ms(lambda: CACHE.route(MAPA, desde, hasta))
        return {
            "algoritmo": "cache",
            "orden": [],
            "camino": res.path,
            "costo": res.cost,
            "expandidos": res.expanded,
            "ms": round(ms, 3),
            "cache": res.stats.get("cache"),
            "stats_cache": CACHE.stats.as_dict(),
            "version": MAPA.version,
        }

    # La traza se captura con on_expand: es el orden real de exploracion.
    orden: list[int] = []
    res, ms = timed_ms(lambda: ALGORITHMS[algo](MAPA, desde, hasta, on_expand=orden.append))
    return {
        "algoritmo": algo.value,
        "orden": orden,
        "camino": res.path,
        "costo": res.cost if res.reachable else None,
        "expandidos": res.expanded,
        "porcentaje": round(100 * res.expanded / MAPA.n, 1),
        "ms": round(ms, 3),
        "pushes": res.stats.get("pushes", 0),
        "heap_peak": res.stats.get("heap_peak", 0),
        "path_nodes": len(res.path),
        "path_edges": max(0, len(res.path) - 1),
        "version": MAPA.version,
    }


@app.get("/api/cortar")
def api_cortar(u: int = Query(ge=0), v: int = Query(ge=0)) -> dict:
    """Corta una calle: sube la version del mapa e invalida la cache."""
    peso = next((w for nb, w in MAPA.adj[u] if nb == v), None) if u < MAPA.n else None
    if peso is None:
        raise ApiError(f"no hay cuadra entre {u} y {v}")
    PESOS_ORIGINALES.setdefault((min(u, v), max(u, v)), peso)
    MAPA.update_weight(u, v, peso * 1000)
    return {
        "ok": True,
        "version": MAPA.version,
        "cortadas": len(PESOS_ORIGINALES),
        "stats_cache": CACHE.stats.as_dict(),
    }


@app.get("/api/reset")
def api_reset() -> dict:
    """Restaura los pesos originales y vacia la cache."""
    for (u, v), peso in PESOS_ORIGINALES.items():
        MAPA.update_weight(u, v, peso)
    PESOS_ORIGINALES.clear()
    CACHE.clear()
    return {"ok": True, "version": MAPA.version}


@app.get("/api/lote")
def api_lote(
    algo: Algoritmo = Algoritmo.astar,
    tamanos: str = Query("50,200,800", pattern=r"^\d+(,\d+){0,3}$"),
) -> dict:
    """Barrido de tamanos de lote: secuencial vs hilos vs procesos.

    Se barre y no se mide un solo tamano a proposito. Con lotes chicos
    arrancar los procesos cuesta mas de lo que ahorra y el paralelismo
    SALE PEOR; recien a partir de cierto volumen se amortiza. Mostrar un
    unico numero ocultaria justamente el resultado interesante: existe un
    punto de cruce, y hay que saber de que lado esta el problema propio.

    Los hilos, en cambio, pierden en todos los tamanos: es el GIL, y no se
    arregla agrandando el lote.
    """
    algo, spec = algo.value, GraphSpec("cordoba", MAPA.n)  # str simple: viaja a los procesos
    filas = []
    for n in (int(x) for x in tamanos.split(",")):
        consultas = make_queries(MAPA.n, min(n, 2000))
        tiempos = {
            "secuencial": timed_ms(lambda q=consultas: solve_sequential(MAPA, q, algo))[1],
            "hilos": timed_ms(lambda q=consultas: solve_threads(MAPA, q, algo))[1],
            "procesos": timed_ms(lambda q=consultas: solve_processes(spec, q, algo))[1],
        }
        tiempos = {modo: round(ms, 1) for modo, ms in tiempos.items()}
        base = tiempos["secuencial"]
        filas.append(
            {
                "n": n,
                "tiempos": tiempos,
                "speedup": {m: round(base / t, 2) for m, t in tiempos.items()},
            }
        )

    cruce = next((f["n"] for f in filas if f["speedup"]["procesos"] > 1.0), None)
    return {"algoritmo": algo, "filas": filas, "cruce": cruce}


def main() -> None:
    """Levanta el servidor en el puerto indicado (8000 por defecto)."""
    import uvicorn

    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(
        f"\n  Visualizador en  http://localhost:{puerto}   (API: /docs)\n  (Ctrl-C para cortar)\n"
    )
    uvicorn.run(app, host="127.0.0.1", port=puerto, log_level="warning")


if __name__ == "__main__":
    main()
