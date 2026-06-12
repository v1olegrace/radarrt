"""Motor deterministico e sem I/O para os indicadores do RadarRT."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd

from . import schemas
from .config import (
    CENARIOS,
    RAZOES_EQUIPE_PADRAO,
    THROUGHPUTS_SENSIBILIDADE,
    Params,
    RazoesEquipe,
)

_GRADES: tuple[tuple[float, int], ...] = (
    (100.0, 0),
    (130.0, 1),
    (300.0, 2),
    (math.inf, 3),
)
GRADE_SEM_LINAC = 4

# LSI e uma leitura de carga anual: 100 = demanda anual igual a capacidade
# instalada; 130 = 1,3 ano de carga; 300 = tres anos de carga. Grade 4 fica
# separada porque ausencia de LINAC e barreira fisica, nao apenas sobrecarga.


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
    """Mapeia o LSI para a grade de prioridade de 0 a 4.

    Os cortes sao ancorados na carga anual relativa: 100 e equilibrio,
    130 e sobrecarga moderada e 300 e colapso estrutural. Zero LINAC sempre
    vira grade 4, independentemente do LSI numerico.
    """
    if n_linacs < 0:
        raise ValueError("n_linacs nao pode ser negativo")
    if n_linacs == 0:
        return GRADE_SEM_LINAC
    for limite, grade in _GRADES:
        if lsi <= limite:
            return grade
    return _GRADES[-1][1]


def utilizacao(demanda_rt: float, n_linacs: int, params: Params) -> float:
    """Fracao da capacidade instalada consumida pela demanda (rho = LSI/100)."""
    if n_linacs < 0:
        raise ValueError("n_linacs nao pode ser negativo")
    if n_linacs == 0:
        return math.inf
    return demanda_rt / (n_linacs * params.linac_throughput)


def prazo_60d_alcancavel(utilizacao_rho: float) -> bool:
    """Condicao NECESSARIA da Lei 12.732/2012: rho < 1 (nao suficiente)."""
    return utilizacao_rho < 1.0


def tempo_espera_meses(
    demanda_reprimida: float,
    demanda_rt: float,
    n_linacs: int,
    params: Params,
) -> float:
    """Meses para drenar o backlog atual com a capacidade ociosa corrente.

    Indicador deterministico (nao e simulacao de filas). Diverge (inf) quando
    nao ha folga: rho >= 1 ou nenhum LINAC.
    """
    if n_linacs < 0:
        raise ValueError("n_linacs nao pode ser negativo")
    folga = n_linacs * params.linac_throughput - demanda_rt
    if n_linacs == 0 or folga <= 0:
        return math.inf
    return demanda_reprimida / folga * 12.0


def deficit_linacs(pacientes_rt: float, n_linacs: int, params: Params) -> int:
    """Calcula LINACs faltantes para cobrir a demanda total esperada.

    Este deficit dimensiona o parque necessario para zerar a fila estrutural
    no cenario, nao apenas o fluxo incremental ainda nao atendido no SIA-AR.
    """
    if n_linacs < 0:
        raise ValueError("n_linacs nao pode ser negativo")
    necessarios = math.ceil(pacientes_rt / params.linac_throughput)
    return max(necessarios - n_linacs, 0)


def deficit_profissionais(
    deficit_linacs: int,
    razoes: RazoesEquipe = RAZOES_EQUIPE_PADRAO,
) -> dict[str, int]:
    """Profissionais a formar para operar ``deficit_linacs`` aceleradores.

    Pessoas sao inteiras: aplique por UF e some nacionalmente. Esta funcao
    dimensiona equipe adicional para operar os LINACs faltantes, nao mede o
    quadro profissional vigente.
    """
    if deficit_linacs < 0:
        raise ValueError("deficit_linacs nao pode ser negativo")
    return {
        "fisico_medico": math.ceil(deficit_linacs * razoes.fisico_medico),
        "radio_oncologista": math.ceil(deficit_linacs * razoes.radio_oncologista),
        "tecnico_rtt": math.ceil(deficit_linacs * razoes.tecnico_rtt),
    }


def linacs_para_meta(
    demanda_rt: float,
    params: Params,
    meta_utilizacao: float = 1.0,
) -> int:
    """Minimo de LINACs para atingir utilizacao menor ou igual a meta."""
    if not 0.0 < meta_utilizacao <= 1.0:
        raise ValueError("meta_utilizacao deve estar em (0, 1]")
    if demanda_rt < 0:
        raise ValueError("demanda_rt nao pode ser negativa")
    return math.ceil(demanda_rt / (params.linac_throughput * meta_utilizacao))


def simular_uf(
    demanda_rt: float,
    demanda_reprimida: float,
    n_linacs: int,
    params: Params = CENARIOS["base"],
    razoes: RazoesEquipe = RAZOES_EQUIPE_PADRAO,
) -> dict[str, float | int | bool]:
    """Recalcula indicadores de uma UF para um parque hipotetico.

    ``demanda_rt`` e ``demanda_reprimida`` sao dados fixos da UF; a simulacao
    varia apenas a capacidade instalada. O backlog nao some, ele drena mais
    rapido quando ha folga de capacidade.
    """
    if demanda_rt < 0:
        raise ValueError("demanda_rt nao pode ser negativa")
    if demanda_reprimida < 0:
        raise ValueError("demanda_reprimida nao pode ser negativa")
    if n_linacs < 0:
        raise ValueError("n_linacs nao pode ser negativo")

    lsi = linac_shortage_index(demanda_rt, n_linacs, params)
    rho = utilizacao(demanda_rt, n_linacs, params)
    deficit = deficit_linacs(demanda_rt, n_linacs, params)
    prof = deficit_profissionais(deficit, razoes)
    return {
        "n_linacs": n_linacs,
        "lsi": lsi,
        "utilizacao": rho,
        "grade": grade_prioridade(lsi, n_linacs),
        "deficit_linacs": deficit,
        "tempo_espera_meses": tempo_espera_meses(
            demanda_reprimida,
            demanda_rt,
            n_linacs,
            params,
        ),
        "prazo_60d_alcancavel": prazo_60d_alcancavel(rho),
        "deficit_fisico_medico": prof["fisico_medico"],
        "deficit_radio_oncologista": prof["radio_oncologista"],
        "deficit_tecnico_rtt": prof["tecnico_rtt"],
        "deficit_profissionais_total": sum(prof.values()),
    }


def plano_nacional(
    df_calc: pd.DataFrame,
    params: Params = CENARIOS["base"],
    razoes: RazoesEquipe = RAZOES_EQUIPE_PADRAO,
    meta_utilizacao: float = 1.0,
    custo_por_linac: float = 10_000_000.0,
) -> dict[str, float]:
    """Plano para levar todas as UFs a utilizacao menor ou igual a meta."""
    if not 0.0 < meta_utilizacao <= 1.0:
        raise ValueError("meta_utilizacao deve estar em (0, 1]")
    if custo_por_linac < 0:
        raise ValueError("custo_por_linac nao pode ser negativo")

    faltando = [
        col
        for col in (schemas.COL_DEMANDA_RT, schemas.COL_LINACS)
        if col not in df_calc.columns
    ]
    if faltando:
        raise ValueError(f"Colunas ausentes para plano nacional: {faltando}")

    demanda = df_calc[schemas.COL_DEMANDA_RT].to_numpy(dtype=float)
    instalados = df_calc[schemas.COL_LINACS].to_numpy(dtype=int)
    necessarios = np.ceil(
        demanda / (params.linac_throughput * meta_utilizacao)
    ).astype(int)
    incremento = np.maximum(necessarios - instalados, 0).astype(int)

    fisicos = int(np.ceil(incremento * razoes.fisico_medico).sum())
    oncos = int(np.ceil(incremento * razoes.radio_oncologista).sum())
    tecnicos = int(np.ceil(incremento * razoes.tecnico_rtt).sum())
    linacs = int(incremento.sum())
    return {
        "meta_utilizacao": float(meta_utilizacao),
        "linacs_a_instalar": float(linacs),
        "deficit_fisico_medico": float(fisicos),
        "deficit_radio_oncologista": float(oncos),
        "deficit_tecnico_rtt": float(tecnicos),
        "profissionais_total": float(fisicos + oncos + tecnicos),
        "investimento_reais": float(linacs * custo_por_linac),
        "ufs_beneficiadas": float((incremento > 0).sum()),
    }


def alocar_expansao(
    deficit_por_uf: np.ndarray,
    n_novas_maquinas: int,
) -> np.ndarray:
    """Distribui maquinas novas proporcionalmente ao deficit local.

    Este e um melhor caso aproximado: nao excede o deficit local e nao modela a
    alocacao real do MS, que pode seguir criterios de vazio assistencial.
    """
    if n_novas_maquinas < 0:
        raise ValueError("n_novas_maquinas nao pode ser negativo")
    deficit = np.asarray(deficit_por_uf, dtype=int).clip(min=0)
    soma = int(deficit.sum())
    if soma == 0 or n_novas_maquinas == 0:
        return np.zeros_like(deficit)
    bruto = np.floor(n_novas_maquinas * deficit / soma).astype(int)
    return np.minimum(bruto, deficit)


def cenario_parque(
    df_base: pd.DataFrame,
    n_novas_maquinas: int,
    params: Params = CENARIOS["base"],
    alocacao_manual: dict[str, int] | None = None,
) -> dict[str, float]:
    """Recalcula deficit e utilizacao com parque expandido.

    A base canonica nao muda. O cenario apenas soma maquinas hipoteticas ao
    parque instalado e recalcula metricas derivadas de capacidade.
    """
    if n_novas_maquinas < 0:
        raise ValueError("n_novas_maquinas nao pode ser negativo")
    schemas.validar_entrada(df_base)

    demanda = (
        df_base[schemas.COL_INCIDENCIA_SEM_PNM].to_numpy(dtype=float)
        * params.fracao_efetiva_rt
    )
    instalados = df_base[schemas.COL_LINACS].to_numpy(dtype=int)
    deficit_inicial = np.maximum(
        np.ceil(demanda / params.linac_throughput) - instalados,
        0,
    ).astype(int)
    if alocacao_manual is not None:
        if any(valor < 0 for valor in alocacao_manual.values()):
            raise ValueError("alocacao_manual nao pode conter valor negativo")
        alocacao = df_base[schemas.COL_UF].map(
            lambda uf: int(alocacao_manual.get(uf, 0))
        ).to_numpy(dtype=int)
    else:
        alocacao = alocar_expansao(deficit_inicial, n_novas_maquinas)

    novo_parque = instalados + alocacao
    deficit_residual = np.maximum(
        np.ceil(demanda / params.linac_throughput) - novo_parque,
        0,
    ).astype(int)
    with np.errstate(divide="ignore", invalid="ignore"):
        rho = np.where(
            novo_parque == 0,
            np.inf,
            demanda / (novo_parque * params.linac_throughput),
        )
    return {
        "parque_total": float(novo_parque.sum()),
        "maquinas_alocadas": float(alocacao.sum()),
        "deficit_residual": float(deficit_residual.sum()),
        "ufs_fila_divergente": float((rho >= 1.0).sum()),
    }


def sensibilidade_throughput(
    df_base: pd.DataFrame,
    throughputs: Sequence[int] = THROUGHPUTS_SENSIBILIDADE,
    params: Params = CENARIOS["base"],
) -> pd.DataFrame:
    """Varre throughput mantendo demanda e oferta fixas.

    A fila reprimida nao depende do throughput. Esta funcao reporta apenas
    metricas derivadas de capacidade: deficit, rho divergente e LSI nacional.
    """
    schemas.validar_entrada(df_base)
    demanda = (
        df_base[schemas.COL_INCIDENCIA_SEM_PNM].to_numpy(dtype=float)
        * params.fracao_efetiva_rt
    )
    instalados = df_base[schemas.COL_LINACS].to_numpy(dtype=int)
    linhas: list[dict[str, int | float]] = []
    for throughput in throughputs:
        if throughput <= 0:
            raise ValueError("throughput deve ser positivo")
        deficit = np.maximum(
            np.ceil(demanda / throughput) - instalados,
            0,
        ).astype(int)
        with np.errstate(divide="ignore", invalid="ignore"):
            rho = np.where(
                instalados == 0,
                np.inf,
                demanda / (instalados * throughput),
            )
        lsi_nacional = demanda.sum() / (instalados.sum() * throughput) * 100.0
        linhas.append(
            {
                "throughput": int(throughput),
                "deficit_linacs": int(deficit.sum()),
                "ufs_fila_divergente": int((rho >= 1.0).sum()),
                "lsi_nacional": round(float(lsi_nacional), 1),
            }
        )
    return pd.DataFrame(linhas)


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

    capacidade = linacs * params.linac_throughput
    util = np.where(linacs == 0, np.inf, demanda / np.where(linacs == 0, 1, capacidade))
    folga = capacidade - demanda
    espera = np.where(
        (linacs == 0) | (folga <= 0),
        np.inf,
        reprimida / np.where(folga > 0, folga, np.nan) * 12.0,
    )
    prazo = util < 1.0
    razoes = RAZOES_EQUIPE_PADRAO
    fisicos = np.ceil(deficit * razoes.fisico_medico).astype(int)
    oncos = np.ceil(deficit * razoes.radio_oncologista).astype(int)
    tecnicos = np.ceil(deficit * razoes.tecnico_rtt).astype(int)

    out[schemas.COL_DEMANDA_RT] = demanda
    out[schemas.COL_DEMANDA_REPRIMIDA] = reprimida
    out[schemas.COL_PACIENTES_POR_LINAC] = pacientes_por_linac
    out[schemas.COL_LSI] = lsi
    out[schemas.COL_GRADE] = grades
    out[schemas.COL_DEFICIT_LINACS] = deficit
    out[schemas.COL_DEF_FISICO] = fisicos
    out[schemas.COL_DEF_ONCO] = oncos
    out[schemas.COL_DEF_TECNICO] = tecnicos
    out[schemas.COL_DEF_PROFISSIONAIS] = fisicos + oncos + tecnicos
    out[schemas.COL_UTILIZACAO] = util
    out[schemas.COL_TEMPO_ESPERA_MESES] = espera
    out[schemas.COL_PRAZO_60D] = prazo
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

    util_nac = demanda_total / (linacs_total * params.linac_throughput) if linacs_total else math.inf
    rho_uf = df_calc[schemas.COL_UTILIZACAO]
    espera_uf = df_calc[schemas.COL_TEMPO_ESPERA_MESES]
    drenaveis = espera_uf[np.isfinite(espera_uf)]

    return {
        "demanda_rt_sus": demanda_total,
        "oferta_realizada": oferta_total,
        "demanda_reprimida": float(df_calc[schemas.COL_DEMANDA_REPRIMIDA].sum()),
        "linacs_instalados": float(linacs_total),
        "lsi_nacional": linac_shortage_index(demanda_total, linacs_total, params),
        "deficit_linacs": float(df_calc[schemas.COL_DEFICIT_LINACS].sum()),
        "deficit_fisico_medico": float(df_calc[schemas.COL_DEF_FISICO].sum()),
        "deficit_radio_oncologista": float(df_calc[schemas.COL_DEF_ONCO].sum()),
        "deficit_tecnico_rtt": float(df_calc[schemas.COL_DEF_TECNICO].sum()),
        "deficit_profissionais_total": float(
            df_calc[schemas.COL_DEF_PROFISSIONAIS].sum()
        ),
        "utilizacao_nacional": util_nac,
        "ufs_fila_divergente": float((rho_uf >= 1.0).sum()),
        "ufs_drenaveis": float(np.isfinite(espera_uf).sum()),
        "tempo_espera_mediano_meses": float(drenaveis.median()) if not drenaveis.empty else math.inf,
    }
