"""Procesamiento de archivos grandes: lotes, buffer y procesos."""

import csv

import pytest

from src.archivos import (
    generar_consultas,
    leer_lotes,
    procesar_archivo,
    procesar_ingenuo,
    procesar_por_lotes,
)
from src.parallel import GraphSpec, solve_sequential

SPEC = GraphSpec("grid", 400)


@pytest.fixture
def consultas(tmp_path):
    ruta = tmp_path / "consultas.csv"
    generar_consultas(ruta, n_nodos=400, cantidad=1000)
    return ruta


def leer(ruta):
    with open(ruta, newline="") as f:
        return list(csv.reader(f))


def test_lotes_cover_whole_file_in_order(consultas):
    # 7 no divide a 1000: el ultimo lote queda incompleto y no se debe perder.
    lotes = list(leer_lotes(consultas, 7))
    assert len(lotes) == 143
    assert len(lotes[-1]) == 1000 % 7
    assert [q for lote in lotes for q in lote] == [tuple(map(int, f)) for f in leer(consultas)[1:]]


def test_batched_equals_naive(consultas, tmp_path):
    g = SPEC.build()

    def resolver(lote):
        return solve_sequential(g, lote, "astar")

    procesar_ingenuo(consultas, tmp_path / "a.csv", resolver)
    procesar_por_lotes(consultas, tmp_path / "b.csv", resolver, tam_lote=7)
    assert leer(tmp_path / "a.csv") == leer(tmp_path / "b.csv")


def test_parallel_equals_sequential(consultas, tmp_path):
    procesar_archivo(consultas, tmp_path / "seq.csv", SPEC, tam_lote=100, paralelo=False)
    procesar_archivo(consultas, tmp_path / "par.csv", SPEC, tam_lote=100, paralelo=True)
    filas = leer(tmp_path / "par.csv")
    assert filas == leer(tmp_path / "seq.csv")
    assert filas[0] == ["origen", "destino", "costo", "nodos_camino"]
    assert len(filas) == 1001
