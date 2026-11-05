# Visualizador — Córdoba, Argentina

Interfaz gráfica para mostrar en vivo cómo se comportan los algoritmos sobre la red de
calles **real** de Córdoba, descargada de OpenStreetMap.

```bash
python3 data/fetch_cordoba.py    # una sola vez: baja el mapa (~25 s)
python3 -m viz.server            # y abrir http://localhost:8000
```

Servidor con **FastAPI** (`pip install -r requirements.txt`) y un `<canvas>`. La API se
documenta sola en http://localhost:8000/docs.

---

## Lo importante: el navegador no calcula nada

El frontend **dibuja**, nada más. Cada ruta que se ve animarse la resolvió el mismo
código Python que medimos en el benchmark (`src/algorithms/`), sobre el mismo `Graph`
que usan la caché y el paralelismo.

El orden en que se pintan las intersecciones es el **orden real de expansión** del
algoritmo, capturado con el callback `on_expand`. No hay una reimplementación en
JavaScript: si el visualizador muestra que A\* explora menos, es porque explora menos.

Eso importa para la defensa oral: la animación **es** evidencia, no una ilustración.

---

## El mapa

| | |
|---|---|
| Fuente | OpenStreetMap vía Overpass API |
| Recorte | centro de Córdoba, ~8 × 8 km alrededor de Plaza San Martín |
| Intersecciones | **8.288** |
| Cuadras | **13.296** |
| Calles con nombre | 1.448 |
| Peso de cada arista | longitud real recorrida, en metros |

OSM guarda las calles como listas de puntos, y la mayoría son sólo curvatura, no
esquinas. El conversor detecta las **intersecciones reales** (puntos que pertenecen a
más de una calle) y colapsa todo lo intermedio en una sola arista con el largo real
acumulado: reduce el grafo un 55% sin perder información de ruteo.

### La heurística salió gratis, pero hubo que demostrarlo

En los grafos sintéticos había que **forzar** que la distancia en línea recta nunca
sobreestimara el costo real. En el mapa real sale sola: el largo de una calle siempre es
mayor o igual que la línea recta entre sus extremos.

Pero el test de admisibilidad encontró **una violación de 2,7 cm** en una cuadra de 10 m.
La causa: los pesos se calcularon con haversine (sobre la esfera) y la heurística usa la
proyección plana, y las dos difieren ~0,4%.

En vez de poner un margen fijo "por las dudas", el margen **se calcula de los datos** al
cargar el mapa:

```
escala = 1 / max( distancia_recta(u,v) / peso(u,v) )   sobre las 13.296 cuadras
```

Eso garantiza `escala × recta(u,v) ≤ peso(u,v)` en toda arista, que es la condición de
**consistencia** — y una heurística consistente es siempre admisible. Da 0,9665 (margen
del 3,3%), y con eso las violaciones pasan a ser cero. La propiedad deja de ser una
esperanza y pasa a ser una consecuencia verificable de los datos.

---

## Qué se puede mostrar, y qué punto de la consigna cubre cada cosa

| Botón | Qué se ve | Punto de la consigna |
|---|---|---|
| **A\* / Dijkstra** | el frente de búsqueda avanzando sobre el mapa | elección de algoritmo (3) |
| **Duelo** | los dos a la vez, misma consulta, lado a lado | análisis de complejidad (2) |
| **Repetir usando la caché** | la misma ruta, ahora en microsegundos | memoización (5) |
| **Cortar una calle** | sube la versión → la caché se invalida sola | invalidación (5) |
| **Barrido de lotes** | secuencial vs hilos vs procesos en 3 tamaños | concurrencia (6) |
| **Baseline** | se niega a correr, y explica por qué | complejidad (2) |

### Números típicos de una corrida (origen 100 → destino 6000)

| | Dijkstra | A\* |
|---|---|---|
| Intersecciones exploradas | 2.920 (35,2% del mapa) | **290 (3,5%)** |
| Tiempo | 6,5 ms | **1,2 ms** |
| Distancia de la ruta | 3,22 km | 3,22 km *(idéntica)* |

**A\* explora 10 veces menos ciudad para llegar exactamente al mismo lugar.** Es la
diapositiva que se explica sola.

### Caché

| | |
|---|---|
| Primera consulta (fallo) | 19,66 ms |
| Repetida (acierto) | **0,045 ms** — 437× más rápido |
| Tras cortar una calle | vuelve a fallar, y la ruta se encarece |

Que el costo **cambie** después del corte es la demostración de que la caché no devolvió
el dato viejo.

### Paralelismo (el resultado incómodo, que conviene mostrar)

| Lote | Hilos | Procesos |
|---|---|---|
| 50 rutas | 0,95× | 0,52× |
| 200 rutas | 0,50× | **1,35×** |
| 800 rutas | 0,53× | **2,86×** |

Con lotes chicos los procesos salen **peor**: arrancarlos cuesta más de lo que ahorran.
El punto de cruce está en las 200 rutas. Los hilos, en cambio, pierden en todos los
tamaños — y eso no se arregla agrandando el lote, porque es el GIL.

En Córdoba el speedup máximo (2,86×) es menor que en los grafos sintéticos (11,87×)
porque A\* resuelve cada ruta real en ~2 ms: hay tan poco trabajo por tarea que el costo
de coordinar procesos pesa mucho más. **La granularidad de la tarea decide si paralelizar
sirve**, y este contraste lo muestra mejor que cualquier explicación.

---

## Guion sugerido para la demo (3 minutos)

1. **Duelo.** Clic en un extremo del mapa, clic en el otro. Se ve a Dijkstra pintando media
   ciudad mientras A\* va derecho. *"Misma ruta, 10 veces menos trabajo."*
2. **Caché.** Botón de caché: 19 ms → 0,045 ms. *"Ya lo habíamos calculado."*
3. **Cortar la calle.** Se corta una cuadra de la ruta. La caché se invalida sola y la ruta
   nueva es más cara. *"No devolvió el dato viejo."*
4. **Barrido de lotes.** *"Paralelizar no siempre conviene: acá hay que pasar las 200
   rutas para que empiece a rendir, y con hilos no rinde nunca."*

---

## Arquitectura

```
navegador  ── canvas, animación, clics
    │  fetch /api/…
viz/server.py  ── FastAPI + uvicorn, 6 endpoints (validados por tipo, /docs)
    │
src/osm.py     ── OSM → Graph (proyección + margen calculado)
src/algorithms/, src/cache.py, src/parallel.py   ← el mismo código del benchmark
```

| Endpoint | Qué hace |
|---|---|
| `/api/mapa` | intersecciones y cuadras para dibujar (0,4 MB, se envía una vez) |
| `/api/ruta` | resuelve y devuelve la traza de expansión |
| `/api/cortar` | corta una calle, sube la versión del mapa |
| `/api/reset` | restaura el mapa original |
| `/api/lote` | barrido secuencial / hilos / procesos |

### Una decisión de diseño: dónde *no* optimizar

`nodo_mas_cercano()` busca la intersección más próxima al clic con un barrido lineal
O(V) sobre las 8.288 esquinas. Se podría hacer en O(log V) con un k-d tree.

No se hizo, y a propósito: se ejecuta **una vez por clic del usuario**, no en el camino
caliente. Tarda menos de un milisegundo y nadie lo nota. Agregar un k-d tree sumaría una
estructura que no aporta nada al análisis del trabajo.

**Elegir dónde no optimizar también es parte de programar eficiente.**
