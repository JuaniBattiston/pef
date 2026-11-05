# Resultados de la parte 3: evidencia de los controles del CI

Este directorio prueba que **cada control del pipeline rechaza un cambio que lo
incumple** y que **la protección de `main` impide integrarlo**.

- Documentación externa: <https://juanibattiston.github.io/pef/>
- Pipeline: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml); diseño en
  [docs/ci.md](../docs/ci.md)
- Todos los controles corren en local con `make ci`
  ([docs/mantenimiento.md](../docs/mantenimiento.md))

## Método

Por cada control se abrió un *pull request* desde `main` con **una sola ruptura chica**
que incumple ese control y ningún otro. Antes de abrirlos, cada ruptura se probó en
local con los mismos targets del `Makefile`. Los PRs se cerraron sin integrar después
de juntar la evidencia. Las corridas siguen disponibles en GitHub Actions.

## Resultado: 11 de 11 controles rechazan

| PR | Control | Ruptura | Job que falló | Motivo del rechazo (del log) | Integración |
| --- | --- | --- | --- | --- | --- |
| [#2](https://github.com/JuaniBattiston/pef/pull/2) | Pruebas | Dijkstra suma el 90 % del peso de cada arista | [4 · pruebas](https://github.com/JuaniBattiston/pef/actions/runs/42117804971/job/127563181145) | `10 failed, 66 passed`: los costos no coinciden con el oráculo | BLOCKED |
| [#3](https://github.com/JuaniBattiston/pef/pull/3) | Cobertura | se borra `tests/test_cli.py` | [4 · pruebas](https://github.com/JuaniBattiston/pef/actions/runs/42117814807/job/127562736163) | `Total coverage: 77.85%` < 90 % | BLOCKED |
| [#4](https://github.com/JuaniBattiston/pef/pull/4) | Análisis estático | import sin usar | [3 · lint](https://github.com/JuaniBattiston/pef/actions/runs/42117830244/job/127562496807) | Ruff `F401 'os' imported but unused` | BLOCKED |
| [#5](https://github.com/JuaniBattiston/pef/pull/5) | Tipado | anotación `int` sobre un valor `float` | [3 · tipado](https://github.com/JuaniBattiston/pef/actions/runs/42117840090/job/127562334811) | mypy `Incompatible return value type` | BLOCKED |
| [#6](https://github.com/JuaniBattiston/pef/pull/6) | Complejidad | función con 22 ramas | [3 · complejidad](https://github.com/JuaniBattiston/pef/actions/runs/42117853132/job/127562426800) | Xenon `clasificar has a rank of D` (límite: C) | BLOCKED |
| [#7](https://github.com/JuaniBattiston/pef/pull/7) | Seguridad (código) | `subprocess.call(..., shell=True)` | [3 · seguridad del código](https://github.com/JuaniBattiston/pef/actions/runs/42117865175/job/127562451416) | Bandit `B602`, severidad alta, confianza alta | BLOCKED |
| [#8](https://github.com/JuaniBattiston/pef/pull/8) | Seguridad (secretos) | API key falsa en un `.env` | [3 · secretos](https://github.com/JuaniBattiston/pef/actions/runs/42117880350/job/127562811954) | gitleaks `generic-api-key`, `leaks found: 1` | BLOCKED |
| [#9](https://github.com/JuaniBattiston/pef/pull/9) | Seguridad (dependencias) | `urllib3` 2.8.0 → 2.4.0 | [5 · dependencias](https://github.com/JuaniBattiston/pef/actions/runs/42117925922/job/127563565914) | pip-audit `Found 14 known vulnerabilities in 1 package` | BLOCKED |
| [#10](https://github.com/JuaniBattiston/pef/pull/10) | Documentación | enlace interno roto | [5 · documentación](https://github.com/JuaniBattiston/pef/actions/runs/42117892072/job/127563345374) | MkDocs `Aborted with 1 warnings in strict mode` | BLOCKED |
| [#11](https://github.com/JuaniBattiston/pef/pull/11) | Benchmark | trabajo extra en el bucle de Dijkstra | [6 · rendimiento](https://github.com/JuaniBattiston/pef/actions/runs/42117913067/job/127563959230) | mediana de `test_ruta_grid[heap]` +168 % (6,1 → 16,4 ms) > 25 % | BLOCKED |
| [#12](https://github.com/JuaniBattiston/pef/pull/12) | Memoria | la caché retiene una copia de cada árbol | [6 · rendimiento](https://github.com/JuaniBattiston/pef/actions/runs/42117915974/job/127563967148) | `cache_32` 17,45 MiB > límite 16,54 MiB (106 %) | BLOCKED |

En los 11 casos falló **solo** el control buscado. En #2 y #3 falla el mismo job en las
dos versiones de Python de la matriz. Los jobs posteriores al que falla aparecen como
*skipped*, porque dependen de él. `BLOCKED` es el estado que reporta GitHub: la regla de
`main` exige el check **"7 · resultado"** en verde.

Detalle de cada caso (tabla de jobs y extracto del log): [`evidencia/`](evidencia/).

## Push directo a `main`: rechazado

Con la protección activa también para administradores
([evidencia/00-push-directo-main.txt](evidencia/00-push-directo-main.txt)):

```text
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: - Changes must be made through a pull request.
remote: - Required status check "7 · resultado" is expected.
 ! [remote rejected] main -> main (protected branch hook declined)
```

## Fallos reales que encontró el pipeline

Además de las rupturas armadas a propósito, el pipeline frenó dos problemas reales del
propio trabajo:

1. **Instalación de lychee rota** ([PR #1](https://github.com/JuaniBattiston/pef/pull/1),
   [corrida](https://github.com/JuaniBattiston/pef/actions/runs/42114127455)). El
   binario venía dentro de una carpeta del `.tar.gz` y el job `5 · documentacion`
   falló. El PR quedó bloqueado hasta corregirlo. En local no aparecía porque `make
   docs` usaba el contenedor de lychee.
2. **Alcance de gitleaks** ([PR #13](https://github.com/JuaniBattiston/pef/pull/13)). Con
   la rama `demo/secretos` en el repo, el control de secretos falló en *todos* los PRs:
   el checkout trae todas las ramas y gitleaks escanea `--all` por defecto. Era un falso
   positivo de configuración. Se corrigió para escanear el historial del commit que se
   integra (`--log-opts="--full-history HEAD"`), y los 11 PRs se volvieron a correr.
   El *secret scanning* de GitHub sigue cubriendo todas las ramas.

También apareció un problema al armar la evidencia: la primera versión de la ruptura de
dependencias (`urllib3` 1.26.4) no funciona en Python 3.14 y rompía otros jobs. Se
reemplazó por la 2.4.0, compatible y vulnerable, para que fallara solo pip-audit.
