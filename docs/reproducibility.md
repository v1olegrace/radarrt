# Reproducibility

## Offline Tests

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## Regenerate 2024 Outputs

The full operational run uses Python 3.11 for PySUS compatibility:

```bash
.\.venv311\Scripts\python.exe -m pip install -e ".[ingest,dev]"
.\.venv311\Scripts\python.exe run_indicadores.py
```

The export command fails by default if a source is unavailable. This prevents a
local missing dependency or network issue from overwriting validated outputs with
synthetic fallback data. For exploratory demos only, pass `--allow-fallback`.

When incidence and offer are already frozen in `data/outputs_2024/base_canonica.csv`
and only the LINAC park changes, regenerate the mart offline instead:

```bash
python scripts/regerar_mart.py
```

Expected RT2030 real output:

```text
parque_nacional: 409
demanda_reprimida: 66539
deficit_linacs: 86
lsi_nacional: 112.5
deficit_fisico_medico: 86
deficit_radio_oncologista: 162
deficit_tecnico_rtt: 258
deficit_profissionais_total: 506
plano_meta_1_linacs: 86
plano_meta_1_profissionais: 506
plano_meta_1_investimento: 860000000
plano_meta_08_linacs: 183
plano_meta_08_profissionais: 1070
plano_meta_08_investimento: 1830000000
parque_base_exp_0_deficit: 86
parque_base_exp_40_deficit: 56
parque_base_exp_121_deficit: 0
parque_superior_exp_0_deficit: 196
parque_superior_exp_40_deficit: 167
parque_superior_exp_121_deficit: 86
throughput_deficits: [201, 126, 86, 59, 44]
throughput_ufs_fila: [24, 22, 19, 18, 17]
throughput_lsi: [144.7, 126.6, 112.5, 101.3, 92.1]
serie_oferta_2024: 141715
painel_spearman_regional: -0.5
procedencia_linacs: real (RT2030)
```

Expected outputs:

- `base_canonica.csv`
- `indicadores_base.csv`
- `ranking_prioridade.csv`
- `sensibilidade_cenarios.csv`
- `sensibilidade_throughput.csv`
- `plano_nacional.csv`
- `cenarios_parque.csv`
- `painel_validacao.csv` (when `data/painel_onco` cache exists)
- `painel_validacao_regional.csv` (when `data/painel_onco` cache exists)
- `serie_temporal.csv`
- `resumo_nacional.csv`
- `auditoria_base.csv`
- `procedencia.csv`

## Refresh PAINEL-Oncologia Cache

The PAINEL layer validates the time model and is not used to compute backlog or
deficit. Refresh it only when you intend to update the official 60-day-law
validation snapshot:

```bash
python - <<'PY'
from radarrt.sources.painel import ConsultaPainel, ingerir_painel

for ano in range(2019, 2025):
    ingerir_painel(ConsultaPainel(ano), usar_cache=False)
PY
python scripts/regerar_mart.py
```

If TabNet is unavailable, export manually from PAINEL-Oncologia with row "UF do
tratamento", column "Tempo Tratamento", filter "Modalidade Terapeutica =
RADIOTERAPIA", years 2019-2024, and save
`data/painel_onco/painel_rt_{ano}.csv` using the cache schema documented in
`docs/data_sources.md`.

## Scientific Probe

```bash
python scripts/probe.py
```

Use `--ano`, `--csv-inca`, `--fonte-capacidade` and `--csv-parque` to probe a
real source configuration.

## Operational Mart Probe

```bash
python scripts/probe_outputs.py
```

This command validates the versioned mart in `data/outputs_2024`. It treats
schema, anchors and provenance as blocking checks, while known data-tension
issues are reported as methodological alerts. Use `--strict` only when you want
those alerts to produce a non-zero exit code.

Current RT2030 anchors are locked in the probe: deficit 86, national LSI 112.5,
grades `[8, 5, 11, 0, 3]`, workforce 86/162/258/506, simulator plans
86/506/R$860M and 183/1070/R$1.83B, expansion residuals base 86/56/0 and
superior 196/167/86, throughput sensitivity deficits 201/126/86/59/44, PAINEL
regional Spearman -0.5 when cache outputs exist, coverage-series 2024 offer
141,715, and capacity provenance `real (RT2030)`.

## Clean Submission ZIP

Do not submit a ZIP created from the whole workspace if it includes `.venv311/`,
caches or local downloads. Build the archive from tracked files instead:

```bash
git archive --format zip --output radarrt_submission_clean.zip HEAD
```

The repository already ignores `.venv311/` through the `.venv*/` rule. You can
confirm before packaging:

```bash
git check-ignore .venv311
git status --short
```
