# Architecture

RadarRT is split into deterministic layers so each number in the output can be
audited.

## Layers

- `radarrt.schemas`: canonical column contract shared by ingestion, engine and
  tests.
- `radarrt.sources`: source adapters for INCA, SIA-AR, CNES-EQ and published
  LINAC park CSVs.
- `radarrt.pipeline`: orchestration and provenance. Source failures fall back
  independently and are recorded in `Procedencia`.
- `radarrt.engine`: pure formulas for demand, shortage index, grade and LINAC
  deficit.
- `radarrt.analise`: datamart, ranking, scenario sensitivity and audit tables.
- `radarrt.validation`: offline scientific checks and benchmark reproduction.
- `radarrt.agent`: deterministic Portuguese parser, SELECT-only SQL builder and
  response renderer.

## Design Principles

- No hidden network calls inside the engine.
- No generative model required for the text-to-SQL agent.
- All source caveats must appear in provenance or validation output.
- CSV outputs are flat by design so they can feed dashboards, notebooks or SQL
  agents without extra joins.
