"""Carga el mapa real de Cordoba (data/cordoba.json) como un `Graph` normal.

El punto de este modulo es que el mapa real entra por la MISMA puerta que los
grafos sinteticos: devuelve un `Graph` identico en estructura, asi que los
cuatro algoritmos, la cache y el paralelismo funcionan sin tocar una linea.
Lo unico que cambia es de donde salen los datos.

Proyeccion
    OSM da latitud y longitud (grados sobre una esfera). Los algoritmos
    trabajan con coordenadas planas en metros, asi que se proyecta con una
    equirectangular centrada en la ciudad:

        x = R * (lon - lon0) * cos(lat0)
        y = R * (lat - lat0)

    Sobre 8 km de extension el error de esta proyeccion es de centimetros,
    despreciable frente a cuadras de 100 metros. Se usa esta y no una
    proyeccion mas seria porque es exacta donde importa (distancias locales)
    y cuesta dos multiplicaciones.

Admisibilidad de la heuristica
    El peso de cada arista es la longitud real recorrida por la calle, que por
    desigualdad triangular es >= la distancia en linea recta entre sus
    extremos. Entonces la distancia en linea recta al destino nunca
    sobreestima el costo real: A* devuelve el optimo. En el mapa real la
    propiedad sale gratis; en los grafos sinteticos habia que forzarla con
    el factor >= 1.

    Hay una sutileza real, detectada por el test de admisibilidad: los pesos
    se calcularon con haversine (sobre la esfera) y la heuristica usa la
    proyeccion plana. Las dos discrepan en torno al 0,4%, y eso alcanzo para
    producir una violacion de 2,7 cm en una cuadra de 10 m. Un margen fijo
    "por las dudas" seria una apuesta, asi que en su lugar el margen se
    CALCULA de los datos: al cargar se recorre cada arista y se mide cuanto
    excede la distancia en linea recta al peso almacenado; el factor de escala
    es la inversa del peor caso.

        escala = 1 / max( euclidea(u,v) / w(u,v) )   sobre todas las aristas

    Con eso queda garantizado que escala * euclidea(u,v) <= w(u,v) para toda
    arista, que es la condicion de CONSISTENCIA. Y una heuristica consistente
    es siempre admisible, por desigualdad triangular. La propiedad deja de ser
    una esperanza y pasa a ser una consecuencia de los datos, verificada en
    O(E) una sola vez al cargar el mapa.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .graph import Graph

DATOS = Path(__file__).resolve().parents[1] / "data" / "cordoba.json"
RADIO_TIERRA = 6371000.0


def cargar_cordoba(ruta: Path | None = None) -> Graph:
    """Lee data/cordoba.json y lo devuelve como un `Graph` en metros."""
    ruta = ruta or DATOS
    if not ruta.exists():
        raise FileNotFoundError(
            f"falta {ruta}. Generalo una sola vez con: python3 data/fetch_cordoba.py"
        )
    d = json.loads(ruta.read_text())

    lats, lons = d["lat"], d["lon"]
    lat0 = sum(lats) / len(lats)
    lon0 = sum(lons) / len(lons)
    k = math.cos(math.radians(lat0))

    coords = [
        (
            RADIO_TIERRA * math.radians(lon - lon0) * k,
            RADIO_TIERRA * math.radians(lat - lat0),
        )
        for lat, lon in zip(lats, lons, strict=True)
    ]

    g = Graph(n=d["n"], coords=coords, family="cordoba")
    for u, v, w in d["edges"]:
        g.add_edge(u, v, w)

    # Margen calculado: garantiza consistencia y, por lo tanto, admisibilidad.
    peor = 1.0
    for u, v, w in g.edges:
        if w > 0:
            peor = max(peor, g.euclid(u, v) / w)
    g.heuristic_scale = 1.0 / peor

    g.latlon = list(zip(lats, lons, strict=True))  # para dibujar sobre un mapa real
    g.ciudad = d["ciudad"]
    return g


def nodo_mas_cercano(g: Graph, x: float, y: float) -> int:
    """Interseccion mas cercana a un punto del plano. O(V) por barrido lineal.

    Se hace asi a proposito: se ejecuta una vez por click del usuario, no en
    el camino caliente. Optimizarlo con un k-d tree agregaria una estructura
    que no aporta al analisis del trabajo. Elegir DONDE no optimizar tambien
    es parte de programar eficiente.
    """
    mejor, mejor_d = 0, float("inf")
    for i, (cx, cy) in enumerate(g.coords):
        d = (cx - x) ** 2 + (cy - y) ** 2
        if d < mejor_d:
            mejor, mejor_d = i, d
    return mejor
