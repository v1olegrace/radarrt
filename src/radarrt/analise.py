"""Ferramentas de auditoria e exploracao cientifica do motor."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from . import schemas
from .config import CENARIOS, Params
from .engine import calcular_indicadores, resumo_nacional


def auditar_base(df: pd.DataFrame) -> dict[str, float]:
    """Resume a base canonica antes de entrar no motor."""
    schemas.validar_entrada(df)
    return {
        "n_ufs": float(df[schemas.COL_UF].nunique()),
        "populacao": float(df[schemas.COL_POP].sum()),
        "incidencia_total": float(df[schemas.COL_INCIDENCIA].sum()),
        "incidencia_sem_pnm": float(df[schemas.COL_INCIDENCIA_SEM_PNM].sum()),
        "linacs_sus": float(df[schemas.COL_LINACS].sum()),
        "cursos_rt_realizados": float(df[schemas.COL_OFERTA_APAC].sum()),
        "ufs_sem_linac": float((df[schemas.COL_LINACS] == 0).sum()),
        "ufs_sem_oferta": float((df[schemas.COL_OFERTA_APAC] == 0).sum()),
    }


def avaliar_cenarios(
    df: pd.DataFrame,
    cenarios: Mapping[str, Params] = CENARIOS,
) -> pd.DataFrame:
    """Executa o motor em todos os cenarios e agrega metricas nacionais."""
    linhas: list[dict[str, float | str]] = []
    for nome, params in cenarios.items():
        calc = calcular_indicadores(df, params)
        resumo = resumo_nacional(calc, params)
        grades = calc[schemas.COL_GRADE].value_counts().to_dict()
        linhas.append(
            {
                "cenario": nome,
                "rur": params.rur,
                "sus_share": params.sus_share,
                "fracao_efetiva_rt": params.fracao_efetiva_rt,
                **resumo,
                "ufs_grade_0": int(grades.get(0, 0)),
                "ufs_grade_1": int(grades.get(1, 0)),
                "ufs_grade_2": int(grades.get(2, 0)),
                "ufs_grade_3": int(grades.get(3, 0)),
                "ufs_grade_4": int(grades.get(4, 0)),
            }
        )
    return pd.DataFrame(linhas)


def ranking_prioridade(df_calc: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Ordena UFs por prioridade, preservando indicadores interpretaveis."""
    colunas = [
        schemas.COL_UF,
        schemas.COL_REGIAO,
        schemas.COL_DEMANDA_REPRIMIDA,
        schemas.COL_DEFICIT_LINACS,
        schemas.COL_LSI,
        schemas.COL_GRADE,
    ]
    faltando = [col for col in colunas if col not in df_calc.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes para ranking: {faltando}")

    ordenavel = df_calc.copy()
    ordenavel["_lsi_ordem"] = ordenavel[schemas.COL_LSI].replace(np.inf, np.nan)
    return (
        ordenavel.sort_values(
            by=[
                schemas.COL_GRADE,
                schemas.COL_DEFICIT_LINACS,
                schemas.COL_DEMANDA_REPRIMIDA,
                "_lsi_ordem",
            ],
            ascending=[False, False, False, False],
        )
        .head(n)[colunas]
        .reset_index(drop=True)
    )


def preparar_datamart(
    df: pd.DataFrame,
    params: Params = CENARIOS["base"],
) -> pd.DataFrame:
    """Tabela plana pronta para dashboard, CSV ou text-to-SQL."""
    return calcular_indicadores(df, params)
