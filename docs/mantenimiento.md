# Mantenimiento

## Cómo contribuir

`main` está protegida: no se puede hacer push directo. Todo cambio entra por *pull
request* con el pipeline aprobado.

```bash
git switch main && git pull
git switch -c mi-cambio          # una rama por cambio
# ... editar ...
make ci                          # los mismos controles que el CI
git commit -am "Descripción del cambio"
git push -u origin mi-cambio
gh pr create --fill              # o desde la web
```

Reglas:

- El PR tiene que estar actualizado con `main` y tener el check **"7 · resultado"** en
  verde.
- Las conversaciones abiertas en el PR deben estar resueltas antes de integrar.
- Si un cambio empeora el rendimiento o la memoria a propósito, se explica en el PR y se
  actualiza la línea base o el límite ([ver abajo](#cambiar-una-linea-base-o-un-limite)).
- Si se agrega una excepción de seguridad, se registra en [Seguridad](seguridad.md#falsos-positivos-y-excepciones).
- Los docstrings siguen el estilo Google: la [API](api.md) se genera desde ellos.

## Ejecutar los controles en local

Requisito adicional de la consigna: **los mismos controles del CI corren en local con
el mismo comando**, porque el CI llama a los mismos targets del `Makefile`.

| Control (job del CI) | Comando local | Reportes en `reports/` |
| --- | --- | --- |
| Todo el pipeline | `make ci` | todos |
| `2 · entorno` | `make setup` | — |
| `3 · lint` | `make lint` | `ruff.sarif`, `pylint.txt` |
| `3 · tipado` | `make types` | `mypy.txt` |
| `3 · complejidad` | `make complexity` | `radon_cc.txt`, `radon_mi.txt` |
| `3 · seguridad del codigo` | `make sec-code` | `bandit.txt`, `bandit.sarif`, `bandit_nosec.txt` |
| `3 · secretos` | `make secrets` | `gitleaks.sarif` |
| `4 · pruebas y cobertura` | `make test` | `junit.xml`, `coverage.xml`, `htmlcov/index.html` |
| `5 · dependencias` | `make sec-deps` | `pip-audit.md`, `pip-audit.json` |
| `5 · documentacion` | `make docs` | `site/`, `lychee.md` |
| `6 · rendimiento` | `make bench-baseline && make bench && make memory && make profile` | `bench.json`, `memory.json`, `profile.html` |

- Los umbrales se pueden ajustar para una prueba puntual sin editar nada:
  `make test COV_MIN=95`, `make bench BENCH_REGRESION=10`.
- `make secrets` y `make docs` usan `gitleaks` y `lychee` si están instalados. Si no,
  los corren con Podman o Docker, en la misma versión que el CI.
- `make clean` borra reportes y cachés.

## Resolver fallos del pipeline

Primero, identificar el job en rojo en la tabla de **"7 · resultado"** y bajar sus
reportes de la sección *Artifacts* de la corrida. Después, reproducirlo en local:

| Job en rojo | Reproducir | Causas típicas y solución |
| --- | --- | --- |
| `2 · entorno` | `make setup` | **Hash que no coincide** o paquete sin hash: se editó un `.in` sin regenerar el lock → `make lock`. Conflicto de versiones: revisar `pip check` |
| `3 · lint` | `make lint` | Formato: `ruff format .`. Errores autocorregibles: `ruff check --fix .`. Pylint bajo 9,5: ver `reports/pylint.txt` |
| `3 · tipado` | `make types` | Función sin anotar o tipos incompatibles. Anotar con los tipos reales; evitar `# type: ignore` salvo justificación |
| `3 · complejidad` | `make complexity` | Una función superó CC 20: ver `reports/radon_cc.txt` y dividirla en funciones más chicas |
| `3 · seguridad del codigo` | `make sec-code` | Ver `reports/bandit.txt`. Corregir el código o, si es falso positivo, seguir el [procedimiento de excepciones](seguridad.md#falsos-positivos-y-excepciones) |
| `3 · secretos` | `make secrets` | **Revocar el secreto primero.** Después quitarlo; si ya se publicó, reescribir el historial. Falso positivo: agregarlo a un `.gitleaksignore` con motivo |
| `4 · pruebas y cobertura` | `make test` | Prueba en rojo: `pytest -x -k <nombre>`. Cobertura baja: abrir `reports/htmlcov/index.html` y agregar pruebas para las líneas nuevas. Falla en 3.12 y no en 3.14: sintaxis o API nueva |
| `5 · dependencias` | `make sec-deps` | Vulnerabilidad: subir la versión (`make lock`) o aceptar el PR de Dependabot. Sin corrección disponible: ver [Seguridad](seguridad.md#medidas-correctivas) |
| `5 · documentacion` | `make docs` | Advertencia de MkDocs: enlace interno roto, página fuera del `nav` o docstring inválido. Estilo: ver la salida de markdownlint. Enlace externo caído: corregirlo o, si es temporal, reintentar la corrida |
| `6 · rendimiento` (bench) | `make bench-baseline && make bench` | Regresión de mediana > 25 %: la tabla compara `0001_base` contra `NOW`. Ver `reports/profile.html` para ubicar la causa. Si la regresión es intencional, justificarla en el PR |
| `6 · rendimiento` (memoria) | `make memory` | Un escenario superó su límite: revisar qué estructura nueva se retiene. Si el aumento es justificado, regenerar los límites |
| `7 · resultado` | — | No falla por sí mismo: refleja el fallo de algún job anterior |

## Cambiar una línea base o un límite

Algunos cambios empeoran una medición de forma justificada (por ejemplo, guardar más
información por consulta).

- **Memoria:** `python -m bench.check_memory --update` vuelve a medir y reescribe
  `bench/memory_limits.json` (medido +30 %). Se commitea con el motivo en el PR.
- **Benchmark:** la línea base es siempre la rama destino, así que no se edita. Una
  regresión aceptada queda como nueva base cuando el PR se integra. Para integrarla hay
  que justificarla y, de forma excepcional, subir `BENCH_REGRESION` en ese PR.

## Actualizar dependencias

```bash
# editar requirements.in (ejecución) o requirements-dev.in (desarrollo)
make lock        # regenera requirements*.txt con versiones exactas y hashes (requiere uv)
make setup       # reinstala
make ci
```

Dependabot abre PRs semanales (los lunes) para paquetes de Python y para las actions de
GitHub. Espera al menos 7 días desde cada publicación antes de proponerla (`cooldown`).
Los PRs de Dependabot pasan por el mismo pipeline que cualquier otro cambio.

## Actualizar la documentación

La documentación vive en `docs/` y se publica sola en GitHub Pages cuando un cambio
llega a `main`. Para editarla:

```bash
mkdocs serve     # vista previa con recarga automática
make docs        # validación completa antes del PR
```

Cada página tiene un enlace *editar* que abre el archivo en GitHub.
