from __future__ import annotations

from pathlib import Path

import pandas as pd

from radarrt import schemas
from scripts import probe_outputs

OUTPUT_DIR = Path("data/outputs_2024")


def test_outputs_2024_estao_prontos_para_text_to_sql() -> None:
    esperados = {
        "base_canonica.csv",
        "indicadores_base.csv",
        "ranking_prioridade.csv",
        "sensibilidade_cenarios.csv",
        "resumo_nacional.csv",
        "auditoria_base.csv",
        "procedencia.csv",
    }
    existentes = {path.name for path in OUTPUT_DIR.glob("*.csv")}

    assert esperados <= existentes


def test_output_base_canonica_preserva_schema_e_totais() -> None:
    base = pd.read_csv(OUTPUT_DIR / "base_canonica.csv")

    assert list(base.columns) == schemas.COLUNAS_ENTRADA
    assert len(base) == 27
    assert base[schemas.COL_INCIDENCIA].sum() == 781_050
    assert base[schemas.COL_INCIDENCIA_SEM_PNM].sum() == 517_770
    assert base[schemas.COL_OFERTA_APAC].sum() == 141_715
    assert base[schemas.COL_LINACS].sum() == 363


def test_output_indicadores_tem_colunas_do_motor() -> None:
    indicadores = pd.read_csv(OUTPUT_DIR / "indicadores_base.csv")
    resumo = pd.read_csv(OUTPUT_DIR / "resumo_nacional.csv")
    procedencia = pd.read_csv(OUTPUT_DIR / "procedencia.csv")

    assert all(col in indicadores.columns for col in schemas.COLUNAS_SAIDA)
    assert _valor(resumo, "demanda_reprimida") == 66_539
    assert _valor(procedencia, "oferta") == "real"
    assert _valor(procedencia, "linacs") == "estimado (parque publicado)"


def test_probe_outputs_real_classifica_alertas_metodologicos() -> None:
    resultado = probe_outputs.auditar_outputs(OUTPUT_DIR)

    assert resultado.passou
    assert resultado.anchors["demanda_reprimida"] == 66_539
    assert resultado.anchors["deficit_linacs"] == 109
    assert resultado.anchors["lsi_nacional"] == 126.8
    assert resultado.anchors["grades_base"] == [1, 6, 18, 0, 2]
    assert any("Oferta anualizada" in alerta.nome for alerta in resultado.alertas)


def _valor(df: pd.DataFrame, metrica: str) -> object:
    return df.set_index("metrica").loc[metrica, "valor"]
