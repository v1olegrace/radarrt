# Pitch Notes

## Core Narrative

RadarRT transforma fontes publicas e parametros auditaveis em um radar de
demanda reprimida de radioterapia no SUS. Ele cruza incidencia do INCA,
producao ambulatorial do SIA/SUS e capacidade de LINACs para criar um mart
transparente por UF. O motor calcula demanda reprimida, LSI, deficit estrutural
estimado e prioridade territorial. O agente offline responde perguntas em
portugues gerando SQL validado, sem LLM e sem internet.

## Validation Wording

Use this wording in the pitch:

> O motor matematico foi validado 11/11 em modo offline e sintetico. O mart
> operacional 2024/2026 passa nos checks bloqueantes, mas revela exatamente a
> limitacao que queremos resolver: sem matriz por residencia e sem censo real
> por UF de LINACs, alguns estados mostram tensao entre oferta observada e
> capacidade estimada. Isso e tratado como alerta metodologico, nao escondido.

Avoid saying:

> Tudo validado 11/11.

That sentence is technically true for `scripts/probe.py` without arguments, but
it is incomplete for the mart versioned in `data/outputs_2024`.

## Demo Line

Perguntei "deficit total no Nordeste" e o sistema respondeu com SQL validado,
sem LLM, sem internet e com dados auditaveis.

## Honest Caveat

Quando os dados entram em conflito, o RadarRT nao esconde: ele transforma isso
em alerta metodologico. Essa e a diferenca entre um dashboard bonito e uma
ferramenta auditavel.

## Methodological Framing

- Say "deficit estrutural estimado de LINACs", not "faltam exatamente 109
  maquinas".
- Read UF rankings as treatment-location rankings because SIA-AR offer is
  attributed by establishment UF (`AP_UFMUN`).
- The next data upgrade is resident attribution using `AP_MUNPCN`.
- The next capacity upgrade is a real UF census of LINACs from mature CNES-EQ
  records after Portaria SAES/MS 3.695/2026 adoption.
