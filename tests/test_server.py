"""API del visualizador (FastAPI) sobre el mapa real de Cordoba, con TestClient."""

import pytest
from fastapi.testclient import TestClient

from tests.reference import bellman_ford
from viz import server


@pytest.fixture(scope="module")
def cliente():
    with TestClient(server.app) as c:  # el `with` corre el lifespan: carga el mapa
        yield c


def test_pagina_y_docs(cliente):
    assert "<canvas" in cliente.get("/").text
    assert cliente.get("/docs").status_code == 200
    rutas = cliente.get("/openapi.json").json()["paths"]
    assert {"/api/mapa", "/api/ruta", "/api/cortar", "/api/reset", "/api/lote"} <= set(rutas)


def test_mapa(cliente):
    m = cliente.get("/api/mapa").json()
    assert m["n"] == len(m["x"]) == len(m["y"]) == server.MAPA.n
    assert len(m["edges"]) == server.MAPA.num_edges


@pytest.mark.parametrize("algo", ["heap", "astar"])
def test_ruta_optima(cliente, algo):
    r = cliente.get("/api/ruta", params={"algo": algo, "desde": 10, "hasta": 5000}).json()
    esperado = bellman_ford(server.MAPA, 10)[5000]
    assert r["costo"] == pytest.approx(esperado)
    assert r["camino"][0] == 10 and r["camino"][-1] == 5000
    assert len(r["orden"]) == r["expandidos"]


def test_ruta_con_cache(cliente):
    params = {"desde": 1, "hasta": 2000, "cache": 1}
    cliente.get("/api/ruta", params=params)
    r = cliente.get("/api/ruta", params=params).json()
    assert r["algoritmo"] == "cache" and r["cache"] == "hit"


@pytest.mark.parametrize(
    "params",
    [
        {"desde": "abc", "hasta": 1},  # tipo invalido
        {"desde": 1, "hasta": 2, "algo": "inexistente"},  # algoritmo invalido
        {"desde": -1, "hasta": 2},  # fuera de rango (ge=0)
    ],
)
def test_validacion_automatica(cliente, params):
    r = cliente.get("/api/ruta", params=params)
    assert r.status_code == 422 and "error" in r.json()


def test_errores_propios(cliente):
    assert "no escala" in cliente.get("/api/ruta?algo=naive&desde=0&hasta=1").json()["error"]
    assert cliente.get("/api/ruta?desde=0&hasta=99999999").status_code == 400
    assert cliente.get("/api/cortar?u=0&v=0").status_code == 400


def test_cortar_y_reset(cliente):
    u, (v, _) = 0, server.MAPA.adj[0][0]
    version = server.MAPA.version
    r = cliente.get("/api/cortar", params={"u": u, "v": v}).json()
    assert r["ok"] and r["version"] > version and r["cortadas"] == 1
    r = cliente.get("/api/reset").json()
    assert r["ok"] and not server.PESOS_ORIGINALES


def test_lote(cliente):
    r = cliente.get("/api/lote", params={"tamanos": "4,8"}).json()
    assert [f["n"] for f in r["filas"]] == [4, 8]
    assert set(r["filas"][0]["tiempos"]) == {"secuencial", "hilos", "procesos"}
    assert cliente.get("/api/lote", params={"tamanos": "1,2,3,4,5"}).status_code == 422
