"""Medicion de tiempo compartida por la CLI y el visualizador."""

from __future__ import annotations

import os  # DEMO: import sin usar
import time
from collections.abc import Callable


def timed_ms[T](fn: Callable[[], T]) -> tuple[T, float]:
    """Ejecuta `fn()` y devuelve (resultado, milisegundos transcurridos)."""
    t0 = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - t0) * 1000
