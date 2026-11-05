# PR #11 — Benchmark

- **PR:** https://github.com/JuaniBattiston/pef/pull/11 (`demo/benchmark`)
- **Criterio de rechazo (consigna 3.1):** Se detecta una regresión significativa respecto de una línea base confiable
- **Job que debía fallar:** `6 · rendimiento (benchmark, memoria, profiling)` — ❌ falló
- **Estado de integración en GitHub:** `BLOCKED` (BLOCKED = la protección de `main` impide integrarlo)
- **Corrida:** https://github.com/JuaniBattiston/pef/actions/runs/42117913067/job/127563959230

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
Performance has regressed:
	test_ruta_grid[heap] (0001_base) - Field 'median' has failed PercentageRegressionCheck: 168.243999947 > 25.000000000
    raise PerformanceRegression('Performance has regressed.')
pytest_benchmark.session.PerformanceRegression: Performance has regressed.
Name (time in ms)                              Min             Median               IQR            Rounds
test_ruta_grid[heap] (0001_base)            5.6983 (741.77)    6.1161 (768.16)   0.2737 (>1000.0)     108
test_ruta_grid[heap] (NOW)                 15.6443 (>1000.0)  16.4059 (>1000.0)  0.6822 (>1000.0)      58
```
