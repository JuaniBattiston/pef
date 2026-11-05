# API y contratos

El sistema expone tres interfaces: la **CLI**, la **API HTTP** del visualizador y la
**API de Python** del núcleo. Las tres usan el mismo código de `src/`.

## CLI

```bash
python -m src.cli <comando> [opciones]
```

Opciones comunes a todos los comandos:

| Opción | Valores | Default |
| --- | --- | --- |
| `--family` | `grid`, `highway`, `dense`, `unweighted` | `grid` |
| `--size` | cantidad aproximada de nodos | `4000` |
| `--seed` | entero (misma semilla ⇒ mismo grafo) | `42` |
| `--origen`, `--destino` | id de nodo | `0` y el último nodo |

| Comando | Opciones propias | Salida |
| --- | --- | --- |
| `ruta` | `--algo {naive,heap,astar,bfs}` (default `astar`) | costo, saltos, nodos expandidos, tiempo, inicio del camino |
| `comparar` | — | tabla de tiempo, expandidos y costo por algoritmo; el baseline se omite si `V·(V+E) > 4·10⁷` |
| `simular` | — | miss → hit → corte de calle → invalidación → nueva consulta |
| `lote` | `--n`, `--modo {secuencial,hilos,procesos,cache}`, `--algo`, `--calientes` | tiempo total y por consulta |
| `generar-consultas` | `--n`, `--salida` | CSV `origen,destino` |
| `archivo` | `--entrada`, `--salida`, `--lote`, `--secuencial` | CSV `origen,destino,costo,nodos` |

**Errores:** `argparse` rechaza opciones o valores inválidos con código de salida 2.
Un nodo fuera de rango produce `IndexError`.

```console
$ python -m src.cli ruta --family grid --size 4000 --algo astar
Graph(family='grid', V=3969, E=7812, weighted=True, version=0)
Consulta 0 -> 3968 con astar
  costo           : 120.2325
  saltos          : 124
  nodos expandidos: 3471  (87.5% del grafo)
  tiempo          : 5.88 ms
  camino          : 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 69 -> ...
```

## API HTTP (visualizador)

Servidor FastAPI en `viz/server.py`. La documentación interactiva generada por FastAPI
(OpenAPI) está en `http://localhost:8000/docs` con el servidor levantado.

| Método y ruta | Parámetros | Respuesta |
| --- | --- | --- |
| `GET /` | — | interfaz web |
| `GET /api/mapa` | — | `n`, `ciudad`, coordenadas y aristas del mapa de Córdoba |
| `GET /api/ruta` | `desde`, `hasta` (enteros ≥ 0), `algo` (`naive`, `heap`, `astar`, `bfs`), `cache` (bool) | costo, camino, orden de expansión, tiempo, estadísticas |
| `GET /api/cortar` | `u`, `v` (enteros ≥ 0) | multiplica por 1000 el peso de la cuadra; devuelve la nueva versión del mapa, calles cortadas y estadísticas de caché |
| `GET /api/reset` | — | mapa restaurado |
| `GET /api/lote` | `algo`, `tamanos` | tiempos por modo de ejecución y tamaño de lote |

**Contrato de errores.** Todo error sale como JSON `{"error": "<mensaje>"}`:

| Situación | Código |
| --- | --- |
| Parámetro de tipo o rango inválido (validación de FastAPI) | 422 |
| Nodo inexistente, cuadra inexistente, baseline pedido sobre el mapa completo (no escala) | 400 |

```console
$ curl 'localhost:8000/api/ruta?desde=0&hasta=99999&algo=astar'
{"error": "el mapa tiene 8288 nodos"}
```

## API de Python

Ejemplo de uso:

```python
from src.algorithms import ALGORITHMS
from src.cache import RouteCache
from src.graph import generate

g = generate("grid", 10_000, seed=42)
res = ALGORITHMS["astar"](g, 0, g.n - 1)
print(res.cost, len(res.path), res.expanded)

cache = RouteCache(capacity=64)
cache.route(g, 0, 500)        # miss: calcula el árbol desde 0
cache.route(g, 0, 9_000)      # hit: misma raíz, sin recalcular
g.update_weight(0, 1, 99.0)   # cambia el mapa -> version + 1
cache.route(g, 0, 500)        # miss: la caché se invalidó
```

Excepciones del núcleo:

| Función | Excepción | Cuándo |
| --- | --- | --- |
| `generate` | `ValueError` | familia desconocida |
| `RouteCache(capacity)` | `ValueError` | `capacity < 1` |
| `bfs` | `ValueError` | el grafo tiene pesos |
| cualquier algoritmo | `IndexError` | nodo fuera de `0..n-1` |
| `Graph.update_weight` | — (devuelve `False`) | la arista no existe; la versión no cambia |

La referencia siguiente se genera automáticamente desde los docstrings con
**mkdocstrings**: si un docstring cambia, la documentación cambia sola.

### Grafo

::: src.graph.Graph

::: src.graph.generate

### Algoritmos

::: src.algorithms.base.SearchResult

::: src.algorithms.base.Algorithm

::: src.algorithms.dijkstra_naive.dijkstra_naive

::: src.algorithms.dijkstra_heap.dijkstra_heap

::: src.algorithms.dijkstra_heap.dijkstra_tree

::: src.algorithms.astar.astar

::: src.algorithms.bfs.bfs

### Caché

::: src.cache.RouteCache

::: src.cache.CacheStats

### Lotes y paralelismo

::: src.parallel.GraphSpec

::: src.parallel.solve_sequential

::: src.parallel.solve_threads

::: src.parallel.solve_processes

::: src.parallel.make_queries

### Archivos

::: src.archivos.generar_consultas

::: src.archivos.leer_lotes

::: src.archivos.procesar_archivo
