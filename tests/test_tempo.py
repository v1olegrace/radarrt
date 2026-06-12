"""Testes da camada de tempo do motor RadarRT (Fase A)."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from radarrt import engine, schemas
from radarrt.config import CENARIOS

OUTPUT_DIR = Path("data/outputs_2024")
PARAMS = CENARIOS["base"]


def test_utilizacao_igual_lsi_sobre_100() -> None:
    base = pd.read_csv(OUTPUT_DIR / "base_canonica.csv")
    calc = engine.calcular_indicadores(base, PARAMS)
    finitos = calc[schemas.COL_LSI].apply(math.isfinite)
    util_fin = calc.loc[finitos, schemas.COL_UTILIZACAO]
    lsi_fin = calc.loc[finitos, schemas.COL_LSI]
    for u, lsi in zip(util_fin, lsi_fin, strict=True):
        assert abs(u * 100 - lsi) < 1e-6, f"util*100={u*100} != lsi={lsi}"


def test_prazo_60d_limiar() -> None:
    assert engine.prazo_60d_alcancavel(0.999) is True
    assert engine.prazo_60d_alcancavel(1.0) is False
    assert engine.prazo_60d_alcancavel(1.2) is False


def test_tempo_inf_quando_rho_ge_1() -> None:
    # folga <= 0: demanda == capacidade
    t = engine.tempo_espera_meses(5000.0, 10_000.0, 20, PARAMS)  # 20*500=10000 -> folga=0
    assert math.isinf(t)
    # folga < 0: demanda > capacidade
    t2 = engine.tempo_espera_meses(5000.0, 12_000.0, 20, PARAMS)
    assert math.isinf(t2)


def test_tempo_finito_quando_rho_lt_1() -> None:
    # fila=1000, demanda=9000, 25 LINACs, throughput=450
    # capacidade=25*450=11250; folga=11250-9000=2250; espera=1000/2250*12=5.333...
    t = engine.tempo_espera_meses(1000.0, 9000.0, 25, PARAMS)
    assert math.isfinite(t)
    assert abs(t - 5.333) < 0.01


def test_tempo_monotonico_em_linacs() -> None:
    t20 = engine.tempo_espera_meses(1000.0, 9000.0, 20, PARAMS)
    t25 = engine.tempo_espera_meses(1000.0, 9000.0, 25, PARAMS)
    assert t25 <= t20


def test_sem_linac_tempo_inf_prazo_falso() -> None:
    t = engine.tempo_espera_meses(500.0, 1000.0, 0, PARAMS)
    assert math.isinf(t)
    u = engine.utilizacao(1000.0, 0, PARAMS)
    assert math.isinf(u)
    assert engine.prazo_60d_alcancavel(u) is False


def test_utilizacao_negativo_levanta_erro() -> None:
    with pytest.raises(ValueError, match="negativo"):
        engine.utilizacao(1000.0, -1, PARAMS)


def test_tempo_espera_negativo_levanta_erro() -> None:
    with pytest.raises(ValueError, match="negativo"):
        engine.tempo_espera_meses(1000.0, 500.0, -1, PARAMS)
