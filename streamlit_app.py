"""Dashboard Streamlit do RadarRT - identidade visual Cherenkov.

Radar de demanda reprimida de radioterapia no SUS. Espaço profundo, glow
Cherenkov (#3DDCFF), Poppins no display e leitura monoespacada nos números,
como um instrumento que ilumina a fila invisível.
"""

from __future__ import annotations

import html
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pandas as pd
import pydeck as pdk
import streamlit as st

from app.agent_tab import render_agente
from radarrt import CENARIOS, engine, geo
from radarrt.agent import nomes

OUTPUT_DIR = ROOT / "data" / "outputs_2024"
GEOJSON_UF = ROOT / "data" / "geo" / "br_uf.json"

# ---------------------------------------------------------------------------
# Identidade visual
# ---------------------------------------------------------------------------
UF_COORDS = {
    "AC": (-9.02, -70.81), "AL": (-9.57, -36.78), "AM": (-3.47, -65.10),
    "AP": (1.41, -51.77), "BA": (-12.58, -41.70), "CE": (-5.20, -39.53),
    "DF": (-15.78, -47.93), "ES": (-19.19, -40.34), "GO": (-15.98, -49.86),
    "MA": (-5.42, -45.44), "MG": (-18.10, -44.38), "MS": (-20.51, -54.54),
    "MT": (-12.64, -55.42), "PA": (-3.79, -52.48), "PB": (-7.28, -36.72),
    "PE": (-8.38, -37.86), "PI": (-6.60, -42.28), "PR": (-24.89, -51.55),
    "RJ": (-22.25, -42.66), "RN": (-5.81, -36.59), "RO": (-10.83, -63.34),
    "RR": (1.99, -61.33), "RS": (-30.17, -53.50), "SC": (-27.45, -50.95),
    "SE": (-10.57, -37.45), "SP": (-22.19, -48.79), "TO": (-10.17, -48.30),
}
# Rampa de grade (0 controlado -> 4 sem serviço). Coral é o hook emocional.
GRADE_HEX = {0: "#2DD4A7", 1: "#A3E635", 2: "#FB923C", 3: "#F87171", 4: "#FF5470"}
GRADE_RGB = {
    0: [45, 212, 167, 235], 1: [190, 242, 100, 238],
    2: [255, 174, 66, 242], 3: [255, 97, 112, 246],
    4: [255, 43, 85, 252],
}
GRADE_LABEL = {
    0: "Controlado", 1: "Atenção", 2: "Crítico", 3: "Severo",
    4: "Sem serviço",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

:root {
  --void:#070B16; --abyss:#0C1322; --panel:#111A2E; --panel-2:#16203A;
  --line:rgba(132,160,210,0.14); --line-strong:rgba(132,160,210,0.28);
  --cherenkov:#3DDCFF; --cherenkov-soft:#7CE7FF; --violet:#7C5CFF;
  --ink:#EAF2FF; --muted:#8090B0; --coral:#FF5470;
}

/* ---- base ---- */
.stApp, [data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1100px 560px at 12% -12%, rgba(61,220,255,0.12), transparent 60%),
    radial-gradient(820px 480px at 102% -6%, rgba(124,92,255,0.10), transparent 55%),
    linear-gradient(180deg, #070B16 0%, #0A1020 60%, #080D1A 100%);
  color: var(--ink);
  font-family:'Poppins',sans-serif;
}
[data-testid="stHeader"]{background:transparent;}
#MainMenu, footer, [data-testid="stToolbar"]{visibility:hidden;}
.block-container{padding-top:2.2rem; padding-bottom:3rem; max-width:1180px;}
[data-testid="stMarkdownContainer"] p{color:var(--ink);}

/* ---- hero ---- */
.rt-eyebrow{
  font-size:.72rem; letter-spacing:.34em; text-transform:uppercase;
  color:var(--cherenkov); font-weight:600; display:flex; align-items:center; gap:.7rem;
}
.rt-eyebrow::before{
  content:""; width:34px; height:1px;
  background:linear-gradient(90deg,var(--cherenkov),transparent);
}
.rt-title{
  font-size:2.55rem; line-height:1.08; font-weight:700; letter-spacing:-.02em;
  margin:.55rem 0 .5rem; color:var(--ink);
}
.rt-title em{
  font-style:normal; color:var(--cherenkov);
  text-shadow:0 0 26px rgba(61,220,255,.45);
}
.rt-sub{color:var(--muted); font-size:1.02rem; font-weight:300; max-width:62ch;}
.rt-prov{
  display:inline-flex; gap:.5rem; flex-wrap:wrap; margin-top:1rem;
}
.rt-chip{
  font-size:.72rem; letter-spacing:.02em; color:var(--cherenkov-soft);
  border:1px solid var(--line-strong); border-radius:999px;
  padding:.3rem .8rem; background:rgba(61,220,255,.05);
}
.rt-chip b{color:var(--ink); font-weight:600;}

/* ---- metric cards ---- */
.rt-cards{display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin:1.8rem 0 .4rem;}
.rt-card{
  position:relative; overflow:hidden; border-radius:18px;
  background:linear-gradient(160deg, var(--panel) 0%, var(--abyss) 100%);
  border:1px solid var(--line); padding:1.15rem 1.2rem 1.25rem;
  box-shadow:0 1px 0 rgba(255,255,255,.03) inset, 0 18px 40px -28px rgba(0,0,0,.9);
  min-height:9rem;
}
.rt-card::after{
  content:""; position:absolute; inset:0 0 auto 0; height:2px;
  background:linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity:.9;
}
.rt-card__eyebrow{
  font-size:.66rem; letter-spacing:.18em; text-transform:uppercase;
  color:var(--muted); font-weight:600;
}
.rt-rho{text-transform:none;}
.rt-card__value{
  font-family:'JetBrains Mono',monospace; font-weight:700;
  font-size:2.1rem; line-height:1; margin:.55rem 0 .2rem;
  color:var(--ink); text-shadow:0 0 22px var(--glow);
  white-space:nowrap; letter-spacing:0;
}
.rt-card__value--text{font-size:1.62rem;}
.rt-card__value--xs{font-size:1.05rem; line-height:1.2; white-space:normal; word-break:break-word;}
.rt-card__unit{font-size:.74rem; color:var(--muted); font-weight:300;}

/* ---- section header ---- */
.rt-sec{
  font-size:.72rem; letter-spacing:.26em; text-transform:uppercase;
  color:var(--muted); font-weight:600; margin:.2rem 0 .9rem;
  display:flex; align-items:center; gap:.7rem;
}
.rt-sec::after{content:""; flex:1; height:1px; background:var(--line);}

/* ---- grade-4 hook ---- */
.rt-hook{
  border-radius:16px; padding:1.05rem 1.25rem; margin:.3rem 0 1.4rem;
  background:linear-gradient(120deg, rgba(255,84,112,.14), rgba(255,84,112,.03));
  border:1px solid rgba(255,84,112,.34);
  display:flex; align-items:center; gap:1rem;
}
.rt-hook__dot{
  width:11px; height:11px; border-radius:50%; background:var(--coral);
  box-shadow:0 0 0 0 rgba(255,84,112,.6); animation:pulse 2s infinite; flex:none;
}
@keyframes pulse{
  0%{box-shadow:0 0 0 0 rgba(255,84,112,.55);}
  70%{box-shadow:0 0 0 14px rgba(255,84,112,0);}
  100%{box-shadow:0 0 0 0 rgba(255,84,112,0);}
}
.rt-hook b{color:var(--coral);}
@media (prefers-reduced-motion: reduce){.rt-hook__dot{animation:none;}}

/* ---- validation story ---- */
.rt-val-hero{
  position:relative; overflow:hidden; border-radius:18px;
  padding:1.25rem 1.35rem; margin:.2rem 0 1.15rem;
  background:
    linear-gradient(135deg, rgba(61,220,255,.18), rgba(124,92,255,.14) 52%, rgba(255,84,112,.15)),
    linear-gradient(180deg, rgba(17,26,46,.96), rgba(9,14,28,.96));
  border:1px solid rgba(124,231,255,.34);
  box-shadow:0 24px 52px -36px rgba(61,220,255,.75);
}
.rt-val-hero::after{
  content:""; position:absolute; inset:0 0 auto 0; height:2px;
  background:linear-gradient(90deg, var(--cherenkov), var(--violet), var(--coral));
}
.rt-val-eyebrow{
  color:var(--cherenkov-soft); font-size:.68rem; letter-spacing:.22em;
  text-transform:uppercase; font-weight:700;
}
.rt-val-title{font-size:1.5rem; line-height:1.18; font-weight:700; margin:.4rem 0 .35rem;}
.rt-val-copy{max-width:78ch; color:#C9D6F2; font-size:.92rem;}
.rt-val-badges{display:flex; flex-wrap:wrap; gap:.55rem; margin-top:.9rem;}
.rt-val-badges span{
  border:1px solid rgba(124,231,255,.32); border-radius:999px;
  padding:.42rem .7rem; background:rgba(8,13,26,.56); color:#DDE8FF; font-size:.78rem;
}
.rt-val-badges b{color:var(--cherenkov-soft);}
.rt-val-panel{
  border:1px solid rgba(132,160,210,.24); border-radius:16px;
  background:linear-gradient(180deg, rgba(17,26,46,.86), rgba(9,14,28,.88));
  padding:1rem 1.05rem; margin:1rem 0 1.2rem;
}
.rt-val-panel__title{
  color:#EAF2FF; font-weight:700; font-size:.88rem; margin-bottom:.75rem;
}
.rt-val-row{
  display:grid; grid-template-columns:132px 58px 1fr 62px; gap:.7rem;
  align-items:center; padding:.48rem 0; border-top:1px solid rgba(132,160,210,.12);
}
.rt-val-row:first-of-type{border-top:0;}
.rt-val-region{font-weight:700; color:#EAF2FF;}
.rt-val-rho{
  font-family:'JetBrains Mono',monospace; color:var(--coral); font-size:.78rem;
}
.rt-val-track{
  height:12px; border-radius:999px; overflow:hidden; background:rgba(132,160,210,.16);
}
.rt-val-fill{display:block; height:100%; border-radius:inherit; box-shadow:0 0 16px rgba(61,220,255,.35);}
.rt-val-pct{
  font-family:'JetBrains Mono',monospace; color:var(--cherenkov-soft);
  font-size:.78rem; text-align:right;
}
.rt-val-svg{
  width:100%; height:auto; display:block; border-radius:16px;
  background:linear-gradient(180deg, rgba(10,16,32,.96), rgba(7,11,22,.98));
  border:1px solid rgba(132,160,210,.24);
}
.rt-val-table{
  width:100%; border-collapse:separate; border-spacing:0; overflow:hidden;
  border:1px solid rgba(132,160,210,.22); border-radius:14px; margin:1rem 0;
  background:rgba(17,26,46,.72);
}
.rt-val-table th{
  text-align:left; color:#7CE7FF; font-size:.72rem; letter-spacing:.12em;
  text-transform:uppercase; padding:.75rem .9rem; background:rgba(61,220,255,.08);
}
.rt-val-table td{
  color:#EAF2FF; padding:.68rem .9rem; border-top:1px solid rgba(132,160,210,.12);
  font-size:.84rem;
}
.rt-val-table td:nth-child(2), .rt-val-table td:nth-child(3){
  font-family:'JetBrains Mono',monospace; color:#DDE8FF;
}

/* ---- ranking ---- */
.rt-rank{display:flex; flex-direction:column; gap:8px;}
.rt-row{
  display:grid; grid-template-columns:auto 1fr auto; align-items:center; gap:.7rem;
  background:var(--panel); border:1px solid var(--line);
  border-radius:12px; padding:.6rem .85rem;
}
.rt-row__uf{
  font-family:'JetBrains Mono',monospace; font-weight:700; font-size:.95rem;
  color:var(--ink); width:2.4ch;
}
.rt-row__meta{font-size:.72rem; color:var(--muted);}
.rt-row__fila{font-family:'JetBrains Mono',monospace; color:var(--cherenkov-soft); font-weight:500;}
.rt-grade{
  font-size:.62rem; letter-spacing:.06em; text-transform:uppercase; font-weight:600;
  padding:.22rem .55rem; border-radius:999px; white-space:nowrap;
}
.rt-map-note{
  color:#B8C7E8; font-size:.78rem; margin:.45rem 0 .2rem;
}

/* ---- streamlit widgets ---- */
.stTabs [data-baseweb="tab-list"]{gap:6px; border-bottom:1px solid var(--line);}
.stTabs [data-baseweb="tab"]{
  background:transparent; color:var(--muted); font-family:'Poppins'; font-weight:500;
  font-size:.86rem; letter-spacing:.01em; padding:.5rem .2rem;
}
.stTabs [aria-selected="true"]{color:var(--cherenkov)!important;}
.stTabs [data-baseweb="tab-highlight"]{background:var(--cherenkov)!important;}
[data-testid="stDataFrame"]{border:1px solid var(--line); border-radius:12px;}
.stTextInput input, .stSelectbox div[data-baseweb="select"]>div{
  background:var(--panel)!important; border:1px solid var(--line-strong)!important;
  color:var(--ink)!important; border-radius:10px!important;
}
.stTextInput input::placeholder{color:var(--muted)!important;}
[data-testid="stExpander"]{border:1px solid var(--line); border-radius:12px; background:var(--abyss);}
.stAlert{border-radius:12px; border:1px solid var(--line-strong);}
.rt-foot{color:var(--muted); font-size:.72rem; margin-top:1.4rem; border-top:1px solid var(--line); padding-top:.9rem;}

/* ---- animacoes ---- */
@keyframes rt-rise{from{opacity:0; transform:translateY(15px);} to{opacity:1; transform:none;}}
@keyframes rt-breathe{0%,100%{opacity:.45; transform:scale(1);} 50%{opacity:.95; transform:scale(1.09);}}
.rt-anim{opacity:0; animation:rt-rise .62s cubic-bezier(.2,.7,.2,1) forwards;}
.block-container{position:relative; z-index:1;}
.stApp::before{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
  background:radial-gradient(640px 380px at 17% 6%, rgba(61,220,255,.10), transparent 62%);
  animation:rt-breathe 9s ease-in-out infinite;
}
.rt-card{transition:transform .25s ease, border-color .25s ease, box-shadow .25s ease;}
.rt-card:hover{
  transform:translateY(-5px); border-color:var(--line-strong);
  box-shadow:0 1px 0 rgba(255,255,255,.05) inset, 0 28px 54px -26px rgba(0,0,0,.95);
}
.rt-card:hover .rt-card__value{text-shadow:0 0 32px var(--glow);}
.rt-row{transition:transform .2s ease, border-color .2s ease, background .2s ease;}
.rt-row:hover{transform:translateX(5px); border-color:var(--line-strong); background:var(--panel-2);}
.rt-chip{transition:border-color .2s ease, background .2s ease;}
.rt-chip:hover{border-color:var(--cherenkov); background:rgba(61,220,255,.10);}

@media (max-width:900px){
  .rt-cards{grid-template-columns:repeat(2,1fr);}
  .rt-title{font-size:2rem;}
}
@media (max-width:520px){
  .rt-cards{grid-template-columns:1fr;}
  .rt-val-row{grid-template-columns:1fr; gap:.28rem;}
  .rt-val-pct{text-align:left;}
}
@media (prefers-reduced-motion: reduce){
  .rt-anim{animation:none; opacity:1;}
  .stApp::before{animation:none;}
  .rt-card:hover, .rt-row:hover{transform:none;}
}
</style>
"""


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------
@st.cache_data
def carregar_mart() -> dict[str, pd.DataFrame]:
    """Carrega os CSVs versionados do mart operacional."""
    mart = {
        "indicadores": pd.read_csv(OUTPUT_DIR / "indicadores_base.csv"),
        "ranking": pd.read_csv(OUTPUT_DIR / "ranking_prioridade.csv"),
        "resumo": pd.read_csv(OUTPUT_DIR / "resumo_nacional.csv"),
        "sensibilidade": pd.read_csv(OUTPUT_DIR / "sensibilidade_cenarios.csv"),
        "sensibilidade_throughput": pd.read_csv(
            OUTPUT_DIR / "sensibilidade_throughput.csv"
        ),
        "procedencia": pd.read_csv(OUTPUT_DIR / "procedencia.csv"),
        "plano": pd.read_csv(OUTPUT_DIR / "plano_nacional.csv"),
        "cenarios_parque": pd.read_csv(OUTPUT_DIR / "cenarios_parque.csv"),
    }
    opcionais = {
        "painel_validacao": OUTPUT_DIR / "painel_validacao.csv",
        "painel_validacao_regional": OUTPUT_DIR / "painel_validacao_regional.csv",
        "serie_temporal": OUTPUT_DIR / "serie_temporal.csv",
    }
    for chave, caminho in opcionais.items():
        if caminho.exists():
            mart[chave] = pd.read_csv(caminho)
    return mart


def _valor(df: pd.DataFrame, metrica: str) -> float:
    return float(df.set_index("metrica").loc[metrica, "valor"])


def _int_br(valor: float) -> str:
    return f"{round(valor):,}".replace(",", ".")


def _float_br(valor: float, casas: int = 1) -> str:
    txt = f"{valor:,.{casas}f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


def _moeda_curta(valor: float) -> str:
    if valor >= 1_000_000_000:
        return f"R$ {_float_br(valor / 1_000_000_000, 2)} bi"
    return f"R$ {_float_br(valor / 1_000_000, 0)} mi"


def _pct(valor: float) -> str:
    if valor == float("inf"):
        return "inf"
    return _float_br(valor, 2)


def _pct_label(valor: float) -> str:
    if pd.isna(valor):
        return "-"
    return f"{_float_br(float(valor) * 100, 1)}%"


def _html(valor: object) -> str:
    return html.escape(str(valor), quote=True)


def _tempo(valor: float) -> str:
    if valor == float("inf"):
        return "fila crescente"
    return f"{_float_br(valor, 1)} meses"


def _cards_html(cards: list[tuple[str, str, str, str, str]]) -> None:
    html = '<div class="rt-cards">'
    for titulo, valor, unidade, accent, glow in cards:
        titulo_html = titulo.replace("ρ", '<span class="rt-rho">ρ</span>')
        valor_class = "rt-card__value"
        if any(letra.isalpha() for letra in str(valor)):
            if len(str(valor)) > 9:
                valor_class += " rt-card__value--xs"
            else:
                valor_class += " rt-card__value--text"
        html += (
            f'<div class="rt-card" style="--accent:{accent}; --glow:{glow}">'
            f'<div class="rt-card__eyebrow">{titulo_html}</div>'
            f'<div class="{valor_class}">{valor}</div>'
            f'<div class="rt-card__unit">{unidade}</div></div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def _render_validacao_hero(spearman: float, saturadas: str, piores: str) -> None:
    """Resumo visual da validação externa contra o PAINEL-Oncologia."""
    confirma = pd.notna(spearman) and spearman < 0
    titulo = (
        "O PAINEL-Oncologia reforça o sinal de saturação"
        if confirma
        else "O PAINEL-Oncologia entra como auditoria externa"
    )
    texto = (
        "Quando a carga estrutural sobe, o cumprimento regional da Lei dos "
        "60 dias cai. A leitura é independente do cálculo do RadarRT e usa "
        "somente o cache PAINEL 2019-2024."
        if confirma
        else "A camada compara o RadarRT com a base oficial sem ajustar o "
        "recorte do PAINEL. O resultado fica exposto, mesmo quando a correlação "
        "não favorece a narrativa."
    )
    st.markdown(
        f"""
        <div class="rt-val-hero">
          <div class="rt-val-eyebrow">Validação externa independente</div>
          <div class="rt-val-title">{_html(titulo)}</div>
          <div class="rt-val-copy">{_html(texto)}</div>
          <div class="rt-val-badges">
            <span><b>{_float_br(float(spearman), 2)}</b> Spearman regional</span>
            <span><b>{_html(saturadas)}</b> maior ρ</span>
            <span><b>{_html(piores)}</b> menor <=60d</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_validacao_regional(regional: pd.DataFrame) -> None:
    """Barras regionais de alto contraste para o cumprimento em até 60 dias."""
    tabela = regional.copy()
    tabela["rho_plot"] = tabela["rho_medio"].replace(float("inf"), pd.NA)
    linhas = ""
    for _, row in tabela.sort_values("pct_ate_60d_medio").iterrows():
        pct = float(row["pct_ate_60d_medio"]) if pd.notna(row["pct_ate_60d_medio"]) else 0.0
        rho = row["rho_medio"]
        rho_label = "∞" if float(rho) == float("inf") else _float_br(float(rho), 2)
        largura = max(4.0, min(100.0, pct * 100))
        cor = (
            "linear-gradient(90deg, #FF5470, #FFAE42)"
            if pct < 0.25
            else "linear-gradient(90deg, #FFAE42, #7CE7FF)"
        )
        if pct >= 0.32:
            cor = "linear-gradient(90deg, #2DD4A7, #7CE7FF)"
        linhas += (
            '<div class="rt-val-row">'
            f'<div class="rt-val-region">{_html(row["regiao"])}</div>'
            f'<div class="rt-val-rho">ρ {rho_label}</div>'
            '<div class="rt-val-track">'
            f'<span class="rt-val-fill" style="width:{largura:.1f}%; background:{cor}"></span>'
            '</div>'
            f'<div class="rt-val-pct">{_pct_label(pct)}</div>'
            '</div>'
        )
    st.markdown(
        f"""
        <div class="rt-val-panel">
          <div class="rt-val-panel__title">Cumprimento regional da Lei dos 60 dias</div>
          {linhas}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_validacao_scatter(painel: pd.DataFrame) -> None:
    """Scatter SVG offline: ρ estrutural x percentual em até 60 dias por UF."""
    scatter = painel.dropna(subset=["pct_ate_60d"]).copy()
    if scatter.empty:
        return
    finitos = scatter.loc[
        scatter["utilizacao"].astype(float) < float("inf"),
        "utilizacao",
    ].astype(float)
    x_max = max(2.0, float(finitos.max()) * 1.12 if not finitos.empty else 2.0)
    y_max = max(40.0, float(scatter["pct_ate_60d"].max()) * 120)
    plot = {"left": 58, "top": 28, "right": 690, "bottom": 282}
    largura = plot["right"] - plot["left"]
    altura = plot["bottom"] - plot["top"]
    corte_x = plot["left"] + min(1.0 / x_max, 1.0) * largura

    # Ticks eixo X (ρ estrutural): 0, 1, 2
    ticks_x = [v for v in [0.0, 1.0, 2.0] if v <= x_max * 1.01]
    # Ticks eixo Y (% <=60d): 0%, 25%, 50%
    ticks_y = [v for v in [0.0, 25.0, 50.0] if v <= y_max * 1.01]

    def _tx(v: float) -> float:
        return plot["left"] + (v / x_max) * largura

    def _ty(pct: float) -> float:
        return plot["bottom"] - min(pct / y_max, 1.0) * altura

    elementos = [
        f'<line x1="{plot["left"]}" y1="{plot["bottom"]}" x2="{plot["right"]}" '
        f'y2="{plot["bottom"]}" stroke="rgba(234,242,255,.35)" />',
        f'<line x1="{plot["left"]}" y1="{plot["top"]}" x2="{plot["left"]}" '
        f'y2="{plot["bottom"]}" stroke="rgba(234,242,255,.35)" />',
        f'<line x1="{corte_x:.1f}" y1="{plot["top"]}" x2="{corte_x:.1f}" '
        f'y2="{plot["bottom"]}" stroke="#FF5470" stroke-dasharray="6 6" />',
        f'<text x="{corte_x + 8:.1f}" y="{plot["top"] + 14}" '
        'fill="#FF9AAD" font-size="12">ρ = 1</text>',
    ]
    # Grid lines + tick labels eixo X
    for v in ticks_x:
        tx = _tx(v)
        label = str(int(v))
        elementos += [
            f'<line x1="{tx:.1f}" y1="{plot["bottom"]}" x2="{tx:.1f}" '
            f'y2="{plot["bottom"] + 5}" stroke="rgba(234,242,255,.5)" />',
            f'<text x="{tx:.1f}" y="{plot["bottom"] + 16}" fill="#8090B0" '
            f'font-size="10" text-anchor="middle">{label}</text>',
            f'<line x1="{tx:.1f}" y1="{plot["top"]}" x2="{tx:.1f}" '
            f'y2="{plot["bottom"]}" stroke="rgba(234,242,255,.08)" />',
        ]
    # Grid lines + tick labels eixo Y
    for pct in ticks_y:
        ty = _ty(pct)
        label = f"{int(pct)}%"
        elementos += [
            f'<line x1="{plot["left"] - 5}" y1="{ty:.1f}" x2="{plot["left"]}" '
            f'y2="{ty:.1f}" stroke="rgba(234,242,255,.5)" />',
            f'<text x="{plot["left"] - 8}" y="{ty + 4:.1f}" fill="#8090B0" '
            f'font-size="10" text-anchor="end">{label}</text>',
            f'<line x1="{plot["left"]}" y1="{ty:.1f}" x2="{plot["right"]}" '
            f'y2="{ty:.1f}" stroke="rgba(234,242,255,.08)" />',
        ]

    # Pontos (circles) + coordenadas para rótulos
    pontos_coords: list[tuple[float, float, str, bool]] = []
    pct_q33 = float(scatter["pct_ate_60d"].quantile(0.33)) * 100
    for grade in range(5):
        pts = scatter.loc[scatter["grade"].astype(int) == grade]
        for _, row in pts.iterrows():
            util_raw = float(row["utilizacao"])
            util = x_max if util_raw == float("inf") else min(util_raw, x_max)
            pct = float(row["pct_ate_60d"]) * 100
            x = plot["left"] + (util / x_max) * largura
            y = plot["bottom"] - min(pct / y_max, 1.0) * altura
            cor = GRADE_HEX[int(row["grade"])]
            elementos.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.2" fill="{cor}" '
                'stroke="rgba(234,242,255,.84)" stroke-width="1.1">'
                f'<title>{_html(row["uf"])} · ρ {_pct(row["utilizacao"])} · '
                f'{_pct_label(row["pct_ate_60d"])}</title></circle>'
            )
            # Outlier: grade severo, ρ alto, ou pct abaixo do tercil inferior
            is_outlier = (
                int(row["grade"]) >= 3
                or util_raw > 1.5
                or pct < pct_q33
            )
            pontos_coords.append((x, y, str(row["uf"]), is_outlier))

    # Rótulos UF — apenas outliers, renderizados após os círculos (z-order)
    for x, y, uf, is_outlier in pontos_coords:
        if is_outlier:
            elementos.append(
                f'<text x="{x + 8:.1f}" y="{y - 5:.1f}" fill="rgba(234,242,255,.80)" '
                f'font-size="9" font-family="monospace">{_html(uf)}</text>'
            )

    svg = (
        '<svg class="rt-val-svg" viewBox="0 0 720 320" role="img" '
        'aria-label="Dispersão entre saturação estrutural e cumprimento em até 60 dias">'
        '<text x="24" y="22" fill="#EAF2FF" font-size="14" font-weight="700">'
        'UFs: saturação estrutural x atendimento em até 60 dias</text>'
        '<text x="24" y="306" fill="#8090B0" font-size="12">ρ estrutural</text>'
        '<text x="18" y="44" fill="#8090B0" font-size="12">% <=60d</text>'
        f'{"".join(elementos)}</svg>'
    )
    st.markdown(svg, unsafe_allow_html=True)


def _render_validacao_tabela(regional: pd.DataFrame) -> None:
    """Tabela escura para manter a validação no mesmo sistema visual."""
    linhas = ""
    for _, row in regional.sort_values("pct_ate_60d_medio").iterrows():
        rho = row["rho_medio"]
        rho_label = "∞" if float(rho) == float("inf") else _float_br(float(rho), 4)
        linhas += (
            "<tr>"
            f"<td>{_html(row['regiao'])}</td>"
            f"<td>{rho_label}</td>"
            f"<td>{_pct_label(row['pct_ate_60d_medio'])}</td>"
            "</tr>"
        )
    st.markdown(
        f"""
        <table class="rt-val-table">
          <thead><tr><th>Região</th><th>ρ médio</th><th>% <=60d médio</th></tr></thead>
          <tbody>{linhas}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Componentes
# ---------------------------------------------------------------------------
def render_hero(procedencia: pd.DataFrame) -> None:
    """Hero: a tese do projeto + procedencia honesta."""
    proc = procedencia.set_index("metrica")["valor"].to_dict()

    def chip(rotulo: str, origem: str) -> str:
        return f'<span class="rt-chip">{rotulo} <b>{origem}</b></span>'

    st.markdown(
        f"""
        <div class="rt-eyebrow rt-anim" style="animation-delay:.02s">RadarRT &middot; Radar de demanda reprimida</div>
        <div class="rt-title rt-anim" style="animation-delay:.10s">A maior barreira da radioterapia<br/>
          no Brasil é <em>invisível</em>.</div>
        <div class="rt-sub rt-anim" style="animation-delay:.20s">Cruzamos incidência, produção ambulatorial e o parque
          de aceleradores para tornar a fila do SUS um número auditável por estado.</div>
        <div class="rt-prov rt-anim" style="animation-delay:.30s">
          {chip("incidência", proc.get("incidencia", "-"))}
          {chip("oferta", proc.get("oferta", "-"))}
          {chip("parque", "real (RT2030)")}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_cards(resumo: pd.DataFrame) -> None:
    """Quatro leituras nacionais como mostradores de instrumento."""
    cards = [
        ("Demanda reprimida", _int_br(_valor(resumo, "demanda_reprimida")),
         "pacientes/ano na fila", "var(--cherenkov)", "rgba(61,220,255,.35)"),
        ("Déficit para fila zero", _int_br(_valor(resumo, "deficit_linacs")),
         "LINACs para demanda total", "var(--coral)", "rgba(255,84,112,.30)"),
        ("LSI nacional", _float_br(_valor(resumo, "lsi_nacional")),
         "índice de escassez (100 = equilíbrio)", "var(--violet)", "rgba(124,92,255,.30)"),
        ("LINACs instalados", _int_br(_valor(resumo, "linacs_instalados")),
         "censo RT2030, todos os setores", "var(--cherenkov-soft)", "rgba(124,231,255,.28)"),
    ]
    html = '<div class="rt-cards">'
    for i, (titulo, valor, unidade, accent, glow) in enumerate(cards):
        atraso = 0.38 + i * 0.08
        html += (
            f'<div class="rt-card rt-anim" '
            f'style="--accent:{accent}; --glow:{glow}; animation-delay:{atraso:.2f}s">'
            f'<div class="rt-card__eyebrow">{titulo}</div>'
            f'<div class="rt-card__value">{valor}</div>'
            f'<div class="rt-card__unit">{unidade}</div></div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_hook(indicadores: pd.DataFrame) -> None:
    """Destaque dos estados sem nenhum acelerador (grade 4)."""
    sem = sorted(indicadores.loc[indicadores["grade"] == 4, "uf"])
    if not sem:
        return
    nomes = ", ".join(sem)
    st.markdown(
        f"""
        <div class="rt-hook rt-anim" style="animation-delay:.70s"><span class="rt-hook__dot"></span>
        <div><b>{len(sem)} estados sem um único acelerador instalado</b> &mdash;
        {nomes}. Segundo o censo RT2030, esses pacientes precisam atravessar
        fronteiras estaduais para tratar.</div></div>
        """,
        unsafe_allow_html=True,
    )



# ---------------------------------------------------------------------------
# Mapa coropletico (estados preenchidos) - degrada para bolhas se faltar geojson
# ---------------------------------------------------------------------------
_SIGLA_KEYS = ("sigla", "sigla_uf", "uf", "abbrev")
_NOME_KEYS = ("name", "nome", "nm_estado", "estado", "nome_uf", "nm_uf")


def _normalizar(texto: object) -> str:
    forma = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in forma if not unicodedata.combining(c)).strip().lower()


def _sigla_da_feature(props: dict) -> str | None:
    for chave in props:
        if chave.lower() in _SIGLA_KEYS:
            valor = str(props[chave]).strip().upper()
            if valor in geo.UFS:
                return valor
    for chave in props:
        if chave.lower() in _NOME_KEYS:
            sigla = nomes.NOME_PARA_UF.get(_normalizar(props[chave]))
            if sigla:
                return sigla
    return None


def enriquecer_geojson(geojson: dict, indicadores: pd.DataFrame) -> dict:
    """Anexa grade, cor e métricas a cada estado do geojson (join por sigla/nome)."""
    idx = indicadores.set_index("uf")
    feats = []
    for feature in geojson.get("features", []):
        props = dict(feature.get("properties") or {})
        sigla = _sigla_da_feature(props)
        if sigla is None or sigla not in idx.index:
            continue
        linha = idx.loc[sigla]
        grade = int(linha["grade"])
        lsi = linha["lsi"]
        props.update({
            "sigla": sigla, "grade": grade, "grade_label": GRADE_LABEL[grade],
            "fila": int(linha["demanda_reprimida"]),
            "deficit": int(linha["deficit_linacs"]),
            "lsi": "inf" if lsi == float("inf") else round(float(lsi)),
            "fill": GRADE_RGB[grade],
        })
        feats.append({**feature, "properties": props})
    return {"type": "FeatureCollection", "features": feats}


@st.cache_data
def _carregar_geojson() -> dict | None:
    if not GEOJSON_UF.exists():
        return None
    try:
        return json.loads(GEOJSON_UF.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def render_coropletico(indicadores: pd.DataFrame, geojson: dict) -> bool:
    """Renderiza estados preenchidos por grade. Retorna False se não deu."""
    enriquecido = enriquecer_geojson(geojson, indicadores)
    if not enriquecido["features"]:
        return False
    camada = pdk.Layer(
        "GeoJsonLayer", data=enriquecido, pickable=True, stroked=True,
        filled=True, get_fill_color="properties.fill",
        get_line_color=[234, 242, 255, 155], line_width_min_pixels=1.15,
        opacity=0.96, auto_highlight=True, highlight_color=[255, 255, 255, 70],
    )
    deck = pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(latitude=-14.6, longitude=-53.2, zoom=3.1),
        layers=[camada],
        tooltip={
            "html": "<b>{sigla}</b> &middot; {grade_label}<br/>"
                    "Fila: {fila}<br/>Déficit: {deficit} &middot; LSI: {lsi}",
            "style": {"backgroundColor": "#111A2E", "color": "#EAF2FF",
                      "fontFamily": "Poppins", "fontSize": "12px",
                      "border": "1px solid rgba(132,160,210,.28)",
                      "borderRadius": "8px"},
        },
    )
    st.pydeck_chart(deck, use_container_width=True)
    return True


def preparar_mapa(indicadores: pd.DataFrame) -> pd.DataFrame:
    """Coordenadas + raio com piso para grade 4 saltar no mapa."""
    mapa = indicadores.copy()
    mapa["lat"] = mapa["uf"].map(lambda uf: UF_COORDS[uf][0])
    mapa["lon"] = mapa["uf"].map(lambda uf: UF_COORDS[uf][1])
    mapa["color"] = mapa["grade"].map(lambda g: GRADE_RGB[int(g)])
    base = (mapa["demanda_reprimida"].clip(lower=600) ** 0.5) * 1700
    # Grade 4 (sem serviço) recebe presença mínima alta: o hook não pode sumir.
    piso = mapa["grade"].map(lambda g: 95000 if int(g) == 4 else 0)
    mapa["radius"] = base.clip(lower=0) + piso
    mapa["radius_halo"] = mapa["radius"] * 1.34
    return mapa


def render_mapa(indicadores: pd.DataFrame) -> None:
    """Mapa por prioridade: estados preenchidos se houver geojson, senão bolhas."""
    st.markdown(
        '<div class="rt-map-note">Cor mais quente = maior prioridade territorial; '
        'grade 4 marca UF sem LINAC instalado.</div>',
        unsafe_allow_html=True,
    )
    geojson = _carregar_geojson()
    if geojson is not None and render_coropletico(indicadores, geojson):
        _legenda_grades()
        return
    mapa = preparar_mapa(indicadores)
    halo = pdk.Layer(
        "ScatterplotLayer", data=mapa,
        get_position="[lon, lat]", get_radius="radius_halo",
        get_fill_color="[color[0], color[1], color[2], 54]",
        pickable=False, stroked=False,
    )
    camada = pdk.Layer(
        "ScatterplotLayer", data=mapa,
        get_position="[lon, lat]", get_radius="radius",
        get_fill_color="color", pickable=True, stroked=True, opacity=0.96,
        get_line_color=[234, 242, 255, 170], line_width_min_pixels=1.2,
        auto_highlight=True, highlight_color=[255, 255, 255, 80],
    )
    deck = pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(latitude=-14.6, longitude=-53.2, zoom=3.05),
        layers=[halo, camada],
        tooltip={
            "html": "<b>{uf}</b> &middot; grade {grade}<br/>"
                    "Fila: {demanda_reprimida}<br/>Déficit: {deficit_linacs}",
            "style": {"backgroundColor": "#111A2E", "color": "#EAF2FF",
                      "fontFamily": "Poppins", "fontSize": "12px",
                      "border": "1px solid rgba(132,160,210,.28)",
                      "borderRadius": "8px"},
        },
    )
    st.pydeck_chart(deck, use_container_width=True)
    _legenda_grades()


def _legenda_grades() -> None:
    chips = "".join(
        f'<span class="rt-grade" style="background:{GRADE_HEX[g]}22;'
        f'color:{GRADE_HEX[g]}; border:1px solid {GRADE_HEX[g]}55">'
        f'{g} &middot; {GRADE_LABEL[g]}</span> '
        for g in range(5)
    )
    st.markdown(f'<div style="margin-top:.4rem">{chips}</div>',
                unsafe_allow_html=True)


def render_ranking(ranking: pd.DataFrame) -> None:
    """Top UFs por prioridade, como linhas de leitura."""
    linhas = ""
    for _, r in ranking.head(8).iterrows():
        g = int(r["grade"])
        hexc = GRADE_HEX[g]
        lsi = "inf" if r["lsi"] == float("inf") else _float_br(float(r["lsi"]), 0)
        linhas += (
            f'<div class="rt-row"><span class="rt-row__uf">{r["uf"]}</span>'
            f'<span class="rt-row__meta">{r["regiao"]} &middot; déficit '
            f'{int(r["deficit_linacs"])} &middot; LSI {lsi}</span>'
            f'<span class="rt-row__fila">{_int_br(r["demanda_reprimida"])}'
            f' <span class="rt-grade" style="background:{hexc}22;color:{hexc};'
            f'border:1px solid {hexc}55">{GRADE_LABEL[g]}</span></span></div>'
        )
    st.markdown(f'<div class="rt-rank">{linhas}</div>', unsafe_allow_html=True)


def render_dimensionar(mart: dict[str, pd.DataFrame]) -> None:
    """Simulador nacional e por UF."""
    indicadores = mart["indicadores"]
    params = CENARIOS["base"]
    st.markdown('<div class="rt-sec">Simulador de dimensionamento</div>',
                unsafe_allow_html=True)
    modo = st.radio(
        "Modo",
        ["Nacional", "Por estado"],
        horizontal=True,
        label_visibility="collapsed",
    )
    if modo == "Nacional":
        render_dimensionar_nacional(indicadores, params)
    else:
        render_dimensionar_uf(indicadores, params)
    render_auditoria_expansao(mart["cenarios_parque"])


def render_dimensionar_nacional(indicadores: pd.DataFrame, params) -> None:
    """Modo nacional do simulador."""
    col_meta, col_custo = st.columns([1, 1])
    with col_meta:
        meta_label = st.select_slider(
            "Meta de utilização",
            options=["ρ <= 1,0", "ρ <= 0,8"],
            value="ρ <= 1,0",
        )
    with col_custo:
        custo_mi = st.slider(
            "Custo por LINAC instalado (R$ mi)",
            min_value=6.0,
            max_value=15.0,
            value=10.0,
            step=0.5,
        )
    meta = 1.0 if meta_label == "ρ <= 1,0" else 0.8
    plano = engine.plano_nacional(
        indicadores,
        params,
        meta_utilizacao=meta,
        custo_por_linac=custo_mi * 1_000_000,
    )
    investimento = float(plano["investimento_reais"])
    profissionais = int(plano["profissionais_total"])
    st.markdown(
        f"""
        <div class="rt-hook"><span class="rt-hook__dot"></span>
        <div><b>{_moeda_curta(investimento)} e {profissionais} profissionais</b>
        tornam a Lei dos 60 dias estruturalmente viável em todo o país.</div></div>
        """,
        unsafe_allow_html=True,
    )
    detalhe_prof = (
        f"{int(plano['deficit_fisico_medico'])} físicos · "
        f"{int(plano['deficit_radio_oncologista'])} oncos · "
        f"{int(plano['deficit_tecnico_rtt'])} técnicos"
    )
    _cards_html(
        [
            ("LINACs a instalar", _int_br(plano["linacs_a_instalar"]),
             "capacidade adicional", "var(--cherenkov)", "rgba(61,220,255,.35)"),
            ("Profissionais", _int_br(profissionais),
             detalhe_prof, "var(--coral)", "rgba(255,84,112,.30)"),
            ("Investimento", _moeda_curta(investimento),
             "equipamento + obras", "var(--violet)", "rgba(124,92,255,.30)"),
            ("UFs beneficiadas", _int_br(plano["ufs_beneficiadas"]),
             f"meta {meta_label}", "var(--cherenkov-soft)", "rgba(124,231,255,.28)"),
        ]
    )


def render_dimensionar_uf(indicadores: pd.DataFrame, params) -> None:
    """Modo por estado do simulador."""
    opcoes = indicadores[["uf", "regiao"]].sort_values("uf")
    ufs = opcoes["uf"].tolist()
    default = ufs.index("BA") if "BA" in ufs else 0
    col_uf, col_add = st.columns([1, 2])
    with col_uf:
        uf = st.selectbox("UF", ufs, index=default)
    linha = indicadores.loc[indicadores["uf"] == uf].iloc[0]
    atual_linacs = int(linha["linacs_sus"])
    deficit_atual = int(linha["deficit_linacs"])
    max_add = max(deficit_atual + 5, 5)
    with col_add:
        adicionar = st.slider(
            "Adicionar LINACs",
            min_value=0,
            max_value=max_add,
            value=min(deficit_atual, max_add),
            step=1,
        )

    demanda = float(linha["demanda_rt_sus"])
    fila = float(linha["demanda_reprimida"])
    antes = engine.simular_uf(demanda, fila, atual_linacs, params)
    depois = engine.simular_uf(demanda, fila, atual_linacs + adicionar, params)
    prof_adicionados = engine.deficit_profissionais(adicionar)
    total_prof = sum(prof_adicionados.values())

    if depois["prazo_60d_alcancavel"]:
        st.markdown(
            """
            <div class="rt-hook"><span class="rt-hook__dot"></span>
            <div><b>60 dias viável</b> como condição estrutural: ρ abaixo de 1.</div></div>
            """,
            unsafe_allow_html=True,
        )

    _cards_html(
        [
            ("Utilização (ρ)", f"{_pct(float(antes['utilizacao']))} -> {_pct(float(depois['utilizacao']))}",
             "demanda/capacidade", "var(--cherenkov)", "rgba(61,220,255,.35)"),
            ("Grade", f"{int(antes['grade'])} -> {int(depois['grade'])}",
             "prioridade territorial", "var(--violet)", "rgba(124,92,255,.30)"),
            ("Déficit LINACs", f"{int(antes['deficit_linacs'])} -> {int(depois['deficit_linacs'])}",
             f"{atual_linacs} -> {atual_linacs + adicionar} instalados",
             "var(--coral)", "rgba(255,84,112,.30)"),
            ("Tempo de espera", _tempo(float(depois["tempo_espera_meses"])),
             f"antes: {_tempo(float(antes['tempo_espera_meses']))}",
             "var(--cherenkov-soft)", "rgba(124,231,255,.28)"),
        ]
    )
    st.caption(
        "Tempo de espera = meses para drenar a fila atual com a folga de "
        "capacidade existente (demanda estável). Não é a espera de um paciente "
        "individual; \"fila crescente\" indica ρ ≥ 1 (a fila não se esgota)."
    )
    _cards_html(
        [
            ("Profissionais", _int_br(total_prof),
             "para operar os LINACs adicionados", "var(--coral)", "rgba(255,84,112,.30)"),
            ("Físicos médicos", _int_br(prof_adicionados["fisico_medico"]),
             "formação especializada", "var(--cherenkov)", "rgba(61,220,255,.35)"),
            ("Radio-oncologistas", _int_br(prof_adicionados["radio_oncologista"]),
             "formação especializada", "var(--violet)", "rgba(124,92,255,.30)"),
            ("Técnicos RTT", _int_br(prof_adicionados["tecnico_rtt"]),
             "formação especializada", "var(--cherenkov-soft)", "rgba(124,231,255,.28)"),
        ]
    )


def render_auditoria_expansao(cenarios_parque: pd.DataFrame) -> None:
    """Bloco de auditoria da expansão PERSUS/Agora Tem Especialistas."""
    st.markdown('<div class="rt-sec">Auditoria da expansão</div>',
                unsafe_allow_html=True)
    col_demanda, col_expansao = st.columns([1, 1])
    with col_demanda:
        cenario = st.radio(
            "Cenário de demanda",
            ["base", "superior"],
            horizontal=True,
            key="auditoria_cenario",
        )
    rotulos_expansao = {
        "Censo RT2030 (+0)": 0,
        "+40 entregues": 40,
        "+121 PERSUS 2026": 121,
    }
    with col_expansao:
        expansao_rotulo = st.select_slider(
            "Expansão hipotética",
            options=list(rotulos_expansao),
            value="+121 PERSUS 2026",
        )
    expansao = rotulos_expansao[expansao_rotulo]
    linha = cenarios_parque.loc[
        (cenarios_parque["cenario_demanda"] == cenario)
        & (cenarios_parque["expansao"].astype(int) == expansao)
    ].iloc[0]
    deficit = int(linha["deficit_residual"])
    divergentes = int(linha["ufs_fila_divergente"])
    if cenario == "base" and expansao == 121 and deficit == 0:
        tese = (
            "A expansão atual fecha o déficit estrutural no cenário base "
            "se for bem alocada."
        )
    elif cenario == "superior" and expansao == 121:
        tese = (
            "Mesmo com os 121 do PERSUS, 86 LINACs continuam faltando no "
            "cenário de maior demanda."
        )
    else:
        tese = (
            "A suficiência depende simultaneamente da demanda assumida e da "
            "alocação das máquinas."
        )
    st.markdown(
        f"""
        <div class="rt-hook"><span class="rt-hook__dot"></span>
        <div><b>{tese}</b> Alocação proporcional ao déficit e melhor caso;
        o plano real deve ser auditado por UF.</div></div>
        """,
        unsafe_allow_html=True,
    )
    _cards_html(
        [
            ("Déficit residual", _int_br(deficit),
             "LINACs após expansão", "var(--coral)", "rgba(255,84,112,.30)"),
            ("UFs ρ ≥ 1", _int_br(divergentes),
             "60 dias estruturalmente inviável", "var(--violet)", "rgba(124,92,255,.30)"),
            ("Parque total", _int_br(linha["parque_total"]),
             "censo + máquinas alocadas", "var(--cherenkov)", "rgba(61,220,255,.35)"),
            ("Máquinas alocadas", _int_br(linha["maquinas_alocadas"]),
             expansao_rotulo, "var(--cherenkov-soft)", "rgba(124,231,255,.28)"),
        ]
    )


def render_validacao_painel(mart: dict[str, pd.DataFrame]) -> None:
    """Validação externa contra o PAINEL-Oncologia, quando há cache."""
    painel = mart.get("painel_validacao")
    regional = mart.get("painel_validacao_regional")
    if painel is None or regional is None:
        return

    st.markdown('<div class="rt-sec">Validação externa (PAINEL)</div>',
                unsafe_allow_html=True)
    spearman = _spearman_dashboard(
        regional["rho_medio"],
        regional["pct_ate_60d_medio"],
    )
    piores = ", ".join(
        regional.sort_values("pct_ate_60d_medio").head(2)["regiao"].tolist()
    )
    saturadas = ", ".join(
        regional.sort_values("rho_medio", ascending=False).head(2)["regiao"].tolist()
    )
    _render_validacao_hero(spearman, saturadas, piores)

    pior_regiao = regional.sort_values("pct_ate_60d_medio").iloc[0]
    ufs_saturadas = int((painel["utilizacao"].astype(float) >= 1.0).sum())
    mediana_pct = float(painel["pct_ate_60d"].median())
    _cards_html(
        [
            ("Spearman regional", _float_br(float(spearman), 2),
             "ρ x pct <=60d", "var(--cherenkov)", "rgba(61,220,255,.35)"),
            ("Pior região PAINEL", str(pior_regiao["regiao"]),
             _pct_label(float(pior_regiao["pct_ate_60d_medio"])),
             "var(--coral)", "rgba(255,84,112,.30)"),
            ("UFs ρ ≥ 1", _int_br(ufs_saturadas),
             "saturação estrutural", "var(--violet)", "rgba(124,92,255,.30)"),
            ("Mediana <=60d", _pct_label(mediana_pct),
             "UF do tratamento", "var(--cherenkov-soft)", "rgba(124,231,255,.28)"),
        ]
    )
    _render_validacao_regional(regional)

    _render_validacao_scatter(painel)
    _render_validacao_tabela(regional)
    st.caption(
        "PAINEL-Oncologia 2019-2024. Linha: UF do tratamento; coluna: tempo "
        "tratamento; modalidade: radioterapia. 'Sem informação' fica fora do "
        "denominador. O detalhe por UF é exploratório por fluxo interestadual "
        "e subnotificação."
    )


def _spearman_dashboard(x: pd.Series, y: pd.Series) -> float:
    pares = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(pares) < 2:
        return float("nan")
    return float(
        pares["x"].rank(method="average").corr(
            pares["y"].rank(method="average"),
            method="pearson",
        )
    )


def render_robustez_throughput(
    sensibilidade: pd.DataFrame,
    resumo: pd.DataFrame,
) -> None:
    """Bloco de robustez para o parâmetro throughput de LINAC."""
    st.markdown('<div class="rt-sec">Robustez ao throughput</div>',
                unsafe_allow_html=True)
    tabela = sensibilidade.sort_values("throughput").copy()
    adotado = tabela.loc[tabela["throughput"] == 450].iloc[0]
    otimista = tabela.loc[tabela["throughput"] == 550].iloc[0]
    otimista_ufs = int(otimista["ufs_fila_divergente"])
    st.markdown(
        f"""
        <div class="rt-hook"><span class="rt-hook__dot"></span>
        <div><b>Mesmo no cenário mais otimista (550), {otimista_ufs}
        estados seguem saturados.</b> A conclusão não depende da premissa de
        throughput; 450 é o valor adotado e conservador.</div></div>
        """,
        unsafe_allow_html=True,
    )
    _cards_html(
        [
            ("Throughput adotado", _int_br(adotado["throughput"]),
             "cursos/máquina/ano", "var(--cherenkov)", "rgba(61,220,255,.35)"),
            ("Déficit em 450", _int_br(adotado["deficit_linacs"]),
             "LINACs para fila zero", "var(--coral)", "rgba(255,84,112,.30)"),
            ("Teto otimista", _int_br(otimista["deficit_linacs"]),
             "LINACs ainda faltantes", "var(--violet)", "rgba(124,92,255,.30)"),
            ("Fila invariável", _int_br(_valor(resumo, "demanda_reprimida")),
             "pacientes/ano", "var(--cherenkov-soft)", "rgba(124,231,255,.28)"),
        ]
    )
    chart = tabela.rename(
        columns={
            "throughput": "Throughput",
            "deficit_linacs": "Déficit LINACs",
            "ufs_fila_divergente": "UFs ρ ≥ 1",
        }
    ).set_index("Throughput")[["Déficit LINACs", "UFs ρ ≥ 1"]]
    st.line_chart(chart, use_container_width=True)
    styled = tabela.style.apply(
        lambda linha: [
            "background-color: rgba(61,220,255,.16)" if linha["throughput"] == 450 else ""
            for _ in linha
        ],
        axis=1,
    )
    st.dataframe(styled, hide_index=True, use_container_width=True)
    st.caption(
        "A fila reprimida (66.539) é invariante ao throughput; apenas a "
        "tradução para máquinas, pessoas e tempo varia."
    )

def render_serie_temporal(serie: pd.DataFrame) -> None:
    """Série 2019-2024: oferta realizada contra demanda de referência."""
    st.markdown('<div class="rt-sec">Cobertura RT-SUS (2019-2024)</div>',
                unsafe_allow_html=True)
    tabela = serie.sort_values("ano").copy()
    tabela["ano"] = tabela["ano"].astype(int)
    for col in ("oferta_realizada", "demanda_esperada", "gap"):
        tabela[col] = pd.to_numeric(tabela[col], errors="coerce")

    validas = tabela.dropna(subset=["oferta_realizada", "demanda_esperada"])
    if validas.empty:
        st.caption(
            "serie_temporal.csv existe, mas não há anos com oferta SIA-AR válida "
            "para desenhar a curva."
        )
        return

    primeiro = validas.iloc[0]
    ultimo = validas.iloc[-1]
    crescimento = (
        (float(ultimo["oferta_realizada"]) / float(primeiro["oferta_realizada"]) - 1)
        * 100
        if float(primeiro["oferta_realizada"]) > 0 and len(validas) >= 2
        else None
    )
    if crescimento is not None:
        cobertura_final = (
            float(ultimo["oferta_realizada"]) / float(ultimo["demanda_esperada"]) * 100
        )
        frase = (
            f"A oferta de radioterapia cresceu {_float_br(crescimento, 1)}% desde "
            f"{int(primeiro['ano'])} (ano sensível a registro), mas em "
            f"{int(ultimo['ano'])} ainda cobre só {_float_br(cobertura_final, 1)}% "
            "da demanda de referência. O gap nacional agregado segue estrutural."
        )
    else:
        frase = (
            "A oferta de radioterapia é comparada a uma linha de demanda de "
            "referência; anos sem extração limpa ficam sinalizados, não imputados."
        )
    st.markdown(
        f"""
        <div class="rt-hook"><span class="rt-hook__dot"></span>
        <div><b>{_html(frase)}</b></div></div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(_serie_temporal_svg(tabela), unsafe_allow_html=True)

    ausentes = tabela.loc[
        tabela["codigos_ausentes"].fillna("").astype(str).str.len() > 0,
        ["ano", "codigos_ausentes"],
    ]
    if not ausentes.empty:
        resumo_ausentes = "; ".join(
            f"{int(row['ano'])}: {row['codigos_ausentes']}"
            for _, row in ausentes.iterrows()
        )
        st.caption(f"Anos com códigos ausentes ou extração incompleta: {resumo_ausentes}.")
    st.caption(
        "Caveat: esta série mostra cobertura nacional agregada, não a fila "
        "territorial conservadora de 66.539 pacientes. A oferta é por UF do "
        "estabelecimento; a demanda é linha de referência porque o INCA reestima "
        "incidência por ciclos. A faixa 2020-2021 marca contexto COVID-19, sem "
        "inferir queda anual a partir destes dados."
    )


def _serie_temporal_svg(tabela: pd.DataFrame) -> str:
    anos = tabela["ano"].astype(int).tolist()
    validas = tabela.dropna(subset=["oferta_realizada", "demanda_esperada"])
    y_max = float(
        max(validas["oferta_realizada"].max(), validas["demanda_esperada"].max())
    )
    y_max = max(1.0, y_max * 1.10)
    plot = {"left": 58, "top": 28, "right": 690, "bottom": 280}
    largura = plot["right"] - plot["left"]
    altura = plot["bottom"] - plot["top"]
    ano_min, ano_max = min(anos), max(anos)
    span = max(1, ano_max - ano_min)

    def tx(ano: float) -> float:
        return plot["left"] + (float(ano) - ano_min) / span * largura

    def ty(valor: float) -> float:
        return plot["bottom"] - max(0.0, float(valor)) / y_max * altura

    demanda_pts = [
        (tx(row["ano"]), ty(row["demanda_esperada"]))
        for _, row in validas.iterrows()
    ]
    oferta_pts = [
        (tx(row["ano"]), ty(row["oferta_realizada"]))
        for _, row in validas.iterrows()
    ]

    def points_attr(pontos: list[tuple[float, float]]) -> str:
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in pontos)

    step = largura / span
    band_x = tx(2020) - step * 0.45
    band_w = tx(2021) - tx(2020) + step * 0.90
    elementos = [
        f'<rect x="{band_x:.1f}" y="{plot["top"]}" width="{band_w:.1f}" '
        f'height="{altura}" fill="rgba(255,174,66,.10)" />',
        f'<text x="{band_x + 8:.1f}" y="{plot["top"] + 16}" fill="#FFAE42" '
        'font-size="11">pandemia (COVID-19)</text>',
        f'<line x1="{plot["left"]}" y1="{plot["bottom"]}" x2="{plot["right"]}" '
        f'y2="{plot["bottom"]}" stroke="rgba(234,242,255,.35)" />',
        f'<line x1="{plot["left"]}" y1="{plot["top"]}" x2="{plot["left"]}" '
        f'y2="{plot["bottom"]}" stroke="rgba(234,242,255,.35)" />',
    ]
    if len(demanda_pts) >= 2:
        area = points_attr(demanda_pts + list(reversed(oferta_pts)))
        elementos.append(
            f'<polygon points="{area}" fill="rgba(255,84,112,.18)" '
            'stroke="none"><title>Área entre demanda e oferta = gap nacional agregado</title></polygon>'
        )
    elementos.extend(
        [
            f'<polyline points="{points_attr(demanda_pts)}" fill="none" '
            'stroke="#FF5470" stroke-width="3" stroke-linejoin="round" />',
            f'<polyline points="{points_attr(oferta_pts)}" fill="none" '
            'stroke="#3DDCFF" stroke-width="3" stroke-linejoin="round" />',
        ]
    )
    for _, row in validas.iterrows():
        elementos.append(
            f'<circle cx="{tx(row["ano"]):.1f}" cy="{ty(row["oferta_realizada"]):.1f}" '
            'r="4.8" fill="#3DDCFF" stroke="#EAF2FF" stroke-width="1" />'
        )
    for ano in anos:
        x = tx(ano)
        elementos.extend(
            [
                f'<line x1="{x:.1f}" y1="{plot["bottom"]}" x2="{x:.1f}" '
                f'y2="{plot["bottom"] + 5}" stroke="rgba(234,242,255,.45)" />',
                f'<text x="{x:.1f}" y="{plot["bottom"] + 20}" fill="#8090B0" '
                f'font-size="10" text-anchor="middle">{ano}</text>',
            ]
        )
    for valor in (0.0, y_max / 2, y_max):
        y = ty(valor)
        elementos.extend(
            [
                f'<line x1="{plot["left"] - 5}" y1="{y:.1f}" x2="{plot["left"]}" '
                f'y2="{y:.1f}" stroke="rgba(234,242,255,.45)" />',
                f'<text x="{plot["left"] - 8}" y="{y + 4:.1f}" fill="#8090B0" '
                f'font-size="10" text-anchor="end">{_int_br(valor)}</text>',
                f'<line x1="{plot["left"]}" y1="{y:.1f}" x2="{plot["right"]}" '
                f'y2="{y:.1f}" stroke="rgba(234,242,255,.07)" />',
            ]
        )
    elementos.extend(
        [
            '<rect x="478" y="36" width="176" height="48" rx="8" '
            'fill="rgba(7,11,22,.72)" stroke="rgba(132,160,210,.22)" />',
            '<line x1="494" y1="52" x2="524" y2="52" stroke="#3DDCFF" stroke-width="3" />',
            '<text x="532" y="56" fill="#EAF2FF" font-size="11">oferta realizada</text>',
            '<line x1="494" y1="72" x2="524" y2="72" stroke="#FF5470" stroke-width="3" />',
            '<text x="532" y="76" fill="#EAF2FF" font-size="11">demanda esperada</text>',
        ]
    )
    return (
        '<svg class="rt-val-svg" viewBox="0 0 720 318" role="img" '
        'aria-label="Cobertura nacional de radioterapia: oferta realizada contra demanda de referência">'
        '<text x="24" y="22" fill="#EAF2FF" font-size="14" font-weight="700">'
        'Cobertura nacional: oferta realizada x demanda de referência</text>'
        f'{"".join(elementos)}</svg>'
    )


def render_caveats(mart: dict[str, pd.DataFrame]) -> None:
    """Limitações honestas - a diferença entre dashboard bonito e ferramenta."""
    proc = mart["procedencia"].set_index("metrica")["valor"].to_dict()
    st.markdown('<div class="rt-sec">Limitações honestas</div>',
                unsafe_allow_html=True)
    st.markdown(
        """
- O RadarRT **não prioriza pacientes** individualmente e não substitui
  regulação, auditoria institucional ou estudos oficiais.
- A oferta SIA-AR 2024 está atribuída por **UF do estabelecimento**
  (`AP_UFMUN`), não por residência do paciente.
- O parque de LINACs por UF vem do **censo RT2030** (Rosa et al.,
  Lancet Oncol 2023, Tabela 1 - instalado, todos os setores). É `real`
  em `procedencia.csv`, usado como proxy de capacidade acessível ao SUS.
- O déficit de LINACs dimensiona o parque para cobrir a demanda RT SUS total
  do cenário e zerar a fila estrutural; não é apenas o fluxo incremental depois
  da oferta SIA-AR observada.
- A camada de formação dimensiona profissionais para operar os LINACs faltantes:
  não mede o quadro profissional vigente no CNES.
- As grades usam carga anual relativa: LSI 100 é equilíbrio, 130 é 1,3 ano de
  carga, 300 é três anos de carga; grade 4 é zero LINAC instalado.
- Rankings por UF são **exploratórios**: quando oferta observada e
  capacidade instalada divergem, isso vira alerta metodológico, não
  número escondido.
        """
    )
    st.markdown('<div class="rt-sec">Procedência</div>', unsafe_allow_html=True)
    st.json(proc)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
def main() -> None:
    """Entrada Streamlit."""
    st.set_page_config(page_title="RadarRT", layout="wide",
                       initial_sidebar_state="collapsed")
    st.markdown(CSS, unsafe_allow_html=True)
    mart = carregar_mart()

    render_hero(mart["procedencia"])
    render_cards(mart["resumo"])
    render_hook(mart["indicadores"])

    tem_painel = (
        "painel_validacao" in mart
        and "painel_validacao_regional" in mart
    )
    nomes_abas = ["Visão geral", "Dimensionar"]
    if tem_painel:
        nomes_abas.append("Validação")
    nomes_abas.extend(["Robustez", "Pergunte aos dados", "Limitações"])
    abas = dict(zip(nomes_abas, st.tabs(nomes_abas), strict=True))

    with abas["Visão geral"]:
        esquerda, direita = st.columns([1.35, 1], gap="large")
        with esquerda:
            st.markdown('<div class="rt-sec">Prioridade territorial</div>',
                        unsafe_allow_html=True)
            render_mapa(mart["indicadores"])
        with direita:
            st.markdown('<div class="rt-sec">Top UFs por prioridade</div>',
                        unsafe_allow_html=True)
            render_ranking(mart["ranking"])

    with abas["Dimensionar"]:
        render_dimensionar(mart)

    if tem_painel:
        with abas["Validação"]:
            render_validacao_painel(mart)

    with abas["Robustez"]:
        if "serie_temporal" in mart:
            render_serie_temporal(mart["serie_temporal"])
        st.markdown('<div class="rt-sec">Cenários de demanda</div>',
                    unsafe_allow_html=True)
        st.caption("A fila varia com os parâmetros de demanda; o parque (409) "
                   "é fixo, pois é dado, não premissa.")
        st.dataframe(mart["sensibilidade"], hide_index=True,
                     use_container_width=True)
        render_robustez_throughput(
            mart["sensibilidade_throughput"],
            mart["resumo"],
        )

    with abas["Pergunte aos dados"]:
        render_agente(mart["indicadores"])

    with abas["Limitações"]:
        render_caveats(mart)

    st.markdown(
        '<div class="rt-foot">RadarRT &middot; equipe Cherenkov &mdash; '
        'INCA 2026 &middot; SIA-AR 2024 &middot; parque LINAC real (censo RT2030). '
        'Demanda reprimida é inferência auditável, não contagem individual.</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
