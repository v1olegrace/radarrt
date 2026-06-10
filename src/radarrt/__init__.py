"""API publica do RadarRT."""

from .analise import auditar_base, avaliar_cenarios, preparar_datamart, ranking_prioridade
from .config import CENARIOS, Params
from .engine import calcular_indicadores, resumo_nacional
from .pipeline import BaseRadarRT, Procedencia, construir_base
from .synthetic import gerar_regioes

__all__ = [
    "BaseRadarRT",
    "CENARIOS",
    "Params",
    "Procedencia",
    "auditar_base",
    "avaliar_cenarios",
    "calcular_indicadores",
    "construir_base",
    "gerar_regioes",
    "preparar_datamart",
    "ranking_prioridade",
    "resumo_nacional",
]
