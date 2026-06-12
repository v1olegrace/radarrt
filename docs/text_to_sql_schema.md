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
- `deficit_linacs` is the full-demand planning deficit: LINACs needed to cover
  expected SUS RT demand and structurally zero the queue, not just incremental
  machines for the currently unmet SIA-AR flow.
- `deficit_fisico_medico`, `deficit_radio_oncologista`, `deficit_tecnico_rtt`
  and `deficit_profissionais_total` size professionals to train for the missing
  LINACs. They do not measure the current workforce gap.
- Priority grades are annual-load bands: LSI 100 is equilibrium, 130 is 1.3
  years of load, 300 is three years of load, and grade 4 means no installed
  LINAC.

`sensibilidade_cenarios.csv`

- One row per scenario: `conservador`, `base`, `superior`.
- National totals and grade counts for sensitivity analysis.

`sensibilidade_throughput.csv`

- One row per throughput stress value: 350, 400, 450, 500 and 550
  courses/LINAC-year.
- Fields: `throughput`, `deficit_linacs`, `ufs_fila_divergente`,
  `lsi_nacional`.
- Demand and observed offer are fixed; backlog is invariant to throughput.
  Only capacity-derived metrics vary.

`plano_nacional.csv`

- National simulator plans for `meta_utilizacao` 1.0 and 0.8.
- Fields: `linacs_a_instalar`, workforce by category, `profissionais_total`,
  `investimento_reais`, `ufs_beneficiadas`.

`cenarios_parque.csv`

- Park-expansion audit by `cenario_demanda` (`base`, `superior`) and `expansao`
  (`0`, `40`, `121`).
- Fields: `parque_total`, `maquinas_alocadas`, `deficit_residual`,
  `ufs_fila_divergente`.

`painel_validacao.csv`

- Optional external-validation table generated when `data/painel_onco` cache is
  present.
- One row per UF.
- Fields: `uf`, `regiao`, `utilizacao`, `grade`, `pct_ate_60d`.
- `pct_ate_60d` excludes "sem informacao de tratamento" from the denominator.
  PAINEL validates the time layer; it does not calculate the RadarRT backlog.

`painel_validacao_regional.csv`

- Optional regional summary of the PAINEL validation.
- Fields: `regiao`, `rho_medio`, `pct_ate_60d_medio`.
- Regional interpretation is the strong claim; UF-level interpretation is
  exploratory because both PAINEL and SIA-AR are treatment-location views.

`ranking_prioridade.csv`

- Top UFs ordered by grade, deficit, demand gap and LSI.
- Intended for dashboard cards and pitch narratives.

`resumo_nacional.csv`, `auditoria_base.csv`, `procedencia.csv`

- Key-value tables for totals, data coverage and provenance.

## Important Caveat

The offer (`cursos_rt_realizados`) is real SIA-AR 2024. Incidence is INCA 2026.
Capacity is the published RT2030 LINAC park by UF, summing to 409 LINACs; it is
explicitly marked as `real (RT2030)` in `procedencia.csv`.

Offer is attributed by treatment establishment UF (`AP_UFMUN`), not patient
residence. Use national totals freely; read UF rankings as treatment-location
rankings until a residence-attributed mart is curated.
