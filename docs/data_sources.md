# Data Sources

## Versioned Inputs

- `data/incidencia_inca_2026.csv`: curated INCA 2026 incidence by UF.
- `data/parque_linacs_2030.csv`: published/estimated LINAC allocation used for
  the 2024 output mart.
- `data/*_TEMPLATE.csv`: input templates for future manual curation.

The INCA 2026 repository entry includes an errata. It was reviewed during the
final audit; the listed corrections affect text, rates and references, not the
national case-count anchors used by the current output mart.

## Versioned Outputs

`data/outputs_2024` contains the reproducible analytical mart used by tests,
dashboard prototypes and the offline text-to-SQL agent.

The current capacity file sums to 363 LINACs and is marked as
`estimado (parque publicado)`. Do not describe it as a real UF census unless the
source file is replaced by a curated census and `procedencia.csv` changes.

SIA-AR offer is counted by UF of the treatment establishment (`AP_UFMUN`). It is
not yet reassigned by patient residence (`AP_MUNPCN`), so UF-level rankings show
local treatment delivery rather than resident demand capture.

## Non-Versioned Data

Raw DATASUS downloads, PySUS caches, virtual environments and patient-level
extracts must stay outside Git. Use `PYSUS_CACHEPATH` from `.env.example` when a
custom cache location is needed.
