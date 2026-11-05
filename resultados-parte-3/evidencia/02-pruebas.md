# PR #2 — Pruebas

- **PR:** https://github.com/JuaniBattiston/pef/pull/2 (`demo/pruebas`)
- **Criterio de rechazo (consigna 3.1):** Una o más pruebas fallan
- **Job que debía fallar:** `4 · pruebas y cobertura (py3.12)` — ❌ falló
- **Estado de integración en GitHub:** `BLOCKED` (BLOCKED = la protección de `main` impide integrarlo)
- **Corrida:** https://github.com/JuaniBattiston/pef/actions/runs/42117804971/job/127563181145

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
E           assert 11.03049057585742 == 9.92744151827168 ± 9.9e-06
E           assert 21.62705351316497 == 19.464348161848473 ± 1.9e-05
E           assert 11.0 == 9.900000000000002 ± 9.9e-06
        assert g.n > 1000
        assert 0 < g.heuristic_scale <= 1.0
            assert g.euclid(u, v) * g.heuristic_scale <= w + EPS
>           assert astar(g, s, t).cost == pytest.approx(dijkstra_heap(g, s, t).cost)
E           assert 2011.89 == 1810.7009999999998 ± 0.0018107
tests/test_algoritmos.py:97: AssertionError
>       assert r["costo"] == pytest.approx(esperado)
E       assert 4131.377999999999 == 4590.419999999998 ± 0.00459042
E         comparison failed
tests/test_server.py:33: AssertionError
FAILED tests/test_algoritmos.py::test_costs_match_reference[dense-heap] - assert 10.109383222539677 == 11.232648025044085 ± 1.1e-05
  comparison failed
FAILED tests/test_algoritmos.py::test_costs_match_reference[grid-heap] - assert 9.92744151827168 == 11.03049057585742 ± 1.1e-05
FAILED tests/test_algoritmos.py::test_costs_match_reference[highway-heap] - assert 19.464348161848473 == 21.62705351316497 ± 2.2e-05
FAILED tests/test_algoritmos.py::test_costs_match_reference[unweighted-heap] - assert 9.900000000000002 == 11.0 ± 1.1e-05
FAILED tests/test_algoritmos.py::test_path_is_valid_and_consistent[dense-heap] - assert 11.232648025044085 == 10.109383222539677 ± 1.0e-05
FAILED tests/test_algoritmos.py::test_path_is_valid_and_consistent[grid-heap] - assert 11.03049057585742 == 9.92744151827168 ± 9.9e-06
FAILED tests/test_algoritmos.py::test_path_is_valid_and_consistent[highway-heap] - assert 21.62705351316497 == 19.464348161848473 ± 1.9e-05
FAILED tests/test_algoritmos.py::test_path_is_valid_and_consistent[unweighted-heap] - assert 11.0 == 9.900000000000002 ± 9.9e-06
FAILED tests/test_algoritmos.py::test_mapa_real_cordoba - assert 2011.89 == 1810.7009999999998 ± 0.0018107
FAILED tests/test_server.py::test_ruta_optima[heap] - assert 4131.377999999999 == 4590.419999999998 ± 0.00459042
10 failed, 66 passed, 8 warnings in 4.03s
```
