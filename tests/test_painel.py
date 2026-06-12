from __future__ import annotations

import math

import pandas as pd
import pytest

from radarrt import schemas, validation
from radarrt.sources import painel


def test_pct_ate_60d_exclui_sem_info() -> None:
    df = pd.DataFrame(
        [
            {
                "uf": "SP",
                "casos_0_30": 20,
                "casos_31_60": 30,
                "casos_mais_60": 50,
                "casos_sem_info": 900,
            }
        ]
    )

    out = painel.pct_ate_60d(df)

    assert out.loc[0, "pct_ate_60d"] == 0.5


def test_pct_ate_60d_zero_denominador() -> None:
    df = pd.DataFrame(
        [
            {
                "uf": "AP",
                "casos_0_30": 0,
                "casos_31_60": 0,
                "casos_mais_60": 0,
                "casos_sem_info": 12,
            }
        ]
    )

    out = painel.pct_ate_60d(df)

    assert math.isnan(out.loc[0, "pct_ate_60d"])


def test_validar_painel_correlacao_negativa() -> None:
    indicadores = pd.DataFrame(
        [
            {schemas.COL_UF: "AM", schemas.COL_REGIAO: "Norte", schemas.COL_UTILIZACAO: 2.0, schemas.COL_GRADE: 2},
            {schemas.COL_UF: "BA", schemas.COL_REGIAO: "Nordeste", schemas.COL_UTILIZACAO: 1.0, schemas.COL_GRADE: 2},
            {schemas.COL_UF: "SC", schemas.COL_REGIAO: "Sul", schemas.COL_UTILIZACAO: 0.4, schemas.COL_GRADE: 0},
        ]
    )
    painel_df = pd.DataFrame(
        [
            {"uf": "AM", "casos_0_30": 1, "casos_31_60": 1, "casos_mais_60": 8, "casos_sem_info": 2},
            {"uf": "BA", "casos_0_30": 2, "casos_31_60": 3, "casos_mais_60": 5, "casos_sem_info": 1},
            {"uf": "SC", "casos_0_30": 7, "casos_31_60": 2, "casos_mais_60": 1, "casos_sem_info": 0},
        ]
    )

    checks = validation.validar_contra_painel(indicadores, painel_df)

    assert checks[0].passou is True
    assert checks[1].passou is True
    assert "Spearman=-1.000" in checks[0].detalhe


def test_ingerir_usa_cache(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "painel_onco"
    cache.mkdir()
    esperado = pd.DataFrame(
        [
            {
                "uf": "SP",
                "casos_0_30": 1,
                "casos_31_60": 2,
                "casos_mais_60": 3,
                "casos_sem_info": 4,
            }
        ]
    )
    esperado.to_csv(cache / "painel_rt_2024.csv", index=False)
    monkeypatch.setattr(painel, "CACHE_DIR", cache)

    def falhar_rede(_consulta: painel.ConsultaPainel, timeout: int = 60) -> str:
        raise AssertionError(f"rede chamada indevidamente: {timeout}")

    monkeypatch.setattr(painel, "_fetch_tabnet", falhar_rede)

    observado = painel.ingerir_painel(painel.ConsultaPainel(2024))

    pd.testing.assert_frame_equal(observado, esperado)
