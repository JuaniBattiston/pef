# Plan — Segundo Parcial (sobre el planificador de rutas)

> **Estado: ejecutado.** Todos los resultados están en `resultados-parte-2/`
> y la presentación en `resultados-parte-2/presentacion.html`.
> Cambios respecto del plan original: el APM es **Pyroscope** (no New Relic, que
> pide cuenta). Framework: **FastAPI** para el visualizador (2026-10-08) además
> de **pytest** para testing; ver §10.

> Criterio rector: **simple**. Cada punto de la consigna se resuelve con la
> herramienta más directa, tocando el mínimo de código. Nada de capas nuevas,
> clases abstractas ni "frameworks propios". Si algo se puede hacer con un
> comando en vez de con código, se hace con el comando.

---

## 0. Punto de partida

Lo que ya hay (parte 1): `src/` con 4 algoritmos, caché LRU, paralelismo, CLI;
`bench/` con cProfile + tracemalloc; `tests/` con 13 tests sin framework;
`viz/server.py` hecho a mano con `http.server`. Todo stdlib, sin dependencias.

Lo que pide la parte 2 y cómo se cubre:

| # | Tema de la consigna | Solución elegida | Esfuerzo |
|---|---|---|---|
| 1 | Eliminar código redundante | 6 duplicaciones concretas (ver §2) | bajo |
| 2 | Herramienta de optimización del lenguaje | **Scalene** (CPU + memoria por línea) y **py-spy** para un flamegraph | bajo, sin código |
| 3 | Herramienta general (APM) | **Grafana Pyroscope** en Docker (sin cuenta) | bajo, sin código |
| 4 | Archivos grandes: batching, buffer, paralelo | comando `archivo` que procesa un CSV de consultas por lotes | medio |
| 5 | Legibilidad / PEP 8 | **ruff** (`format` + `check`) + docstrings faltantes | bajo |
| 6 | Generador de documentación | **Sphinx** con `autodoc` + `napoleon` | bajo |
| 7 | Análisis de calidad | **SonarQube** en Docker (antes / después) | bajo |
| 8 | Refactorización | sale de los puntos 1 y 5 | — |
| 9 | Testing | pasar a **pytest** + **pytest-cov** | bajo |
| 10 | Uso de algún framework (de testing) | **pytest** con fixtures, parametrize y pytest-cov | bajo |

La aplicación **sigue sin dependencias** (solo biblioteca estándar). Las
herramientas de desarrollo y medición van en `requirements-dev.txt`.

---

## 1. Orden de trabajo

El orden importa: **primero la red de seguridad, después tocar código**.

1. Testing con pytest (§9) → así cualquier refactor queda cubierto.
2. SonarQube "antes" (§7) → foto inicial de la calidad.
3. Eliminar redundancia + refactor (§2).
4. PEP 8 con ruff (§5).
5. Archivos grandes (§4).
6. Perfilado con Scalene / py-spy (§3) y APM con Pyroscope (§3b).
7. Sphinx (§6).
8. SonarQube "después" + tabla comparativa final.

Después de cada paso: `pytest` en verde. Si no, no se avanza.

---

## 2. Eliminar código redundante (puntos 1 y 8)

Duplicaciones encontradas revisando el código, de mayor a menor impacto:

### 2.1 El diccionario de algoritmos está repetido 3 veces
- `src/parallel.py:64` → `ALGORITHMS = {...}`
- `src/cli.py:44` → dict inline dentro de `cmd_ruta`
- `viz/server.py:43` → `ALGORITMOS = {...}` (con otros nombres)

**Solución:** dejar uno solo en `src/algorithms/__init__.py`:

```python
ALGORITHMS = {"naive": dijkstra_naive, "heap": dijkstra_heap, "astar": astar, "bfs": bfs}
```

y que los tres lo importen. El servidor usa los mismos nombres (`heap` en vez
de `dijkstra`, `naive` en vez de `baseline`; se ajusta `index.html`).

### 2.2 `dijkstra_heap` y `dijkstra_tree` tienen el mismo bucle
`src/algorithms/dijkstra_heap.py`: las dos funciones copian el bucle principal.
**Solución:** `dijkstra_tree` pasa a ser una línea:

```python
def dijkstra_tree(graph, source):
    res = dijkstra_heap(graph, source, target=None)  # sin corte temprano
    return res.dist, res.parent
```

Para eso `dijkstra_heap` acepta `target=None` (nunca corta) y devuelve también
`dist` y `parent` (dos campos más en `SearchResult`, opcionales). Hay que
**re-medir** después: si la versión unificada es más lenta en el benchmark de
caché, se documenta como trade-off (o se vuelve atrás, también es un resultado).

### 2.3 El párrafo de `on_expand` está copiado 4 veces
Mismo texto en los docstrings de `dijkstra_naive`, `dijkstra_heap`, `astar`,
`bfs`. **Solución:** dejarlo una vez en `src/algorithms/base.py` y en cada
algoritmo una línea: `on_expand: ver base.py`.

### 2.4 Función de cronometrar repetida
`_timed` en `cli.py`, `timed` en `bench/run_bench.py`, y `t0 = perf_counter()`
a mano 4 veces en `viz/server.py`. **Solución:** una sola `medir_ms(fn)` en
`src/utils.py` (5 líneas) usada por CLI y servidor. `bench/timed` se queda
porque además mide memoria (se aclara en su docstring).

### 2.5 Secuencial e hilos repiten el "resolver una consulta"
`solve_sequential`, `solve_threads` y `_solve_in_worker` hacen lo mismo:
`res = algo(g, s, t); return (res.cost, len(res.path))`.
**Solución:** una función `_answer(algo, graph, query)` y las tres la llaman.

### 2.6 Basura menor
- `uncached_route` en `src/cache.py:143` no se usa en ningún lado → borrar.
- `import random` dentro de `make_queries` → subirlo arriba (PEP 8).
- `cmd_ruta` y `cmd_comparar` repiten el cálculo de `src`/`dst` por defecto →
  helper `_extremos(args, g)`.
- `sys.path.insert(...)` en 5 archivos → se borran todos al agregar
  `pyproject.toml` y correr siempre como módulo (`python -m ...`) o con
  `pythonpath` de pytest.
- `Graph.update_weight` tiene un bucle con `other = v if cont is ... else u`
  difícil de leer → dos bucles explícitos o un helper `_set_weight(lista, nodo, w)`.

**Cómo se demuestra:** líneas de código antes/después (`wc -l` o el "Duplications"
de SonarQube) y tests en verde.

---

## 3. Perfilado con herramientas del lenguaje (punto 2)

Ya tenemos cProfile y tracemalloc. Se suman herramientas **que no requieren
tocar código**:

### 3a. Scalene (herramienta principal)
Da CPU (Python vs nativo), memoria y copias **por línea**: justo lo que cProfile
no mostraba (el baseline era "una caja negra" y tuvimos que instrumentar a mano).

```bash
scalene --cli --reduced-profile bench/profile_run.py   > results/scalene_profile.txt
scalene --html --outfile results/scalene.html  -m src.cli lote --modo secuencial
```

Qué mostrar: que Scalene encuentra **solo** el bucle de aristas del baseline
(el 65,9% que antes medimos a mano) → valida el análisis de la parte 1.

### 3b. py-spy (flamegraph) — opcional
```bash
py-spy record -o results/flame.svg -- python -m src.cli lote --n 200 --modo secuencial
```
Un SVG para la presentación. También sirve contra el servidor ya corriendo
(`py-spy top --pid <PID>`), sin reiniciarlo.

### 3c. SnakeViz — opcional
Visualiza los `.prof` de cProfile que ya generamos (`bench/profile_run.py` solo
tiene que guardar además el `.prof` con `profiler.dump_stats(...)`).

---

## 3b. Herramienta general / APM (punto 3) — Grafana Pyroscope

Se eligió **Grafana Pyroscope** (open source) en lugar de New Relic: corre local
en un contenedor, no pide cuenta ni license key, y la consigna permite
"cualquier otra". Hace monitoreo continuo: muestra en una web qué funciones
consumen CPU, filtrable por operación.

```bash
docker run -d --name pyroscope-pef -p 4040:4040 grafana/pyroscope
python -m bench.apm_pyroscope        # corre la CLI con el agente conectado
# abrir http://localhost:4040  (app: pef.rutas, filtrar por operacion=...)
```

El código de la aplicación no se toca: `bench/apm_pyroscope.py` conecta el
agente y etiqueta cada operación (`comparar`, `lote-cache`, `generar`, `archivo`).

---

## 4. Archivos grandes: batching, buffer y paralelo (punto 4)

Es el único punto que agrega funcionalidad nueva. Encaja natural con el
problema: **el despachante recibe un archivo con muchas consultas y tiene que
devolver un archivo con las respuestas.**

### Qué se agrega
Un módulo chico `src/archivos.py` (~60 líneas) y un comando de CLI:

```bash
python -m src.cli generar-consultas --n 1000000 --salida data/consultas.csv
python -m src.cli archivo --entrada data/consultas.csv --salida results/respuestas.csv \
                          --lote 10000 --modo procesos
```

### Las 3 técnicas, cada una en pocas líneas

**Batching — leer en lotes con un generador** (nunca se carga el archivo entero):

```python
def leer_lotes(ruta, tam_lote):
    with open(ruta, newline="", buffering=1 << 20) as f:
        lector = csv.reader(f)
        next(lector)  # cabecera
        while lote := list(islice(lector, tam_lote)):
            yield [(int(s), int(t)) for s, t in lote]
```

**Buffer — escribir con buffer grande y `writerows`** (una llamada por lote, no
por fila):

```python
with open(salida, "w", newline="", buffering=1 << 20) as f:
    escritor = csv.writer(f)
    for lote in leer_lotes(entrada, tam_lote):
        escritor.writerows(resolver(lote))
```

**Paralelo — cada lote se reparte entre procesos**, reutilizando lo que ya
existe en `parallel.py`. Un único `ProcessPoolExecutor` abierto para todo el
archivo (resuelve de paso el "pool persistente" que quedó pendiente en la parte 1).

### Qué se mide (tabla nueva para el informe)

| Versión | Tiempo | Memoria pico | Observación |
|---|---|---|---|
| Ingenua: `read()` todo + escribir fila a fila con `flush()` | X | X | baseline |
| Lotes (generador) | X | X | memoria constante |
| Lotes + buffer + `writerows` | X | X | menos syscalls |
| Lotes + buffer + procesos | X | X | CPU en paralelo |

La versión ingenua se deja en el mismo módulo (`procesar_ingenuo`) solo para
comparar, igual que se hizo con `dijkstra_naive`. Se mide con el `timed()` que
ya existe en `bench/run_bench.py` (nuevo experimento `bench_archivos`).

Puntos a explicar en la defensa:
- La memoria de la versión por lotes **no crece** con el tamaño del archivo
  (probar con 100k y 1M líneas).
- El tamaño de lote es un trade-off: muy chico → mucho overhead; muy grande →
  más memoria.
- El cuello de botella real es el cálculo de rutas, no el I/O: Scalene lo
  muestra. Para que el I/O se note conviene usar `--modo cache` con pocos
  orígenes calientes.

> Extra opcional: `data/fetch_cordoba.py` y `src/osm.py` leen JSON de 3 MB con
> `read_text()` entero. Es chico, **no** vale la pena cambiarlo; decirlo es
> parte del análisis ("dónde no optimizar").

---

## 5. Legibilidad y mantenibilidad — PEP 8 (punto 5)

Con **ruff**, que hace formato y lint en una sola herramienta:

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "D"]   # pep8, errores, imports, nombres, docstrings
[tool.ruff.lint.pydocstyle]
convention = "google"
```

```bash
ruff check . --statistics      # foto "antes" -> results/ruff_antes.txt
ruff format .
ruff check . --fix
ruff check . --statistics      # foto "después"
```

Además, a mano:
- **Docstrings** en formato Google (`Args:`, `Returns:`) en las funciones
  públicas que no tienen (CLI, `parallel.py`, `server`). Los módulos ya tienen
  docstrings muy buenos: se dejan.
- **Nombres:** hay mezcla español/inglés (`cargar_cordoba`, `solve_processes`).
  No se renombra todo (riesgo alto, poco valor); se fija la regla "nombres de
  código en inglés, textos al usuario en español" y se aplica solo a lo nuevo.
  Mencionarlo como decisión consciente.
- Variables de una letra solo donde son convención (`u`, `v`, `w` en grafos).

---

## 6. Generación de documentación — Sphinx (punto 6)

```bash
sphinx-quickstart docs --no-sep -p "Planificador de rutas" -a "Grupo" -l es
```

En `docs/conf.py`:
```python
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx.ext.viewcode"]
```

```bash
sphinx-apidoc -o docs/api src
make -C docs html          # -> docs/_build/html/index.html
```

`index.rst` incluye el README (vía `.. include::` o myst-parser si se quiere
markdown; sin él, alcanza con linkear). Los docstrings largos que ya existen en
los módulos se convierten solos en la documentación: es la ganancia de haberlos
escrito en la parte 1.

---

## 7. Análisis de calidad — SonarQube (punto 7)

Lo mínimo para tenerlo andando:

```bash
docker run -d --name sonar -p 9000:9000 sonarqube:community
# entrar a http://localhost:9000 (admin/admin), crear proyecto local, generar token
```

```properties
# sonar-project.properties
sonar.projectKey=pef-rutas
sonar.sources=src,viz
sonar.tests=tests
sonar.python.version=3.14
sonar.python.coverage.reportPaths=coverage.xml
```

```bash
pytest --cov=src --cov-report=xml
docker run --rm --network host -v "$PWD:/usr/src" \
  -e SONAR_HOST_URL=http://localhost:9000 -e SONAR_TOKEN=<token> sonarsource/sonar-scanner-cli
```

Se corre **dos veces**: antes del refactor y al final. Tabla para la presentación:

| Métrica Sonar | Antes | Después |
|---|---|---|
| Code smells | X | X |
| Duplicaciones (%) | X | X |
| Complejidad cognitiva máx. | X | X |
| Cobertura (%) | X | X |
| Bugs / vulnerabilidades | X | X |

*Plan B sin Docker:* `ruff` + `radon cc src -a` (complejidad) + `pytest-cov`.
Cubre lo mismo en texto plano.

---

## 8. Refactorización (punto 8)

No es un paso aparte: es el resultado de §2 y §5, **guiado por las métricas**
de SonarQube/ruff y **protegido por los tests**. En el informe se presenta así:

1. qué detectó la herramienta,
2. qué se cambió,
3. que los tests siguen en verde,
4. que el benchmark no empeoró (correr `bench/run_bench.py` y comparar con el
   `results.csv` de la parte 1).

---

## 9. Testing (punto 9)

Los tests actuales ya son funciones `test_*` con `assert`: **pytest los corre
sin cambios**. Pasos:

1. `pyproject.toml`:
   ```toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   pythonpath = ["."]
   ```
   → se borra el `sys.path.insert` y el runner manual del final de
   `tests/test_correctness.py`.
2. Usar `@pytest.mark.parametrize` donde hoy hay `for family in FAMILIES`
   (cada familia pasa a ser un test separado: si falla una, se ve cuál).
3. Tests nuevos, chicos:
   - `tests/test_archivos.py`: generar un CSV de 1.000 consultas en `tmp_path`,
     procesarlo en lotes de 7 (número que no divide exacto) y comparar contra
     resolverlo de una vez. Mismo resultado en modo secuencial y procesos.
   - `tests/test_parallel.py`: secuencial, hilos y procesos dan lo mismo.
   - `tests/test_cli.py`: cada comando de la CLI corre (con `capsys`).
   - `tests/test_cache.py`: los tests de caché existentes + orden LRU.
4. Cobertura: `pytest --cov=src --cov-report=term-missing`. Objetivo razonable:
   >80% de `src/` (no hace falta 100%).

---

## 10. Uso de un framework — pytest (punto 10)

El framework que pide la consigna es **de testing**: se usa **pytest** (ver §9).
Lo que aporta frente al runner casero de la parte 1:

- **Descubrimiento automático**: cualquier `test_*.py` / `test_*` se ejecuta solo.
- **Fixtures** (`conftest.py`): grafos de prueba compartidos y `tmp_path` para
  archivos temporales, sin código de preparación repetido.
- **`parametrize`**: un mismo test corre por cada familia de grafo y cada
  algoritmo; si falla uno, el reporte dice exactamente cuál.
- **`pytest.raises` / `pytest.approx`**: comparaciones de errores y de floats
  sin `try/except` ni epsilons a mano.
- **Plugins**: `pytest-cov` mide la cobertura, que después lee SonarQube.

**Actualización:** además se migró el visualizador (`viz/server.py`) de
`http.server` a **FastAPI**: ruteo con decoradores, validación de parámetros
por tipo (422 automático), documentación interactiva en `/docs` y
`tests/test_server.py` con `TestClient`. Los endpoints quedan como `def`
(CPU-bound, pool de hilos), no `async`. El núcleo `src/` sigue sin dependencias.

---

## 11. Entregables

Todo en `resultados-parte-2/`:

- `antes/` y `despues/`: métricas de calidad (ruff, radon, pylint, cobertura, SonarQube).
- `archivos/`: tablas del experimento de archivos grandes.
- `perfilado/`: Scalene, py-spy (flamegraph), capturas de Pyroscope.
- `docs/`: la documentación HTML generada por Sphinx.
- `presentacion.html`: la presentación para la clase.

Además: `EJECUCION.md` y `README.md` con los comandos nuevos, `pyproject.toml`
(pytest + ruff), `requirements-dev.txt`, `.gitignore`.

## 12. Lo que NO se hace (a propósito)

- No se reescriben los algoritmos: ya están medidos y justificados.
- No se renombra todo al mismo idioma (riesgo > beneficio).
- No se agrega base de datos, framework web, Docker para la app ni async: no
  lo pide la consigna y complica.
- No se optimiza la lectura del JSON de Córdoba (3 MB, se lee una vez).
