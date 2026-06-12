# PROMPT DE EXECUÇÃO — Fase D: Validação Externa com o PAINEL-Oncologia

> **Papel:** Você é um engenheiro de ML/IA especializado em dados públicos de saúde
> do SUS (DATASUS) e em radioterapia. Implementa com rigor (PEP8 + type hints),
> adaptadores de fonte isolados, cache versionado e **honestidade metodológica
> inegociável**. Sua tarefa é validar externamente a camada de tempo do RadarRT: os
> estados/regiões que o motor classifica como ρ≥1 (fila estruturalmente divergente)
> devem ser os mesmos com pior cumprimento da Lei dos 60 dias segundo o
> **PAINEL-Oncologia**, a ferramenta oficial do governo que monitora essa lei. Se
> bater, sua inferência deixa de ser "plausível" e passa a ser "confirmada pelo dado
> oficial".

---

## 1. CONTEXTO (leia antes de codar)

O PAINEL-Oncologia (DATASUS) monitora a Lei 12.732/2012. É um **painel derivado**
(cruza SIA+SIH+SISCAN por CNS/CID com regras de negócio no servidor do tabnet) —
**não** é base bruta. Por isso **não** use PySUS (que lê arquivos brutos): você
teria de reconstruir o algoritmo oficial e qualquer divergência viraria munição
contra o projeto. **Use raspagem HTTP do tabnet**, isolada e materializada em cache.

**Recorte de tabulação** (confirmado na Nota Técnica do PAINEL):
- Linha: **UF do tratamento** (consistente com a oferta SIA-AR já usada, `AP_UFMUN`).
- Coluna: **Tempo tratamento** (0 a 30 / 31 a 60 / mais de 60 / sem informação).
- Filtro: **Modalidade terapêutica = radioterapia**.
- Janela: **2019–2024** (antes de mai/2018 o registro de CNS+CID não era obrigatório
  para a maioria dos cânceres → dado parcial; declare a janela).

**Métrica derivada (honesta):**
```
pct_ate_60d(UF) = (casos_0_30 + casos_31_60) / (casos_0_30 + casos_31_60 + casos_mais_60)
```
Exclua "sem informação de tratamento" do denominador (não é atraso, é ausência de
registro) — e **declare** essa escolha.

**Resultado esperado (já ancorado na literatura — use como alvo de validação):**
a Região Norte tem chance de atraso ~3,4× a da Região Sul, e a RT é a modalidade
com pior cumprimento. Logo, espera-se **correlação negativa** entre a utilização
média regional (ρ) e o `pct_ate_60d` regional: mais escassez → menos gente tratada
a tempo. **Se a correlação não for negativa, NÃO force — reporte o achado como é**
(o RadarMR informa, não confirma a tese a qualquer custo).

**Escopo (decisão de design):** validação **regional sólida + UF exploratória**.
A regional é robusta a subnotificação por UF e é onde a literatura é forte. A UF
entra como camada exploratória, com o caveat de UF-de-tratamento (viés de fluxo
entre estados — o mesmo do alerta metodológico das 5 UFs) **declarado**.

---

## 2. IMPLEMENTAÇÃO — passo a passo

### 2.1 `src/radarrt/sources/painel.py` — adaptador isolado (raspagem + cache)

```python
"""Ingestao do PAINEL-Oncologia (DATASUS) para validacao da Lei dos 60 dias.

Painel derivado: raspagem HTTP do tabnet (nao PySUS). Materializa em cache
versionado + sidecar de procedencia (query, data, filtros) para auditabilidade.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import requests

TABNET_BASE = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?PAINEL_ONCO/PAINEL_ONCOLOGIABR.def"
CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "painel_onco"


@dataclass(frozen=True)
class ConsultaPainel:
    """Parametros da consulta ao PAINEL (entram no sidecar de procedencia)."""

    ano: int
    modalidade: str = "radioterapia"
    linha: str = "UF do tratamento"
    coluna: str = "Tempo tratamento"


def _fetch_tabnet(consulta: ConsultaPainel, timeout: int = 60) -> str:
    """POST no tabnet e retorna o HTML/CSV cru. Isolar toda fragilidade aqui.

    IMPORTANTE: os nomes EXATOS dos campos do formulario (Linha, Coluna,
    Arquivos/ano, SModalidade, etc.) devem ser extraidos do .def ao vivo —
    faca primeiro um GET no formulario, parseie os <select>/<option> e monte
    o POST. Nao confie em nomes fixos; eles variam por painel.
    """
    raise NotImplementedError("montar POST a partir do formulario parseado")


def _parsear(html: str) -> pd.DataFrame:
    """Extrai a tabela UF x faixa-de-tempo do retorno do tabnet (latin-1)."""
    raise NotImplementedError("parsear tabela; tratar encoding latin-1 e separador")


def ingerir_painel(consulta: ConsultaPainel, usar_cache: bool = True) -> pd.DataFrame:
    """Retorna casos de RT por UF e faixa de tempo; materializa cache + sidecar."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    csv = CACHE_DIR / f"painel_rt_{consulta.ano}.csv"
    sidecar = CACHE_DIR / f"painel_rt_{consulta.ano}.meta.json"
    if usar_cache and csv.exists():
        return pd.read_csv(csv)
    html = _fetch_tabnet(consulta)
    df = _parsear(html)
    df.to_csv(csv, index=False)
    sidecar.write_text(
        json.dumps(
            {
                "fonte": "PAINEL-Oncologia (DATASUS)",
                "url": TABNET_BASE,
                "ano": consulta.ano,
                "modalidade": consulta.modalidade,
                "linha": consulta.linha,
                "coluna": consulta.coluna,
                "extraido_em": date.today().isoformat(),
                "janela_valida": "2019-2024",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return df


def pct_ate_60d(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula % <=60 dias por UF, excluindo 'sem informacao' do denominador."""
    out = df.copy()
    denom = out["casos_0_30"] + out["casos_31_60"] + out["casos_mais_60"]
    out["pct_ate_60d"] = (out["casos_0_30"] + out["casos_31_60"]) / denom.where(denom > 0)
    return out[["uf", "pct_ate_60d"]]
```

> **Modo de contingência (OBRIGATÓRIO documentar):** o tabnet cai e muda layout.
> Se `ingerir_painel` falhar, o analista extrai manualmente no tabnet (Linha=UF do
> tratamento, Coluna=Tempo, filtro Modalidade=radioterapia, ano a ano 2019–2024),
> exporta "Copia como CSV" e salva em `data/painel_onco/painel_rt_{ano}.csv` no
> mesmo schema (`uf,casos_0_30,casos_31_60,casos_mais_60,casos_sem_info`),
> preenchendo o sidecar `.meta.json` à mão. A Fase D **não pode** ficar refém da
> fragilidade do scraping no palco.

### 2.2 `src/radarrt/validation.py` — checagem de validação externa

```python
def validar_contra_painel(
    indicadores: pd.DataFrame, painel: pd.DataFrame
) -> list[Check]:
    """Cruza utilizacao (rho) por UF com % <=60 dias do PAINEL.

    Regional (robusto): correlacao de Spearman entre rho medio regional e
    pct_ate_60d regional deve ser NEGATIVA. UF (exploratorio): mesma direcao,
    declarada com caveat de UF-de-tratamento.
    """
```
Implemente: junte por UF; agrupe por região (média de ρ e média ponderada de
`pct_ate_60d`); calcule Spearman regional; `Check` passa se ρ↑ ⇒ pct↓ (correlação
negativa). Adicione um `Check` informativo com o valor de Spearman por UF (sem
travar pass/fail nele — é exploratório).

### 2.3 `scripts/regerar_mart.py` — novo CSV `painel_validacao.csv`

Se o cache do PAINEL existir, gere `data/outputs_2024/painel_validacao.csv` com:
`uf, regiao, utilizacao, grade, pct_ate_60d`. Se o cache não existir, **pule** a
geração (não quebre o mart) e registre aviso. Inclua um resumo regional
(`painel_validacao_regional.csv`: `regiao, rho_medio, pct_ate_60d_medio`).

### 2.4 Testes — `tests/test_painel.py` (offline, com fixture)

**Sem rede.** Use uma fixture CSV pequena (3–4 UFs) que imite o schema do cache:
- `test_pct_ate_60d_exclui_sem_info` — denominador ignora `casos_sem_info`.
- `test_pct_ate_60d_zero_denominador` — UF sem casos → NaN, não erro.
- `test_validar_painel_correlacao_negativa` — fixture montada com ρ alto↔pct baixo
  retorna `Check.passou is True`.
- `test_ingerir_usa_cache` — com CSV de cache presente, `ingerir_painel` não chama
  rede (monkeypatch em `_fetch_tabnet` para levantar se chamado).

### 2.5 Dashboard — bloco "Validação externa (PAINEL)"

Nova seção (aba Limitações ou nova aba "Validação"), **só renderiza se o cache
existir** (degrade gracioso):
- **Mapa/scatter**: ρ por UF × `pct_ate_60d` (espera-se nuvem descendente).
- **Cartão regional**: a correlação de Spearman regional + frase-âncora dinâmica:
  *"As regiões que o RadarRT aponta como saturadas (ρ≥1) são as mesmas com menor
  cumprimento da Lei dos 60 dias no PAINEL-Oncologia — Norte e Nordeste à frente."*
- **Caveat declarado**: UF do tratamento (viés de fluxo entre estados);
  subnotificação por UF; janela 2019–2024; "sem informação" fora do denominador.

### 2.6 Docs / pitch

- `docs/data_sources.md`: PAINEL-Oncologia como fonte de **validação** (não de
  cálculo da fila), com a Nota Técnica, o recorte e a janela. Sidecar citado.
- `docs/pitch_notes.md`: a tese — *"não pedimos confiança na nossa inferência: ela
  bate com o monitoramento oficial da Lei dos 60 dias. Onde dizemos que falta
  capacidade, o governo mede mais atraso."*
- `CHANGELOG.md`: `Add external validation against PAINEL-Oncologia (60-day law)`.

---

## 3. CRITÉRIOS DE ACEITAÇÃO

- [ ] `ruff check .` limpo · `pytest` verde (98 + novos de `test_painel.py`, todos offline) · `probe_outputs.py` OK.
- [ ] `src/radarrt/sources/painel.py` com adaptador + cache + sidecar de procedência.
- [ ] Pipeline principal **inalterado**: demanda reprimida 66.539, déficit 86, ρ 1,125 — o PAINEL valida, não recalcula nada.
- [ ] Com cache presente: `painel_validacao.csv` + `painel_validacao_regional.csv` gerados; bloco do dashboard renderiza offline.
- [ ] Sem cache: mart e dashboard degradam graciosamente (sem erro).
- [ ] Correlação regional ρ × pct_ate_60d **reportada** (negativa esperada; reportar o valor real seja qual for).

---

## 4. GUARDRAILS DE HONESTIDADE (inegociáveis)

1. **O PAINEL valida, não calcula.** Não entra no cálculo da fila/déficit; é
   evidência externa independente. Procedência da fila **inalterada**.
2. **Reporte o achado como é.** Se a correlação não for negativa, diga — não ajuste
   recorte até "dar certo". A força do projeto é a honestidade.
3. **Caveats declarados**: UF do tratamento (fluxo entre estados), subnotificação
   por UF, janela 2019–2024, exclusão de "sem informação" do denominador.
4. **Cache versionado + sidecar** tornam a extração auditável e reproduzível; o
   contingente manual segue o mesmo schema e preenche o sidecar.
5. **Regional é a afirmação forte; UF é exploratória** — nunca apresente o detalhe
   por UF sem o caveat de fluxo.

---

*Fim do prompt. Execute 2.1 → 2.6. Primeiro a ingestão e o cache; rode a extração
(ou a contingência manual) para 2019–2024; só então gere o mart de validação e o
bloco do dashboard. Em divergência entre expectativa e dado, o DADO vence — reporte.*
