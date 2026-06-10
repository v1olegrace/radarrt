"""Orquestrador do agente conversacional sem LLM.

Fluxo: pergunta -> parse -> SQL validado -> execucao -> frase.
O executor usa a interface DB-API, entao roda com DuckDB em producao e sqlite3
nos testes offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from . import intent as intent_mod
from . import responder
from . import sql as sql_mod


@dataclass(frozen=True)
class Resposta:
    """Resultado completo de uma pergunta ao agente."""

    pergunta: str
    intent: intent_mod.Intent
    sql: str | None
    resultado: pd.DataFrame | None
    frase: str
    reconhecida: bool


def conectar_duckdb(df: pd.DataFrame) -> Any:
    """Cria conexao DuckDB in-memory com a tabela ``indicadores``."""
    import duckdb

    con = duckdb.connect()
    con.register("indicadores", df)
    return con


def executar(conexao: Any, sql: str) -> pd.DataFrame:
    """Executa SQL via DB-API e devolve um DataFrame."""
    cursor = conexao.execute(sql)
    colunas = [desc[0] for desc in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=colunas)


def responder_pergunta(pergunta: str, conexao: Any) -> Resposta:
    """Pergunta em PT-BR -> resposta estruturada e SQL transparente."""
    intent = intent_mod.parse(pergunta)
    if intent.tipo == "desconhecido":
        return Resposta(
            pergunta=pergunta,
            intent=intent,
            sql=None,
            resultado=None,
            frase=responder.texto_sugestoes(),
            reconhecida=False,
        )

    sql = sql_mod.build_sql(intent)
    resultado = executar(conexao, sql)
    return Resposta(
        pergunta=pergunta,
        intent=intent,
        sql=sql,
        resultado=resultado,
        frase=responder.frase(intent, resultado),
        reconhecida=True,
    )
