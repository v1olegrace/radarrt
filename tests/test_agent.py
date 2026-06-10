"""Testes offline do agente conversacional."""

from __future__ import annotations

import sqlite3

import pandas as pd

from radarrt.agent import core
from radarrt.agent import intent as I
from radarrt.agent import sql as S
from radarrt.agent.sql import SQLInvalido


def _conn() -> sqlite3.Connection:
    df = pd.DataFrame(
        [
            ("SP", "Sudeste", 44, 193, 132, 70, 1358, 132000, 51042, 0, 101.0, 1, 2),
            ("MG", "Sudeste", 20, 93, 58, 30, 1240, 58000, 21491, 0, 133.0, 2, 13),
            ("RJ", "Sudeste", 16, 81, 52, 25, 848, 52000, 19742, 0, 134.0, 2, 13),
            ("BA", "Nordeste", 14, 42, 30, 8, 253, 30000, 11940, 0, 152.0, 2, 10),
            ("CE", "Nordeste", 8, 32, 21, 5, 0, 21000, 8688, 0, 138.0, 2, 6),
            ("TO", "Norte", 1, 3, 2, 1, 194, 2400, 2000, 0, 320.0, 3, 5),
            ("RR", "Norte", 0, 1, 0, 0, 0, 800, 800, 0, None, 4, 4),
        ],
        columns=[
            "uf",
            "regiao",
            "populacao",
            "incidencia_total",
            "incidencia_sem_pnm",
            "linacs_sus",
            "cursos_rt_realizados",
            "demanda_rt_sus",
            "demanda_reprimida",
            "pacientes_por_linac",
            "lsi",
            "grade",
            "deficit_linacs",
        ],
    )
    con = sqlite3.connect(":memory:")
    df.to_sql("indicadores", con, index=False)
    return con


def test_parse_ranking() -> None:
    intent = I.parse("Quais os 5 estados com maior demanda reprimida?")
    assert intent.tipo == "ranking"
    assert intent.metrica == "demanda_reprimida"
    assert intent.n == 5
    assert intent.ordem == "desc"


def test_parse_ranking_ascendente() -> None:
    intent = I.parse("Os 3 estados com menor LSI")
    assert intent.tipo == "ranking"
    assert intent.ordem == "asc"
    assert intent.n == 3


def test_parse_valor_uf_por_nome() -> None:
    intent = I.parse("Qual o deficit de aceleradores em Tocantins?")
    assert intent.tipo == "valor_uf"
    assert intent.ufs == ["TO"]
    assert intent.metrica == "deficit_linacs"


def test_parse_comparacao_por_sigla() -> None:
    intent = I.parse("Compare SP e MG")
    assert intent.tipo == "comparacao"
    assert set(intent.ufs) == {"SP", "MG"}


def test_parse_filtro_grade() -> None:
    intent = I.parse("Quais estados estao em grade 3?")
    assert intent.tipo == "filtro_grade"
    assert intent.grade == 3


def test_parse_desconhecida() -> None:
    assert I.parse("ola, tudo bem?").tipo == "desconhecido"


def test_valor_uf_executa() -> None:
    resposta = core.responder_pergunta("deficit de aceleradores em Tocantins", _conn())
    assert resposta.reconhecida
    assert int(resposta.resultado.iloc[0]["deficit_linacs"]) == 5
    assert "TO" in resposta.frase and "5" in resposta.frase


def test_ranking_executa_e_ordena() -> None:
    resposta = core.responder_pergunta(
        "top 3 estados com maior demanda reprimida",
        _conn(),
    )
    assert resposta.resultado["uf"].tolist() == ["SP", "MG", "RJ"]
    assert "LIMIT 3" in resposta.sql


def test_filtro_grade_executa() -> None:
    resposta = core.responder_pergunta("quais estados estao em grade 3", _conn())
    assert resposta.resultado["uf"].tolist() == ["TO"]


def test_agregado_regional() -> None:
    resposta = core.responder_pergunta("deficit total no Nordeste", _conn())
    assert int(resposta.resultado.iloc[0]["total"]) == 16


def test_agregado_nacional() -> None:
    resposta = core.responder_pergunta(
        "demanda reprimida total do Brasil",
        _conn(),
    )
    assert int(resposta.resultado.iloc[0]["total"]) == (
        51042 + 21491 + 19742 + 11940 + 8688 + 2000 + 800
    )


def test_comparacao_executa() -> None:
    resposta = core.responder_pergunta("compare SP e MG", _conn())
    assert set(resposta.resultado["uf"]) == {"SP", "MG"}


def test_desconhecida_sugere() -> None:
    resposta = core.responder_pergunta("conte uma piada", _conn())
    assert not resposta.reconhecida
    assert "Tente algo como" in resposta.frase


def test_validador_bloqueia_nao_select() -> None:
    invalidos = [
        "DROP TABLE indicadores",
        "SELECT 1; DROP TABLE x",
        "SELECT * FROM outra",
        "DELETE FROM indicadores",
        "SELECT 1",
        "SELECT * FROM indicadores JOIN outra ON outra.uf = indicadores.uf",
    ]
    for ruim in invalidos:
        try:
            S.validar_select(ruim)
        except SQLInvalido:
            continue
        raise AssertionError(f"deveria bloquear: {ruim}")


def test_validador_aceita_select_valido() -> None:
    ok = S.validar_select("SELECT uf, lsi FROM indicadores WHERE grade = 3")
    assert ok.startswith("SELECT")
