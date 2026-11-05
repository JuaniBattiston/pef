# PR #9 — Seguridad (dependencias)

- **PR:** https://github.com/JuaniBattiston/pef/pull/9 (`demo/dependencias`)
- **Criterio de rechazo (consigna 3.1):** Se detecta una vulnerabilidad que supera el umbral de rechazo
- **Job que debía fallar:** `5 · dependencias (pip-audit)` — ❌ falló
- **Estado de integración en GitHub:** `BLOCKED` (BLOCKED = la protección de `main` impide integrarlo)
- **Corrida:** https://github.com/JuaniBattiston/pef/actions/runs/42117925922/job/127563565914

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
| 5 · dependencias (pip-audit) | ❌ rechazado |
| 5 · documentacion (mkdocs, markdownlint, lychee) | ✅ aprobado |
| 6 · rendimiento (benchmark, memoria, profiling) | ⏭️ no corrió |
| 7 · resultado | ❌ rechazado |

## Extracto del log del job que falló

```text
Found 14 known vulnerabilities in 1 package
[urllib3](https://pypi.org/project/urllib3/) | 2.4.0 | [PYSEC-2026-1997](https://osv.dev/vulnerability/PYSEC-2026-1997) | 2.5.0 | urllib3 [supports](https://urllib3.re...
[urllib3](https://pypi.org/project/urllib3/) | 2.4.0 | [PYSEC-2026-1999](https://osv.dev/vulnerability/PYSEC-2026-1999) | 2.5.0 | urllib3 handles redirects and retries...
[urllib3](https://pypi.org/project/urllib3/) | 2.4.0 | [PYSEC-2026-1998](https://osv.dev/vulnerability/PYSEC-2026-1998) | 2.6.0 | ## Impact  urllib3 supports chained H...
[urllib3](https://pypi.org/project/urllib3/) | 2.4.0 | [PYSEC-2026-1994](https://osv.dev/vulnerability/PYSEC-2026-1994) | 2.6.0 | ### Impact  urllib3's [streaming API]...
[urllib3](https://pypi.org/project/urllib3/) | 2.4.0 | [PYSEC-2026-1996](https://osv.dev/vulnerability/PYSEC-2026-1996) | 2.6.3 | ### Impact  urllib3's [streaming API]...
[urllib3](https://pypi.org/project/urllib3/) | 2.4.0 | [PYSEC-2026-141](https://osv.dev/vulnerability/PYSEC-2026-141) | 2.7.0 | ### Impact  When following cross-origin...
[urllib3](https://pypi.org/project/urllib3/) | 2.4.0 | [PYSEC-2026-141](https://osv.dev/vulnerability/PYSEC-2026-141) | 2.7.0 | urllib3 is an HTTP client library for P...
[urllib3](https://pypi.org/project/urllib3/) | 2.4.0 | [PYSEC-2026-4177](https://osv.dev/vulnerability/PYSEC-2026-4177) | 2.8.0 | ## Impact  urllib3's [streaming API](...
[urllib3](https://pypi.org/project/urllib3/) | 2.4.0 | [PYSEC-2026-4175](https://osv.dev/vulnerability/PYSEC-2026-4175) | 2.8.0 | ## Impact  urllib3 supports configuri...
```
