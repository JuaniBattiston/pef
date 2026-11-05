# Planificador inteligente de rutas
### Primer Parcial – Programación Eficiente (Opción 1, Python)

Aplicación que encuentra rutas óptimas sobre una red de puntos de entrega, construida
como **banco de mediciones**: cada optimización es una variante activable por separado,
de modo que la mejora se puede atribuir a una sola causa por vez.

---

## 1. El problema

Un despachante recibe lotes de consultas origen→destino sobre una red de reparto.
Es interesante desde el rendimiento porque combina tres presiones distintas:

- el **tamaño de la red** hace explotar los algoritmos ingenuos,
- el **volumen de consultas** invita a paralelizar,
- la **repetición de orígenes** (pocos depósitos, muchos destinos) invita a cachear,
- y el **mapa cambia** (cortes de calle), lo que obliga a invalidar lo cacheado.

## 2. Cómo correrlo

```bash
pytest                                 # 76 tests (pytest)
python3 -m bench.run_bench             # mediciones -> results/results.csv
python3 -m bench.make_report           # tablas   -> results/tablas.md
python3 -m bench.profile_run           # perfilado -> results/profile_*.txt

python3 -m src.cli comparar --family grid --size 16000
python3 -m src.cli simular  --family grid --size 4000
python3 -m src.cli lote --family grid --size 16000 --n 200 --modo procesos
```

El núcleo (`src/`) no tiene dependencias: sólo la biblioteca estándar (Python 3.12+).
El visualizador usa FastAPI: `pip install -r requirements.txt`.

## 3. Estructura

```
src/graph.py                    red + 4 familias de grafos + contador de versión
src/algorithms/dijkstra_naive.py  BASELINE  O(V² + V·E)
src/algorithms/dijkstra_heap.py   adyacencia + heap + set  O((V+E) log V)
src/algorithms/astar.py           A* con heurística euclídea
src/algorithms/bfs.py             O(V+E), sólo pesos uniformes
src/cache.py                      memoización de árboles + caché LRU con invalidación
src/parallel.py                   secuencial / hilos / procesos
src/cli.py                        demostración por consola
src/osm.py                        mapa real de Córdoba (OSM) -> Graph
data/fetch_cordoba.py             descarga de OpenStreetMap (se corre una vez)
viz/server.py, viz/index.html     visualizador gráfico sobre Córdoba
bench/                            medición, perfilado y generación de tablas
tests/                            oráculo Bellman-Ford + 13 tests
```

### Visualizador

```bash
python3 data/fetch_cordoba.py    # una sola vez: baja el mapa (~25 s)
python3 -m viz.server            # y abrir http://localhost:8000 (API en /docs)
```

Interfaz gráfica sobre la red de calles **real** de Córdoba (8.288 intersecciones,
13.296 cuadras). El navegador sólo dibuja: todos los cálculos los hace el mismo código
de `src/algorithms/`, y las esquinas se pintan en el orden real de expansión capturado
con el callback `on_expand`. Detalle completo en [`viz/README.md`](viz/README.md).

---

## 4. Análisis de complejidad

### 4.1 Baseline: Dijkstra ingenuo — O(V² + V·E)

El algoritmo repite V veces: *elegir el nodo no visitado más cercano* y *relajar sus vecinos*.

**Selección del mínimo.** Sin estructura auxiliar hay que recorrer el arreglo de
distancias entero para encontrar el menor no visitado: V comparaciones. Se hace una vez
por iteración y hay V iteraciones, de donde sale `V · V = O(V²)`.

**Búsqueda de vecinos.** Con las aristas en una lista plana, saber quiénes son los
vecinos de `u` exige revisar las E aristas y quedarse con las que tocan `u`: O(E) por
iteración, V iteraciones, `O(V·E)`.

Total `O(V² + V·E)`. En una malla urbana E ≈ 2V, así que domina el término cuadrático;
en un grafo denso E ≈ V²/10 y el término `V·E` se vuelve **cúbico**, que es la razón de
que el baseline sea directamente inejecutable en la familia `dense` (ver tablas).

*Verificación empírica:* de V=1024 a V=3969 (×3.9 en nodos) el tiempo pasó de 113 ms a
1687 ms, ×14.9. El cuadrado de 3.9 es 15.2. La medición coincide con la derivación.

### 4.2 Optimizado: Dijkstra con heap — O((V+E) log V)

**Selección del mínimo.** El heap binario mantiene el mínimo en la raíz. Extraer cuesta
O(log V) porque tras quitar la raíz hay que rehundir un elemento por un árbol de altura
log V. Se extrae a lo sumo una vez por inserción.

**Inserciones.** Se inserta una vez por relajación exitosa, y las relajaciones son a lo
sumo E. Cada inserción cuesta O(log V) por el mismo argumento de altura.

**Búsqueda de vecinos.** Con lista de adyacencia, `adj[u]` da los vecinos de `u` en
O(grado(u)). La suma de los grados sobre todos los nodos es 2E, así que **todo** el
recorrido de vecinos del algoritmo completo cuesta O(E), no O(E) por iteración.

Total `O((V + E) log V)`.

**Por qué importa:** en una malla de 64.000 nodos el baseline necesitaría del orden de
`64.000 × 191.000 ≈ 1,2·10¹⁰` operaciones por consulta. La versión con heap resuelve la
misma consulta en 19 ms. No es una mejora de constante: es la diferencia entre tener o
no tener aplicación.

### 4.3 BFS sobre grafos sin pesos — O(V+E)

Con todas las aristas de igual costo, la cola FIFO ya entrega los nodos en orden de
distancia creciente: no hace falta ordenar la frontera y desaparece el factor `log V`.
Cada nodo entra y sale de la cola una vez (O(V)) y cada arista se mira una vez (O(E)).

Requiere `deque`: `list.pop(0)` es O(n) porque desplaza todos los elementos restantes, y
convertiría el algoritmo en O(V² + E).

### 4.4 A\*: misma cota, distinto trabajo real

A\* ordena la frontera por `f(n) = g(n) + h(n)` en vez de `g(n)`. La cota asintótica es
**idéntica** a la de Dijkstra: la ganancia está en el factor constante, porque descarta
las direcciones que se alejan del destino. Por eso la métrica que lo justifica es
**nodos expandidos**, no sólo el reloj:

| Familia | V | Dijkstra expande | A\* expande | Reducción |
|---|---|---|---|---|
| `grid` | 64.009 | 28.802 (45% del grafo) | 7.741 (12%) | **3,7×** |
| `highway` | 15.876 | 6.638 | 1.286 | **5,2×** |
| `dense` | 2.000 | 1.170 | 62 | **18,9×** |

---

## 5. Decisiones de diseño y justificación

### 5.1 Elección de algoritmo: A\* sobre Dijkstra, con heurística admisible

Se reemplazó Dijkstra por A\* para las consultas punto a punto. La decisión no es
gratuita: exige que la heurística sea **admisible** (nunca sobreestimar el costo real),
porque si no A\* devuelve rutas subóptimas.

Para garantizarlo, el generador crea cada peso como `w = dist_euclídea(u,v) × factor`
con `factor ≥ 1`. Así la distancia en línea recta es una cota inferior del costo real por
construcción. En la familia sin pesos esto no se cumple —una arista de largo 1,4 cuesta
1—, así que la heurística se escala por `1/longitud_máxima`, que restablece la cota.

La propiedad se verifica en `test_heuristic_is_admissible`, que compara `h(u, destino)`
contra el costo real calculado por Bellman-Ford para **todos** los nodos de las cuatro
familias. Sin ese test, la comparación entera sería inválida.

**Cuándo A\* no conviene:** cuando la heurística no informa. Se ve en `unweighted`, donde
la reducción de nodos expandidos es sólo 2× y BFS —que no usa heurística alguna— gana
igual por no pagar el `log V` del heap.

### 5.2 Estructuras de datos

| Estructura | Dónde | Operación dominante | Por qué |
|---|---|---|---|
| **Lista de adyacencia** | `Graph.adj` | "vecinos de u", una vez por nodo cerrado | O(grado(u)) en vez de O(E) por barrido de lista plana. Sobre todo el algoritmo: O(E) contra O(V·E) |
| **Heap binario** | frontera de Dijkstra/A\* | extraer el mínimo, V veces | O(log V) por extracción contra O(V) del barrido lineal |
| **Set** | nodos cerrados | "¿ya lo cerré?", una vez por extracción | pertenencia O(1) promedio por hashing; ocupa proporcional a lo realmente visitado, no a V |
| **`deque`** | cola de BFS | `popleft`, una vez por nodo | O(1); con `list.pop(0)` sería O(n) y BFS degeneraría a O(V²) |
| **`OrderedDict`** | caché | acceso + reordenar por uso reciente | dict + lista doblemente enlazada: `move_to_end` y `popitem` en O(1), que es exactamente lo que pide LRU |

**Un detalle deliberado:** `adj` es una *lista* indexada por entero y no un `dict`. Los
ids de nodo son densos (0..V-1), así que la lista da indexación directa sin costo de
hashing ni overhead por entrada. El `dict` se reserva para claves dispersas: la caché.
Elegir la estructura por el patrón de acceso, no por costumbre.

### 5.3 Memoización y caching

El enunciado distingue ambos conceptos y el sistema implementa los dos, combinados:

**Qué se almacena (memoización).** No la ruta de un par (origen, destino), sino el
**árbol de caminos mínimos completo desde un origen**: los vectores `dist` y `parent`.

**Por qué conviene.** Dijkstra ya resuelve todos los destinos mientras busca uno; cortar
al llegar tira el resto del trabajo. Guardando el árbol, una ejecución responde las V−1
consultas que salen de ese origen. Cachear por par daría, con V=16.000, hasta 2,5·10⁸
claves posibles; por origen, 1,6·10⁴.

**Cuándo se reutiliza.** Un acierto reconstruye el camino siguiendo punteros al padre:
O(longitud del camino), sin tocar el grafo.

**Cómo se evita información obsoleta.** El grafo lleva un contador `version` que se
incrementa ante cualquier cambio del mapa, y la clave de caché es `(version, origen)`.
Una entrada vieja queda **estructuralmente inalcanzable**: no hay forma de leerla por
accidente. Además, al detectar el cambio de versión el almacén se vacía —las entradas
viejas ya no se pueden acceder, pero seguirían ocupando memoria. Lo primero es
correctitud; lo segundo, higiene. Verificado en `test_cache_invalidates_on_map_change`.

**Política de desalojo (caching).** LRU con capacidad acotada, porque las consultas de
rutas tienen localidad temporal marcada: unos pocos orígenes concentran el tráfico.

**Qué mejora se obtiene.** Con 5 orígenes calientes y 200 consultas: **2.734 ms → 115 ms
(23,9×)**, con 97,5% de aciertos.

### 5.4 Concurrencia

**Qué se ejecuta en paralelo:** consultas distintas de un mismo lote.

**Por qué son independientes:** cada consulta sólo *lee* el grafo; ninguna lo modifica.
No hay estado compartido mutable, por lo tanto no hay condiciones de carrera ni hace
falta sincronización. Es paralelismo de datos puro.

**Mecanismo:** `concurrent.futures`, con las dos implementaciones para poder comparar.
`ProcessPoolExecutor` es la que sirve —cada proceso tiene su propio intérprete y su
propio GIL—; `ThreadPoolExecutor` se mide igual, para documentar con números que **no**
ayuda.

**Problemas que aparecieron y cómo se resolvieron:**

1. *Serialización del grafo.* Mandar el grafo en cada tarea lo serializa una y otra vez.
   Solución: `initializer`, que construye el grafo una sola vez por proceso; como la
   generación es determinista a partir de `(familia, tamaño, semilla)`, se envía esa
   receta de tres campos en lugar del grafo. En Python 3.14 esto es obligatorio, no una
   mejora: el arranque por defecto en Linux ya no es `fork`, así que los workers no
   heredan la memoria del padre.
2. *Overhead de arranque.* Crear procesos cuesta decenas de ms y con lotes chicos ese
   costo domina. Por eso el benchmark barre tamaños de lote, para encontrar el cruce.
3. *Granularidad.* Una tarea por consulta genera demasiado ida y vuelta: se agrupa con
   `chunksize`.
4. *Payload de retorno.* Se devuelve el costo y la longitud del camino, no el camino
   completo, para no serializar listas largas.

**Qué no se paralelizó y por qué:** un Dijkstra individual. Es inherentemente secuencial
—cada extracción del mínimo depende de las relajaciones anteriores—; paralelizarlo
requiere otro algoritmo (delta-stepping) y sincronización cuyo costo se comería la
ganancia a esta escala.

---

## 6. Perfilado

| Herramienta | Qué mide | Para qué se usó |
|---|---|---|
| `cProfile` | tiempo y llamadas por función | localizar el cuello de botella |
| `pstats` | ordenamiento por tiempo propio | separar costo propio del de las llamadas |
| `tracemalloc` | asignaciones del intérprete, por línea | columna de memoria de la tabla |
| `time.perf_counter` | reloj monótono de alta resolución | mediciones limpias, sin instrumentación |

`cProfile` instrumenta cada llamada y por lo tanto distorsiona los tiempos absolutos: se
usa para **ubicar** el cuello de botella y comparar proporciones, no para medir
velocidad. Los tiempos reportados en las tablas salen de `perf_counter` sin instrumentar.

Salidas en `results/profile_*.txt`. Metodología de medición: semilla fija, corrida de
calentamiento previa, y `min` sobre las repeticiones en vez de promedio —el mínimo es
más robusto frente al ruido del planificador del sistema operativo, que sólo puede
agregar tiempo, nunca quitarlo.

---

## 7. Resultados

> **Dos correcciones de metodología, ambas encontradas midiendo.**
>
> 1. *Corridas solapadas.* Una tanda quedó invalidada porque dos ejecuciones del benchmark
>    se pisaron y compitieron por CPU, lo que distorsiona sobre todo la concurrencia. Los
>    números de acá salen de una corrida limpia, sin otra carga en el sistema.
>
> 2. *El medidor de memoria inflaba el reloj.* La primera versión de `timed()` cronometraba
>    con `tracemalloc` activo. Ese trazador intercepta cada asignación del intérprete, y
>    resultó que **duplicaba los tiempos**: `dijkstra_heap` sobre V=16.000 medía 24,96 ms
>    con el trazador prendido y 12,6 ms sin él. Cronometrar con el medidor de memoria
>    encendido es medir el medidor. Ahora tiempo y memoria se miden en pasadas separadas.
>
> Las conclusiones no cambiaron con ninguna de las dos correcciones; las magnitudes sí.

Las tablas completas se generan desde el CSV: **[`results/tablas.md`](results/tablas.md)**.
Datos crudos en `results/results.csv`, log de la corrida en `results/bench.log`.

---

## 8. Conclusiones

### Dónde está el cuello de botella

El perfilado a nivel de función mostró el baseline como una caja negra: los dos bucles
calientes están inline dentro de una sola función. Hizo falta instrumentar por fases
(`results/profile_cuello_botella.txt`):

| Fase del baseline | Complejidad | Porcentaje del tiempo |
|---|---|---|
| Barrido de la lista de aristas para hallar vecinos | O(V·E) | **65,9%** |
| Selección del mínimo por barrido lineal | O(V²) | 34,1% |

**Esto cambió el orden de trabajo.** La intuición decía "el problema es no tener heap";
la medición dijo que el heap ataca sólo un tercio del costo. Se aplicó primero la lista
de adyacencia. Perfilar antes de optimizar no fue un trámite: evitó atacar la fase
equivocada.

### Qué optimización produjo mayor impacto

**Las estructuras de datos, por lejos: 235,9× de un solo golpe** (16.641 ms → 70,5 ms),
más que todas las demás optimizaciones juntas. Cambiar `O(V² + V·E)` por
`O((V+E) log V)` es un salto asintótico; el resto son mejoras de factor constante o de
reutilización, valiosas pero de otro orden de magnitud.

Le sigue la caché en su escenario favorable (23,9× sobre 200 consultas con orígenes
repetidos), y después el paralelismo (4,2× con lotes grandes).

### Qué decisión no produjo la mejora esperada

**Tres, y las tres son informativas:**

**1. Los hilos empeoraron el rendimiento en todos los tamaños de lote** —speedup entre
0,71× y 0,78×, es decir hasta **1,4× más lento** que secuencial. Es el GIL: la carga es
CPU-bound pura y los hilos no pueden ejecutar bytecode en paralelo, así que sólo agregan
contención por el lock y cambios de contexto. Confirma que "usar threads" no es
optimizar; los procesos sobre la misma carga dan 4,2×.

**2. La caché fue contraproducente con orígenes uniformes:** 2.606 ms → 3.599 ms
(**1,4× más lenta**) y la memoria pasó de 1,2 MB a 42 MB. Con 0,5% de aciertos, cada
consulta paga el Dijkstra completo *sin* corte temprano al destino —el precio de
construir el árbol entero— y encima almacena un resultado que nadie reutiliza. La caché
no es una mejora incondicional: depende del patrón de acceso, y hay que medirlo.

**3. La predicción sobre grafos densos falló.** Se esperaba que en `dense` el baseline
O(V²) le ganara al heap, porque con E→V² el término `E log V` supera a `V²`. No pasó:
en V=500 el baseline tardó 139 ms/consulta contra 1,55 ms del heap. La razón es que
nuestro baseline no es un O(V²) puro —tiene además el término `O(V·E)` del barrido de
aristas, que en un grafo denso es cúbico y domina todo lo demás. El razonamiento teórico
era correcto para un baseline con matriz de adyacencia, no para el nuestro. **Una
predicción que la medición desmiente es exactamente para lo que se mide.**

### Sobre la escalabilidad

La mejora **se amplifica** al aumentar el volumen, no se mantiene apenas:

- El baseline queda inejecutable a partir de V≈4.000 (trabajo estimado 10¹⁰ operaciones
  por consulta); las versiones optimizadas resuelven V=64.009 en 19 ms.
- La ventaja de A\* crece con el tamaño: en `grid` pasa de 1,6× (V=1.024) a 2,5×
  (V=64.009) en tiempo, y de 2,9× a 3,7× en nodos expandidos.
- El paralelismo recién cruza el punto de rentabilidad entre 10 y 50 consultas, y de ahí
  sigue mejorando: 0,52× con 10, 1,76× con 50, 3,26× con 200, 4,22× con 800. Con lotes chicos el arranque de
  procesos se come la ganancia; con lotes grandes se amortiza.

### Trade-offs asumidos

| Optimización | Se ganó | Se pagó |
|---|---|---|
| Heap con borrado perezoso | simplicidad, sin índice de posiciones | el heap crece hasta O(E) en vez de O(V); 21% de extracciones descartadas por obsoletas |
| Caché de árboles | 23,9× con orígenes repetidos | 3× la memoria; y 1,4× **más lento** si los orígenes no se repiten |
| A\* | 3,7× menos nodos expandidos | exige coordenadas y una heurística admisible verificada |
| Procesos | 4,2× | ~150 ms de arranque; obliga a reconstruir el grafo por worker |

### Qué haríamos distinto

1. **Caché adaptativa.** Medir la tasa de aciertos en caliente y desactivarse sola cuando
   cae por debajo de un umbral. Hoy la política es fija y el escenario uniforme la vuelve
   una penalización.
2. **Dijkstra bidireccional.** Buscar desde ambos extremos reduce el frente explorado
   aproximadamente a la raíz cuadrada. Es la mejora obvia que quedó fuera de alcance.
3. **Baseline con matriz de adyacencia** además del de lista de aristas, para poder
   contrastar el O(V²) puro contra el heap en grafos densos y cerrar la predicción
   fallida con datos en lugar de una explicación.
4. **Pool de procesos persistente.** Hoy se crea y destruye por lote; reutilizarlo
   eliminaría los ~150 ms de arranque y bajaría el punto de rentabilidad.
