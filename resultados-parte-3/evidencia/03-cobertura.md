# PR #3 — Cobertura

- **PR:** https://github.com/JuaniBattiston/pef/pull/3 (`demo/cobertura`)
- **Criterio de rechazo (consigna 3.1):** Se encuentra por debajo del umbral definido
- **Job que debía fallar:** `4 · pruebas y cobertura (py3.12)` — ❌ falló
- **Estado de integración en GitHub:** `BLOCKED` (BLOCKED = la protección de `main` impide integrarlo)
- **Corrida:** https://github.com/JuaniBattiston/pef/actions/runs/42117814807/job/127562736163

## Jobs del pipeline

| Job | Resultado |
| --- | --- |
| 2 · entorno reproducible | ✅ aprobado |
| 3 · complejidad (radon, xenon) | ✅ aprobado |
| 3 · lint (ruff, pylint) | ✅ aprobado |
| 3 · secretos (gitleaks) | ✅ aprobado |
| 3 · seguridad del codigo (bandit) | ✅ aprobado |
| 3 · tipado (mypy) | ✅ aprobado |
| 4 · pruebas y cobertura (py3.12) | ❌ rechazado |
| 4 · pruebas y cobertura (py3.14) | ❌ rechazado |
| 5 · dependencias (pip-audit) | ⏭️ no corrió |
| 5 · documentacion (mkdocs, markdownlint, lychee) | ⏭️ no corrió |
| 6 · rendimiento (benchmark, memoria, profiling) | ⏭️ no corrió |
| 7 · resultado | ❌ rechazado |

## Extracto del log del job que falló

```text
ERROR: Coverage failure: total of 78 is less than fail-under=90
TOTAL                                623    138    78%
FAIL Required test coverage of 90% not reached. Total coverage: 77.85%
```
