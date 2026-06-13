# RadarRT

RadarRT estima demanda reprimida de radioterapia no SUS cruzando demanda
epidemiológica esperada, oferta realizada e capacidade instalada. O projeto foi
desenhado para hackathons e auditoria técnica: motor determinístico, fontes
rastreáveis, testes offline e agente text-to-SQL sem LLM.

RadarRT não prioriza pacientes individualmente e não substitui regulação,
auditoria institucional ou estudos oficiais. Ele é uma ferramenta analítica
para explorar gargalos agregados e explicitar incertezas dos dados.

## Entregas

- Base canônica por UF para radioterapia no Brasil.
- Indicadores de demanda, oferta, LSI, grade de prioridade e déficit de LINACs.
- Análise de sensibilidade para cenários conservador, base e superior.
- Análise de robustez por throughput de LINAC, de 350 a 550 cursos/máquina/ano.
- Série de cobertura RT-SUS 2019-2024: oferta SIA-AR realizada contra demanda
  nacional de referência, com caveat explícito para 2019.
- CSVs planos prontos para dashboard, notebook ou agente SQL.
- Agente conversacional PT-BR determinístico que gera apenas `SELECT` validado.
- Laudo offline de validação científica e operacional.

## Status

- [x] Motor determinístico validado contra LSI nacional 2020 arredondado para 221.
- [x] Ingestão INCA, SIA-AR, CNES-EQ novo e parque RT2030 publicado.
- [x] Fallback isolado por fonte com procedência explícita.
- [x] Agente text-to-SQL offline.
- [x] Testes automatizados para motor, ingestão, outputs, validação e agente.
- [x] Dashboard Streamlit de demo com mapa, ranking, robustez, validação e agente.
- [x] Narrativa de pitch e limitações metodológicas documentadas.
- [x] Anchors do mart RT2030 real re-travados nos testes e no probe operacional.
- [x] Série de cobertura nacional 2019-2024 versionada e auditada offline.

## Documentação

- `docs/visao_geral.md`: mapa completo do RadarRT, fluxo ponta a ponta,
  fórmulas, módulos, outputs, validação, caveats e submissão limpa.
- `docs/architecture.md`: camadas técnicas e princípios de desenho.
- `docs/data_sources.md`: fontes, caveats e dados versionados.
- `docs/reproducibility.md`: comandos para testes, probes e regeneração do mart.
- `docs/text_to_sql_schema.md`: schema consumido pelo agente offline.
- `docs/pitch_notes.md`: narrativa recomendada e frases metodologicamente
  seguras para demo.

## Quickstart

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

Run the synthetic/scientific probe:

```bash
python scripts/probe.py
```

Run the operational mart probe:

```bash
python scripts/probe_outputs.py
```

Operational exports intentionally fail if a real source is unavailable. Use
Python 3.11 for the reproducible 2024 export:

```bash
.\.venv311\Scripts\python.exe run_indicadores.py
```

After editable install, the packaged CLI is also available:

```bash
radarrt-indicadores
```

Run the demo dashboard:

```bash
python -m pip install -e ".[dashboard]"
streamlit run streamlit_app.py
```

## Real Data Ingestion

The deterministic engine and tests run on Python 3.13. Real DATASUS ingestion
via PySUS 2.x should use Python 3.11 in this workspace because the current
PySUS dependency stack pins `numpy<2`.

```bash
.\.venv311\Scripts\python.exe -m pip install -e ".[ingest,dev]"
.\.venv311\Scripts\python.exe run_indicadores.py
```

The default operational run uses:

- INCA 2026: `data/incidencia_inca_2026.csv`
- SIA-AR 2024: real unique CNS count for external radiotherapy procedures
- Capacity: `data/parque_linacs_2030.csv`, published RT2030 park by UF
- External validation: PAINEL-Oncologia 2019-2024 cache in `data/painel_onco`
- Output directory: `data/outputs_2024`

The directory name is historical: the mart combines offer observed in SIA-AR
2024, INCA 2026 incidence and the published RT2030 LINAC park.

## Data Contract

The single contract between ingestion and engine is `radarrt.schemas.COLUNAS_ENTRADA`:

```text
uf, regiao, populacao, incidencia_total, incidencia_sem_pnm,
linacs_sus, cursos_rt_realizados
```

`construir_base` always validates this contract before returning. If one source
fails, only that source falls back to synthetic data and the decision is recorded
in `BaseRadarRT.procedencia`.

## Outputs

The operational mart contains:

```text
data/outputs_2024/base_canonica.csv
data/outputs_2024/indicadores_base.csv
data/outputs_2024/ranking_prioridade.csv
data/outputs_2024/sensibilidade_cenarios.csv
data/outputs_2024/sensibilidade_throughput.csv
data/outputs_2024/resumo_nacional.csv
data/outputs_2024/auditoria_base.csv
data/outputs_2024/procedencia.csv
data/outputs_2024/plano_nacional.csv
data/outputs_2024/cenarios_parque.csv
data/outputs_2024/painel_validacao.csv
data/outputs_2024/painel_validacao_regional.csv
data/outputs_2024/serie_temporal.csv
```

These files are intentionally versioned because tests and demos use them as the
current analytical mart.

`run_indicadores.py` rebuilds the mart from source adapters. When incidence and
offer are already frozen in `base_canonica.csv`, regenerate the derived mart
offline without re-downloading SIA/INCA with:

```bash
python scripts/regerar_mart.py
```

## Agent Example

```python
from radarrt.agent import core

resposta = core.responder_pergunta(
    "Quais os 5 estados com maior demanda reprimida?",
    conexao,
)

print(resposta.sql)
print(resposta.frase)
```

The agent is deterministic and offline: Portuguese intent parser -> SQL builder
-> SELECT-only validator -> DB-API execution -> short answer.

## Repository Layout

```text
src/radarrt/            package source
src/radarrt/sources/    source adapters for INCA, SIA, CNES and LINAC park
src/radarrt/agent/      deterministic PT-BR text-to-SQL agent
tests/                  offline regression and scientific tests
data/                   curated inputs, templates and reproducible outputs
docs/                   architecture, sources and reproducibility notes
app/                    Streamlit integration components
scripts/                operational probes, validation runners and mart rebuilds
```

See `docs/pitch_notes.md` for the recommended demo narrative and validation
wording.

For a full Portuguese walkthrough, read `docs/visao_geral.md`.

## Methodology

| Step | Calculation | Source |
|---|---|---|
| Potential demand | incidence excluding non-melanoma skin cancer | INCA |
| SUS RT demand | incidence x RUR x SUS dependency | Params |
| Delivered offer | unique patients in external RT APACs | SIA-AR |
| Unmet demand | `max(demand - offer, 0)` | engine |
| LINAC Shortage Index | `(patients/LINAC / throughput) x 100` | engine |
| LINAC deficit | `ceil(demand / throughput) - installed` | engine |
| Workforce to train | `ceil(deficit_linacs x professionals_per_LINAC)` by UF | engine |

`deficit_linacs` is a full-demand planning deficit: it sizes the installed park
needed to cover expected SUS RT demand in the scenario and structurally zero the
queue. It is not an incremental-machine count computed only from the unmet flow
after SIA-AR offer.

Priority grades are anchored to annual load. LSI 100 means one year of expected
demand equals one year of installed capacity; 130 means 1.3 years of load; 300
means three years of load. Grade 4 is separate: no installed LINAC is a physical
access barrier, not just overload.

The specialized-workforce layer sizes the additional team needed to operate the
missing LINACs, not the current workforce gap. Ratios are derived from Lancet
Global Health 2024 and IAEA Pub.1296 using the same 450 patients/LINAC/year
throughput: 1.0 medical physicist, 1.8 radiation oncologists and 3.0 RTTs per
LINAC. With ceil by UF, the current 86-LINAC deficit requires 506 professionals:
86 physicists, 162 radiation oncologists and 258 RTTs.

The dimensioning simulator turns those diagnostics into a plan. It keeps demand
and offer fixed, varies only installed capacity, and reports LINACs to install,
workforce to train, investment and UFs benefited. Current national anchors:
rho <= 1.0 requires 86 LINACs, 506 professionals and R$ 860M; rho <= 0.8
requires 183 LINACs, 1,070 professionals and R$ 1.83B.

Park-expansion scenarios audit whether ongoing PERSUS expansion is sufficient
under demand uncertainty. In the best-case proportional allocation, residual
deficits are base `86/56/0` for `+0/+40/+121` machines and superior
`196/167/86`. The baseline RT2030 park remains unchanged; expansion scenarios
are derived audits, not new provenance.

Throughput sensitivity stress-tests 350, 400, 450, 500 and 550 courses per
machine-year. The adopted value remains 450. Across that range, the LINAC
deficit moves from 201 to 44 and UFs with rho >= 1 move from 24 to 17, while
backlog stays fixed at 66,539 patients. This shows the core conclusion is
robust to plausible capacity assumptions.

The PAINEL-Oncologia layer validates the time model against the official
monitoring of the 60-day law. It is cached from TabNet for 2019-2024 with row
`UF do tratamento`, column `Tempo Tratamento` and filter
`Modalidade Terapeutica = RADIOTERAPIA`. It does not enter backlog, LSI or
deficit calculations. In the current cache, regional Spearman between rho and
`pct_ate_60d` is `-0.500`; the UF correlation is `-0.100` and remains
exploratory because the view is by treatment UF.

The SIA-AR coverage series (`serie_temporal.csv`) is intentionally named as
coverage, not backlog. It compares national delivered external-radiotherapy
offer with the mart demand reference line from 2019 to 2024. The 2024 aggregate
gap is 65,393, while the headline backlog remains the territorial conservative
sum of UF deficits: 66,539 patients. The 2019 point is reproducible but should
be presented with a registration caveat; the current data do not show a
production drop from 2019 to 2020.

## Scientific Caveat

The 2024 output mart uses real SIA-AR offer, INCA 2026 incidence and the
published RT2030 LINAC park by UF. The current park sums to 409 LINACs and is
marked as `real (RT2030)` in `procedencia.csv`.

SIA-AR offer is attributed by UF of treatment establishment (`AP_UFMUN`), not by
patient residence. State rankings therefore describe where treatment happened;
residence-based attribution is the main next data upgrade.

## Quality Gates

```bash
python -m pytest
python -m ruff check .
python scripts/probe_outputs.py
.\.venv311\Scripts\python.exe run_indicadores.py
```

Current local validation: 116/116 tests passing, ruff clean, operational
probe 51/51 blocking checks OK with one methodological alert, and Playwright
visual smoke checked for the Streamlit map, PAINEL validation tab and coverage
series block.

GitHub Actions runs tests and lint on Python 3.11 and 3.13.

## References

- Portaria SAES/MS 3.695/2026:
  https://bvsms.saude.gov.br/bvs/saudelegis/saes/2026/prt3695_27_01_2026.html
- Estimativa INCA 2026:
  https://ninho.inca.gov.br/jspui/handle/123456789/17914
- Historico de procedimentos no RTS/SIGTAP:
  https://wiki.saude.gov.br/RTS/index.php/Procedimento_SUS
- API PySUS 2.x:
  https://pysus.readthedocs.io/en/latest/
