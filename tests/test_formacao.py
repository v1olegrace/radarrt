"""Testes da camada de formacao especializada (Fase B)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from radarrt import engine
from radarrt.config import RazoesEquipe

OUTPUT_DIR = Path("data/outputs_2024")


def test_razoes_por_linac() -> None:
    razoes = RazoesEquipe()

    assert razoes.fisico_medico == 1.0
    assert razoes.radio_oncologista == 1.8
    assert razoes.tecnico_rtt == 3.0
    with pytest.raises(ValueError):
        RazoesEquipe(fisico_medico=0)


def test_deficit_profissionais_exemplo() -> None:
    assert engine.deficit_profissionais(12) == {
        "fisico_medico": 12,
        "radio_oncologista": 22,
        "tecnico_rtt": 36,
    }


def test_deficit_profissionais_zero() -> None:
    assert engine.deficit_profissionais(0) == {
        "fisico_medico": 0,
        "radio_oncologista": 0,
        "tecnico_rtt": 0,
    }


def test_ceil_por_uf() -> None:
    assert engine.deficit_profissionais(7)["radio_oncologista"] == 13


def test_negativo_levanta() -> None:
    with pytest.raises(ValueError, match="negativo"):
        engine.deficit_profissionais(-1)


def test_mart_total_nacional() -> None:
    resumo = pd.read_csv(OUTPUT_DIR / "resumo_nacional.csv").set_index("metrica")["valor"]

    assert int(float(resumo["deficit_fisico_medico"])) == 86
    assert int(float(resumo["deficit_radio_oncologista"])) == 162
    assert int(float(resumo["deficit_tecnico_rtt"])) == 258
    assert int(float(resumo["deficit_profissionais_total"])) == 506
