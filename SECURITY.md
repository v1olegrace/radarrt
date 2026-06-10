# Security Policy

RadarRT does not require API keys for its deterministic engine or offline
text-to-SQL agent.

## Reporting

Report suspected vulnerabilities through GitHub private vulnerability reporting
when available. If the repository is private or the feature is disabled, open a
minimal issue without sensitive details and ask for a private channel.

## Data Handling

- Do not commit credentials, tokens, `.env` files or local DATASUS caches.
- Do not commit patient-level source extracts.
- Version only aggregated CSVs needed to reproduce the public demo outputs.
- Keep generated caches covered by `.gitignore`.
