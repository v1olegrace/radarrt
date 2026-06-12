# Changelog

## Unreleased

- Add throughput sensitivity analysis to prove robustness of the core
  conclusion across 350, 400, 450, 500 and 550 courses/LINAC-year:
  `sensibilidade_throughput.csv`, pure engine function, probe anchors and a
  dashboard robustness block.

- Add external validation against PAINEL-Oncologia (60-day law): TabNet cache
  adapter with sidecars, `painel_validacao*.csv`, offline tests, probe reporting
  and a conditional Streamlit `Validação` tab.

- Add park-expansion scenarios to audit PERSUS sufficiency and allocation:
  `cenarios_parque.csv`, pure allocation functions, probe anchors for base and
  superior demand, and a dashboard block in `Dimensionar`.

- Add dimensioning simulator with pure national/per-state planning functions,
  `data/outputs_2024/plano_nacional.csv`, probe anchors for rho targets 1.0
  and 0.8, and a Streamlit `Dimensionar` tab.

- Add specialized workforce dimensioning layer using Lancet/IAEA ratios:
  1.0 medical physicist, 1.8 radiation oncologists and 3.0 RTTs per missing
  LINAC, with `ceil` by UF. Anchors: 86 physicists, 162 radiation oncologists,
  258 RTTs and 506 total professionals to train.

- Add time layer (utilization, 60-day structural feasibility, backlog-drainage wait): three pure functions (`utilizacao`, `prazo_60d_alcancavel`, `tempo_espera_meses`), vectorized columns in `calcular_indicadores`, four new keys in `resumo_nacional`, four new invariants in `validation.py`, and `tests/test_tempo.py` (8 tests). Anchors re-travados: `utilizacao_nacional=1.125`, `ufs_fila_divergente=19`, `ufs_drenaveis=8`, `tempo_espera_mediano_meses=6.6`. SP insight: deficit zero, ~57 meses para drenar a fila.

- Replaced the estimated LINAC park with the published RT2030 park by UF
  (409 LINACs; SP=127; AC/AP/RR=0).
- Added `scripts/regerar_mart.py` to regenerate `data/outputs_2024` offline
  when incidence and offer are frozen and only the LINAC park changes.
- Regenerated the operational mart: deficit 86 LINACs, national LSI 112.5 and
  `real (RT2030)` provenance for capacity.
- Re-anchored output tests and `scripts/probe_outputs.py` to the RT2030 mart,
  adding coverage for 409 LINACs, SP=127, AC/AP/RR=0 and grade-4 states.
- Added a Streamlit demo dashboard over the versioned mart.
- Added `scripts/probe_outputs.py` to validate operational CSV outputs separately
  from the synthetic scientific probe.
- Added pitch notes with explicit validation wording and methodological caveats.
- Fixed single-UF questions that also say "total" so the UF filter is preserved.
- Hardened the SQL validator against comma joins and DuckDB file-loading helpers.
- Documented the SIA-AR treatment-location attribution caveat.

## 0.1.0 - 2026-06-10

- Organized the project as an installable Python package.
- Added GitHub-ready CI, repository hygiene files and contribution docs.
- Preserved offline tests and deterministic text-to-SQL behavior.
- Documented architecture, data sources and reproducibility workflow.
