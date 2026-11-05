# Seguridad

## Riesgos identificados

| Riesgo | Dónde | Impacto | Medida |
| --- | --- | --- | --- |
| Dependencia con vulnerabilidad conocida | FastAPI, Uvicorn y sus dependencias | ejecución remota o denegación de servicio en el visualizador | versiones fijadas con hashes; `pip-audit` en cada cambio; Dependabot |
| Paquete alterado en el registro (cadena de suministro) | instalación de dependencias | código malicioso en el entorno | `pip install --require-hashes`; actions de GitHub fijadas por SHA; gitleaks verificado por checksum |
| Secreto publicado en el repositorio | todo el historial de git | filtración de credenciales | gitleaks sobre todo el historial del commit que se integra (no sobre otras ramas: un secreto en una rama ajena no debe rechazar un PR sano); *secret scanning* y *push protection* de GitHub, que sí miran todas las ramas |
| Patrón de código inseguro | `src/`, `viz/`, `bench/`, `data/` | inyección, uso indebido de criptografía | Bandit y CodeQL |
| Entrada maliciosa a la API | `viz/server.py` | errores no controlados, consumo excesivo | validación de tipos y rangos de FastAPI (`Query(ge=0)`), errores controlados; el servidor escucha solo en `127.0.0.1` |
| Workflow de CI inseguro | `.github/workflows/` | robo del token del repositorio | permisos mínimos por job, `persist-credentials: false`, CodeQL sobre los workflows |

El núcleo (`src/`) no abre archivos ni sockets a partir de datos del usuario, salvo las
rutas de CSV que se pasan explícitamente por la CLI.

## Herramientas

| Qué se analiza | Herramienta | Comando | Reporte |
| --- | --- | --- | --- |
| Código fuente (patrones) | Bandit | `make sec-code` | `bandit.txt`, `bandit.sarif` |
| Código fuente (semántico) | CodeQL (`security-extended`) | workflow `codeql.yml` | pestaña *Security → Code scanning* |
| Dependencias | pip-audit | `make sec-deps` | `pip-audit.md`, `pip-audit.json` |
| Dependencias (alertas y actualizaciones) | Dependabot | `.github/dependabot.yml` | PRs automáticos y alertas |
| Secretos | gitleaks + secret scanning de GitHub | `make secrets` | `gitleaks.sarif` |

Bandit y CodeQL se complementan. Bandit busca patrones conocidos en el árbol sintáctico
(por ejemplo `subprocess` con `shell=True`). CodeQL sigue el flujo de datos desde las
entradas hasta los puntos peligrosos. pip-audit no mira nuestro código, sino las
versiones instaladas contra la base de vulnerabilidades de PyPI/OSV.

Los SARIF de Ruff, Bandit y gitleaks se suben a *Code scanning*, así que todos los
hallazgos se ven en un solo lugar, junto con los de CodeQL.

## Política de bloqueo por severidad

| Fuente | Bloquea la integración | Se revisa antes de integrar | Solo se reporta |
| --- | --- | --- | --- |
| Bandit | severidad **alta** con confianza media o alta | severidad media | severidad baja |
| pip-audit | **cualquier** vulnerabilidad conocida | — | — |
| gitleaks | **cualquier** hallazgo | — | — |
| CodeQL | — | alertas `error` y `warning` | `note` |

La política es verificable: los umbrales de Bandit y la lista de excepciones de
pip-audit son variables del `Makefile` (`BANDIT_SEV`, `BANDIT_CONF`,
`PIP_AUDIT_IGNORE`), y el job correspondiente del CI falla si se superan.

**Por qué pip-audit bloquea todo.** pip-audit no filtra por puntaje CVSS, y nuestras
dependencias de ejecución son pocas. Es más simple y más seguro bloquear y decidir caso
por caso que mantener un filtro por severidad.

**Por qué CodeQL no bloquea.** Sus alertas necesitan análisis humano (muchas dependen
del contexto). Se revisan en *Code scanning* antes de integrar.

## Falsos positivos y excepciones

Una excepción solo es válida si cumple las tres condiciones:

1. Está marcada en el código (`# nosec BXXX`) o en el `Makefile`
   (`PIP_AUDIT_IGNORE += --ignore-vuln ID`).
2. Tiene una línea de comentario con el motivo justo encima.
3. Está registrada en la tabla siguiente.

`make sec-code` genera además `reports/bandit_nosec.txt` **ignorando** las marcas
`nosec`, para que las excepciones sigan visibles y se puedan auditar.

| ID | Ubicación | Motivo | Decisión | Fecha |
| --- | --- | --- | --- | --- |
| B311 | `src/graph.py` (×3), `src/archivos.py`, `src/parallel.py` | `random.Random(seed)` genera grafos y consultas **de prueba** reproducibles. No hay uso criptográfico: la previsibilidad es justamente lo que se busca. | falso positivo, `# nosec B311` | 2026-11-05 |
| B310 | `data/fetch_cordoba.py:88` | `urlopen` sobre una URL **fija** `https://` de la lista `ENDPOINTS`; nunca proviene del usuario. Es un script de descarga que se corre una vez, fuera de la aplicación. | falso positivo, `# nosec B310` | 2026-11-05 |

No hay vulnerabilidades de dependencias aceptadas (`PIP_AUDIT_IGNORE` está vacío).

## Estado actual

| Control | Resultado |
| --- | --- |
| Bandit | 0 hallazgos (6 suprimidos y documentados arriba) |
| pip-audit | 0 vulnerabilidades en las 99 dependencias auditadas (de 100 fijadas: una es solo para otra plataforma) |
| gitleaks | 0 secretos en todo el historial |
| CodeQL (Python y Actions) | 0 alertas |

## Medidas correctivas

| Situación | Qué hacer |
| --- | --- |
| pip-audit reporta una vulnerabilidad con versión corregida | subir la versión en `requirements*.in` si hace falta, `make lock`, `make ci` y abrir un PR (o aceptar el PR de Dependabot) |
| Vulnerabilidad sin versión corregida | evaluar si el código vulnerable se usa. Si no, agregar `--ignore-vuln` con motivo y registrarlo en la tabla de excepciones. Si se usa, buscar una alternativa |
| Bandit reporta un hallazgo real | corregir el código. Si es falso positivo, seguir el procedimiento de excepciones |
| gitleaks encuentra un secreto | **revocar el secreto primero** (borrarlo del código no alcanza: queda en el historial), después quitarlo y, si corresponde, reescribir el historial |
| Alerta de CodeQL | analizarla en *Code scanning*; corregirla o descartarla en la interfaz con motivo |
