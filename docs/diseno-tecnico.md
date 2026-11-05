# Diseño técnico

## Estructuras de datos

| Estructura | Dónde | Operación dominante | Por qué |
| --- | --- | --- | --- |
| Lista de adyacencia (`list[list[tuple[int, float]]]`) | `Graph.adj` | "vecinos de u", una vez por nodo cerrado | O(grado(u)) en vez de O(E). Sobre todo el algoritmo: O(E) contra O(V·E) |
| Heap binario (`heapq`) | frontera de Dijkstra y A\* | extraer el mínimo | O(log V) contra O(V) del barrido lineal |
| `set` | nodos cerrados | "¿ya lo cerré?" | pertenencia O(1) promedio; ocupa lo visitado, no V |
| `collections.deque` | cola de BFS | `popleft` | O(1); `list.pop(0)` sería O(n) y BFS degeneraría a O(V²) |
| `OrderedDict` | `RouteCache` | acceso + reordenar por uso | `move_to_end` y `popitem` en O(1): exactamente lo que pide LRU |

`adj` es una **lista** indexada por entero y no un `dict`: los ids de nodo son densos
(0..V−1), así que la lista indexa directo, sin hashing ni overhead por entrada. El `dict`
se reserva para claves dispersas, como la caché.

### El grafo

```python
@dataclass
class Graph:
    n: int                                   # cantidad de nodos
    coords: list[tuple[float, float]]        # para la heurística de A*
    adj: list[list[tuple[int, float]]]       # vecino, peso
    edges: list[tuple[int, int, float]]      # lista plana: la usa el baseline
    version: int = 0                         # se incrementa ante cada cambio del mapa
    weighted: bool = True
    heuristic_scale: float = 1.0             # garantiza que la heurística sea admisible
```

## Algoritmos y complejidad

| Algoritmo | Complejidad | Cuándo conviene |
| --- | --- | --- |
| Dijkstra ingenuo (línea base) | O(V² + V·E) | nunca en producción; es la referencia |
| Dijkstra con heap | O((V + E) log V) | uso general; árbol completo para la caché |
| A\* | O((V + E) log V) en el peor caso | punto a punto con coordenadas |
| BFS | O(V + E) | solo grafos sin pesos |

### Línea base: O(V² + V·E)

El algoritmo repite V veces *elegir el nodo no visitado más cercano* y *relajar sus
vecinos*. Sin heap, elegir el mínimo recorre las V distancias: V·V = **O(V²)**. Con las
aristas en una lista plana, hallar los vecinos de `u` recorre las E aristas: V·E =
**O(V·E)**. En una malla E ≈ 2V y domina el término cuadrático. En un grafo denso
E ≈ V²/10 y el término V·E se vuelve cúbico.

*Verificación empírica:* de V=1.024 a V=3.969 (×3,9 nodos) el tiempo pasó de 113 ms a
1.687 ms (×14,9). 3,9² = 15,2: la medición coincide con la derivación.

### Dijkstra con heap: O((V + E) log V)

Cada extracción del heap cuesta O(log V) y hay a lo sumo una por inserción. Se inserta
una vez por relajación exitosa, como máximo E veces. Con lista de adyacencia el
recorrido de **todos** los vecinos suma 2E en todo el algoritmo, no por iteración.

Se usa **borrado perezoso**: en vez de actualizar la prioridad de un nodo se inserta de
nuevo y las entradas viejas se descartan al extraerlas (`if u in visited: continue`).
Es más simple que mantener un índice de posiciones. El costo es que el heap crece hasta
O(E) en vez de O(V): el 21 % de las extracciones se descartan por obsoletas.

### A\*: misma cota, menos trabajo

A\* ordena la frontera por `f(n) = g(n) + h(n)`. La cota asintótica es la de Dijkstra.
La ganancia está en **cuántos nodos expande**, porque descarta direcciones que se alejan
del destino:

| Familia | V | Dijkstra expande | A\* expande | Reducción |
| --- | --- | --- | --- | --- |
| `grid` | 64.009 | 28.802 (45 %) | 7.741 (12 %) | 3,7× |
| `highway` | 15.876 | 6.638 | 1.286 | 5,2× |
| `dense` | 2.000 | 1.170 | 62 | 18,9× |

**Admisibilidad.** Cada peso se genera como `distancia_euclídea × factor`, con
`factor ≥ 1`, así que la línea recta nunca sobreestima. En `unweighted` (peso 1 por
arista) la heurística se escala por `1/longitud_máxima`. En el mapa real el margen se
calcula a partir de las aristas (`src/osm.py`). Lo verifica `test_heuristic_is_admissible`
contra Bellman-Ford para todos los nodos de las cuatro familias.

### BFS: O(V + E)

Con pesos uniformes la cola FIFO ya entrega los nodos por distancia creciente: no hace
falta el heap y desaparece el factor log V. `bfs` rechaza grafos con pesos
(`ValueError`).

## Memoización y caché

**Qué se guarda.** No la ruta de un par, sino el **árbol de caminos mínimos desde un
origen** (`dist` y `parent`). Una ejecución responde las V−1 consultas de ese origen.
Por par habría hasta V² claves; por origen, V.

**Cuándo se reutiliza.** Un acierto reconstruye el camino por punteros al padre:
O(largo del camino), sin tocar el grafo.

**Cómo se evita información obsoleta.** La clave es `(graph.version, origen)` y la
versión cambia con cada modificación del mapa. Una entrada vieja queda inalcanzable.
Además el almacén se vacía al detectar el cambio, para liberar memoria.

**Desalojo.** LRU con capacidad acotada: pocos orígenes (depósitos) concentran el
tráfico.

**Trade-off medido.** Con 5 orígenes calientes: 23,9× más rápido. Con orígenes
uniformes (0,5 % de aciertos): 1,4× **más lento** y 35 veces más memoria, porque cada
consulta paga el árbol completo sin corte temprano.

## Concurrencia

- **Qué se paraleliza:** consultas distintas de un lote. Solo leen el grafo; no hay
  estado compartido mutable ni sincronización.
- **Procesos, no hilos:** la carga es CPU-bound y el GIL serializa los hilos. Los hilos
  dan 0,71×–0,78× (más lento); los procesos, 4,2× con lotes grandes.
- **El grafo se envía como receta** (`GraphSpec`) y cada proceso lo construye una vez
  en su `initializer`. Desde Python 3.14 es obligatorio: el arranque por defecto en Linux
  ya no es `fork`.
- **`chunksize`** agrupa consultas por envío; se devuelve `(costo, nodos)` y no el
  camino completo.
- **Un Dijkstra individual no se paraleliza:** cada extracción depende de la anterior.

## Archivos grandes (parte 2)

| Técnica | Implementación | Efecto medido (1.000.000 filas) |
| --- | --- | --- |
| Batching | `leer_lotes` es un generador de lotes de `tam_lote` filas | memoria constante: 7,5 MB contra 190 MB |
| Buffer | archivos abiertos con buffer de 1 MB; `writerows` por lote | 1.137 ms → 741 ms |
| Paralelo | un pool de procesos para todo el archivo | 14,1 s → 2,8 s con cálculo real |

## Decisiones de implementación

| Decisión | Alternativa descartada | Motivo |
| --- | --- | --- |
| Lista de adyacencia antes que heap | heap primero | el perfilado mostró que el barrido de aristas era el 65,9 % del costo |
| `dijkstra_tree` repite el bucle de `_search` | reutilizar `_search` | reutilizarlo era 6 % más lento en el camino caliente de la caché |
| `GraphSpec` en vez de enviar el grafo | serializar `Graph` | el costo de serializar superaba al de resolver |
| Semillas fijas en todos los generadores | aleatoriedad real | mediciones reproducibles entre máquinas y en el CI |
| Núcleo sin dependencias | usar networkx | medir nuestras estructuras, no las de una librería |
