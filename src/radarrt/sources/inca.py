"""Ingestao do CSV preparado a partir da Estimativa do INCA."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .. import geo, schemas

RAZAO_SEM_PNM_PADRAO = 0.69


def carregar_incidencia(caminho_csv: str | Path) -> pd.DataFrame:
    """Le um CSV do INCA e delega toda a validacao ao normalizador puro."""
    return normalizar_incidencia(pd.read_csv(caminho_csv))


def normalizar_incidencia(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normaliza incidencia para ``[uf, total, sem_pnm]``."""
    df = df_raw.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]

    obrigatorias = [schemas.COL_UF, schemas.COL_INCIDENCIA]
    faltando = [col for col in obrigatorias if col not in df.columns]
    if faltando:
        raise ValueError(f"CSV do INCA sem colunas obrigatorias: {faltando}")

    df[schemas.COL_UF] = df[schemas.COL_UF].astype("string").str.upper().str.strip()
    if df[schemas.COL_UF].isna().any() or (df[schemas.COL_UF] == "").any():
        raise ValueError("CSV do INCA contem UF vazia")
    invalidas = sorted(set(df[schemas.COL_UF]) - set(geo.UFS))
    if invalidas:
        raise ValueError(f"UFs invalidas no CSV do INCA: {invalidas}")
    duplicadas = sorted(df.loc[df[schemas.COL_UF].duplicated(), schemas.COL_UF].unique())
    if duplicadas:
        raise ValueError(f"UFs duplicadas no CSV do INCA: {duplicadas}")

    df[schemas.COL_INCIDENCIA] = pd.to_numeric(
        df[schemas.COL_INCIDENCIA],
        errors="coerce",
    )
    if schemas.COL_INCIDENCIA_SEM_PNM not in df.columns:
        df[schemas.COL_INCIDENCIA_SEM_PNM] = (
            df[schemas.COL_INCIDENCIA] * RAZAO_SEM_PNM_PADRAO
        )
    else:
        df[schemas.COL_INCIDENCIA_SEM_PNM] = pd.to_numeric(
            df[schemas.COL_INCIDENCIA_SEM_PNM],
            errors="coerce",
        )

    numericas = [schemas.COL_INCIDENCIA, schemas.COL_INCIDENCIA_SEM_PNM]
    valores = df[numericas].to_numpy(dtype=float)
    if not np.isfinite(valores).all():
        raise ValueError("CSV do INCA contem incidencia ausente ou invalida")
    if (valores < 0).any():
        raise ValueError("CSV do INCA contem incidencia negativa")
    if (df[schemas.COL_INCIDENCIA_SEM_PNM] > df[schemas.COL_INCIDENCIA]).any():
        raise ValueError("incidencia_sem_pnm nao pode exceder incidencia_total")

    return df[[schemas.COL_UF, *numericas]].reset_index(drop=True)
