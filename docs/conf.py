"""Configuracion de Sphinx: genera la documentacion desde los docstrings."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

project = "Planificador de rutas"
author = "Programacion Eficiente"
release = "2.0"
language = "es"

extensions = [
    "sphinx.ext.autodoc",  # lee los docstrings
    "sphinx.ext.napoleon",  # entiende el formato Google (Args:, Returns:)
    "sphinx.ext.viewcode",  # agrega el codigo fuente resaltado
]
autodoc_member_order = "bysource"
html_theme = "alabaster"
html_theme_options = {"page_width": "1100px"}
