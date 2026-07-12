# Frontend polido para apresentação ao vivo (5 min)

## Arquivo
`streamlit_app.py` → SUBSTITUI o da raiz. **Zero toque no motor** — só camada de
apresentação. Seus 110 testes não correm risco (nenhuma função de cálculo mudou).

## O que mudou

### 1. Acentuação completa (o maior ganho de polimento)
Todo o texto de tela agora tem português correto: "Visão geral", "invisível",
"Limitações", "Validação", "Utilização", "Déficit", "Físicos médicos",
"formação", "condição estrutural", etc. As **chaves de dados** (`"regiao"`,
`"incidencia"`, `"deficit_linacs"`, `"cenario_demanda"`...) foram preservadas
intactas — acentuação só no que o júri lê.

### 2. Ordem das abas no fluxo do pitch
Antes: Visão geral · Sensibilidade · Dimensionar · Validação · Pergunte · Limitações
Agora: **Visão geral · Dimensionar · Validação · Robustez · Pergunte · Limitações**
- "Dimensionar" (a solução) sobe logo após o problema.
- "Sensibilidade" virou "Robustez" e recuou (é defesa, não narrativa).
- Apoio (Pergunte aos dados, Limitações) fica no fim, para perguntas.

### 3. Legenda anti-confusão no tempo de espera
O simulador agora explica, abaixo dos cards: *"Tempo de espera = meses para
drenar a fila atual com a folga de capacidade existente; não é a espera de um
paciente individual; 'fila crescente' indica ρ ≥ 1"*. Blinda o "57 meses" de
virar pergunta capciosa ao vivo.

### 4. ρ legível
"rho" virou "ρ" nos rótulos de exibição (UFs ρ ≥ 1, Utilização (ρ)).

### 5. Validação e mapa com contraste de palco
A aba **Validação** ganhou uma leitura visual completa: hero de evidência,
badges, cards, barras regionais, scatter SVG offline e tabela escura. O mapa da
**Visão geral** agora usa cores mais fortes, contorno mais claro e nota curta de
leitura antes do coroplético. A intenção é que o júri entenda o sinal visual sem
precisar interpretar dataframe branco ou gráfico apagado.

## Roteiro sugerido de 3 atos (≈3min50s de tela)
1. **Visão geral** (~1min) — o mapa acende, AC/AP/RR em coral. "66.539 na fila,
   3 estados sem um único acelerador." O cair-o-queixo de abertura.
2. **Dimensionar** (~1min30s) — modo nacional (R$ 860 mi / 506 profissionais para
   a Lei dos 60 dias) e o slider por estado (Bahia: espera cai, selo "60 dias
   viável" acende). O momento interativo.
3. **Validação** (~1min) — a correlação com o PAINEL-Oncologia. "Nossa inferência
   bate com o monitoramento oficial."
As abas Robustez, Pergunte e Limitações ficam prontas para as perguntas do júri.

## Validação
- `py_compile`: OK
- `ruff`: OK
- `pytest`: 110/110
- `probe_outputs`: 49/49 checks bloqueantes
- Playwright visual: mapa e aba Validação renderizando sem erro de console
- chaves de dados: 9/9 intactas
- acentos de exibição: presentes
- nenhuma função de cálculo alterada
