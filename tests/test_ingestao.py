"""Testes offline dos normalizadores e do pipeline de ingestao."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from radarrt import construir_base, geo, schemas
from radarrt.sources import cnes, inca, parque, sia


def _raw_sia_ar() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "AP_UFMUN": ["355030", "355030", "355030", "150140", "355030", "355030"],
            "AP_PRIPAL": [
                "0304010413",
                "0304010413",
                "0304010456",
                "0304010367",
                "0304010286",  # legado por campo: nao pertence ao modelo atual
                "0304010413",
            ],
            "AP_CNSPCN": ["A1", "A1", "A2", "B1", "A3", ""],
        }
    )


def _raw_cnes_eq() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "CODUFMUN": ["355030", "355030", "355030", "150140", "355030"],
            "TP_EQUIP": ["12", "12", "12", "12", "01"],
            "CODEQUIP": ["01", "02", "01", "01", "33"],
            "QT_USO": [2, 1, 5, 1, 9],
            "IND_SUS": [1, 1, 0, 1, 1],
        }
    )


def test_normalizar_sia_conta_cns_unico_e_completa_ufs() -> None:
    out = sia.normalizar_sia_ar(_raw_sia_ar(), ["SP", "PA", "AC"])
    por_uf = out.set_index(schemas.COL_UF)[schemas.COL_OFERTA_APAC].to_dict()

    assert por_uf == {"SP": 2, "PA": 1, "AC": 0}


def test_normalizar_sia_falha_cedo_com_colunas_ausentes() -> None:
    with pytest.raises(ValueError, match="colunas esperadas"):
        sia.normalizar_sia_ar(pd.DataFrame({"X": [1]}))


def test_normalizar_cnes_usa_tipo_e_codigos_da_portaria_3695() -> None:
    out = cnes.normalizar_cnes_eq(_raw_cnes_eq(), ["SP", "PA", "AC"])
    por_uf = out.set_index(schemas.COL_UF)[schemas.COL_LINACS].to_dict()

    assert {"01", "02"} == cnes.COD_ACELERADOR_LINEAR
    assert por_uf == {"SP": 3, "PA": 1, "AC": 0}


def test_cnes_eq_rejeita_competencia_anterior_a_portaria() -> None:
    with pytest.raises(ValueError, match="2026-02"):
        cnes.baixar_cnes_eq(["SP"], ano=2024, mes=12)


def test_normalizar_cnes_falha_com_quantidade_invalida() -> None:
    raw = _raw_cnes_eq()
    raw["QT_USO"] = raw["QT_USO"].astype(object)
    raw.loc[0, "QT_USO"] = "invalido"

    with pytest.raises(ValueError, match="QT_USO invalido"):
        cnes.normalizar_cnes_eq(raw)


def test_inca_normaliza_e_aplica_razao_quando_necessario() -> None:
    raw = pd.DataFrame(
        {"uf": ["SP", "PA"], "incidencia_total": [100_000, 10_000]}
    )

    out = inca.normalizar_incidencia(raw)

    assert out.set_index("uf").loc["SP", schemas.COL_INCIDENCIA_SEM_PNM] == 69_000
    with pytest.raises(ValueError, match="duplicadas"):
        inca.normalizar_incidencia(pd.concat([raw, raw.iloc[[0]]]))


def test_csv_inca_2026_oficial_fecha_totais_nacionais() -> None:
    out = inca.carregar_incidencia("data/incidencia_inca_2026.csv")

    assert len(out) == 27
    assert out[schemas.COL_INCIDENCIA].sum() == 781_050
    assert out[schemas.COL_INCIDENCIA_SEM_PNM].sum() == 517_770


def test_pipeline_fallback_e_selecao_de_ufs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def falhar(*args: object, **kwargs: object) -> pd.DataFrame:
        raise RuntimeError("fonte indisponivel")

    monkeypatch.setattr(sia, "baixar_sia_ar", falhar)
    monkeypatch.setattr(cnes, "baixar_cnes_eq", falhar)

    base = construir_base(ano=2024, ufs=["SP", "PA"], meses=[1])

    schemas.validar_entrada(base.dados)
    assert list(base.dados[schemas.COL_UF]) == ["SP", "PA"]
    assert base.procedencia.incidencia == "sintetico"
    assert base.procedencia.oferta == "sintetico"
    assert base.procedencia.linacs == "sintetico"
    assert len(base.procedencia.avisos) == 3


def test_pipeline_mantem_fontes_reais_isoladas(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    caminho = tmp_path / "inca.csv"
    pd.DataFrame(
        {
            "uf": ["SP", "PA"],
            "incidencia_total": [100_000, 10_000],
            "incidencia_sem_pnm": [70_000, 7_000],
        }
    ).to_csv(caminho, index=False)

    monkeypatch.setattr(sia, "baixar_sia_ar", lambda *args, **kwargs: _raw_sia_ar())
    monkeypatch.setattr(cnes, "baixar_cnes_eq", lambda *args, **kwargs: _raw_cnes_eq())

    base = construir_base(
        ano=2026,
        csv_inca=caminho,
        ufs=["SP", "PA"],
        meses=[1],
        mes_cnes=5,
    )

    assert base.procedencia.tudo_real
    assert not base.procedencia.avisos
    assert base.dados.set_index("uf").loc["SP", schemas.COL_LINACS] == 3
    assert base.dados.set_index("uf").loc["PA", schemas.COL_OFERTA_APAC] == 1


def test_pipeline_registra_uf_sem_arquivo_sia(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    caminho = tmp_path / "inca.csv"
    pd.DataFrame(
        {
            "uf": ["SP", "PA", "AC"],
            "incidencia_total": [100_000, 10_000, 1_000],
            "incidencia_sem_pnm": [70_000, 7_000, 700],
        }
    ).to_csv(caminho, index=False)

    raw_sia = _raw_sia_ar()
    raw_sia.attrs["ufs_sem_arquivo"] = ["AC"]
    monkeypatch.setattr(sia, "baixar_sia_ar", lambda *args, **kwargs: raw_sia)
    monkeypatch.setattr(cnes, "baixar_cnes_eq", lambda *args, **kwargs: _raw_cnes_eq())

    base = construir_base(
        ano=2026,
        csv_inca=caminho,
        ufs=["SP", "PA", "AC"],
        meses=[1],
        mes_cnes=5,
    )

    assert any(
        "AC" in aviso and "SIA-AR sem arquivos" in aviso
        for aviso in base.procedencia.avisos
    )


def test_pipeline_fallback_desativado_propaga_falha() -> None:
    with pytest.raises(RuntimeError, match="fallback sintetico esta desativado"):
        construir_base(ano=2024, ufs=["SP"], meses=[1], permitir_fallback=False)


# ---------------------------------------------------------------------------
# Passo 2b - parque publicado (RT2030) e check de benchmark
# ---------------------------------------------------------------------------
def _csv_parque_completo(tmp_path: Path) -> Path:
    linhas = {"uf": list(geo.UFS), "linacs_sus": [13] * len(geo.UFS)}
    caminho = tmp_path / "parque.csv"
    pd.DataFrame(linhas).to_csv(caminho, index=False)
    return caminho  # 27 * 13 = 351 (~ benchmark 360)


def test_parque_normaliza_e_valida() -> None:
    df = parque.normalizar_parque(
        pd.DataFrame({"uf": ["SP", "pa "], "linacs_sus": [5, 2], "fonte": ["x", "y"]})
    )
    assert set(df.columns) == {"uf", "linacs_sus"}
    assert df.set_index("uf").loc["PA", "linacs_sus"] == 2


def test_parque_rejeita_valor_ausente() -> None:
    with pytest.raises(ValueError, match="preencha o template"):
        parque.normalizar_parque(pd.DataFrame({"uf": ["SP"], "linacs_sus": [None]}))


def test_benchmark_pega_transicao_cnes() -> None:
    assert parque.checar_benchmark(27) is not None  # 27 vs ~360 -> avisa
    assert parque.checar_benchmark(360) is None  # no alvo -> ok
    assert parque.checar_benchmark(351) is None  # dentro da tolerancia


def test_pipeline_fonte_parque_publicado(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sia, "baixar_sia_ar", lambda *args, **kwargs: _raw_sia_ar())
    caminho = _csv_parque_completo(tmp_path)
    base = construir_base(
        ano=2026,
        fonte_capacidade="parque_publicado",
        csv_parque=caminho,
    )
    schemas.validar_entrada(base.dados)
    assert base.procedencia.linacs == "real (parque publicado)"
    assert int(base.dados[schemas.COL_LINACS].sum()) == 351
    # 351 ~ 360: nenhum aviso de benchmark (outras fontes podem ter avisos)
    assert not any("benchmark" in a for a in base.procedencia.avisos)


def test_pipeline_parque_estimado_nao_vira_real(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sia, "baixar_sia_ar", lambda *args, **kwargs: _raw_sia_ar())
    base = construir_base(
        ano=2026,
        csv_inca="data/incidencia_inca_2026.csv",
        fonte_capacidade="parque_publicado",
        csv_parque="data/parque_linacs_2030.csv",
    )

    assert base.procedencia.linacs == "estimado (parque publicado)"
    assert any("estimados" in aviso for aviso in base.procedencia.avisos)


def test_pipeline_fonte_invalida() -> None:
    with pytest.raises(ValueError, match="fonte_capacidade"):
        construir_base(ano=2026, fonte_capacidade="inexistente")
