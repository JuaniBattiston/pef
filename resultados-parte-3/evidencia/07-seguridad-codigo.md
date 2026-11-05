# PR #7 — Seguridad (código)

- **PR:** https://github.com/JuaniBattiston/pef/pull/7 (`demo/seguridad-codigo`)
- **Criterio de rechazo (consigna 3.1):** Se detecta una vulnerabilidad que supera el umbral de rechazo
- **Job que debía fallar:** `3 · seguridad del codigo (bandit)` — ❌ falló
- **Estado de integración en GitHub:** `BLOCKED` (BLOCKED = la protección de `main` impide integrarlo)
- **Corrida:** https://github.com/JuaniBattiston/pef/actions/runs/42117865175/job/127562451416

## Jobs del pipeline

| Job | Resultado |
| --- | --- |
| 2 · entorno reproducible | ✅ aprobado |
| 3 · complejidad (radon, xenon) | ✅ aprobado |
| 3 · lint (ruff, pylint) | ✅ aprobado |
| 3 · secretos (gitleaks) | ✅ aprobado |
| 3 · seguridad del codigo (bandit) | ❌ rechazado |
| 3 · tipado (mypy) | ✅ aprobado |
| 4 · pruebas y cobertura (py${{ matrix.python }}) | ⏭️ no corrió |
| 5 · dependencias (pip-audit) | ⏭️ no corrió |
| 5 · documentacion (mkdocs, markdownlint, lychee) | ⏭️ no corrió |
| 6 · rendimiento (benchmark, memoria, profiling) | ⏭️ no corrió |
| 7 · resultado | ❌ rechazado |

## Extracto del log del job que falló

```text
  pythonLocation: /opt/hostedtoolcache/Python/3.14.10/x64
>> Issue: [B602:subprocess_popen_with_shell_equals_true] subprocess call with shell=True identified, security issue.
   Severity: High   Confidence: High
   Location: src/timing.py:19:11
19	    return subprocess.call(comando, shell=True)
```
