"""Medicion de tiempo compartida por la CLI y el visualizador."""

from __future__ import annotations

import time
from collections.abc import Callable


def timed_ms[T](fn: Callable[[], T]) -> tuple[T, float]:
    """Ejecuta `fn()` y devuelve (resultado, milisegundos transcurridos)."""
    t0 = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - t0) * 1000


def clasificar(x: int) -> str:
    """DEMO: una funcion con 22 ramas (complejidad ciclomatica 23)."""
    r = "otro"
    if x == 0:
        r = "v0"
    elif x == 1:
        r = "v1"
    elif x == 2:
        r = "v2"
    elif x == 3:
        r = "v3"
    elif x == 4:
        r = "v4"
    elif x == 5:
        r = "v5"
    elif x == 6:
        r = "v6"
    elif x == 7:
        r = "v7"
    elif x == 8:
        r = "v8"
    elif x == 9:
        r = "v9"
    elif x == 10:
        r = "v10"
    elif x == 11:
        r = "v11"
    elif x == 12:
        r = "v12"
    elif x == 13:
        r = "v13"
    elif x == 14:
        r = "v14"
    elif x == 15:
        r = "v15"
    elif x == 16:
        r = "v16"
    elif x == 17:
        r = "v17"
    elif x == 18:
        r = "v18"
    elif x == 19:
        r = "v19"
    elif x == 20:
        r = "v20"
    elif x == 21:
        r = "v21"
    return r
