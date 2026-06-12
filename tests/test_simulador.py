"""Testes do simulador de dimensionamento (Fase C)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from radarrt import engine, schemas
from radarrt.config import CENARIOS

OUTPUT_DIR = Path("data/outputs_2024")
PARAMS = CENARIOS["base"]


def _indicadores() -> pd.DataFrame:
    return pd.read_csv(OUTPUT_DIR / "indicadores_base.csv")


def _bahia() -> pd.Series:
    return _indicadores().loc[lambda df: df[schemas.COL_UF] == "BA"].iloc[0]


def test_linacs_para_meta_invalida() -> None:
    for meta in (0, 1.5):
        with pytest.raises(ValueError, match="meta_utilizacao"):
            engine.linacs_para_meta(1_000, PARAMS, meta)


def test_simular_uf_zera_deficit() -> None:
    ba = _bahia()
    depois = engine.simular_uf(
        float(ba[schemas.COL_DEMANDA_RT]),
        float(ba[schemas.COL_DEMANDA_REPRIMIDA]),
        int(ba[schemas.COL_LINACS]) + 12,
        PARAMS,
    )

    assert depois["n_linacs"] == 28
    assert depois["deficit_linacs"] == 0
    assert depois["utilizacao"] == pytest.approx(0.98, abs=0.01)
    assert depois["prazo_60d_alcancavel"] is True


def test_simular_uf_monotonia() -> None:
    ba = _bahia()
    demanda = float(ba[schemas.COL_DEMANDA_RT])
    fila = float(ba[schemas.COL_DEMANDA_REPRIMIDA])
    plano_28 = engine.simular_uf(demanda, fila, 28, PARAMS)
    plano_33 = engine.simular_uf(demanda, fila, 33, PARAMS)

    assert plano_33["utilizacao"] < plano_28["utilizacao"]
    assert plano_33["tempo_espera_meses"] < plano_28["tempo_espera_meses"]


def test_plano_nacional_meta_1() -> None:
    plano = engine.plano_nacional(_indicadores(), PARAMS, meta_utilizacao=1.0)

    assert plano["linacs_a_instalar"] == 86
    assert plano["profissionais_total"] == 506
    assert plano["investimento_reais"] == 860_000_000
    assert plano["ufs_beneficiadas"] == 19


def test_plano_nacional_meta_08() -> None:
    plano = engine.plano_nacional(_indicadores(), PARAMS, meta_utilizacao=0.8)

    assert plano["linacs_a_instalar"] == 183
    assert plano["profissionais_total"] == 1_070
    assert plano["investimento_reais"] == 1_830_000_000
    assert plano["ufs_beneficiadas"] == 24


def test_plano_nacional_meta_invalida() -> None:
    with pytest.raises(ValueError, match="meta_utilizacao"):
        engine.plano_nacional(_indicadores(), PARAMS, meta_utilizacao=0)
    with pytest.raises(ValueError, match="custo_por_linac"):
        engine.plano_nacional(_indicadores(), PARAMS, custo_por_linac=-1)
