"""Aba Streamlit "Pergunte aos dados" para o agente deterministico."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from radarrt.agent import core

_EXEMPLOS = [
    "Quais os 5 estados com maior demanda reprimida?",
    "Qual o deficit de aceleradores em Tocantins?",
    "Quais estados estao em grade 3?",
    "Deficit total no Nordeste",
    "Compare SP e MG",
]


def render_agente(calc: pd.DataFrame) -> None:
    """Renderiza pergunta -> SQL -> tabela -> resposta no dashboard."""
    st.subheader("Pergunte aos dados")
    st.caption(
        "Agente deterministico: traduz portugues para SQL validado e consulta "
        "os indicadores ao vivo. Sem chave, sem rede, 100% offline."
    )

    conexao = core.conectar_duckdb(calc)

    col_pergunta, col_exemplo = st.columns([3, 2])
    with col_pergunta:
        pergunta = st.text_input(
            "Sua pergunta",
            placeholder=_EXEMPLOS[0],
            key="pergunta_agente",
        )
    with col_exemplo:
        exemplo = st.selectbox("ou escolha um exemplo", [""] + _EXEMPLOS)
        if exemplo:
            pergunta = exemplo

    if not pergunta:
        return

    resposta = core.responder_pergunta(pergunta, conexao)
    if not resposta.reconhecida:
        st.warning(resposta.frase)
        return

    st.success(resposta.frase)
    with st.expander("SQL gerado"):
        st.code(resposta.sql, language="sql")
    if resposta.resultado is not None and not resposta.resultado.empty:
        st.dataframe(resposta.resultado, use_container_width=True, hide_index=True)
