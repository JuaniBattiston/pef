# Pruebas

## Estrategia

| Nivel | Qué se verifica | Cómo |
| --- | --- | --- |
| Correctitud de algoritmos | el costo es el mínimo y el camino es válido | **oráculo Bellman-Ford** (`tests/reference.py`), independiente del código probado |
| Propiedades | heurística admisible, A\* no expande más que Dijkstra, árbol = consultas individuales | se comprueban sobre todos los nodos, no sobre ejemplos |
| Invariantes de la caché | mismo resultado con y sin caché, invalidación, capacidad, orden LRU | `tests/test_cache.py` |
| Equivalencia de variantes | secuencial = hilos = procesos; ingenuo = por lotes = paralelo | cada optimización debe dar el mismo resultado que su línea base |
| Integración | CLI completa y API HTTP | `src.cli.main()` con argumentos reales; `TestClient` de FastAPI |
| Datos reales | el mapa de Córdoba carga y se resuelve | `test_mapa_real_cordoba` |

**Principio:** una optimización sin un test que demuestre que da el mismo resultado no
se acepta. Por eso cada variante rápida se compara contra su línea base.

**Parametrización.** La fixture `graph` de `tests/conftest.py` se parametriza sobre las
cuatro familias de grafos: cada test de algoritmos corre una vez por familia. Las
semillas son fijas, así que los grafos y los pares origen-destino son siempre los
mismos.

## Casos de prueba

| Archivo | Tests | Casos |
| --- | --- | --- |
| `test_algoritmos.py` | 10 (× familias) | costos iguales al oráculo; camino válido y consistente con el costo; heurística admisible; árbol = consultas individuales; BFS correcto en grafos sin pesos y rechaza grafos con pesos; A\* no expande más que Dijkstra; origen = destino; `on_expand` informa cada nodo; mapa real |
| `test_grafo.py` | 4 | la versión cambia con el mapa; una arista inexistente no cambia la versión; generación reproducible; familia desconocida rechazada |
| `test_cache.py` | 5 | mismos resultados con caché; invalidación ante cambio del mapa; respeta la capacidad; LRU conserva lo reciente; capacidad inválida |
| `test_parallel.py` | 3 | todos los modos coinciden; orígenes calientes concentran consultas; consultas reproducibles |
| `test_archivos.py` | 3 | los lotes cubren el archivo en orden; por lotes = ingenuo; paralelo = secuencial |
| `test_cli.py` | 2 | todos los subcomandos terminan bien; generar y procesar un archivo |
| `test_server.py` | 8 | página y `/docs`; mapa; ruta óptima; ruta con caché; validación automática (422); errores propios (400); cortar y restaurar; lote |

Con la parametrización por familia son **76 casos** en total.

## Cómo ejecutarlas

```bash
make test                     # lo mismo que el CI: pytest + cobertura + umbral
pytest                        # solo las pruebas
pytest tests/test_cache.py -v # un archivo
pytest -k admisible           # por nombre
```

## Criterio de aprobación

| Control | Rechaza si |
| --- | --- |
| Pruebas | falla una o más pruebas |
| Cobertura | la cobertura de `src/` baja del **90 %** (`COV_MIN` en el `Makefile`) |

El umbral es 90 % y no el valor actual (97,6 %) para dejar margen sin permitir que la
cobertura se degrade. Las pruebas corren en **Python 3.12 y 3.14** (matriz del CI).

## Resultados

Última corrida en el CI: **76 pruebas aprobadas** en ambas versiones de Python,
cobertura **97,6 %**.

| Módulo | Sentencias | Sin cubrir | Cobertura |
| --- | --- | --- | --- |
| `src/algorithms/astar.py` | 32 | 0 | 100 % |
| `src/algorithms/base.py` | 27 | 1 | 96 % |
| `src/algorithms/bfs.py` | 27 | 1 | 96 % |
| `src/algorithms/dijkstra_heap.py` | 54 | 0 | 100 % |
| `src/algorithms/dijkstra_naive.py` | 33 | 2 | 94 % |
| `src/archivos.py` | 49 | 0 | 100 % |
| `src/cache.py` | 52 | 0 | 100 % |
| `src/cli.py` | 127 | 5 | 96 % |
| `src/graph.py` | 122 | 0 | 100 % |
| `src/osm.py` | 35 | 1 | 97 % |
| `src/parallel.py` | 52 | 5 | 90 % |
| `src/timing.py` | 9 | 0 | 100 % |
| **Total** | **625** | **15** | **97,6 %** |

De las 5 líneas sin cubrir de `parallel.py`, 3 corren dentro de los procesos *worker*
(`_init_worker`, `_solve_in_worker`), donde coverage no mide por defecto, y 2 son la
rama de `GraphSpec.build` para el mapa real, que solo se usa desde el visualizador. Los reportes de cada corrida (JUnit XML, `coverage.xml`
y HTML navegable) se descargan desde los artefactos del CI: `reportes-test-py3.12` y
`reportes-test-py3.14`.
