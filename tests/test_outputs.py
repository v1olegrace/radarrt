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
        "sensibilidade_throughput.csv",
        "resumo_nacional.csv",
        "auditoria_base.csv",
        "procedencia.csv",
        "plano_nacional.csv",
        "cenarios_parque.csv",
        "painel_validacao.csv",
        "painel_validacao_regional.csv",
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
    assert base[schemas.COL_LINACS].sum() == 409


def test_output_indicadores_tem_colunas_do_motor() -> None:
    indicadores = pd.read_csv(OUTPUT_DIR / "indicadores_base.csv")
    resumo = pd.read_csv(OUTPUT_DIR / "resumo_nacional.csv")
    procedencia = pd.read_csv(OUTPUT_DIR / "procedencia.csv")

    assert all(col in indicadores.columns for col in schemas.COLUNAS_SAIDA)
    assert _valor(resumo, "demanda_reprimida") == 66_539
    assert _valor(resumo, "deficit_fisico_medico") == 86
    assert _valor(resumo, "deficit_radio_oncologista") == 162
    assert _valor(resumo, "deficit_tecnico_rtt") == 258
    assert _valor(resumo, "deficit_profissionais_total") == 506
    assert _valor(procedencia, "oferta") == "real"
    assert _valor(procedencia, "linacs") == "real (RT2030)"

    # Camadas derivadas obrigatorias: formacao especializada + tempo.
    for col in (
        schemas.COL_DEF_FISICO,
        schemas.COL_DEF_ONCO,
        schemas.COL_DEF_TECNICO,
        schemas.COL_DEF_PROFISSIONAIS,
        schemas.COL_UTILIZACAO,
        schemas.COL_TEMPO_ESPERA_MESES,
        schemas.COL_PRAZO_60D,
    ):
        assert col in indicadores.columns, f"coluna ausente: {col}"

    ba = indicadores.loc[indicadores[schemas.COL_UF] == "BA"].iloc[0]
    assert int(ba[schemas.COL_DEF_PROFISSIONAIS]) == 70

    # Insight-ancora: SP tem deficit zero mas ~57 meses de espera
    sp = indicadores.loc[indicadores[schemas.COL_UF] == "SP"].iloc[0]
    assert abs(sp[schemas.COL_TEMPO_ESPERA_MESES] - 57.2) < 1.0, (
        f"SP tempo_espera_meses={sp[schemas.COL_TEMPO_ESPERA_MESES]:.1f}, esperado ~57.2"
    )


def test_probe_outputs_real_classifica_alertas_metodologicos() -> None:
    resultado = probe_outputs.auditar_outputs(OUTPUT_DIR)

    assert resultado.passou
    assert resultado.anchors["demanda_reprimida"] == 66_539
    assert resultado.anchors["deficit_linacs"] == 86
    assert resultado.anchors["lsi_nacional"] == 112.5
    assert resultado.anchors["grades_base"] == [8, 5, 11, 0, 3]
    assert resultado.anchors["deficit_fisico_medico"] == 86
    assert resultado.anchors["deficit_radio_oncologista"] == 162
    assert resultado.anchors["deficit_tecnico_rtt"] == 258
    assert resultado.anchors["deficit_profissionais_total"] == 506
    assert resultado.anchors["plano_meta_1_linacs"] == 86
    assert resultado.anchors["plano_meta_1_profissionais"] == 506
    assert resultado.anchors["plano_meta_1_investimento"] == 860_000_000
    assert resultado.anchors["plano_meta_08_linacs"] == 183
    assert resultado.anchors["plano_meta_08_profissionais"] == 1_070
    assert resultado.anchors["plano_meta_08_investimento"] == 1_830_000_000
    assert resultado.anchors["parque_base_exp_0_deficit"] == 86
    assert resultado.anchors["parque_base_exp_40_deficit"] == 56
    assert resultado.anchors["parque_base_exp_121_deficit"] == 0
    assert resultado.anchors["parque_superior_exp_0_deficit"] == 196
    assert resultado.anchors["parque_superior_exp_40_deficit"] == 167
    assert resultado.anchors["parque_superior_exp_121_deficit"] == 86
    assert resultado.anchors["throughput_deficits"] == [201, 126, 86, 59, 44]
    assert resultado.anchors["throughput_ufs_fila"] == [24, 22, 19, 18, 17]
    assert resultado.anchors["throughput_lsi"] == [144.7, 126.6, 112.5, 101.3, 92.1]
    assert resultado.anchors["painel_spearman_regional"] == -0.5
    assert any("Oferta anualizada" in alerta.nome for alerta in resultado.alertas)


def test_output_painel_validacao_externa() -> None:
    painel = pd.read_csv(OUTPUT_DIR / "painel_validacao.csv")
    regional = pd.read_csv(OUTPUT_DIR / "painel_validacao_regional.csv")

    assert list(painel.columns) == [
        "uf",
        "regiao",
        "utilizacao",
        "grade",
        "pct_ate_60d",
    ]
    assert len(painel) == 27
    assert painel["pct_ate_60d"].dropna().between(0, 1).all()
    assert list(regional.columns) == ["regiao", "rho_medio", "pct_ate_60d_medio"]
    assert len(regional) == 5


def test_output_sensibilidade_throughput() -> None:
    tabela = pd.read_csv(OUTPUT_DIR / "sensibilidade_throughput.csv")

    assert list(tabela.columns) == [
        "throughput",
        "deficit_linacs",
        "ufs_fila_divergente",
        "lsi_nacional",
    ]
    assert tabela["throughput"].tolist() == [350, 400, 450, 500, 550]
    assert tabela["deficit_linacs"].tolist() == [201, 126, 86, 59, 44]
    assert tabela["ufs_fila_divergente"].tolist() == [24, 22, 19, 18, 17]
    assert tabela["lsi_nacional"].tolist() == [144.7, 126.6, 112.5, 101.3, 92.1]


def _valor(df: pd.DataFrame, metrica: str) -> object:
    return df.set_index("metrica").loc[metrica, "valor"]


def test_parque_rt2030_real_por_uf() -> None:
    # Blinda o dado real do censo RT2030 (Tabela 1, instalado todos os setores).
    parque = pd.read_csv("data/parque_linacs_2030.csv")

    assert len(parque) == 27 and parque["uf"].nunique() == 27
    assert parque["linacs_sus"].sum() == 409
    por_uf = dict(zip(parque["uf"], parque["linacs_sus"], strict=True))
    assert por_uf["SP"] == 127
    assert por_uf["AC"] == 0 and por_uf["AP"] == 0 and por_uf["RR"] == 0
    # A fonte nunca pode disparar a classificacao de 'estimado'.
    assert not parque["fonte"].str.contains("estimad|proporcional", case=False).any()


def test_grade_4_sao_estados_sem_acelerador() -> None:
    indicadores = pd.read_csv(OUTPUT_DIR / "indicadores_base.csv")
    grade_4 = sorted(indicadores.loc[indicadores[schemas.COL_GRADE] == 4, schemas.COL_UF])

    assert grade_4 == ["AC", "AP", "RR"]


def test_parque_real_nao_altera_demanda_reprimida() -> None:
    # O parque entra so em LSI/deficit/grade; a fila (incidencia - oferta)
    # permanece ancorada em 66.539 independentemente do parque adotado.
    resumo = pd.read_csv(OUTPUT_DIR / "resumo_nacional.csv").set_index("metrica")["valor"]

    assert int(resumo["demanda_reprimida"]) == 66_539
    assert int(resumo["linacs_instalados"]) == 409
