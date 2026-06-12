"""API publica do RadarRT."""

from .analise import auditar_base, avaliar_cenarios, preparar_datamart, ranking_prioridade
from .config import CENARIOS, RAZOES_EQUIPE_PADRAO, Params, RazoesEquipe
from .engine import (
    alocar_expansao,
    calcular_indicadores,
    cenario_parque,
    deficit_profissionais,
    linacs_para_meta,
    plano_nacional,
    resumo_nacional,
    sensibilidade_throughput,
    simular_uf,
)
from .pipeline import BaseRadarRT, Procedencia, construir_base
from .synthetic import gerar_regioes

__all__ = [
    "BaseRadarRT",
    "CENARIOS",
    "Params",
    "Procedencia",
    "RAZOES_EQUIPE_PADRAO",
    "RazoesEquipe",
    "alocar_expansao",
    "auditar_base",
    "avaliar_cenarios",
    "calcular_indicadores",
    "cenario_parque",
    "construir_base",
    "deficit_profissionais",
    "gerar_regioes",
    "linacs_para_meta",
    "plano_nacional",
    "preparar_datamart",
    "ranking_prioridade",
    "resumo_nacional",
    "sensibilidade_throughput",
    "simular_uf",
]
