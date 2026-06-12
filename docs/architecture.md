# Architecture

RadarRT is split into deterministic layers so each number in the output can be
audited.

## Layers

- `radarrt.schemas`: canonical column contract shared by ingestion, engine and
  tests.
- `radarrt.sources`: source adapters for INCA, SIA-AR, CNES-EQ, published
  LINAC park CSVs and PAINEL-Oncologia validation caches.
- `radarrt.pipeline`: orchestration and provenance. Source failures fall back
  independently and are recorded in `Procedencia`.
- `radarrt.engine`: pure formulas for demand, shortage index, grade, LINAC
  deficit, time indicators, specialized workforce to train, dimensioning
  simulator plans, park-expansion audit and throughput sensitivity.
- `radarrt.analise`: datamart, ranking, scenario sensitivity and audit tables.
- `radarrt.validation`: offline scientific checks, benchmark reproduction and
  PAINEL-Oncologia external validation.
- `radarrt.agent`: deterministic Portuguese parser, SELECT-only SQL builder and
  response renderer.
- `streamlit_app.py`: demo dashboard over the versioned CSV mart, including
  national cards, UF ranking, choropleth/fallback map, dimensioning simulator,
  throughput robustness, PAINEL validation, caveats and agent tab.

## Design Principles

- No hidden network calls inside the engine.
- No generative model required for the text-to-SQL agent.
- All source caveats must appear in provenance or validation output.
- CSV outputs are flat by design so they can feed dashboards, notebooks or SQL
  agents without extra joins.

## Demo Flow

```text
INCA 2026 -------\
SIA-AR 2024 -----> base canonica -> motor deterministico -> CSVs -> dashboard
LINAC RT2030 ----/                                      \        \
                                                         \        -> agente SQL offline
PAINEL 2019-2024 -----------------------------------------> validacao externa
```
