"""Descarga la red de calles real de Cordoba (Argentina) desde OpenStreetMap.

La convierte al formato de `src.graph.Graph`.

Se ejecuta UNA vez: el resultado queda en data/cordoba.json y de ahi en mas se
trabaja offline. Bajar el mapa en cada demo seria lento y poco cortes con el
servidor publico de Overpass.

Como se construye el grafo
    OSM guarda las calles como "ways": listas de puntos que dibujan la
    geometria. La mayoria de esos puntos son solo curvatura, no esquinas.
    Nos interesan unicamente las INTERSECCIONES, asi que:

      1. Se cuenta en cuantas calles aparece cada punto.
      2. Un punto es nodo del grafo si aparece en 2 o mas calles (es un cruce)
         o si es la punta de una calle.
      3. Entre dos cruces consecutivos de una misma calle se crea una arista,
         cuyo peso es la suma de las distancias de todos los puntos
         intermedios: la longitud real que se recorre por esa cuadra.

    Esto reduce el grafo en torno a un 70% sin perder informacion de ruteo.

Por que la heuristica de A* sigue siendo valida
    El peso de una arista es la longitud real recorrida, que por desigualdad
    triangular siempre es mayor o igual que la distancia en linea recta entre
    sus extremos. Por lo tanto la distancia en linea recta al destino nunca
    sobreestima el costo real: la heuristica es admisible sin necesidad de
    inventar factores, como si hacia falta en los grafos sinteticos.

Simplificaciones documentadas
    - Se ignoran los sentidos unicos: el grafo es no dirigido. Rutear
      respetando manos requeriria aristas dirigidas y duplicaria el modelo;
      para lo que se quiere mostrar (comportamiento de los algoritmos) no
      cambia nada conceptual.
    - Se ignoran semaforos, velocidades maximas y giros prohibidos. El costo
      es distancia, no tiempo.
"""

from __future__ import annotations

import json
import math
import sys
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "cordoba.json"
RAW = ROOT / "data" / "cordoba_raw.json"

# Centro de Cordoba y alrededores. Plaza San Martin esta en -31.4173, -64.1833.
BBOX = (-31.4550, -64.2200, -31.3800, -64.1450)  # sur, oeste, norte, este

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

TIPOS_CALLE = (
    "motorway|trunk|primary|secondary|tertiary|residential|unclassified"
    "|living_street|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link"
)

QUERY = f"""
[out:json][timeout:180];
way["highway"~"^({TIPOS_CALLE})$"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
(._;>;);
out body;
"""


def descargar() -> dict:
    """Baja las calles de Overpass, o reutiliza la descarga previa."""
    if RAW.exists():
        print(f"Usando descarga previa: {RAW.name}")
        return json.loads(RAW.read_text())

    datos = urllib.parse.urlencode({"data": QUERY}).encode()
    for url in ENDPOINTS:
        print(f"Consultando {url} ...")
        try:
            req = urllib.request.Request(
                url, data=datos, headers={"User-Agent": "pef-parcial/1.0 (uso academico)"}
            )
            with urllib.request.urlopen(req, timeout=240) as resp:
                crudo = json.loads(resp.read().decode())
            RAW.write_text(json.dumps(crudo))
            print(f"  descargado: {len(crudo.get('elements', []))} elementos")
            return crudo
        except OSError as e:  # URLError y TimeoutError son subclases de OSError
            print(f"  fallo: {e}")
    sys.exit("No se pudo descargar el mapa desde ningun servidor de Overpass.")


def haversine(lat1, lon1, lat2, lon2) -> float:
    """Distancia en metros sobre la superficie terrestre."""
    radio = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radio * math.asin(math.sqrt(a))


def _leer_elementos(crudo: dict):
    """Separa los puntos (lat, lon) y las calles (nombre, lista de puntos)."""
    puntos: dict[int, tuple[float, float]] = {}
    calles: list[tuple[str, list[int]]] = []
    for el in crudo["elements"]:
        if el["type"] == "node":
            puntos[el["id"]] = (el["lat"], el["lon"])
        elif el["type"] == "way" and len(el.get("nodes", [])) >= 2:
            calles.append((el.get("tags", {}).get("name", ""), el["nodes"]))
    print(f"  {len(puntos)} puntos, {len(calles)} calles crudas")
    return puntos, calles


def _detectar_cruces(puntos: dict, calles: list) -> set[int]:
    """Pasos 1-2: un punto es cruce si esta en mas de una calle, o es una punta."""
    apariciones: dict[int, int] = defaultdict(int)
    for _, nodos in calles:
        for nid in nodos:
            apariciones[nid] += 1

    cruces: set[int] = set()
    for _, nodos in calles:
        cruces.update((nodos[0], nodos[-1]))
        cruces.update(nid for nid in nodos[1:-1] if apariciones[nid] > 1)
    cruces = {n for n in cruces if n in puntos}
    reduccion = 100 * (1 - len(cruces) / len(puntos))
    print(f"  {len(cruces)} intersecciones (reduccion {reduccion:.0f}%)")
    return cruces


def _colapsar_tramos(puntos: dict, calles: list, cruces: set[int]) -> dict:
    """Paso 3: cada tramo entre dos cruces pasa a ser una arista con su largo real."""
    aristas: dict[tuple[int, int], tuple[float, str]] = {}
    for nombre, nodos_calle in calles:
        nodos = [n for n in nodos_calle if n in puntos]
        if len(nodos) < 2:
            continue
        inicio, largo = nodos[0], 0.0
        for prev, act in zip(nodos, nodos[1:], strict=False):
            largo += haversine(*puntos[prev], *puntos[act])
            if act not in cruces:
                continue
            clave = (min(inicio, act), max(inicio, act))
            es_mejor = clave not in aristas or largo < aristas[clave][0]
            if act != inicio and largo > 0 and es_mejor:
                aristas[clave] = (largo, nombre)
            inicio, largo = act, 0.0
    print(f"  {len(aristas)} tramos entre intersecciones")
    return aristas


def _componente_mayor(aristas: dict) -> set[int]:
    """Componente conexa mas grande (BFS).

    Descarta calles sueltas fuera del recorte, que si no arruinarian las
    consultas al no tener ruta posible.
    """
    vecinos: dict[int, list[int]] = defaultdict(list)
    for clave in aristas:
        a, b = clave  # cada clave es un par de intersecciones
        vecinos[a].append(b)
        vecinos[b].append(a)

    visto: set[int] = set()
    mayor: list[int] = []
    for origen in vecinos:
        if origen in visto:
            continue
        comp, cola = [], deque([origen])
        visto.add(origen)
        while cola:
            u = cola.popleft()
            comp.append(u)
            nuevos = [v for v in vecinos[u] if v not in visto]
            visto.update(nuevos)
            cola.extend(nuevos)
        if len(comp) > len(mayor):
            mayor = comp

    print(
        f"  componente conexa mayor: {len(mayor)} intersecciones "
        f"({100 * len(mayor) / len(vecinos):.1f}% del total)"
    )
    return set(mayor)


def construir(crudo: dict) -> dict:
    """Reduce los puntos de OSM a intersecciones y arma las aristas."""
    puntos, calles = _leer_elementos(crudo)
    cruces = _detectar_cruces(puntos, calles)
    aristas = _colapsar_tramos(puntos, calles, cruces)
    conservados = _componente_mayor(aristas)

    # Reindexar a 0..n-1 para poder usar listas en vez de diccionarios.
    orden = sorted(conservados)
    indice = {osm_id: i for i, osm_id in enumerate(orden)}

    lats = [puntos[n][0] for n in orden]
    lons = [puntos[n][1] for n in orden]
    salida_aristas = []
    nombres: dict[str, int] = defaultdict(int)
    for (a, b), (largo, nombre) in aristas.items():
        if a in indice and b in indice:
            salida_aristas.append([indice[a], indice[b], round(largo, 2)])
            if nombre:
                nombres[nombre] += 1

    return {
        "ciudad": "Cordoba, Argentina",
        "bbox": list(BBOX),
        "n": len(orden),
        "lat": [round(x, 6) for x in lats],
        "lon": [round(x, 6) for x in lons],
        "edges": salida_aristas,
        "calles_con_nombre": len(nombres),
    }


def main() -> None:
    """Descarga, construye y guarda data/cordoba.json."""
    crudo = descargar()
    print("Construyendo el grafo...")
    datos = construir(crudo)
    OUT.write_text(json.dumps(datos, separators=(",", ":")))
    mb = OUT.stat().st_size / 1e6
    print(f"\n{datos['n']} intersecciones, {len(datos['edges'])} tramos")
    print(f"{datos['calles_con_nombre']} calles con nombre")
    print(f"-> {OUT}  ({mb:.1f} MB)")


if __name__ == "__main__":
    main()
