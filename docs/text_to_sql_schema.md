# RadarRT Text-to-SQL Schema

Use `data/outputs_2024` as the initial analytical mart.

## Tables

`base_canonica.csv`

- One row per UF.
- Canonical input schema expected by the engine:
  `uf`, `regiao`, `populacao`, `incidencia_total`, `incidencia_sem_pnm`,
  `linacs_sus`, `cursos_rt_realizados`.

`indicadores_base.csv`

- One row per UF.
- Includes every input column plus:
  `demanda_rt_sus`, `demanda_reprimida`, `pacientes_por_linac`, `lsi`, `grade`,
  `deficit_linacs`.
- Base scenario: `rur=0.50`, `sus_share=0.80`, `linac_throughput=450`.

`sensibilidade_cenarios.csv`

- One row per scenario: `conservador`, `base`, `superior`.
- National totals and grade counts for sensitivity analysis.

`ranking_prioridade.csv`

- Top UFs ordered by grade, deficit, demand gap and LSI.
- Intended for dashboard cards and pitch narratives.

`resumo_nacional.csv`, `auditoria_base.csv`, `procedencia.csv`

- Key-value tables for totals, data coverage and provenance.

## Important Caveat

The offer (`cursos_rt_realizados`) is real SIA-AR 2024. Incidence is INCA 2026.
Capacity is an estimated UF allocation summing to 363 LINACs; it is explicitly
marked as `estimado (parque publicado)` in `procedencia.csv`.

Offer is attributed by treatment establishment UF (`AP_UFMUN`), not patient
residence. Use national totals freely; read UF rankings as treatment-location
rankings until a residence-attributed mart is curated.
