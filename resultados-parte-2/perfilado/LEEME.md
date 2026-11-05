# Perfilado (parte 2)

| Archivo | Herramienta | Qué muestra |
|---|---|---|
| `scalene_baseline.txt` / `.json` / `.html` | Scalene 1.5.51 (`--cpu`) | Líneas más caras de `dijkstra_naive` |
| `scalene_archivo.txt` / `.json` / `.html` | Scalene 1.5.51 (CPU + memoria) | Reparto del tiempo al procesar un CSV de 20.000 consultas |
| `pyspy_baseline.txt` | py-spy (raw, con número de línea) | Lo mismo que Scalene, con otra técnica de muestreo |
| `pyspy_archivo.txt` | py-spy (raw) | Reparto del tiempo al procesar el CSV |
| `flamegraph.svg` | py-spy | Flamegraph interactivo (abrir en el navegador) del mismo proceso |
| `cprofile/profile_*.prof` / `.txt` | cProfile | Abrir los `.prof` con `snakeviz cprofile/profile_baseline.prof` |
| `scalene_2.3.0_fallido/` | Scalene 2.3.0 | El primer intento, que atribuía mal el tiempo (ver abajo) |

Los `.html` de Scalene se abren directo en el navegador.

## Cómo se corrió Scalene

```bash
uvx --python 3.12 --from scalene==1.5.51 scalene --cli --cpu --profile-all \
    --profile-exclude threading bench/cargas_perfilado.py --- baseline
```

- `uvx --python 3.12`: Scalene corre en un entorno aislado con Python 3.12; el
  proyecto (Python 3.14) no se toca. El código es compatible con 3.12.
- `--profile-exclude threading`: sin esto, Scalene reporta un 66,7% en
  `threading.py` (un hilo que no es del programa; no se investigó cuál) y los porcentajes del
  programa quedan divididos por 3.
- `--cpu` para el baseline: con la memoria activada, el costo extra de medirla
  deforma el reparto (53% / 43%); para la pregunta "¿qué línea gasta CPU?" se
  usa solo CPU.

## Resultado principal: baseline, grid V=2.500, 20 consultas

| Fase del baseline | Líneas | Scalene (3 corridas) | py-spy | Cronómetros a mano (parte 1) |
|---|---|---|---|---|
| (b) barrido de la lista de aristas | 59–65 | **66,0–67,4%** | 63,0% | 65,9% |
| (a) mínimo por barrido lineal | 45–46 | **31,5–33,2%** | 35,1% | 34,1% |

Tres herramientas independientes llegan al mismo reparto, sin tocar el código.

## Procesar un archivo de 20.000 consultas (secuencial)

| Dónde | Scalene | py-spy |
|---|---|---|
| `astar` (búsqueda) | 59% | 96,6% en el cálculo |
| `Graph.heuristic` + `Graph.euclid` (heurística de A*) | 37% | (incluido arriba) |
| `archivos.py` (leer y escribir el CSV) | 0,75% | ~2,5% |

Pico de memoria: **10 MB**, independiente del tamaño del archivo (lectura por lotes).

Hallazgo nuevo que no se veía en la parte 1: **la heurística de A* sola se
lleva más de un tercio del tiempo**. Es una llamada a método más `math.hypot`
por cada vecino que se encola. Sería el próximo candidato a optimizar (por
ejemplo, precalcular las coordenadas del destino o hacer la cuenta en línea).

## Por qué no se usó Scalene 2.3.0

Scalene 2.3.0 (la última versión) **no atribuye bien el tiempo por línea**,
ni en Python 3.14 ni en 3.12:

- con `--profile-only src` mide 13,9 s pero asigna 0% a `src/`, y carga todo
  el tiempo a la línea que llama a `dijkstra_naive`;
- con `--profile-all` reparte el tiempo de forma inconsistente (por ejemplo,
  5,8% en `on_expand(u)`, una línea que en esta carga nunca se ejecuta).

La versión 1.5.51 sobre Python 3.12 sí funciona y coincide con py-spy y con la
medición manual. Lección: un perfilador también puede equivocarse; hay que
contrastarlo con algo conocido.
