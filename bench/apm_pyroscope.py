"""Monitoreo continuo con Grafana Pyroscope (herramienta general / APM).

No modifica el codigo de la aplicacion: este script conecta el agente de
Pyroscope y despues corre la CLI normal. Cada operacion se etiqueta
(`operacion=...`) para poder filtrarla en la interfaz web.

Requiere el servidor corriendo:
    docker run -d --name pyroscope-pef -p 4040:4040 grafana/pyroscope

Uso:  python3 -m bench.apm_pyroscope       y abrir http://localhost:4040
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pyroscope

from src.cli import main as cli

SERVIDOR = "http://localhost:4040"

pyroscope.configure(
    application_name="pef.rutas",
    server_address=SERVIDOR,
    sample_rate=100,
    tags={"version": "parte-2"},
)

with tempfile.TemporaryDirectory() as d:
    consultas, respuestas = Path(d) / "q.csv", Path(d) / "r.csv"
    trabajos = {
        "comparar": ["comparar", "--size", "2500"],
        "lote-cache": ["lote", "--size", "16000", "--n", "300", "--modo", "cache"],
        "generar": [
            "generar-consultas", "--size", "2000", "--n", "60000", "--salida", str(consultas),
        ],
        "archivo": [
            "archivo", "--size", "2000", "--entrada", str(consultas),
            "--salida", str(respuestas), "--secuencial",
        ],
    }  # fmt: skip
    for _ in range(2):  # dos vueltas: mas muestras en el panel
        for nombre, argv in trabajos.items():
            with pyroscope.tag_wrapper({"operacion": nombre}):
                cli(argv)

pyroscope.shutdown()
print(f"\nPerfiles enviados. Ver {SERVIDOR}  (app: pef.rutas)")
