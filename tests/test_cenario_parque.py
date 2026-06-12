"""Testes dos cenarios de parque expandido."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from radarrt import engine, schemas
from radarrt.config import CENARIOS

OUTPUT_DIR = Path("data/outputs_2024")


def _base() -> pd.DataFrame:
    return pd.read_csv(OUTPUT_DIR / "base_canonica.csv")


def test_alocar_nao_excede_deficit() -> None:
    deficit = np.array([12, 10, 0, 3])
    alocacao = engine.alocar_expansao(deficit, 20)

    assert int(alocacao.sum()) <= int(deficit.sum())
    assert (alocacao <= deficit).all()


def test_alocar_zero() -> None:
    deficit = np.array([1, 2, 3])

    assert (engine.alocar_expansao(deficit, 0) == 0).all()
    assert (engine.alocar_expansao(np.zeros(3, dtype=int), 10) == 0).all()


def test_cenario_base_mais_121_zera() -> None:
    resultado = engine.cenario_parque(_base(), 121, CENARIOS["base"])

    assert int(resultado["deficit_residual"]) == 0
    assert int(resultado["ufs_fila_divergente"]) == 1


def test_cenario_superior_mais_121_resta_86() -> None:
    resultado = engine.cenario_parque(_base(), 121, CENARIOS["superior"])

    assert int(resultado["deficit_residual"]) == 86
    assert int(resultado["ufs_fila_divergente"]) == 24


def test_alocacao_manual() -> None:
    resultado = engine.cenario_parque(
        _base(),
        0,
        CENARIOS["base"],
        alocacao_manual={"BA": 12, "RJ": 10},
    )

    assert int(resultado["maquinas_alocadas"]) == 22
    assert int(resultado["parque_total"]) == 431


def test_negativo_levanta() -> None:
    with pytest.raises(ValueError, match="negativo"):
        engine.alocar_expansao(np.array([1, 2]), -1)
    with pytest.raises(ValueError, match="negativo"):
        engine.cenario_parque(_base(), -1, CENARIOS["base"])
    with pytest.raises(ValueError, match="negativo"):
        engine.cenario_parque(
            _base(),
            0,
            CENARIOS["base"],
            alocacao_manual={schemas.COL_UF: -1},
        )
