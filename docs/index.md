# Planificador inteligente de rutas

Aplicación en Python que encuentra rutas óptimas sobre una red de puntos de entrega.
Se construyó como **banco de mediciones** de técnicas de programación eficiente: cada
optimización es una variante que se puede activar por separado, para atribuir cada
mejora a una sola causa.

Este sitio es la documentación externa del proyecto. Reúne la información funcional,
técnica y operativa en un solo lugar, versionada en Git junto con el código.

## Problema que resuelve

Un despachante recibe lotes de consultas *origen → destino* sobre una red de reparto y
tiene que responder el camino de menor costo para cada una. El problema combina cuatro
presiones de rendimiento distintas:

| Presión | Consecuencia | Técnica aplicada |
| --- | --- | --- |
| Redes grandes (decenas de miles de nodos) | los algoritmos ingenuos explotan | Dijkstra con heap, A\* |
| Muchas consultas por lote | conviene repartirlas | paralelismo con procesos |
| Pocos orígenes, muchos destinos | se repite trabajo | memoización de árboles + caché LRU |
| El mapa cambia (cortes de calle) | lo cacheado puede quedar obsoleto | invalidación por versión del grafo |

## Alcance

**Incluye:**

- Representación de la red como grafo con lista de adyacencia y cuatro familias de
  grafos sintéticos (`grid`, `highway`, `dense`, `unweighted`).
- El mapa **real** de calles de Córdoba (OpenStreetMap, 8.288 intersecciones).
- Cuatro algoritmos de camino mínimo: Dijkstra ingenuo (línea base), Dijkstra con heap,
  A\* y BFS.
- Caché de árboles de caminos mínimos con desalojo LRU e invalidación.
- Resolución de lotes en modo secuencial, con hilos y con procesos.
- Procesamiento de archivos CSV grandes por lotes, con buffer y en paralelo.
- Una CLI de demostración y un visualizador web (FastAPI) sobre el mapa de Córdoba.
- Benchmarks, perfilado y un pipeline de CI con controles de calidad y eficiencia.

**No incluye:** ruteo con restricciones (ventanas horarias, capacidad de vehículos),
tráfico en tiempo real ni persistencia en base de datos.

## Requisitos

### Funcionales

| ID | Requisito | Dónde se cumple |
| --- | --- | --- |
| RF1 | Calcular el camino mínimo entre dos nodos y su costo | `src/algorithms/` |
| RF2 | Comparar algoritmos sobre la misma consulta | `python -m src.cli comparar` |
| RF3 | Resolver lotes de consultas, opcionalmente en paralelo | `src/parallel.py` |
| RF4 | Reutilizar resultados sin devolver rutas obsoletas tras un cambio del mapa | `src/cache.py` |
| RF5 | Procesar archivos de consultas más grandes que la memoria disponible | `src/archivos.py` |
| RF6 | Visualizar la búsqueda sobre un mapa real | `viz/` |

### No funcionales

| ID | Requisito | Cómo se verifica |
| --- | --- | --- |
| RNF1 | Las rutas son óptimas (mismo costo que un oráculo Bellman-Ford) | [Pruebas](pruebas.md) |
| RNF2 | Una consulta sobre 10.000 nodos se resuelve en milisegundos | [Benchmark del CI](rendimiento.md#benchmark-del-ci) |
| RNF3 | La memoria del procesamiento de archivos es acotada | [Control de memoria](rendimiento.md#control-de-memoria) |
| RNF4 | El núcleo (`src/`) no tiene dependencias externas | `requirements.in` |
| RNF5 | Ningún cambio se integra si incumple los controles de calidad | [Integración continua](ci.md) |

## Mapa de la documentación

| Sección | Contenido |
| --- | --- |
| [Arquitectura](arquitectura-vieja.md) | módulos, responsabilidades, dependencias y diagrama de componentes |
| [Instalación y ejecución](instalacion.md) | dependencias, configuración y comandos |
| [Diseño técnico](diseno-tecnico.md) | estructuras de datos, algoritmos y decisiones de implementación |
| [API y contratos](api.md) | CLI, API HTTP y API de Python: entradas, salidas, excepciones |
| [Pruebas](pruebas.md) | estrategia, casos de prueba y resultados |
| [Rendimiento](rendimiento.md) | benchmarks, profiling, complejidad y memoria |
| [Seguridad](seguridad.md) | riesgos, dependencias, política de bloqueo y excepciones |
| [Integración continua](ci.md) | etapas del pipeline y matriz de controles |
| [Mantenimiento](mantenimiento.md) | cómo contribuir, correr los controles en local y resolver fallos |
