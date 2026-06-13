# Data Sources

## Versioned Inputs

- `data/incidencia_inca_2026.csv`: curated INCA 2026 incidence by UF.
- `data/parque_linacs_2030.csv`: published RT2030 LINAC park by UF used for the
  2024 output mart.
- `data/*_TEMPLATE.csv`: input templates for future manual curation.

The INCA 2026 repository entry includes an errata. It was reviewed during the
final audit; the listed corrections affect text, rates and references, not the
national case-count anchors used by the current output mart.

## Versioned Outputs

`data/outputs_2024` contains the reproducible analytical mart used by tests,
dashboard prototypes and the offline text-to-SQL agent.

The current capacity file sums to 409 LINACs and is marked as
`real (RT2030)`. The file applies the RT2030 corrections currently
tracked in the mart: SP=127, AC=0, AP=0 and RR=0.

The RT2030 park is the audited baseline and reflects a pre-current-expansion
vintage (roughly 2018-2020). It remains unchanged in `procedencia.csv`.
Expansion numbers such as about 40 delivered machines since 2023 and 121 new
machines expected by 2026 under PERSUS / Agora Tem Especialistas are used only
as policy context in derived scenarios, not as replacement source data.

SIA-AR offer is counted by UF of the treatment establishment (`AP_UFMUN`). It is
not yet reassigned by patient residence (`AP_MUNPCN`), so UF-level rankings show
local treatment delivery rather than resident demand capture.

## SIA-AR Coverage Series 2019-2024

`data/outputs_2024/serie_temporal.csv` adds a national coverage view for
2019-2024: delivered SIA-AR offer versus the RT-SUS demand reference line. The
offer side uses the same SIA-AR external-radiotherapy procedure set as the 2024
mart (`radarrt.sources.sia.PROC_RADIOTERAPIA_EXTERNA`), so the 2024 point must
match `resumo_nacional.csv/oferta_realizada` exactly.

Before the national series is assembled, RadarRT checks every year for the full
procedure-code set. Missing codes are written to `codigos_ausentes`; years with
incomplete extraction are flagged rather than silently compared as complete.

The demand side is a reference line, currently the base-scenario national
RT-SUS demand from the mart. It is not treated as a precise annual series
because INCA incidence is reestimated by multi-year cycles, not annually. The
resulting `gap` is a national aggregate coverage gap, not the territorial
conservative backlog used as the hero figure in the mart. In the current
outputs, the coverage-series 2024 gap is 65,393, while the mart backlog remains
66,539 patients after summing non-transferable UF deficits.

The 2019 point is useful for reproducibility, but it should be read with a
registration caveat: lower recorded offer in that year may reflect procedure
coverage or extraction completeness rather than a real clinical production
floor. The 2020-2021 interval is marked only as COVID-19 context. The current
series does not support a production-drop narrative because recorded offer
increases from 2019 to 2020.

## External Validation: PAINEL-Oncologia

`data/painel_onco/painel_rt_{ano}.csv` caches the official PAINEL-Oncologia
TabNet output for 2019-2024. It is a validation source only: it does not enter
the calculation of demand, backlog, LSI or LINAC deficit.

The extraction uses the official derived panel, not PySUS raw files, because
the PAINEL applies server-side business rules over SIA, SIH, SISCAN, CNES and
Cadweb. Query cut:

- row: UF do tratamento;
- column: Tempo Tratamento;
- filter: Modalidade Terapeutica = RADIOTERAPIA;
- period: Ano do diagnostico, 2019-2024.

`pct_ate_60d` is calculated as `(0-30 + 31-60) / (0-30 + 31-60 + mais de 60)`.
`Sem informacao de tratamento` is excluded from the denominator and declared as
missing registration, not as delay. Each cache has a `.meta.json` sidecar with
URL, query parameters, extraction date and valid window.

If TabNet changes layout or is unavailable, use the documented contingency:
export the same query manually from the PAINEL as CSV and save it with the same
schema (`uf,casos_0_30,casos_31_60,casos_mais_60,casos_sem_info`) plus a
matching sidecar. The dashboard renders the PAINEL validation only when the
cache-derived outputs exist.

## Specialized Workforce Ratios

The workforce layer is derived from the LINAC deficit; it does not add a new
data source to `procedencia.csv` and does not claim to measure the current
professional workforce.

Ratios are cited from Lancet Global Health 2024 ("Global radiotherapy demands
and corresponding radiotherapy-professional workforce requirements") and IAEA
Pub.1296 / Human Health Series guidance. They align with the RadarRT throughput
of 450 patients per LINAC-year:

- medical physicist: 1 per 450 patients/year -> 1.0 per LINAC;
- radiation oncologist: 1 per 250 patients/year -> 1.8 per LINAC;
- RTT: 1 per 150 patients/year -> 3.0 per LINAC.

People are integer resources: RadarRT applies `ceil` by UF and then sums
nationally.

## Simulator Cost Parameter

`plano_nacional.csv` uses a default planning cost of R$ 10 million per installed
LINAC, labeled as installed capacity (equipment plus works), not as a table
price for the machine alone.

The default sits between public planning anchors cited in the pitch material:
PERSUS 2014 invested about R$ 500 million for 80 accelerators (about R$ 6.25
million each), "Agora Tem Especialistas" 2026 announced about R$ 58.8 million
for five services (about R$ 11.8 million each), and individual installations
can be around R$ 14.4 million. The dashboard keeps this as an adjustable
parameter.

## Throughput Sensitivity

The base model keeps `linac_throughput = 450` courses per machine-year. This is
the adopted Lancet Global Health 2024 workforce anchor and is intentionally
treated as a parameter, not as a hidden constant.

`sensibilidade_throughput.csv` stress-tests a defensible range:

- 350: pessimistic floor for older/cobalt-heavy capacity;
- 400: IAEA conservative staffing anchor;
- 450: adopted Lancet workforce anchor;
- 500: Lancet machine-need anchor / modern two-shift services;
- 550: optimistic high-productivity ceiling.

The sensitivity does not change incidence, offer or backlog. It only changes
capacity-derived translations: LINAC deficit, utilization rho, LSI and waiting
time. In the current mart, deficit ranges from 201 to 44 LINACs across 350-550,
while backlog remains 66,539 patients.

## Park Expansion Scenarios

`cenarios_parque.csv` audits whether a hypothetical expansion is sufficient
under different demand assumptions. It keeps the canonical base fixed and adds
machines as a best-case proportional allocation to UF deficits. This is an upper
bound of allocation efficiency; the real Ministry of Health allocation can
follow empty-care-area criteria rather than minimizing utilization rho.

## Non-Versioned Data

Raw DATASUS downloads, PySUS caches, virtual environments and patient-level
extracts must stay outside Git. Use `PYSUS_CACHEPATH` from `.env.example` when a
custom cache location is needed.
