# PR #5 — Tipado

- **PR:** https://github.com/JuaniBattiston/pef/pull/5 (`demo/tipado`)
- **Criterio de rechazo (consigna 3.1):** Existen errores que la política considera bloqueantes
- **Job que debía fallar:** `3 · tipado (mypy)` — ❌ falló
- **Estado de integración en GitHub:** `BLOCKED` (BLOCKED = la protección de `main` impide integrarlo)
- **Corrida:** https://github.com/JuaniBattiston/pef/actions/runs/42117840090/job/127562334811

## Jobs del pipeline

| Job | Resultado |
| --- | --- |
| 2 · entorno reproducible | ✅ aprobado |
| 3 · complejidad (radon, xenon) | ✅ aprobado |
| 3 · lint (ruff, pylint) | ✅ aprobado |
| 3 · secretos (gitleaks) | ✅ aprobado |
| 3 · seguridad del codigo (bandit) | ✅ aprobado |
| 3 · tipado (mypy) | ❌ rechazado |
| 4 · pruebas y cobertura (py${{ matrix.python }}) | ⏭️ no corrió |
| 5 · dependencias (pip-audit) | ⏭️ no corrió |
| 5 · documentacion (mkdocs, markdownlint, lychee) | ⏭️ no corrió |
| 6 · rendimiento (benchmark, memoria, profiling) | ⏭️ no corrió |
| 7 · resultado | ❌ rechazado |

## Extracto del log del job que falló

```text
src/timing.py:13: error: Incompatible return value type (got "tuple[T, float]", expected "tuple[T, int]")  [return-value]
Found 1 error in 1 file (checked 14 source files)
```
