# PR #12 — Memoria

- **PR:** https://github.com/JuaniBattiston/pef/pull/12 (`demo/memoria`)
- **Criterio de rechazo (consigna 3.1):** Se supera un límite justificado y medido en condiciones reproducibles
- **Job que debía fallar:** `6 · rendimiento (benchmark, memoria, profiling)` — ❌ falló
- **Estado de integración en GitHub:** `BLOCKED` (BLOCKED = la protección de `main` impide integrarlo)
- **Corrida:** https://github.com/JuaniBattiston/pef/actions/runs/42117915974/job/127563967148

## Jobs del pipeline

| Job | Resultado |
| --- | --- |
| 2 · entorno reproducible | ✅ aprobado |
| 3 · complejidad (radon, xenon) | ✅ aprobado |
| 3 · lint (ruff, pylint) | ✅ aprobado |
| 3 · secretos (gitleaks) | ✅ aprobado |
| 3 · seguridad del codigo (bandit) | ✅ aprobado |
| 3 · tipado (mypy) | ✅ aprobado |
| 4 · pruebas y cobertura (py3.12) | ✅ aprobado |
| 4 · pruebas y cobertura (py3.14) | ✅ aprobado |
| 5 · dependencias (pip-audit) | ✅ aprobado |
| 5 · documentacion (mkdocs, markdownlint, lychee) | ✅ aprobado |
| 6 · rendimiento (benchmark, memoria, profiling) | ❌ rechazado |
| 7 · resultado | ❌ rechazado |

## Extracto del log del job que falló

```text
escenario            pico MiB  limite MiB    uso  estado
grafo_grid               7.36        9.57    77%  OK
dijkstra_heap            0.89        1.16    77%  OK
cache_32                17.45       16.54   106%  EXCEDE
archivo_lotes            2.69        3.50    77%  OK
archivo_ingenuo         13.49       17.54    77%  OK
RECHAZADO: se supero el limite de memoria en cache_32
```
