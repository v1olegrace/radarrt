"""Populacao estatica por UF para o schema canonico offline."""

from __future__ import annotations

import pandas as pd

from . import geo, schemas

# Estimativas IBGE 2024 arredondadas, mantidas offline para garantir o
# denominador mesmo quando DATASUS/IBGE estiverem indisponiveis.
POPULACAO_UF: dict[str, int] = {
    "AC": 830_000,
    "AP": 730_000,
    "AM": 4_280_000,
    "PA": 8_120_000,
    "RO": 1_580_000,
    "RR": 640_000,
    "TO": 1_580_000,
    "AL": 3_130_000,
    "BA": 14_140_000,
    "CE": 8_790_000,
    "MA": 6_770_000,
    "PB": 3_970_000,
    "PE": 9_060_000,
    "PI": 3_270_000,
    "RN": 3_300_000,
    "SE": 2_210_000,
    "DF": 2_810_000,
    "GO": 7_060_000,
    "MT": 3_660_000,
    "MS": 2_760_000,
    "ES": 3_830_000,
    "MG": 20_540_000,
    "RJ": 16_050_000,
    "SP": 44_410_000,
    "PR": 11_440_000,
    "RS": 10_880_000,
    "SC": 7_610_000,
}


def populacao_por_uf(ufs: list[str] | tuple[str, ...] | None = None) -> pd.DataFrame:
    """Retorna ``[uf, regiao, populacao]`` para as UFs solicitadas."""
    selecionadas = geo.normalizar_ufs(ufs)
    linhas = [
        {
            schemas.COL_UF: uf,
            schemas.COL_REGIAO: geo.regiao_de_uf(uf),
            schemas.COL_POP: POPULACAO_UF[uf],
        }
        for uf in selecionadas
    ]
    return pd.DataFrame(
        linhas,
        columns=[schemas.COL_UF, schemas.COL_REGIAO, schemas.COL_POP],
    )
