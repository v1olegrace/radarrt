# Dashboard RadarRT — Cherenkov (final, pronto pra subir)

## Arquivos do pacote
| Arquivo aqui | Destino no repo | Ação |
|---|---|---|
| `streamlit_app.py` | `streamlit_app.py` (raiz) | **SUBSTITUI** |
| `baixar_geojson.py` | `scripts/baixar_geojson.py` | **NOVO** |
| `preview.html` | — | só pra ver no navegador (não vai pro repo) |

## Ver agora, sem rodar nada
Abra `preview.html`. É o visual real e completo: hero, mostradores que sobem
(boot), mapa coroplético dos estados, hook grade-4 pulsando e ranking.

## Subir o dashboard (3 comandos)
```bash
# 1. copie streamlit_app.py (raiz) e scripts/baixar_geojson.py
# 2. (opcional, p/ o mapa coroplético) baixe o GeoJSON UMA vez:
python scripts/baixar_geojson.py        # -> data/geo/br_uf.json
# 3. rode:
streamlit run streamlit_app.py
```
Depois de baixar, **versione** `data/geo/br_uf.json`: o coroplético roda 100%
offline no palco. Sem o arquivo, o app cai automaticamente nas bolhas — nada quebra.

## Design
- **Cherenkov**: espaço profundo, glow #3DDCFF, Poppins + JetBrains Mono.
- **Mapa coroplético**: estados pela grade (teal→lime→âmbar→coral). AC/AP/RR coral.
  Join por sigla OU nome via `nomes.NOME_PARA_UF` — aceita quase qualquer GeoJSON.
- **Animações**: entrada escalonada (hero→cards→hook), glow respirando, hover,
  pulso grade-4. Tudo desliga com `prefers-reduced-motion`.

## Conteúdo (pendência do "estimado" resolvida)
- Todo "estimado por UF" → **"real (RT2030)"**.
- Procedência: incidência real · oferta real · parque real (RT2030).
- Limitações: caveats honestos mantidos (oferta por estabelecimento; ranking exploratório).

## Cidades
Sem pontos de cidade de propósito: exigiria geocodar estabelecimentos do CNES
(não está no parque por UF). Próximo passo honesto, não dado inventado.

## Técnico
- Compila limpo; sem localStorage; offline-safe no app.
- Contagem dos números é do preview; no Streamlit os números entram com a
  revelação CSS dos cards (Streamlit não executa <script>).
- Requer streamlit>=1.36 e pydeck>=0.9 (já no requirements).
