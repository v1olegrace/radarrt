"""Gerador deterministico de dados ilustrativos no schema canonico."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import geo, ibge, schemas
from .config import CENARIOS, Params

_FATOR_ACESSO: dict[str, float] = {
    "Norte": 0.45,
    "Nordeste": 0.70,
    "Centro-Oeste": 0.55,
    "Sudeste": 1.10,
    "Sul": 1.05,
}

_INCIDENCIA_BRUTA_POR_100K: dict[str, float] = {
    "Norte": 230.0,
    "Nordeste": 300.0,
    "Centro-Oeste": 360.0,
    "Sudeste": 430.0,
    "Sul": 470.0,
}

_RAZAO_SEM_PNM = 0.69


def gerar_regioes(
    seed: int = 42,
    params: Params = CENARIOS["base"],
    ufs: list[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Gera uma linha por UF usando a geografia/populacao canonicas."""
    rng = np.random.default_rng(seed)
    linhas: list[dict[str, object]] = []

    for uf in geo.normalizar_ufs(ufs):
        regiao = geo.regiao_de_uf(uf)
        pop = ibge.POPULACAO_UF[uf]
        taxa = _INCIDENCIA_BRUTA_POR_100K[regiao]
        incidencia_total = pop / 100_000 * taxa * rng.normal(1.0, 0.08)
        incidencia_sem_pnm = incidencia_total * _RAZAO_SEM_PNM
        demanda_rt = incidencia_sem_pnm * params.fracao_efetiva_rt

        linacs_ideais = demanda_rt / params.linac_throughput
        linacs = max(int(round(linacs_ideais * _FATOR_ACESSO[regiao])), 0)

        capacidade = (
            linacs * params.linac_throughput * rng.uniform(0.75, 0.95)
        )
        oferta = min(demanda_rt * rng.uniform(0.85, 1.0), capacidade)

        linhas.append(
            {
                schemas.COL_UF: uf,
                schemas.COL_REGIAO: regiao,
                schemas.COL_POP: pop,
                schemas.COL_INCIDENCIA: round(incidencia_total, 1),
                schemas.COL_INCIDENCIA_SEM_PNM: round(incidencia_sem_pnm, 1),
                schemas.COL_LINACS: linacs,
                schemas.COL_OFERTA_APAC: round(oferta, 1),
            }
        )

    return pd.DataFrame(linhas, columns=schemas.COLUNAS_ENTRADA)
