"""Dashboard Streamlit de demo para os CSVs versionados do RadarRT."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

from app.agent_tab import render_agente

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "data" / "outputs_2024"

UF_COORDS = {
    "AC": (-9.02, -70.81),
    "AL": (-9.57, -36.78),
    "AM": (-3.47, -65.10),
    "AP": (1.41, -51.77),
    "BA": (-12.58, -41.70),
    "CE": (-5.20, -39.53),
    "DF": (-15.78, -47.93),
    "ES": (-19.19, -40.34),
    "GO": (-15.98, -49.86),
    "MA": (-5.42, -45.44),
    "MG": (-18.10, -44.38),
    "MS": (-20.51, -54.54),
    "MT": (-12.64, -55.42),
    "PA": (-3.79, -52.48),
    "PB": (-7.28, -36.72),
    "PE": (-8.38, -37.86),
    "PI": (-6.60, -42.28),
    "PR": (-24.89, -51.55),
    "RJ": (-22.25, -42.66),
    "RN": (-5.81, -36.59),
    "RO": (-10.83, -63.34),
    "RR": (1.99, -61.33),
    "RS": (-30.17, -53.50),
    "SC": (-27.45, -50.95),
    "SE": (-10.57, -37.45),
    "SP": (-22.19, -48.79),
    "TO": (-10.17, -48.30),
}
GRADE_COLORS = {
    0: [46, 125, 50, 210],
    1: [124, 179, 66, 220],
    2: [251, 140, 0, 225],
    3: [216, 67, 21, 230],
    4: [183, 28, 28, 240],
}


@st.cache_data
def carregar_mart() -> dict[str, pd.DataFrame]:
    """Carrega os CSVs versionados usados na demo."""
    return {
        "indicadores": pd.read_csv(OUTPUT_DIR / "indicadores_base.csv"),
        "ranking": pd.read_csv(OUTPUT_DIR / "ranking_prioridade.csv"),
        "resumo": pd.read_csv(OUTPUT_DIR / "resumo_nacional.csv"),
        "sensibilidade": pd.read_csv(OUTPUT_DIR / "sensibilidade_cenarios.csv"),
        "procedencia": pd.read_csv(OUTPUT_DIR / "procedencia.csv"),
    }


def valor_metricas(df: pd.DataFrame, metrica: str) -> float:
    """Extrai um valor do CSV chave-valor."""
    return float(df.set_index("metrica").loc[metrica, "valor"])


def formatar_int(valor: float) -> str:
    """Formata inteiros com separador brasileiro simples."""
    return f"{round(valor):,}".replace(",", ".")


def formatar_float(valor: float) -> str:
    """Formata uma casa decimal com virgula."""
    return f"{valor:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def preparar_mapa(indicadores: pd.DataFrame) -> pd.DataFrame:
    """Adiciona coordenadas aproximadas ao mart por UF."""
    mapa = indicadores.copy()
    mapa["lat"] = mapa["uf"].map(lambda uf: UF_COORDS[uf][0])
    mapa["lon"] = mapa["uf"].map(lambda uf: UF_COORDS[uf][1])
    mapa["color"] = mapa["grade"].map(lambda grade: GRADE_COLORS[int(grade)])
    mapa["radius"] = (mapa["demanda_reprimida"].clip(lower=500) ** 0.5) * 1800
    return mapa


def render_mapa(indicadores: pd.DataFrame) -> None:
    """Renderiza um mapa de bolhas por prioridade."""
    mapa = preparar_mapa(indicadores)
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=mapa,
        get_position="[lon, lat]",
        get_radius="radius",
        get_fill_color="color",
        pickable=True,
        stroked=True,
        get_line_color=[40, 40, 40, 180],
        line_width_min_pixels=1,
    )
    deck = pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(latitude=-14.2, longitude=-52.9, zoom=3.15),
        layers=[layer],
        tooltip={
            "html": (
                "<b>{uf}</b><br/>Grade: {grade}<br/>"
                "Demanda reprimida: {demanda_reprimida}<br/>"
                "Deficit LINACs: {deficit_linacs}<br/>LSI: {lsi}"
            )
        },
    )
    st.pydeck_chart(deck, use_container_width=True)


def render_visao_geral(mart: dict[str, pd.DataFrame]) -> None:
    """Renderiza cards, mapa e ranking principal."""
    indicadores = mart["indicadores"]
    resumo = mart["resumo"]
    ranking = mart["ranking"]

    st.caption("Mart operacional: SIA-AR 2024 + INCA 2026 + parque LINAC estimado por UF.")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Demanda reprimida", formatar_int(valor_metricas(resumo, "demanda_reprimida")))
    col2.metric("Deficit estrutural LINACs", formatar_int(valor_metricas(resumo, "deficit_linacs")))
    col3.metric("LSI nacional", formatar_float(valor_metricas(resumo, "lsi_nacional")))
    col4.metric("LINACs estimados", formatar_int(valor_metricas(resumo, "linacs_instalados")))

    esquerda, direita = st.columns([1.35, 1])
    with esquerda:
        st.subheader("Prioridade territorial")
        render_mapa(indicadores)
    with direita:
        st.subheader("Top UFs por prioridade")
        st.dataframe(
            ranking[
                [
                    "uf",
                    "regiao",
                    "demanda_reprimida",
                    "deficit_linacs",
                    "lsi",
                    "grade",
                ]
            ],
            hide_index=True,
            use_container_width=True,
        )

    st.subheader("Demanda reprimida por UF")
    barras = indicadores.sort_values("demanda_reprimida", ascending=False).set_index("uf")
    st.bar_chart(barras["demanda_reprimida"], use_container_width=True)


def render_sensibilidade(mart: dict[str, pd.DataFrame]) -> None:
    """Renderiza tabela de cenarios."""
    st.subheader("Cenarios")
    st.dataframe(mart["sensibilidade"], hide_index=True, use_container_width=True)


def render_caveats(mart: dict[str, pd.DataFrame]) -> None:
    """Renderiza ressalvas metodologicas para pitch."""
    proc = mart["procedencia"].set_index("metrica")["valor"].to_dict()
    st.subheader("Limitacoes honestas")
    st.markdown(
        """
- RadarRT nao prioriza pacientes individualmente e nao substitui regulacao,
  auditoria institucional ou estudos oficiais.
- A oferta SIA-AR 2024 esta atribuida por UF do estabelecimento (`AP_UFMUN`),
  nao por residencia do paciente.
- O parque LINAC por UF e estimado a partir de fonte publicada e esta marcado
  como `estimado (parque publicado)` em `procedencia.csv`.
- Rankings por UF sao exploratorios: quando oferta observada e capacidade
  estimada divergem, isso vira alerta metodologico, nao numero escondido.
"""
    )
    st.subheader("Procedencia")
    st.json(proc)
    st.subheader("Arquitetura")
    st.code(
        "\n".join(
            [
                "INCA 2026 ----\\",
                "SIA-AR 2024 ----> base canonica -> motor deterministico -> CSVs -> dashboard",
                "LINAC park ---/                                      \\",
                "                                                       -> agente SQL offline",
            ]
        ),
        language="text",
    )


def main() -> None:
    """Entrada Streamlit."""
    st.set_page_config(
        page_title="RadarRT",
        layout="wide",
    )
    st.title("RadarRT")
    st.caption("Radar auditavel de demanda reprimida de radioterapia no SUS.")
    mart = carregar_mart()

    aba_visao, aba_sensibilidade, aba_agente, aba_caveats = st.tabs(
        ["Visao geral", "Sensibilidade", "Pergunte aos dados", "Caveats"]
    )
    with aba_visao:
        render_visao_geral(mart)
    with aba_sensibilidade:
        render_sensibilidade(mart)
    with aba_agente:
        render_agente(mart["indicadores"])
    with aba_caveats:
        render_caveats(mart)


if __name__ == "__main__":
    main()
