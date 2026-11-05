# Guía de Ejecución — PEF (Planificador de Rutas)

## Requisitos

- Python 3.12+. El núcleo (`src/`) usa solo la biblioteca estándar; el visualizador
  usa FastAPI (`pip install -r requirements.txt`).
- Herramientas de desarrollo y CI (parte 3, versiones fijadas con hashes): `pip install --require-hashes -r requirements-dev.txt`
- Herramientas de perfilado de la parte 2 (Scalene, py-spy, Pyroscope): `pip install -r requirements-parte2.txt`
- Ejecutar siempre desde la raíz del proyecto (la carpeta que contiene `src/`).

---

## 1. Tests (pytest)

```bash
pytest                                   # 76 tests
pytest --cov --cov-report=term-missing   # con cobertura (97%)
```

Archivos: `test_algoritmos.py` (contra Bellman-Ford), `test_grafo.py`, `test_cache.py`,
`test_parallel.py`, `test_archivos.py`, `test_cli.py`, `test_server.py` (API FastAPI con `TestClient`). Fixtures compartidas en `conftest.py`.

---

## 2. CLI — `src/cli.py`

```bash
python3 -m src.cli <comando> [opciones]
```

### 2.1 `ruta` — consulta individual

```bash
python3 -m src.cli ruta [--family FAMILY] [--size SIZE] [--seed SEED] \
                        [--origen ORIGEN] [--destino DESTINO] [--algo ALGO]
```

| Opción | Valores | Default |
|--------|---------|---------|
| `--family` | `grid` `highway` `dense` `unweighted` | `grid` |
| `--size` | entero (nodos) | `4000` |
| `--seed` | entero | `42` |
| `--origen` | id de nodo | `0` |
| `--destino` | id de nodo | último nodo |
| `--algo` | `naive` `heap` `astar` `bfs` | `astar` |

```bash
# Ejemplos
python3 -m src.cli ruta --family grid --size 16000 --origen 100 --destino 15000 --algo astar
python3 -m src.cli ruta --family unweighted --size 4000 --algo bfs
python3 -m src.cli ruta --family highway --size 8000 --algo heap
```

### 2.2 `comparar` — comparación de algoritmos

Ejecuta todos los algoritmos apropiados sobre la misma ruta y muestra tiempos comparativos.

```bash
python3 -m src.cli comparar [--family FAMILY] [--size SIZE] [--seed SEED] \
                             [--origen ORIGEN] [--destino DESTINO]
```

```bash
# Ejemplos
python3 -m src.cli comparar --family grid --size 4000
python3 -m src.cli comparar --family highway --size 16000
python3 -m src.cli comparar --family dense --size 1000
```

> `dijkstra_naive` se omite automáticamente si el grafo es muy grande (`V*(V+E) > 4e7`).

### 2.3 `simular` — invalidación de caché

Demuestra el ciclo completo: cache miss → cache hit → corte de calle → invalidación → recalculo.

```bash
python3 -m src.cli simular [--family FAMILY] [--size SIZE] [--seed SEED]
```

```bash
# Ejemplos
python3 -m src.cli simular --family grid --size 4000
python3 -m src.cli simular --family highway --size 8000
```

### 2.4 `lote` — lote de consultas con distintos modos de ejecución

```bash
python3 -m src.cli lote [--family FAMILY] [--size SIZE] [--seed SEED] \
                        [--n N] [--modo MODO] [--algo ALGO] [--calientes CALIENTES]
```

| Opción | Valores | Default |
|--------|---------|---------|
| `--n` | cantidad de consultas | `200` |
| `--modo` | `secuencial` `hilos` `procesos` `cache` | `procesos` |
| `--algo` | `naive` `heap` `astar` `bfs` | `astar` |
| `--calientes` | nodos fuente frecuentes (0 = uniforme) | `5` |

```bash
# Por modo de ejecución
python3 -m src.cli lote --family grid --size 16000 --n 200 --modo secuencial
python3 -m src.cli lote --family grid --size 16000 --n 200 --modo hilos
python3 -m src.cli lote --family grid --size 16000 --n 200 --modo procesos
python3 -m src.cli lote --family grid --size 16000 --n 200 --modo cache --calientes 5

# Cache sin hits (distribución uniforme, peor caso)
python3 -m src.cli lote --family grid --size 16000 --n 200 --modo cache --calientes 0

# Estudio de escalado
python3 -m src.cli lote --family grid --size 16000 --n 50  --modo procesos
python3 -m src.cli lote --family grid --size 16000 --n 200 --modo procesos
python3 -m src.cli lote --family grid --size 16000 --n 800 --modo procesos
```

### 2.5 `generar-consultas` y `archivo` — archivos grandes (parte 2)

```bash
python3 -m src.cli generar-consultas --size 2000 --n 1000000 --salida consultas.csv
python3 -m src.cli archivo --size 2000 --entrada consultas.csv --salida respuestas.csv --lote 10000
python3 -m src.cli archivo ... --secuencial      # sin procesos
```

Lee el CSV por lotes (generador), escribe con buffer de 1 MB y reparte cada lote entre procesos.

---

## 3. Benchmarking

> Estos scripts **deben ejecutarse como script** (no interactivamente) por requisito de `ProcessPoolExecutor`.

### 3.1 Suite completa de benchmarks

```bash
python3 -m bench.run_bench
```

Genera:
- `results/results.csv` — datos brutos
- `results/bench.log` — log de la corrida

Experimentos incluidos:
1. Algoritmos por familia y tamaño
2. Impacto de caché (fuentes calientes vs uniformes)
3. Concurrencia (secuencial / hilos / procesos) por tamaño de lote
4. Tabla resumen de las 5 versiones del sistema

### 3.2 Generación de tablas

```bash
python3 -m bench.make_report
```

Requiere `results/results.csv` previo. Genera `results/tablas.md`.

---

## 4. Perfilado

```bash
python3 -m bench.profile_run
```

Genera en `results/`:
- `profile_baseline.txt` — cProfile de Dijkstra naive
- `profile_optimizado.txt` — cProfile de Dijkstra heap
- `profile_astar.txt` — cProfile de A*
- `profile_cuello_botella.txt` — atribución por operación (selección mínimo vs escaneo aristas)
- `profile_memoria.txt` — perfilado de memoria con `tracemalloc`

---

### 4.1 Herramientas de la parte 2

```bash
python3 -m bench.bench_archivos                               # batching / buffer / paralelo
# Scalene por línea (1.5.51 en Python 3.12 vía uv: la 2.3.0 no atribuye bien las líneas)
uvx --python 3.12 --from scalene==1.5.51 scalene --cli --cpu --profile-all \
    --profile-exclude threading bench/cargas_perfilado.py --- baseline
py-spy record -o flame.svg -- python -m src.cli lote --modo secuencial
snakeviz results/profile_baseline.prof                        # visor de cProfile
python3 -m bench.apm_pyroscope                                # APM, ver http://localhost:4040
make ci                                                       # todos los controles del CI (parte 3)
mkdocs serve                                                  # documentación (parte 3)
```

Todos los resultados de la parte 2 están en `resultados-parte-2/`.

---

## 5. Visualización interactiva

```bash
# Solo la primera vez (~25 segundos)
python3 data/fetch_cordoba.py

# Levanta el servidor en http://localhost:8000
python3 -m viz.server

# Puerto alternativo
python3 -m viz.server 8080
```

Endpoints disponibles en el servidor:

| Endpoint | Parámetros | Descripción |
|----------|------------|-------------|
| `GET /` | — | Interfaz web |
| `GET /api/mapa` | — | Coordenadas y aristas |
| `GET /api/ruta` | `desde`, `hasta`, `algo`, `cache` | Resolver ruta |
| `GET /api/cortar` | `u`, `v` | Simular corte de calle |
| `GET /api/reset` | — | Restaurar mapa original |
| `GET /api/lote` | `algo`, `tamanos` | Benchmark de modos concurrentes |

---

## 6. Flujos de trabajo típicos

**Verificar correctitud antes de medir:**
```bash
pytest
```

**Benchmark completo + informe:**
```bash
python3 -m bench.run_bench
python3 -m bench.make_report
python3 -m bench.profile_run
```

**Comparación rápida de algoritmos:**
```bash
python3 -m src.cli comparar --family grid --size 4000
```

**Estudio de concurrencia:**
```bash
python3 -m src.cli lote --family grid --size 16000 --n 200 --modo secuencial
python3 -m src.cli lote --family grid --size 16000 --n 200 --modo hilos
python3 -m src.cli lote --family grid --size 16000 --n 200 --modo procesos
```

**Visualización sobre el mapa real de Córdoba:**
```bash
python3 data/fetch_cordoba.py
python3 -m viz.server
# Abrir http://localhost:8000
```

---

## 7. Referencia rápida de algoritmos y familias

| Algoritmo | Complejidad | Cuándo usarlo |
|-----------|-------------|---------------|
| `naive` | O(V² + V·E) | Baseline, grafos pequeños |
| `heap` | O((V+E) log V) | Uso general |
| `astar` | O((V+E) log V)* | Punto a punto con heurística euclidiana |
| `bfs` | O(V+E) | Solo grafos no pesados |

| Familia | Características |
|---------|-----------------|
| `grid` | Topología de grilla, pesado, buena heurística para A* |
| `highway` | Disperso, tipo autopista |
| `dense` | Altamente conectado |
| `unweighted` | Peso 1 en todas las aristas (solo BFS) |
