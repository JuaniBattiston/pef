# Rendimiento

Esta sección junta tres cosas: los resultados de las entregas anteriores (por qué el
sistema es rápido), los controles del CI (cómo se evita que deje de serlo) y la
complejidad de cada operación.

## Complejidad temporal y espacial

| Operación | Tiempo | Memoria extra |
| --- | --- | --- |
| Dijkstra ingenuo | O(V² + V·E) | O(V) |
| Dijkstra con heap | O((V + E) log V) | O(V + E) (heap con borrado perezoso) |
| A\* | O((V + E) log V) peor caso | O(V + E) |
| BFS | O(V + E) | O(V) |
| `RouteCache.route`, acierto | O(largo del camino) | — |
| `RouteCache.route`, fallo | O((V + E) log V) | O(V) por árbol guardado |
| Procesar archivo por lotes | O(filas × consulta) | O(tam_lote), independiente del tamaño del archivo |
| `Graph.update_weight` | O(grado(u) + grado(v) + E) | — |

La derivación de cada cota está en [Diseño técnico](diseno-tecnico.md#algoritmos-y-complejidad).

## Resultados de las partes 1 y 2

### Comparación de versiones

Grafo `grid` de V=2.500, 50 consultas con 5 orígenes calientes; todas las versiones
resuelven la misma carga.

| Versión | Tiempo | Memoria (pico) | Aceleración |
| --- | --- | --- | --- |
| Implementación inicial (Dijkstra ingenuo) | 16.640,9 ms | 0,18 MB | 1,0× |
| Estructuras optimizadas (adyacencia + heap + set) | 70,5 ms | 0,24 MB | 235,9× |
| Algoritmo optimizado (A\*) | 43,0 ms | 0,24 MB | 386,8× |
| Concurrencia (`ProcessPoolExecutor`) | 83,5 ms | 0,24 MB | 199,3× |
| Versión final (A\* + caché LRU) | 12,7 ms | 0,64 MB | 1.307,7× |

### Escalabilidad por algoritmo (familia `grid`)

| V | Dijkstra con heap | A\* | Nodos expandidos (heap → A\*) |
| --- | --- | --- | --- |
| 1.024 | 0,56 ms | 0,34 ms | 53 % → 18 % |
| 3.969 | 1,94 ms | 0,93 ms | 43 % → 11 % |
| 15.876 | 11,81 ms | 5,05 ms | 45 % → 12 % |
| 64.009 | 48,29 ms | 19,14 ms | 45 % → 12 % |

Tablas completas en `results/tablas.md` y `resultados-parte-2/`.

### Archivos grandes

| Variante | 1.000.000 filas | Memoria pico |
| --- | --- | --- |
| Ingenuo (todo a memoria, flush por fila) | 1.137 ms | 190,1 MB |
| Lotes + buffer | 741 ms | 7,5 MB |

## Profiling de CPU

| Herramienta | Uso |
| --- | --- |
| **pyinstrument** | perfil por muestreo del CI: árbol de llamadas en HTML y texto |
| **cProfile + pstats** | top-20 funciones por tiempo propio en el CI; perfiles de las partes 1 y 2 |
| Scalene, py-spy | perfil por línea y flamegraph (parte 2, `resultados-parte-2/perfilado/`) |

`make profile` perfila un lote de 100 consultas A\* sobre una grilla de 16.000 nodos.
Resultado típico (cProfile, ordenado por tiempo propio):

| Función | Llamadas | Tiempo propio |
| --- | --- | --- |
| `astar` | 100 | 0,69 s |
| `Graph.euclid` | 427.798 | 0,21 s |
| `heapq.heappop` | 374.126 | 0,20 s |
| `Graph.heuristic` | 396.298 | 0,15 s |

El cuello de botella es el bucle de A\* y el cálculo de la heurística. Es lo esperado:
el resto del sistema (construcción del grafo, E/S) no pesa.

**Criterio:** el profiling es **informativo** y no bloquea. Sus tiempos están
distorsionados por la instrumentación, así que no sirven como umbral. Para eso está el
benchmark. Se publica en cada corrida (`reportes-perf`) para revisar el cuello de
botella cuando el benchmark detecta una regresión.

## Benchmark del CI

`bench/test_benchmarks.py` mide con **pytest-benchmark** siete operaciones
representativas, una por cada decisión de diseño defendida:

| Benchmark | Qué protege | Mediana local |
| --- | --- | --- |
| `test_ruta_grid[heap]` | Dijkstra con heap, V=10.000 | 11,3 ms |
| `test_ruta_grid[astar]` | A\*, V=10.000 | 15,7 ms |
| `test_ruta_bfs` | BFS sin pesos, V=10.000 | 3,9 ms |
| `test_ruta_naive` | la línea base, V=1.000 | 103,2 ms |
| `test_arbol_caminos_minimos` | `dijkstra_tree`, camino caliente de la caché | 10,5 ms |
| `test_cache_hit` | consulta resuelta por la caché | 0,013 ms |
| `test_lote_secuencial` | 20 consultas A\* | 85,2 ms |

**Línea base confiable.** Comparar contra números guardados de otra máquina no sirve:
los runners de GitHub varían. Por eso el job de rendimiento mide **en la misma máquina y
en el mismo job** la rama base (`main` en un PR, el commit anterior en un push) y el
cambio, con los mismos benchmarks (`make bench-baseline` usa `git worktree`).

**Reducción de ruido.** Calentamiento, recolector de basura desactivado durante la
medición, al menos 10 rondas, y comparación por **mediana** (robusta frente a valores
atípicos).

**Criterio de rechazo:** la mediana de cualquier benchmark empeora más de **25 %**
contra la base (`BENCH_REGRESION`). Entre dos corridas del mismo código la diferencia
medida fue menor a 2 %. Una regresión real (un cálculo extra en el bucle de Dijkstra)
dio +76 % y el control la rechazó.

## Control de memoria

`bench/check_memory.py` mide el **pico de memoria con tracemalloc** en cinco escenarios:

| Escenario | Pico medido | Límite |
| --- | --- | --- |
| `grafo_grid` — construir V=10.000 | 7,36 MiB | 9,57 MiB |
| `dijkstra_heap` — una consulta | 0,89 MiB | 1,16 MiB |
| `cache_32` — caché con 32 árboles | 12,72 MiB | 16,54 MiB |
| `archivo_lotes` — 50.000 consultas por lotes | 2,69 MiB | 3,50 MiB |
| `archivo_ingenuo` — lo mismo, todo a memoria | 13,49 MiB | 17,54 MiB |

**Por qué tracemalloc.** Cuenta las asignaciones del intérprete y no incluye el ruido del
sistema operativo. Con la misma versión de Python el pico es determinista: dos corridas
dan el mismo valor. Eso permite un límite fijo, que con RSS no sería justo.

**Criterio de rechazo:** algún pico supera su límite, que es lo medido **+30 %**
(`bench/memory_limits.json`). Una fuga que duplicaba cada árbol de la caché llevó
`cache_32` al 106 % del límite y el control la rechazó. Un aumento justificado se acepta
regenerando los límites (ver [Mantenimiento](mantenimiento.md#cambiar-una-linea-base-o-un-limite)).
