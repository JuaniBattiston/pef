# PR #4 — Análisis estático

- **PR:** https://github.com/JuaniBattiston/pef/pull/4 (`demo/lint`)
- **Criterio de rechazo (consigna 3.1):** Existen errores bloqueantes según la configuración
- **Job que debía fallar:** `3 · lint (ruff, pylint)` — ❌ falló
- **Estado de integración en GitHub:** `BLOCKED` (BLOCKED = la protección de `main` impide integrarlo)
- **Corrida:** https://github.com/JuaniBattiston/pef/actions/runs/42117830244/job/127562496807

## Jobs del pipeline

| Job | Resultado |
| --- | --- |
| 2 · entorno reproducible | ✅ aprobado |
| 3 · complejidad (radon, xenon) | ✅ aprobado |
| 3 · lint (ruff, pylint) | ❌ rechazado |
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
F401 [*] `os` imported but unused
 --> src/timing.py:5:8
Found 1 error.
```
