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

> O motor matematico foi validado em modo offline e sintetico. O mart
> operacional combina INCA 2026, SIA-AR 2024 e parque RT2030 publicado por UF.
> A principal limitacao metodologica restante e que a oferta SIA-AR ainda esta
> atribuida pela UF do estabelecimento, nao pela residencia do paciente.

Avoid saying:

> Tudo validado 11/11.

That sentence is technically true for `scripts/probe.py` without arguments, but
it is incomplete while the operational mart anchors are being re-travados after
the RT2030 capacity update.

## Demo Line

Perguntei "deficit total no Nordeste" e o sistema respondeu com SQL validado,
sem LLM, sem internet e com dados auditaveis.

## Honest Caveat

Quando os dados entram em conflito, o RadarRT nao esconde: ele transforma isso
em alerta metodologico. Essa e a diferenca entre um dashboard bonito e uma
ferramenta auditavel.

## Camada de Tempo — Argumento Central

19 das 27 UFs operam acima de 100% de capacidade — para elas a Lei dos 60 dias
e estruturalmente inalcancavel. E mesmo Sao Paulo, com deficit zero de maquinas,
levaria ~57 meses para drenar sua fila.

O deficit sozinho esconde isso. A camada de tempo revela.

## Camada de Formacao Especializada

Nao basta comprar maquina: operar os 86 LINACs faltantes exige formar 506
profissionais - 86 fisicos medicos, 162 radio-oncologistas e 258 tecnicos RTT.
E formar um fisico medico leva anos, nao meses.

Use a frase com o caveat: essa camada dimensiona a equipe adicional necessaria
para operar as maquinas faltantes; ela nao mede o quadro profissional vigente
no CNES. Pessoas sao inteiras, entao o arredondamento e `ceil` por UF antes da
soma nacional.

## Simulador de Dimensionamento

Frase nacional:

> Com R$ 860 milhoes e 506 profissionais a formar, o plano leva todas as UFs a
> rho <= 1, tornando a Lei dos 60 dias estruturalmente viavel como condicao
> necessaria.

Validacao externa:

> O Ministerio da Saude tambem dimensiona expansao por deficit regional. O
> RadarRT usa a mesma logica conservadora: capacidade de radioterapia nao e
> transferivel entre estados no planejamento operacional.

Caveat do simulador: demanda e oferta permanecem fixas. Adicionar LINACs nao
apaga o backlog; aumenta a folga e drena a fila mais rapido. O custo por LINAC
e parametro ajustavel, rotulado como instalado (equipamento + obras).

## Auditor da Expansao

Pergunta perigosa do juri:

> O governo ja esta instalando aceleradores; o deficit nao some sozinho?

Resposta segura:

> O RadarRT nao compete com o plano de expansao; ele audita se a expansao e
> suficiente e se vai para os estados certos. No melhor caso proporcional ao
> deficit, +121 maquinas zeram o deficit no cenario base, mas ainda deixam 86
> LINACs faltando no cenario superior.

Tabela de palco:

```text
base:     +0 -> 86 | +40 -> 56 | +121 -> 0
superior: +0 -> 196 | +40 -> 167 | +121 -> 86
```

Caveat: alocacao proporcional ao deficit e melhor caso, nao plano real do MS.
O plano real deve ser auditado por UF; os numeros do PERSUS sao contexto de
politica publica e nao mudam a procedencia do mart.

## Validacao Externa PAINEL-Oncologia

Frase forte, mas segura:

> Nao pedimos confianca cega na nossa inferencia: ela foi confrontada com o
> monitoramento oficial da Lei dos 60 dias. Onde o RadarRT mede maior saturacao
> regional, o PAINEL-Oncologia mede menor cumprimento do prazo.

Numero de palco da extracao 2019-2024:

```text
Spearman regional rho x pct_ate_60d: -0,500
Spearman UF rho x pct_ate_60d:       -0,100 (exploratorio)
```

Use a qualificacao: a validacao forte e regional. A camada por UF usa UF do
tratamento, sofre fluxo interestadual e subnotificacao, e deve ser apresentada
como exploratoria. O PAINEL valida a camada de tempo; ele nao recalcula fila,
deficit ou LSI.

## Robustez ao Throughput

Pergunta tecnica provavel:

> E se cada LINAC fizer 500 cursos por ano, em vez de 450?

Resposta segura:

> Testamos de 350 a 550 cursos por maquina/ano. O deficit varia, como deveria,
> mas a tese nao desaparece: mesmo no teto otimista ainda faltam 44 LINACs e 17
> UFs seguem saturadas. A fila reprimida, 66.539 pacientes, nao muda com
> throughput porque vem de incidencia menos oferta observada.

Tabela de palco:

```text
throughput  deficit  UFs rho>=1  LSI nacional  fila
350         201      24          144,7         66.539
400         126      22          126,6         66.539
450          86      19          112,5         66.539
500          59      18          101,3         66.539
550          44      17           92,1         66.539
```

Frase curta: 450 e conservador, nao inflado. Com a ancora IAEA de 400, o
deficit seria 126, nao 86.

## Série Temporal de Cobertura

Pergunta provavel:

> A fila esta crescendo?

Resposta pronta:

> A forma honesta de olhar nao e inventar uma demanda anual precisa, porque o
> INCA reestima incidencia por ciclos. O RadarRT mostra cobertura: oferta
> SIA-AR realizada contra a demanda RT-SUS de referencia. O SUS quase dobrou a
> producao registrada desde 2019 e ainda assim, em 2024, cobre so 68,4% da
> necessidade. Isso mostra esforco real e gap estrutural ao mesmo tempo.

Numero de palco do mart atual: a oferta registrada cresceu 88,3% desde 2019
(75.260 -> 141.715), mas 2019 deve ser tratado com caveat por possivel
subestimacao de registro/cobertura. Todos os anos ficam abaixo da demanda de
referencia. O gap de 2024 na serie e nacional agregado (65.393), diferente da
fila territorial conservadora do mart (66.539).
Se algum ano vier com `codigos_ausentes` em nova extracao, diga isso antes de
usar a tendencia. Codigos ausentes: nenhum na extracao atual.

### Metodologia da Camada de Tempo

Tres grandezas, todas derivadas do que ja existe no mart:

- **Utilizacao (rho = LSI/100):** rho >= 1 = regime supersaturado, fila cresce
  sem limite.
- **Prazo 60 dias (Lei 12.732/2012):** rho < 1 e condicao NECESSARIA, nao
  suficiente. Nunca afirmar que rho < 1 garante cumprimento.
- **Tempo de espera:** indicador deterministico — meses para drenar o backlog
  com a folga de capacidade corrente. Diverge (infinito) quando rho >= 1 ou
  n_linacs = 0. Proximo refinamento possivel: Erlang-C / M/M/c (nao
  implementado).

Caveat obrigatorio ao exibir tempo de espera: quando rho > 0,9, a espera e
muito sensivel a pequenas variacoes de dado.

## Methodological Framing

- Say "deficit estrutural estimado de LINACs", not "faltam exatamente 86
  maquinas".
- If asked about the deficit formula, say it sizes the park for total expected
  SUS RT demand and fila zero; it is not an incremental count after crediting
  the current SIA-AR offer.
- If asked about grade thresholds, anchor them in annual load: LSI 100 is
  equilibrium, 130 is 1.3 years of load, 300 is three years of load, and grade
  4 is no installed LINAC.
- If asked about workforce, say "professionals to train for the missing LINACs",
  not "current workforce shortage"; current workforce measurement requires CNES
  professional rosters and is future work.
- If asked about the simulator, say rho <= 1 is structural feasibility for the
  60-day law, not a guarantee of compliance.
- If asked about PERSUS, say sufficiency is conditional on demand scenario and
  allocation; do not say it simply solves or does not solve the deficit.
- Read UF rankings as treatment-location rankings because SIA-AR offer is
  attributed by establishment UF (`AP_UFMUN`).
- The next data upgrade is resident attribution using `AP_MUNPCN`.
- The RT2030 park upgrade is integrated; a future capacity refresh can compare
  it against mature CNES-EQ records after Portaria SAES/MS 3.695/2026 adoption.
