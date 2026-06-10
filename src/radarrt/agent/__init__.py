"""Agente conversacional deterministico do RadarRT."""

from .core import Resposta, conectar_duckdb, responder_pergunta

__all__ = ["Resposta", "conectar_duckdb", "responder_pergunta"]
