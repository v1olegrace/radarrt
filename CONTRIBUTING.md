# Contributing

RadarRT is a deterministic public-health analytics project. Keep changes small,
auditable and reproducible.

## Local Setup

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

For real DATASUS ingestion, use Python 3.11 and install the ingestion extras:

```bash
.\.venv311\Scripts\python.exe -m pip install -e ".[ingest,dev]"
```

## Engineering Rules

- Preserve the canonical schema in `radarrt.schemas`.
- Keep ingestion fallbacks isolated per source and recorded in `Procedencia`.
- Do not commit credentials, local caches or virtual environments.
- Add tests when changing formulas, validators, SQL generation or data contracts.
- Prefer deterministic rules over generative calls for the offline agent.

## Validation Before Pull Request

```bash
python -m pytest
python -m ruff check .
.\.venv311\Scripts\python.exe run_indicadores.py
```
