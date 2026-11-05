"""Medicion de tiempo compartida por la CLI y el visualizador."""

from __future__ import annotations

import time


def timed_ms(fn):
    """Ejecuta `fn()` y devuelve (resultado, milisegundos transcurridos)."""
    t0 = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - t0) * 1000
