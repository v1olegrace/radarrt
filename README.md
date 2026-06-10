# RadarRT

RadarRT estima demanda reprimida de radioterapia no SUS cruzando demanda
epidemiologica esperada, oferta realizada e capacidade instalada. O projeto foi
desenhado para hackathons e auditoria tecnica: motor deterministico, fontes
rastreaveis, testes offline e agente text-to-SQL sem LLM.

## What It Delivers

- Base canonica por UF para radioterapia no Brasil.
- Indicadores de demanda, oferta, LSI, grade de prioridade e deficit de LINACs.
- Analise de sensibilidade para cenarios conservador, base e superior.
- CSVs planos prontos para dashboard, notebook ou agente SQL.
- Agente conversacional PT-BR deterministico que gera apenas `SELECT` validado.
- Laudo offline de validacao cientifica e operacional.

## Project Status

- [x] Motor deterministico validado contra LSI nacional 2020 arredondado para 221.
- [x] Ingestao INCA, SIA-AR, CNES-EQ novo e parque publicado/estimado.
- [x] Fallback isolado por fonte com procedencia explicita.
- [x] Agente text-to-SQL offline.
- [x] Testes automatizados para motor, ingestao, outputs, validacao e agente.
- [ ] Dashboard Streamlit completo e mapa.
- [ ] Pitch final e narrativa visual.

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

Operational exports intentionally fail if a real source is unavailable. Use
Python 3.11 for the reproducible 2024 export:

```bash
.\.venv311\Scripts\python.exe run_indicadores.py
```

After editable install, the packaged CLI is also available:

```bash
radarrt-indicadores
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
- Capacity: `data/parque_linacs_2030.csv`
- Output directory: `data/outputs_2024`

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

`run_indicadores.py` exports:

```text
data/outputs_2024/base_canonica.csv
data/outputs_2024/indicadores_base.csv
data/outputs_2024/ranking_prioridade.csv
data/outputs_2024/sensibilidade_cenarios.csv
data/outputs_2024/resumo_nacional.csv
data/outputs_2024/auditoria_base.csv
data/outputs_2024/procedencia.csv
```

These files are intentionally versioned because tests and demos use them as the
current analytical mart.

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
scripts/                operational probes and validation runners
```

## Methodology

| Step | Calculation | Source |
|---|---|---|
| Potential demand | incidence excluding non-melanoma skin cancer | INCA |
| SUS RT demand | incidence x RUR x SUS dependency | Params |
| Delivered offer | unique patients in external RT APACs | SIA-AR |
| Unmet demand | `max(demand - offer, 0)` | engine |
| LINAC Shortage Index | `(patients/LINAC / throughput) x 100` | engine |
| LINAC deficit | `ceil(demand / throughput) - installed` | engine |

## Scientific Caveat

The 2024 output mart uses real SIA-AR offer and INCA 2026 incidence. Capacity is
an estimated UF allocation that sums to 363 LINACs and is marked as
`estimado (parque publicado)` in `procedencia.csv`. Treat it as exploration and
sensitivity input, not as a real census by UF.

SIA-AR offer is attributed by UF of treatment establishment (`AP_UFMUN`), not by
patient residence. State rankings therefore describe where treatment happened;
residence-based attribution is the main next data upgrade.

## Quality Gates

```bash
python -m pytest
python -m ruff check .
.\.venv311\Scripts\python.exe run_indicadores.py
```

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
