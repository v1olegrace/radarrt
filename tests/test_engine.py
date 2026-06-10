"""Testes do contrato cientifico e operacional do motor RadarRT."""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError

import pandas as pd
import pytest

from radarrt import engine, schemas
from radarrt.config import CENARIOS, Params


def _entrada_valida() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                schemas.COL_UF: "AA",
                schemas.COL_REGIAO: "Norte",
                schemas.COL_POP: 1_000_000,
                schemas.COL_INCIDENCIA: 1_200.0,
                schemas.COL_INCIDENCIA_SEM_PNM: 1_000.0,
                schemas.COL_LINACS: 1,
                schemas.COL_OFERTA_APAC: 300.0,
            },
            {
                schemas.COL_UF: "BB",
                schemas.COL_REGIAO: "Sul",
                schemas.COL_POP: 2_000_000,
                schemas.COL_INCIDENCIA: 2_500.0,
                schemas.COL_INCIDENCIA_SEM_PNM: 2_000.0,
                schemas.COL_LINACS: 0,
                schemas.COL_OFERTA_APAC: 100.0,
            },
        ],
        columns=schemas.COLUNAS_ENTRADA,
    )


def test_ancora_reproduz_lsi_221() -> None:
    params = Params(rur=0.50, sus_share=0.80)
    pacientes_rt = engine.demanda_rt_sus(625_370, params)

    lsi = engine.linac_shortage_index(pacientes_rt, 252, params)

    assert lsi == pytest.approx(220.59, abs=0.01)
    assert round(lsi) == 221


def test_params_sao_validados_imutaveis_e_definem_tres_cenarios() -> None:
    params = Params(rur=0.5, sus_share=0.8)

    assert params.fracao_efetiva_rt == pytest.approx(0.4)
    assert set(CENARIOS) == {"conservador", "base", "superior"}
    with pytest.raises(FrozenInstanceError):
        params.rur = 0.7
    with pytest.raises(ValueError):
        Params(rur=0)
    with pytest.raises(ValueError):
        Params(linac_throughput=math.inf)


def test_demanda_escalar_e_reprimida_nunca_negativa() -> None:
    params = Params(rur=0.5, sus_share=0.8)

    assert engine.demanda_rt_sus(1_000, params) == pytest.approx(400)
    assert engine.demanda_reprimida(400, 250) == pytest.approx(150)
    assert engine.demanda_reprimida(400, 500) == 0


def test_lsi_infinito_sem_linac_e_grades_nos_limites() -> None:
    params = Params()

    assert math.isinf(engine.linac_shortage_index(100, 0, params))
    assert engine.grade_prioridade(math.inf, 0) == 4
    assert engine.grade_prioridade(100, 1) == 0
    assert engine.grade_prioridade(130, 1) == 1
    assert engine.grade_prioridade(300, 1) == 2
    assert engine.grade_prioridade(301, 1) == 3


def test_deficit_linacs_usa_throughput_injetado() -> None:
    params = Params(linac_throughput=500)

    assert engine.deficit_linacs(1_001, 1, params) == 2
    assert engine.deficit_linacs(400, 2, params) == 0


def test_schema_declara_colunas_e_validar_entrada_falha_cedo() -> None:
    assert len(schemas.COLUNAS_ENTRADA) == 7
    assert len(schemas.COLUNAS_SAIDA) == 6

    sem_uf = _entrada_valida().drop(columns=schemas.COL_UF)
    with pytest.raises(ValueError, match="Colunas ausentes"):
        schemas.validar_entrada(sem_uf)

    incidencia_invalida = _entrada_valida()
    incidencia_invalida.loc[0, schemas.COL_INCIDENCIA_SEM_PNM] = 2_000
    with pytest.raises(ValueError, match="nao pode exceder"):
        schemas.validar_entrada(incidencia_invalida)


def test_calcular_indicadores_valida_copia_e_calcula_seis_saidas() -> None:
    entrada = _entrada_valida()
    original = entrada.copy(deep=True)

    calculado = engine.calcular_indicadores(entrada, Params())
    repetido = engine.calcular_indicadores(entrada, Params())

    pd.testing.assert_frame_equal(entrada, original)
    pd.testing.assert_frame_equal(calculado, repetido)
    assert calculado is not entrada
    assert all(col in calculado.columns for col in schemas.COLUNAS_SAIDA)
    assert calculado.loc[0, schemas.COL_DEMANDA_RT] == pytest.approx(400)
    assert calculado.loc[0, schemas.COL_DEMANDA_REPRIMIDA] == pytest.approx(100)
    assert calculado.loc[1, schemas.COL_GRADE] == 4
    assert math.isinf(calculado.loc[1, schemas.COL_LSI])

    with pytest.raises(ValueError, match="Colunas ausentes"):
        engine.calcular_indicadores(entrada.drop(columns=schemas.COL_UF), Params())


def test_resumo_nacional_agrega_resultados_regionais() -> None:
    params = Params()
    calculado = engine.calcular_indicadores(_entrada_valida(), params)

    resumo = engine.resumo_nacional(calculado, params)

    assert resumo["demanda_rt_sus"] == pytest.approx(1_200)
    assert resumo["oferta_realizada"] == pytest.approx(400)
    assert resumo["demanda_reprimida"] == pytest.approx(800)
    assert resumo["linacs_instalados"] == 1
    assert resumo["lsi_nacional"] == pytest.approx(266.6667)
    assert resumo["deficit_linacs"] == 2
