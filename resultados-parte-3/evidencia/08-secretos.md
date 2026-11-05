# PR #8 — Seguridad (secretos)

- **PR:** https://github.com/JuaniBattiston/pef/pull/8 (`demo/secretos`)
- **Criterio de rechazo (consigna 3.1):** Se detecta una vulnerabilidad que supera el umbral de rechazo
- **Job que debía fallar:** `3 · secretos (gitleaks)` — ❌ falló
- **Estado de integración en GitHub:** `BLOCKED` (BLOCKED = la protección de `main` impide integrarlo)
- **Corrida:** https://github.com/JuaniBattiston/pef/actions/runs/42117880350/job/127562811954

## Jobs del pipeline

| Job | Resultado |
| --- | --- |
| 2 · entorno reproducible | ✅ aprobado |
| 3 · complejidad (radon, xenon) | ✅ aprobado |
| 3 · lint (ruff, pylint) | ✅ aprobado |
| 3 · secretos (gitleaks) | ❌ rechazado |
| 3 · seguridad del codigo (bandit) | ✅ aprobado |
| 3 · tipado (mypy) | ✅ aprobado |
| 4 · pruebas y cobertura (py${{ matrix.python }}) | ⏭️ no corrió |
| 5 · dependencias (pip-audit) | ⏭️ no corrió |
| 5 · documentacion (mkdocs, markdownlint, lychee) | ⏭️ no corrió |
| 6 · rendimiento (benchmark, memoria, profiling) | ⏭️ no corrió |
| 7 · resultado | ❌ rechazado |

## Extracto del log del job que falló

```text
Finding:     api_key = "REDACTED"
RuleID:      generic-api-key
File:        demo_credenciales.env
10:02PM WRN leaks found: 1
```
