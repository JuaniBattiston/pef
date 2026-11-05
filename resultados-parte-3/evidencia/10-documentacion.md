# PR #10 — Documentación

- **PR:** https://github.com/JuaniBattiston/pef/pull/10 (`demo/documentacion`)
- **Criterio de rechazo (consigna 3.1):** No se puede generar correctamente o falla una validación obligatoria
- **Job que debía fallar:** `5 · documentacion (mkdocs, markdownlint, lychee)` — ❌ falló
- **Estado de integración en GitHub:** `BLOCKED` (BLOCKED = la protección de `main` impide integrarlo)
- **Corrida:** https://github.com/JuaniBattiston/pef/actions/runs/42117892072/job/127563345374

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
| 5 · documentacion (mkdocs, markdownlint, lychee) | ❌ rechazado |
| 6 · rendimiento (benchmark, memoria, profiling) | ⏭️ no corrió |
| 7 · resultado | ❌ rechazado |

## Extracto del log del job que falló

```text
  To disable this warning, set NO_MKDOCS_2_WARNING=1.
WARNING -  Doc file 'index.md' contains a link 'arquitectura-vieja.md', but the target is not found among documentation files.
Aborted with 1 warnings in strict mode!
```
