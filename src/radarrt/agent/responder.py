"""Gera frases em PT-BR a partir do resultado tabular."""

from __future__ import annotations

import math

import pandas as pd

from . import nomes
from .intent import Intent

SUGESTOES = [
    "Quais os 5 estados com maior demanda reprimida?",
    "Qual o deficit de aceleradores em Tocantins?",
    "Quais estados estao em grade 3?",
    "Deficit total no Nordeste",
    "Compare SP e MG",
]


def _num(valor: object) -> str:
    """Formata numeros para PT-BR simples, preservando ausencia de dado."""
    if valor is None:
        return "sem dado"
    if isinstance(valor, float) and math.isnan(valor):
        return "sem dado"
    if isinstance(valor, float) and not valor.is_integer():
        return f"{valor:,.1f}".replace(",", ".")
    return f"{int(valor):,}".replace(",", ".")


def frase(intent: Intent, df: pd.DataFrame) -> str:
    """Transforma a saida da query em resposta curta de palco."""
    if df.empty:
        return "Nao encontrei dados para essa pergunta."
    rotulo = nomes.ROTULO_METRICA.get(intent.metrica or "", intent.metrica or "")

    if intent.tipo == "ranking":
        direcao = "maior" if intent.ordem == "desc" else "menor"
        itens = ", ".join(
            f"{linha['uf']} ({_num(linha[intent.metrica])})"
            for _, linha in df.iterrows()
        )
        return f"Estados com {direcao} {rotulo}: {itens}."

    if intent.tipo == "valor_uf":
        linha = df.iloc[0]
        return f"{linha['uf']}: {rotulo} = {_num(linha[intent.metrica])}."

    if intent.tipo == "comparacao":
        partes = [
            f"{linha['uf']} ({_num(linha[intent.metrica])})"
            for _, linha in df.iterrows()
        ]
        return f"Comparacao de {rotulo}: " + " vs ".join(partes) + "."

    if intent.tipo == "filtro_grade":
        ufs = ", ".join(df["uf"].tolist()) or "nenhum"
        return f"Estados em grade {intent.grade}: {ufs}."

    if intent.tipo == "agregado":
        total = df.iloc[0]["total"]
        escopo = intent.regiao or "Brasil"
        return f"{rotulo} total ({escopo}): {_num(total)}."

    return "Pergunta nao reconhecida."


def texto_sugestoes() -> str:
    """Retorna exemplos acionaveis quando a pergunta nao foi reconhecida."""
    linhas = "\n".join(f"  - {sugestao}" for sugestao in SUGESTOES)
    return "Nao entendi a pergunta. Tente algo como:\n" + linhas
