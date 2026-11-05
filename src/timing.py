"""Medicion de tiempo compartida por la CLI y el visualizador."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def timed_ms(fn: Callable[[], T]) -> tuple[T, float]:
    """Ejecuta `fn()` y devuelve (resultado, milisegundos transcurridos)."""
    t0 = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - t0) * 1000
