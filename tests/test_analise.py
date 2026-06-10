from __future__ import annotations

import pandas as pd
import pytest

from radarrt import (
    auditar_base,
    avaliar_cenarios,
    preparar_datamart,
    ranking_prioridade,
    schemas,
)
from radarrt.config import CENARIOS
from radarrt.synthetic import gerar_regioes


def test_auditar_base_resume_schema_canonico() -> None:
    base = gerar_regioes(seed=1, ufs=["SP", "PA"])

    auditoria = auditar_base(base)

    assert auditoria["n_ufs"] == 2
    assert auditoria["incidencia_sem_pnm"] > 0
    assert auditoria["linacs_sus"] >= 0


def test_avaliar_cenarios_preserva_ordem_de_sensibilidade() -> None:
    base = gerar_regioes(seed=1)

    cenarios = avaliar_cenarios(base)
    por_cenario = cenarios.set_index("cenario")

    assert list(cenarios["cenario"]) == list(CENARIOS)
    assert (
        por_cenario.loc["conservador", "demanda_rt_sus"]
        < por_cenario.loc["base", "demanda_rt_sus"]
        < por_cenario.loc["superior", "demanda_rt_sus"]
    )


def test_preparar_datamart_e_ranking_para_text_to_sql() -> None:
    base = gerar_regioes(seed=1)
    datamart = preparar_datamart(base)

    ranking = ranking_prioridade(datamart, n=5)

    assert all(col in datamart.columns for col in schemas.COLUNAS_SAIDA)
    assert len(ranking) == 5
    assert ranking.iloc[0][schemas.COL_GRADE] >= ranking.iloc[-1][schemas.COL_GRADE]


def test_ranking_falha_cedo_sem_indicadores() -> None:
    with pytest.raises(ValueError, match="Colunas ausentes"):
        ranking_prioridade(pd.DataFrame({"uf": ["SP"]}))
