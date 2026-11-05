# PR #6 — Complejidad

- **PR:** https://github.com/JuaniBattiston/pef/pull/6 (`demo/complejidad`)
- **Criterio de rechazo (consigna 3.1):** Se supera un límite de complejidad establecido
- **Job que debía fallar:** `3 · complejidad (radon, xenon)` — ❌ falló
- **Estado de integración en GitHub:** `BLOCKED` (BLOCKED = la protección de `main` impide integrarlo)
- **Corrida:** https://github.com/JuaniBattiston/pef/actions/runs/42117853132/job/127562426800

## Jobs del pipeline

| Job | Resultado |
| --- | --- |
| 2 · entorno reproducible | ✅ aprobado |
| 3 · complejidad (radon, xenon) | ❌ rechazado |
| 3 · lint (ruff, pylint) | ✅ aprobado |
| 3 · secretos (gitleaks) | ✅ aprobado |
| 3 · seguridad del codigo (bandit) | ✅ aprobado |
| 3 · tipado (mypy) | ✅ aprobado |
| 4 · pruebas y cobertura (py${{ matrix.python }}) | ⏭️ no corrió |
| 5 · dependencias (pip-audit) | ⏭️ no corrió |
| 5 · documentacion (mkdocs, markdownlint, lychee) | ⏭️ no corrió |
| 6 · rendimiento (benchmark, memoria, profiling) | ⏭️ no corrió |
| 7 · resultado | ❌ rechazado |

## Extracto del log del job que falló

```text
ERROR:xenon:block "src/timing.py:16 clasificar" has a rank of D
```
