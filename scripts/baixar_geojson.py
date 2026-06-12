"""Baixa UMA vez o GeoJSON das UFs do Brasil e salva em data/geo/br_uf.json.

Depois de salvo e versionado, o dashboard usa o arquivo local - 100% offline
no palco. O ``streamlit_app`` degrada para o mapa de bolhas se o arquivo faltar,
entao rodar isto e opcional (so para ter o mapa coropletico).

Uso:
    python scripts/baixar_geojson.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

DESTINO = Path(__file__).resolve().parents[1] / "data" / "geo" / "br_uf.json"

# Fontes publicas de fronteiras das UFs (tenta em ordem ate uma funcionar).
FONTES = (
    "https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/"
    "public/data/brazil-states.geojson",
    "https://raw.githubusercontent.com/giuliano-macedo/geodata-br-states/main/"
    "geojson/br_states.json",
    "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/"
    "geojs-100-mun.json",
)


def baixar() -> int:
    """Tenta cada fonte e salva o primeiro GeoJSON valido."""
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    for url in FONTES:
        try:
            print(f"tentando {url} ...")
            with urllib.request.urlopen(url, timeout=30) as resp:
                dados = json.loads(resp.read().decode("utf-8"))
            if dados.get("type") == "FeatureCollection" and dados.get("features"):
                DESTINO.write_text(json.dumps(dados), encoding="utf-8")
                print(f"OK: {len(dados['features'])} feicoes salvas em {DESTINO}")
                return 0
        except Exception as exc:  # noqa: BLE001 - runner manual, melhor mensagem
            print(f"  falhou: {exc}")
    print(
        "Nenhuma fonte respondeu. Baixe um GeoJSON de UFs do Brasil manualmente "
        f"e salve em {DESTINO} (o join aceita propriedade 'sigla' ou 'name')."
    )
    return 1


if __name__ == "__main__":
    sys.exit(baixar())
