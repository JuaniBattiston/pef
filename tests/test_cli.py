"""La CLI de demostracion corre de punta a punta."""

import pytest

from src.cli import main


@pytest.mark.parametrize(
    "argv, esperado",
    [
        (["ruta", "--size", "400", "--algo", "heap"], "costo"),
        (["ruta", "--family", "unweighted", "--size", "400", "--algo", "bfs"], "saltos"),
        (["comparar", "--size", "400"], "naive"),
        (["comparar", "--family", "unweighted", "--size", "400"], "bfs"),
        (["simular", "--size", "400"], "invalidations"),
        (["lote", "--size", "400", "--n", "20", "--modo", "secuencial"], "por consulta"),
        (["lote", "--size", "400", "--n", "20", "--modo", "hilos"], "por consulta"),
        (["lote", "--size", "400", "--n", "20", "--modo", "cache"], "hit_rate"),
    ],
)
def test_comandos(argv, esperado, capsys):
    main(argv)
    assert esperado in capsys.readouterr().out


def test_generar_y_procesar_archivo(tmp_path, capsys):
    entrada, salida = tmp_path / "q.csv", tmp_path / "r.csv"
    main(["generar-consultas", "--size", "400", "--n", "300", "--salida", str(entrada)])
    main(
        [
            "archivo",
            "--size",
            "400",
            "--entrada",
            str(entrada),
            "--salida",
            str(salida),
            "--lote",
            "50",
            "--secuencial",
        ]
    )
    assert len(salida.read_text().splitlines()) == 301
