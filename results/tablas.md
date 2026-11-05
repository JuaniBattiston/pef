# Resultados de las mediciones

Generado por `bench/make_report.py` a partir de `results/results.csv`. No editar a mano.

## Comparación obligatoria

Grafo `grid` V=2500, E=4900; 50 consultas con 5 orígenes calientes. Todas las versiones resuelven exactamente la misma carga.

| Versión | Tiempo | Memoria (pico) | Aceleración | Observación |
|---|---|---|---|---|
| Implementación inicial | 16,640.86 ms | 0.18 MB | 1.0x | Implementacion inicial |
| Estructura optimizada | 70.53 ms | 0.24 MB | 235.9x | Adyacencia + heap + set |
| Algoritmo optimizado | 43.03 ms | 0.24 MB | 386.8x | A* con heuristica euclidea |
| Concurrencia / paralelismo | 83.49 ms | 0.24 MB | 199.3x | ProcessPoolExecutor |
| Versión final | 12.72 ms | 0.64 MB | 1307.7x | A* + cache LRU por origen |

## Algoritmos por familia de grafo y tamaño

`ms/consulta` normaliza porque el baseline se corre con menos repeticiones. `expandidos` es la cantidad media de nodos cerrados: es la métrica que explica la diferencia entre Dijkstra y A*, que comparten cota asintótica.


### Familia `grid`

| V | E | Algoritmo | ms/consulta | MB | Expandidos | % del grafo |
|---|---|---|---|---|---|---|
| 1024 | 1984 | `dijkstra_naive` | 58.52 | 0.07 | 590 | 57.6% |
| 1024 | 1984 | `dijkstra_heap` | 0.56 | 0.08 | 542 | 53.0% |
| 1024 | 1984 | `astar` | 0.34 | 0.07 | 186 | 18.1% |
| 3969 | 7812 | `dijkstra_heap` | 1.94 | 0.29 | 1,719 | 43.3% |
| 3969 | 7812 | `astar` | 0.93 | 0.27 | 434 | 10.9% |
| 15876 | 31500 | `dijkstra_heap` | 11.81 | 1.15 | 7,076 | 44.6% |
| 15876 | 31500 | `astar` | 5.05 | 1.06 | 1,829 | 11.5% |
| 64009 | 127512 | `dijkstra_heap` | 48.29 | 4.59 | 28,802 | 45.0% |
| 64009 | 127512 | `astar` | 19.14 | 4.17 | 7,741 | 12.1% |

### Familia `highway`

| V | E | Algoritmo | ms/consulta | MB | Expandidos | % del grafo |
|---|---|---|---|---|---|---|
| 1024 | 2035 | `dijkstra_naive` | 55.66 | 0.07 | 508 | 49.6% |
| 1024 | 2035 | `dijkstra_heap` | 0.57 | 0.08 | 492 | 48.0% |
| 1024 | 2035 | `astar` | 0.34 | 0.07 | 191 | 18.6% |
| 3969 | 8010 | `dijkstra_heap` | 2.39 | 0.29 | 1,752 | 44.2% |
| 3969 | 8010 | `astar` | 1.09 | 0.28 | 519 | 13.1% |
| 15876 | 32293 | `dijkstra_heap` | 11.62 | 1.18 | 6,638 | 41.8% |
| 15876 | 32293 | `astar` | 3.21 | 1.11 | 1,286 | 8.1% |

### Familia `dense`

| V | E | Algoritmo | ms/consulta | MB | Expandidos | % del grafo |
|---|---|---|---|---|---|---|
| 500 | 12500 | `dijkstra_naive` | 139.03 | 0.03 | 169 | 33.8% |
| 500 | 12500 | `dijkstra_heap` | 1.55 | 0.09 | 171 | 34.2% |
| 500 | 12500 | `astar` | 0.45 | 0.07 | 21 | 4.2% |
| 1000 | 50000 | `dijkstra_heap` | 12.90 | 0.32 | 466 | 46.6% |
| 1000 | 50000 | `astar` | 1.89 | 0.16 | 35 | 3.5% |
| 2000 | 200000 | `dijkstra_heap` | 99.07 | 0.85 | 1,170 | 58.5% |
| 2000 | 200000 | `astar` | 7.28 | 0.70 | 62 | 3.1% |

### Familia `unweighted`

| V | E | Algoritmo | ms/consulta | MB | Expandidos | % del grafo |
|---|---|---|---|---|---|---|
| 1024 | 1984 | `dijkstra_naive` | 67.25 | 0.07 | 592 | 57.8% |
| 1024 | 1984 | `dijkstra_heap` | 0.50 | 0.08 | 544 | 53.1% |
| 1024 | 1984 | `astar` | 0.42 | 0.07 | 313 | 30.5% |
| 1024 | 1984 | `bfs` | 0.19 | 0.04 | 544 | 53.2% |
| 3969 | 7812 | `dijkstra_heap` | 1.83 | 0.29 | 1,716 | 43.2% |
| 3969 | 7812 | `astar` | 1.31 | 0.28 | 816 | 20.6% |
| 3969 | 7812 | `bfs` | 0.74 | 0.16 | 1,713 | 43.2% |
| 15876 | 31500 | `dijkstra_heap` | 13.03 | 1.14 | 6,947 | 43.8% |
| 15876 | 31500 | `astar` | 10.22 | 1.05 | 3,406 | 21.5% |
| 15876 | 31500 | `bfs` | 7.53 | 0.62 | 6,938 | 43.7% |

**Casos donde el baseline no es ejecutable:** grid V=3969 (omitido: trabajo estimado 4.7e+07 operaciones), grid V=15876 (omitido: trabajo estimado 7.5e+08 operaciones), grid V=64009 (omitido: trabajo estimado 1.2e+10 operaciones), highway V=3969 (omitido: trabajo estimado 4.8e+07 operaciones), highway V=15876 (omitido: trabajo estimado 7.6e+08 operaciones), dense V=1000 (omitido: trabajo estimado 5.1e+07 operaciones), dense V=2000 (omitido: trabajo estimado 4.0e+08 operaciones), unweighted V=3969 (omitido: trabajo estimado 4.7e+07 operaciones), unweighted V=15876 (omitido: trabajo estimado 7.5e+08 operaciones). Que un algoritmo deje de ser viable a cierta escala es un resultado del análisis, no una omisión.

## Caché: impacto y sensibilidad al patrón de consultas

| Escenario | Variante | Tiempo | Memoria | Tasa de aciertos |
|---|---|---|---|---|
| origenes_calientes | `sin_cache` | 2,734.12 ms | 1.17 MB | -- |
| origenes_calientes | `con_cache` | 114.59 ms | 3.73 MB | 0.975 |
| origenes_uniformes | `sin_cache` | 2,605.72 ms | 1.17 MB | -- |
| origenes_uniformes | `con_cache` | 3,599.15 ms | 42.04 MB | 0.005 |

## Concurrencia: barrido de tamaño de lote

| Consultas | Secuencial | Hilos | Procesos | Speedup hilos | Speedup procesos |
|---|---|---|---|---|---|
| 10 | 82.42 ms | 105.91 ms | 158.10 ms | 0.78x | 0.52x |
| 50 | 451.02 ms | 635.10 ms | 256.70 ms | 0.71x | 1.76x |
| 200 | 1,987.42 ms | 2,588.00 ms | 609.80 ms | 0.77x | 3.26x |
| 800 | 8,004.70 ms | 10,226.06 ms | 1,896.35 ms | 0.78x | 4.22x |
