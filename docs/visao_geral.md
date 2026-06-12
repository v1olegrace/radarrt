# Visao Geral do RadarRT

Este documento descreve o RadarRT de ponta a ponta: o que ele calcula, quais
fontes usa, como os dados atravessam o pipeline, onde cada modulo entra, quais
arquivos sao gerados e quais limites metodologicos precisam aparecer em qualquer
demo, pitch ou submissao.

## Resumo em Uma Frase

RadarRT cruza tres fontes publicas - incidencia de cancer do INCA, producao de
radioterapia realizada no SIA-SUS e parque de aceleradores lineares - para
estimar, por UF, demanda reprimida de radioterapia no SUS, deficit estrutural de
LINACs e prioridade territorial em grades de 0 a 4.

O projeto e deterministico, auditavel e offline-first. O dashboard e o agente
conversacional leem CSVs versionados; o agente responde em portugues por
intencao e SQL validado, sem LLM.

## O Que Ele Faz

RadarRT transforma dados publicos agregados em um mart analitico por UF. Para
cada estado, ele estima:

- demanda esperada de radioterapia no SUS;
- oferta realizada observada em APACs de radioterapia externa;
- demanda reprimida, limitada inferiormente a zero;
- pacientes esperados por LINAC;
- LINAC Shortage Index (LSI);
- deficit estrutural estimado de LINACs;
- grade de prioridade territorial;
- utilizacao da capacidade instalada (rho = LSI/100);
- viabilidade estrutural da Lei dos 60 dias (Lei 12.732/2012);
- tempo estimado para drenagem do backlog atual (indicador deterministico).
- profissionais especializados a formar para operar os LINACs faltantes.
- planos simulados de expansao nacional e por UF.
- auditoria de cenarios de expansao do parque.
- validacao externa da camada de tempo contra o PAINEL-Oncologia.
- robustez da conclusao central a diferentes throughputs por LINAC.

## Camada de Tempo (Fase A)

O motor original produzia um modelo de estoque (fila reprimida, deficit de LINACs).
A Fase A adicionou a dimensao de tempo, com tres grandezas derivadas:

**Utilizacao (rho):** fracao da capacidade instalada consumida pela demanda.
`rho = demanda_rt_anual / (n_linacs x 450 cursos/maquina/ano) = LSI / 100`.
rho >= 1 significa que a demanda iguala ou supera a capacidade; a fila cresce
sem limite (regime supersaturado). Estados sem LINAC recebem rho = infinito.

**Viabilidade estrutural da Lei dos 60 dias (Lei 12.732/2012):** rho < 1 e
condicao NECESSARIA (nao suficiente) para que o prazo seja matematicamente
alcancavel. Se rho >= 1, o prazo e estruturalmente inalcancavel.

**Tempo de espera por drenagem do backlog:**
```
folga = capacidade_anual - demanda_rt_anual
tempo_meses = (fila_reprimida / folga) x 12
```
Se n_linacs == 0 ou folga <= 0, tempo = infinito.
Interpretacao honesta: "meses para drenar o backlog atual usando a capacidade
ociosa corrente, supondo demanda estavel e toda a folga dedicada a fila."
E um indicador deterministico, nao simulacao de filas (proximo refinamento
possivel: modelo Erlang-C / M/M/c).

Caveat de saturacao: quando rho > 0,9 a espera e muito sensivel a pequenas
variaciones de dado. rho >= 1 e representado como infinito (nunca substituir
por numero finito "bonito").

**Insight central:** 19 das 27 UFs operam acima de 100% de capacidade — para
elas a Lei dos 60 dias e estruturalmente inalcancavel. E mesmo Sao Paulo, com
deficit zero de maquinas, levaria ~57 meses para drenar sua fila.

## Camada de Formacao Especializada (Fase B)

A Fase B dimensiona a equipe adicional necessaria para operar os LINACs do
deficit. Ela nao mede o quadro profissional atual; isso exigiria CNES de
profissionais e fica como trabalho futuro.

As razoes sao citadas da Lancet Global Health 2024 e IAEA Pub.1296 / Human
Health Series, derivadas pelo mesmo throughput do RadarRT (450 pacientes por
LINAC-ano):

```text
fisico-medico      = 450 / 450 = 1,0 por LINAC
radio-oncologista  = 450 / 250 = 1,8 por LINAC
tecnico RTT        = 450 / 150 = 3,0 por LINAC
```

Pessoas sao inteiras: o motor aplica `ceil` por UF e so depois soma o nacional.
Por isso 86 LINACs faltantes exigem 162 radio-oncologistas, nao 154,8.

Ancora de pitch: operar os 86 LINACs faltantes exige formar 506 profissionais:
86 fisicos medicos, 162 radio-oncologistas e 258 tecnicos RTT.

## Simulador de Dimensionamento (Fase C)

O simulador transforma o diagnostico em plano. Ele tem dois modos:

- Nacional: calcula quantos LINACs, profissionais e investimento sao necessarios
  para levar todas as UFs a uma meta de utilizacao (`rho <= 1,0` ou `rho <= 0,8`).
- Por estado: recalcula ao vivo a UF escolhida quando o usuario adiciona LINACs,
  mostrando utilizacao, grade, deficit, tempo de espera e profissionais a formar.

Guardrail metodologico: demanda e oferta ficam fixas. O slider muda apenas a
capacidade. O backlog nao desaparece; ele passa a drenar mais rapido quando a
folga de capacidade aumenta.

Com custo padrao de R$ 10 milhoes por LINAC instalado (equipamento + obras):

```text
rho <= 1,0: 86 LINACs, 506 profissionais, R$ 860 milhoes
rho <= 0,8: 183 LINACs, 1.070 profissionais, R$ 1,83 bilhao
```

Na Bahia, a ancora de teste e: 16 LINACs atuais, rho=1,71, deficit 12; com +12
LINACs, o parque vai a 28, rho cai para ~0,98, deficit zera e a condicao
estrutural da Lei dos 60 dias acende.

## Robustez ao Throughput

O valor adotado do motor e 450 cursos por maquina/ano. A sensibilidade final
estressa esse parametro porque ele afeta deficit, utilizacao, LSI, tempo e
dimensionamento de equipe, mas nao altera incidencia nem oferta observada.

Faixa testada:

```text
350: piso pessimista para parque antigo/cobalto
400: ancora conservadora IAEA
450: valor adotado, ancora Lancet de equipe
500: ancora Lancet de necessidade de maquina / servicos modernos
550: teto otimista de alta produtividade
```

Resultado do mart:

```text
throughput  deficit LINACs  UFs rho>=1  LSI nacional
350         201             24          144,7
400         126             22          126,6
450          86             19          112,5
500          59             18          101,3
550          44             17           92,1
```

Leitura segura: a conclusao central sobre saturacao territorial sobrevive em
toda a faixa plausivel. A demanda reprimida permanece 66.539 em todos os
throughputs, porque e incidencia estimada menos oferta observada.

## Auditoria da Expansao do Parque

O censo RT2030 e a base auditada. A expansao PERSUS / Agora Tem Especialistas e
tratada como cenario derivado: a pergunta nao e "o deficit some?", mas sob qual
demanda e com qual alocacao ele some.

`cenarios_parque.csv` calcula um melhor caso proporcional ao deficit local:

```text
cenario base:     +0 -> 86 | +40 -> 56 | +121 -> 0
cenario superior: +0 -> 196 | +40 -> 167 | +121 -> 86
```

Leitura segura: os 121 novos aceleradores fecham o deficit no cenario base se
forem bem alocados, mas ainda deixam 86 LINACs faltando no cenario superior.
A alocacao proporcional e um limite superior de eficiencia; o plano real deve
ser auditado por UF.

RadarRT nao prioriza pacientes individuais, nao substitui regulacao assistencial
e nao resolve atribuicao por residencia do paciente. No mart atual, a oferta
SIA-AR ainda e lida pela UF do estabelecimento.

## Validacao Externa PAINEL-Oncologia (Fase D)

O PAINEL-Oncologia e usado como fonte independente de validacao da Lei dos 60
dias. Ele nao recalcula demanda reprimida, LSI, deficit ou prioridade; apenas
testa se regioes com maior utilizacao rho no RadarRT tambem aparecem com pior
cumprimento oficial do prazo.

Recorte cacheado em `data/painel_onco`:

```text
linha: UF do tratamento
coluna: Tempo Tratamento
filtro: Modalidade Terapeutica = RADIOTERAPIA
janela: Ano do diagnostico 2019-2024
```

Metrica:

```text
pct_ate_60d = (casos_0_30 + casos_31_60) /
              (casos_0_30 + casos_31_60 + casos_mais_60)
```

`Sem informacao de tratamento` fica fora do denominador. A validacao forte e
regional; UF e exploratorio por fluxo interestadual e subnotificacao. Na
extracao versionada atual:

```text
Spearman regional rho x pct_ate_60d: -0,500
Spearman UF rho x pct_ate_60d:       -0,100
```

## Fluxo de Ponta a Ponta

```text
INCA 2026, incidencia --------\
SIA-AR 2024, oferta -----------> base canonica -> motor deterministico -> CSVs do mart
Parque LINAC, RT2030 ----------/                                      |
                                                                      +-> dashboard
                                                                      +-> agente SQL offline
PAINEL-Oncologia 2019-2024 ---> validacao externa opcional ------------/
```

1. A ingestao le as tres fontes e monta uma base canonica com 27 linhas, uma por
   UF.
2. O contrato de entrada valida que os dados sao finitos, nao-negativos, cobrem
   as 27 UFs e respeitam `incidencia_sem_pnm <= incidencia_total`.
3. O motor aplica formulas puras, sem I/O e sem chamadas de rede.
4. A camada de analise gera o mart em `data/outputs_2024`.
5. O dashboard e o agente consultam os CSVs versionados, sem recalcular nem
   baixar dados durante a demo.

## Fontes de Dados

### INCA 2026

Arquivo versionado: `data/incidencia_inca_2026.csv`.

Uso no RadarRT: incidencia total e incidencia excluindo pele nao melanoma por UF.
A coluna sem pele nao melanoma e a base epidemiologica para estimar demanda
potencial de radioterapia.

### SIA-AR 2024

Uso no RadarRT: oferta realizada de radioterapia externa, medida como pacientes
unicos em APACs de procedimentos compativeis.

Caveat obrigatorio: a oferta e atribuida pela UF do estabelecimento de
tratamento (`AP_UFMUN`), nao pela residencia do paciente. Rankings por UF devem
ser interpretados como rankings de local de tratamento ate existir uma matriz
por residencia (`AP_MUNPCN`).

### Parque de LINACs

Arquivo versionado: `data/parque_linacs_2030.csv`.

Uso no RadarRT: capacidade instalada por UF para calcular LSI e deficit de
maquinas.

Caveat obrigatorio: o mart atual usa o parque RT2030 publicado por UF, somando
409 LINACs e aparecendo em `procedencia.csv` como `real (RT2030)`.
As correcoes integradas no CSV atual sao SP=127, AC=0, AP=0 e RR=0.

### PAINEL-Oncologia

Arquivos versionados: `data/painel_onco/painel_rt_{ano}.csv` e sidecars
`.meta.json`.

Uso no RadarRT: validacao externa do modelo de tempo contra o monitoramento
oficial da Lei dos 60 dias. Nao altera procedencia da fila nem os calculos do
motor.

## Base Canonica

O contrato entre ingestao e motor e definido em `radarrt.schemas`:

```text
uf
regiao
populacao
incidencia_total
incidencia_sem_pnm
linacs_sus
cursos_rt_realizados
```

Regras bloqueantes:

- exatamente 27 UFs quando o mart nacional e produzido;
- valores finitos e nao-negativos;
- siglas de UF validas;
- `incidencia_sem_pnm` menor ou igual a `incidencia_total`;
- ausencia de `NaN` antes de chamar o motor.

## Matematica do Motor

Parametros do cenario base:

```text
RUR = 0.50
dependencia SUS = 0.80
throughput LINAC = 450 pacientes/ano
fracao efetiva RT = RUR * dependencia SUS = 0.40
```

Formulas principais:

```text
demanda_rt_sus = incidencia_sem_pnm * RUR * dependencia_SUS
demanda_reprimida = max(demanda_rt_sus - cursos_rt_realizados, 0)
pacientes_por_linac = demanda_rt_sus / linacs_sus
lsi = (pacientes_por_linac / throughput_linac) * 100
deficit_linacs = max(ceil(demanda_rt_sus / throughput_linac) - linacs_sus, 0)
deficit_fisico_medico = ceil(deficit_linacs * 1,0)
deficit_radio_oncologista = ceil(deficit_linacs * 1,8)
deficit_tecnico_rtt = ceil(deficit_linacs * 3,0)
deficit_profissionais_total = fisico + radio_oncologista + tecnico
```

`deficit_linacs` dimensiona o parque necessario para cobrir a demanda RT SUS
total do cenario e zerar a fila estrutural. Ele nao e uma conta incremental de
maquinas apenas para o fluxo ainda nao atendido depois da oferta observada no
SIA-AR.

Grades:

```text
grade 0: UF com LINAC e LSI <= 100
grade 1: UF com LINAC e 100 < LSI <= 130
grade 2: UF com LINAC e 130 < LSI <= 300
grade 3: UF com LINAC e LSI > 300
grade 4: UF sem LINAC
```

As faixas sao uma leitura de carga anual, nao cortes soltos. LSI 100 e o ponto
de equilibrio: um ano de demanda esperada cabe em um ano de capacidade instalada.
LSI 130 representa 1,3 ano de carga anual, ja acima da saturacao. LSI 300
representa tres anos de carga anual e separa colapso operacional extremo. Grade
4 fica isolada porque zero LINAC e uma barreira fisica de acesso, mesmo quando a
demanda absoluta da UF e menor.

O motor tambem reproduz o benchmark nacional da literatura para 2020, com LSI
arredondado para 221 no cenario base.

## Outputs Versionados

O comando `run_indicadores.py` exporta:

```text
data/outputs_2024/base_canonica.csv
data/outputs_2024/indicadores_base.csv
data/outputs_2024/ranking_prioridade.csv
data/outputs_2024/sensibilidade_cenarios.csv
data/outputs_2024/sensibilidade_throughput.csv
data/outputs_2024/plano_nacional.csv
data/outputs_2024/cenarios_parque.csv
data/outputs_2024/painel_validacao.csv
data/outputs_2024/painel_validacao_regional.csv
data/outputs_2024/resumo_nacional.csv
data/outputs_2024/auditoria_base.csv
data/outputs_2024/procedencia.csv
```

Quando incidencia e oferta ja estao congeladas em `base_canonica.csv` e apenas
as camadas derivadas precisam ser recomputadas, `scripts/regerar_mart.py`
recompoe o mart offline, sem baixar SIA/INCA novamente.

Numeros-ancora do mart atual:

```text
demanda reprimida: 66.539 pacientes
deficit estrutural estimado: 86 LINACs
LSI nacional: 112,5
linacs instalados no mart: 409
oferta realizada observada: 141.715 pacientes
demanda RT SUS estimada: 207.108 pacientes
grades base [0-4]: 8, 5, 11, 0, 3
profissionais a formar: 506 (86 fisicos, 162 radio-oncologistas, 258 tecnicos)
plano nacional rho<=1,0: 86 LINACs, 506 profissionais, R$ 860 milhoes
plano nacional rho<=0,8: 183 LINACs, 1.070 profissionais, R$ 1,83 bilhao
auditoria expansao base: 86, 56, 0
auditoria expansao superior: 196, 167, 86
sensibilidade throughput deficit: 201, 126, 86, 59, 44
sensibilidade throughput UFs rho>=1: 24, 22, 19, 18, 17
PAINEL Spearman regional: -0,500
```

Esses numeros estao travados nos testes e no probe operacional para detectar
regressao no mart atualizado.

## Mapa do Repositorio

```text
src/radarrt/               pacote principal
src/radarrt/sources/       adaptadores de fontes publicas
src/radarrt/agent/         agente PT-BR deterministico sem LLM
tests/                     testes de motor, ingestao, validacao, agente e mart
scripts/                   probes, validadores e regeneracao offline do mart
data/                      entradas curadas, templates e outputs versionados
docs/                      arquitetura, fontes, reproducibilidade e pitch
app/                       componentes auxiliares do dashboard Streamlit
```

## Modulos Principais

### `src/radarrt/engine.py`

Motor matematico puro. Calcula demanda, demanda reprimida, pacientes por LINAC,
LSI, grade, deficit, tempo e formacao especializada. Nao faz I/O, nao baixa
dados e e totalmente testavel com DataFrames de entrada.

### `src/radarrt/config.py`

Centraliza parametros e cenarios. O cenario base usa `RUR=0.50`, dependencia
SUS `0.80` e throughput de `450` pacientes por LINAC/ano. Tambem define os
cenarios conservador e superior para sensibilidade e as razoes de equipe por
LINAC.

### `src/radarrt/schemas.py`

Define o contrato da base canonica e valida os dados antes do motor. Garante
cobertura, dominio numerico e consistencia entre incidencia total e incidencia
sem pele nao melanoma.

### `src/radarrt/geo.py`

Mapa oficial de UF para regiao, lista de siglas e normalizacao de recortes
territoriais.

### `src/radarrt/pipeline.py`

Orquestra a ingestao. Chama INCA, SIA e capacidade, junta tudo com populacao por
UF, valida a base canonica e registra procedencia. O fallback sintetico e
isolado por fonte e pode ser desligado no CLI.

### `src/radarrt/validation.py`

Executa checks cientificos e operacionais: invariantes, monotonicidade,
reproducao do benchmark 2020 e consistencia entre oferta observada e capacidade
publicada ou estimada. E nessa camada que alertas metodologicos ficam
explicitos.

### `src/radarrt/analise.py`

Monta ranking de prioridade, sensibilidade por cenario, resumo nacional e
tabelas auxiliares para dashboard e agente.

### `src/radarrt/cli.py`

Interface de linha de comando `radarrt-indicadores`. Por padrao, a exportacao
operacional nao permite fallback sintetico; isso evita sobrescrever mart real
com dados artificiais por falha local de dependencia ou rede.

### `src/radarrt/ibge.py` e `src/radarrt/synthetic.py`

Fornecem populacao por UF e uma base sintetica para testes offline. A base
sintetica existe para validar o motor sem depender de rede ou de arquivos reais.

## Adaptadores de Fontes

### `src/radarrt/sources/inca.py`

Le incidencia curada por UF e normaliza os nomes das colunas para o contrato
canonico.

### `src/radarrt/sources/sia.py`

Baixa e normaliza SIA-AR via DATASUS/PySUS. A oferta e contada por UF do
estabelecimento (`AP_UFMUN`). Esse caveat deve acompanhar qualquer leitura por
UF.

### `src/radarrt/sources/cnes.py`

Adaptador para CNES-EQ, preparado para o codigo novo de equipamento da Portaria
SAES/MS 3.695/2026.

### `src/radarrt/sources/parque.py`

Le o parque publicado, classifica qualidade da fonte como real ou estimada e
executa checks de benchmark do total nacional.

### `src/radarrt/sources/painel.py`

Raspa o TabNet do PAINEL-Oncologia, salva cache anual e sidecar de procedencia,
e calcula `pct_ate_60d`. Usa contingencia manual quando o TabNet cai ou muda
layout.

## Agente Sem LLM

O agente fica em `src/radarrt/agent/` e segue um fluxo deterministico:

```text
pergunta em portugues -> parser de intencao -> SQL allowlist -> DB-API -> resposta curta
```

Arquivos:

- `intent.py`: identifica metrica, UF, ranking, total ou recorte regional;
- `sql.py`: gera apenas `SELECT` validado contra allowlist;
- `nomes.py`: mapeia nomes de estados para siglas;
- `core.py` e `responder.py`: executam a query em DuckDB/SQLite e formatam a
  resposta.

O agente nao chama LLM, nao usa internet e nao executa escrita no banco.

## Dashboard

`streamlit_app.py` consome `data/outputs_2024` e apresenta cards nacionais,
ranking, mapa aproximado, sensibilidade, caveats e aba do agente.

`app/agent_tab.py` isola a integracao do agente no dashboard para manter o app
principal simples.

## Validacao

Checks principais:

```bash
python -m pytest
python -m ruff check .
python scripts/probe_outputs.py
```

Probe cientifico opcional:

```bash
python scripts/probe.py
```

`scripts/probe.py` valida o motor em modo sintetico/offline. `scripts/probe_outputs.py`
valida o mart versionado em `data/outputs_2024`, separando:

- checks bloqueantes: schema, arquivos esperados, anchors, procedencia e
  invariantes;
- alertas metodologicos: tensoes conhecidas entre oferta por estabelecimento e
  capacidade publicada por UF.

O alerta metodologico esperado apos a troca para RT2030 real envolve AC, MA, PI,
GO e ES. Ele nao e uma falha do motor; sinaliza tensao entre oferta observada por
estabelecimento e capacidade publicada por UF.

Quando `painel_validacao*.csv` existe, o probe tambem reporta a validacao
externa PAINEL. O anchor atual e Spearman regional -0,5.

## Reproducibilidade

Instalacao para desenvolvimento:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

Exportacao operacional com PySUS:

```bash
.\.venv311\Scripts\python.exe -m pip install -e ".[ingest,dev]"
.\.venv311\Scripts\python.exe run_indicadores.py
```

Regeneracao offline do mart atual:

```bash
python scripts/regerar_mart.py
```

Dashboard:

```bash
python -m pip install -e ".[dashboard]"
streamlit run streamlit_app.py
```

## Submissao Limpa

Nao envie ZIP criado a partir da pasta inteira do workspace se ele incluir
`.venv311/`, caches ou downloads locais. A forma recomendada e gerar o pacote a
partir do Git:

```bash
git archive --format zip --output radarrt_submission_clean.zip HEAD
```

`.gitignore` ja cobre `.venv311/` por causa da regra `.venv*/`. Antes de
submeter, confira:

```bash
git check-ignore .venv311
git status --short
```

## Estado Atual do Projeto

A troca para RT2030 real esta aplicada e validada:

- incidencia: real, INCA 2026 curado;
- oferta: real, SIA-AR 2024;
- capacidade: real, parque RT2030 publicado;
- parque nacional: 409 LINACs;
- mart regenerado offline por `python scripts/regerar_mart.py`;
- anchors novos do mart: demanda reprimida 66.539, deficit 86, LSI 112,5,
  formacao 86/162/258/506, planos 86/506/R$860M e 183/1070/R$1,83B,
  expansao base 86/56/0 e superior 196/167/86, throughput 201/126/86/59/44,
  PAINEL Spearman -0,5;
- suite automatizada: 110 testes passando;
- lint: `ruff check .` limpo;
- probe operacional: 49/49 checks bloqueantes OK e 1 alerta metodologico.

## Proximos Upgrades

1. Reatribuir oferta por residencia do paciente com `AP_MUNPCN`, mantendo
   tambem a visao por estabelecimento.
2. Medir quadro profissional vigente com CNES de profissionais, quando houver
   recorte confiavel por UF e ocupacao.
3. Comparar o parque RT2030 com CNES-EQ maduro apos adocao plena da Portaria
   SAES/MS 3.695/2026.

## Frase Segura Para Pitch

Use:

> RadarRT mostra a fila invisivel da radioterapia com dados publicos, motor
> deterministico, procedencia explicita e um agente SQL offline. Quando as
> fontes entram em tensao, o sistema transforma isso em alerta metodologico em
> vez de esconder o problema.

Evite:

> Faltam exatamente 86 maquinas no Brasil.

Prefira:

> O mart atual estima deficit estrutural de 86 LINACs no cenario base, com
> capacidade por UF marcada como real (RT2030).

E acrescente, quando o tema for formacao:

> Operar esses 86 LINACs exige formar 506 profissionais especializados: 86
> fisicos medicos, 162 radio-oncologistas e 258 tecnicos RTT.
