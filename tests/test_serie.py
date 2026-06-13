from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from radarrt import engine, schemas
from radarrt.sources import sia_temporal

OUTPUT_DIR = Path("data/outputs_2024")


def test_consistencia_detecta_ausente(monkeypatch: pytest.MonkeyPatch) -> None:
    sia_temporal._baixar_sia_ar_ano.cache_clear()

    def baixar(ano: int) -> pd.DataFrame:
        codigos = ["0000000001", "0000000002"] if ano == 2020 else ["0000000001"]
        return pd.DataFrame({"AP_PRIPAL": codigos})

    monkeypatch.setattr(sia_temporal, "_baixar_sia_ar_ano", baixar)

    ausentes = sia_temporal.checar_consistencia_codigos(
        [2020, 2021],
        {"0000000001": "A", "0000000002": "B"},
    )

    assert ausentes[2020] == []
    assert ausentes[2021] == ["0000000002"]


def test_gap_nao_negativo() -> None:
    oferta = pd.DataFrame(
        {
            "ano": [2023, 2023],
            schemas.COL_UF: ["AA", "BB"],
            "oferta_realizada": [700, 600],
        }
    )

    serie = engine.serie_temporal_oferta(oferta, demanda_esperada=1_000)

    assert serie.loc[0, "oferta_realizada"] == 1_300
    assert serie.loc[0, "gap"] == 0


def test_flag_pandemia() -> None:
    oferta = pd.DataFrame(
        {
            "ano": [2019, 2020, 2021, 2022],
            schemas.COL_UF: ["AA", "AA", "AA", "AA"],
            "oferta_realizada": [10, 10, 10, 10],
        }
    )

    serie = engine.serie_temporal_oferta(oferta, demanda_esperada=20)

    assert serie.set_index("ano")["pandemia"].to_dict() == {
        2019: False,
        2020: True,
        2021: True,
        2022: False,
    }


def test_serie_ordenada_sem_buraco_silencioso() -> None:
    oferta = pd.DataFrame(
        {
            "ano": [2021, 2019],
            schemas.COL_UF: ["AA", "AA"],
            "oferta_realizada": [11, 9],
        }
    )

    serie = engine.serie_temporal_oferta(oferta, demanda_esperada=20)

    assert serie["ano"].tolist() == [2019, 2020, 2021]
    assert pd.isna(serie.loc[serie["ano"] == 2020, "oferta_realizada"]).all()


def test_oferta_2024_bate_mart_principal() -> None:
    serie = pd.read_csv(OUTPUT_DIR / "serie_temporal.csv")
    resumo = pd.read_csv(OUTPUT_DIR / "resumo_nacional.csv").set_index("metrica")[
        "valor"
    ]

    oferta_2024 = float(serie.loc[serie["ano"] == 2024, "oferta_realizada"].iloc[0])

    assert round(oferta_2024) == round(float(resumo["oferta_realizada"])) == 141_715
