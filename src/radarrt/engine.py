"""Motor deterministico e sem I/O para os indicadores do RadarRT."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import schemas
from .config import Params

_GRADES: tuple[tuple[float, int], ...] = (
    (100.0, 0),
    (130.0, 1),
    (300.0, 2),
    (math.inf, 3),
)
GRADE_SEM_LINAC = 4


def demanda_rt_sus(incidencia_sem_pnm: float, params: Params) -> float:
    """Calcula a demanda esperada de radioterapia no SUS."""
    return incidencia_sem_pnm * params.fracao_efetiva_rt


def demanda_reprimida(demanda: float, oferta_realizada: float) -> float:
    """Calcula a demanda nao atendida, limitada inferiormente a zero."""
    return max(demanda - oferta_realizada, 0.0)


def linac_shortage_index(
    pacientes_rt: float, n_linacs: int, params: Params
) -> float:
    """Calcula o LSI; uma regiao sem LINAC recebe infinito."""
    if n_linacs < 0:
        raise ValueError("n_linacs nao pode ser negativo")
    if n_linacs == 0:
        return math.inf
    return pacientes_rt / n_linacs / params.linac_throughput * 100.0


def grade_prioridade(lsi: float, n_linacs: int) -> int:
    """Mapeia o LSI para a grade de prioridade de 0 a 4."""
    if n_linacs < 0:
        raise ValueError("n_linacs nao pode ser negativo")
    if n_linacs == 0:
        return GRADE_SEM_LINAC
    for limite, grade in _GRADES:
        if lsi <= limite:
            return grade
    return _GRADES[-1][1]


def deficit_linacs(pacientes_rt: float, n_linacs: int, params: Params) -> int:
    """Calcula quantos LINACs faltam para atender ``pacientes_rt``."""
    if n_linacs < 0:
        raise ValueError("n_linacs nao pode ser negativo")
    necessarios = math.ceil(pacientes_rt / params.linac_throughput)
    return max(necessarios - n_linacs, 0)


def calcular_indicadores(df: pd.DataFrame, params: Params) -> pd.DataFrame:
    """Retorna uma copia de ``df`` acrescida das seis colunas calculadas."""
    schemas.validar_entrada(df)
    out = df.copy()

    incidencia = out[schemas.COL_INCIDENCIA_SEM_PNM].to_numpy(dtype=float)
    linacs = out[schemas.COL_LINACS].to_numpy(dtype=int)
    oferta = out[schemas.COL_OFERTA_APAC].to_numpy(dtype=float)

    demanda = incidencia * params.fracao_efetiva_rt
    reprimida = np.maximum(demanda - oferta, 0.0)

    with np.errstate(divide="ignore", invalid="ignore"):
        pacientes_por_linac = np.where(linacs == 0, np.inf, demanda / linacs)
        lsi = np.where(
            linacs == 0,
            np.inf,
            pacientes_por_linac / params.linac_throughput * 100.0,
        )

    deficit = np.maximum(
        np.ceil(demanda / params.linac_throughput) - linacs,
        0,
    ).astype(int)
    grades = np.fromiter(
        (grade_prioridade(valor, int(n)) for valor, n in zip(lsi, linacs, strict=True)),
        dtype=int,
        count=len(out),
    )

    out[schemas.COL_DEMANDA_RT] = demanda
    out[schemas.COL_DEMANDA_REPRIMIDA] = reprimida
    out[schemas.COL_PACIENTES_POR_LINAC] = pacientes_por_linac
    out[schemas.COL_LSI] = lsi
    out[schemas.COL_GRADE] = grades
    out[schemas.COL_DEFICIT_LINACS] = deficit
    return out


def resumo_nacional(df_calc: pd.DataFrame, params: Params) -> dict[str, float]:
    """Agrega resultados regionais e recalcula o LSI nacional."""
    faltando = [
        col
        for col in [*schemas.COLUNAS_ENTRADA, *schemas.COLUNAS_SAIDA]
        if col not in df_calc.columns
    ]
    if faltando:
        raise ValueError(f"Colunas ausentes para o resumo nacional: {faltando}")

    demanda_total = float(df_calc[schemas.COL_DEMANDA_RT].sum())
    oferta_total = float(df_calc[schemas.COL_OFERTA_APAC].sum())
    linacs_total = int(df_calc[schemas.COL_LINACS].sum())

    return {
        "demanda_rt_sus": demanda_total,
        "oferta_realizada": oferta_total,
        "demanda_reprimida": float(df_calc[schemas.COL_DEMANDA_REPRIMIDA].sum()),
        "linacs_instalados": float(linacs_total),
        "lsi_nacional": linac_shortage_index(demanda_total, linacs_total, params),
        "deficit_linacs": float(df_calc[schemas.COL_DEFICIT_LINACS].sum()),
    }
