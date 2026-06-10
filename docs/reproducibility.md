# Reproducibility

## Offline Tests

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## Regenerate 2024 Outputs

The validated operational run uses Python 3.11 for PySUS compatibility:

```bash
.\.venv311\Scripts\python.exe -m pip install -e ".[ingest,dev]"
.\.venv311\Scripts\python.exe run_indicadores.py
```

The export command fails by default if a source is unavailable. This prevents a
local missing dependency or network issue from overwriting validated outputs with
synthetic fallback data. For exploratory demos only, pass `--allow-fallback`.

Expected outputs:

- `base_canonica.csv`
- `indicadores_base.csv`
- `ranking_prioridade.csv`
- `sensibilidade_cenarios.csv`
- `resumo_nacional.csv`
- `auditoria_base.csv`
- `procedencia.csv`

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
