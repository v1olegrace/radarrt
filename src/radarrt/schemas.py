"""Contrato de dados da tabela regional usada pelo motor RadarRT."""

from __future__ import annotations

import numpy as np
import pandas as pd

# Colunas de entrada
COL_UF = "uf"
COL_REGIAO = "regiao"
COL_POP = "populacao"
COL_INCIDENCIA = "incidencia_total"
COL_INCIDENCIA_SEM_PNM = "incidencia_sem_pnm"
COL_LINACS = "linacs_sus"
COL_OFERTA_APAC = "cursos_rt_realizados"

COLUNAS_ENTRADA: list[str] = [
    COL_UF,
    COL_REGIAO,
    COL_POP,
    COL_INCIDENCIA,
    COL_INCIDENCIA_SEM_PNM,
    COL_LINACS,
    COL_OFERTA_APAC,
]

# Colunas de saida
COL_DEMANDA_RT = "demanda_rt_sus"
COL_DEMANDA_REPRIMIDA = "demanda_reprimida"
COL_PACIENTES_POR_LINAC = "pacientes_por_linac"
COL_LSI = "lsi"
COL_GRADE = "grade"
COL_DEFICIT_LINACS = "deficit_linacs"
COL_DEF_FISICO = "deficit_fisico_medico"
COL_DEF_ONCO = "deficit_radio_oncologista"
COL_DEF_TECNICO = "deficit_tecnico_rtt"
COL_DEF_PROFISSIONAIS = "deficit_profissionais_total"
COL_UTILIZACAO = "utilizacao"
COL_TEMPO_ESPERA_MESES = "tempo_espera_meses"
COL_PRAZO_60D = "prazo_60d_alcancavel"

COLUNAS_SAIDA: list[str] = [
    COL_DEMANDA_RT,
    COL_DEMANDA_REPRIMIDA,
    COL_PACIENTES_POR_LINAC,
    COL_LSI,
    COL_GRADE,
    COL_DEFICIT_LINACS,
    COL_DEF_FISICO,
    COL_DEF_ONCO,
    COL_DEF_TECNICO,
    COL_DEF_PROFISSIONAIS,
    COL_UTILIZACAO,
    COL_TEMPO_ESPERA_MESES,
    COL_PRAZO_60D,
]

_COLUNAS_TEXTO = [COL_UF, COL_REGIAO]
_COLUNAS_NUMERICAS = [
    COL_POP,
    COL_INCIDENCIA,
    COL_INCIDENCIA_SEM_PNM,
    COL_LINACS,
    COL_OFERTA_APAC,
]


def validar_entrada(df: pd.DataFrame) -> None:
    """Falha cedo quando ``df`` nao respeita o contrato de entrada."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("entrada deve ser um pandas.DataFrame")

    duplicadas = df.columns[df.columns.duplicated()].tolist()
    if duplicadas:
        raise ValueError(f"Colunas duplicadas no schema de entrada: {duplicadas}")

    faltando = [col for col in COLUNAS_ENTRADA if col not in df.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes no schema de entrada: {faltando}")

    for col in _COLUNAS_TEXTO:
        if df[col].isna().any() or not df[col].map(
            lambda valor: isinstance(valor, str) and bool(valor.strip())
        ).all():
            raise ValueError(f"Coluna '{col}' deve conter strings nao vazias")

    for col in _COLUNAS_NUMERICAS:
        serie = df[col]
        if not pd.api.types.is_numeric_dtype(serie):
            raise ValueError(f"Coluna '{col}' deve ser numerica")
        if serie.isna().any() or not np.isfinite(serie.to_numpy(dtype=float)).all():
            raise ValueError(f"Coluna '{col}' deve conter apenas valores finitos")
        if (serie < 0).any():
            raise ValueError(f"Coluna '{col}' contem valores negativos")

    linacs = df[COL_LINACS].to_numpy(dtype=float)
    if not np.equal(linacs, np.floor(linacs)).all():
        raise ValueError(f"Coluna '{COL_LINACS}' deve conter numeros inteiros")

    if (df[COL_INCIDENCIA_SEM_PNM] > df[COL_INCIDENCIA]).any():
        raise ValueError("incidencia_sem_pnm nao pode exceder incidencia_total")
