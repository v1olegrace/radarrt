"""Testes offline da camada de validacao cientifica."""

from __future__ import annotations

from radarrt import gerar_regioes
from radarrt import validation as v


def test_reproduz_benchmark_2020() -> None:
    check = v.reproduzir_benchmark_2020()
    assert check.passou, check.detalhe


def test_invariantes_todas_ok_em_base_valida() -> None:
    checks = v.invariantes(gerar_regioes())
    assert all(check.passou for check in checks), [
        str(check) for check in checks if not check.passou
    ]


def test_anualizar() -> None:
    assert v.anualizar(11_799, 3) == 47_196.0
    assert v.anualizar(100, 12) == 100.0


def test_anualizar_rejeita_meses_invalidos() -> None:
    for meses in (0, 13, -1):
        try:
            v.anualizar(100, meses)
        except ValueError:
            continue
        raise AssertionError(f"deveria rejeitar meses={meses}")


def test_diagnostico_nacional_separa_escalas() -> None:
    base = gerar_regioes()
    diag = v.diagnostico_nacional(base, meses_oferta=3)

    assert abs(diag["oferta_anualizada"] - diag["oferta_observada"] * 4) < 1.0
    assert diag["demanda_reprimida_honesta"] >= 0


def test_sensibilidade_ordena_demanda_por_cenario() -> None:
    df = v.sensibilidade(gerar_regioes()).set_index("cenario")

    assert df.loc["superior", "demanda_rt_sus"] > df.loc["base", "demanda_rt_sus"]
    assert df.loc["base", "demanda_rt_sus"] > df.loc["conservador", "demanda_rt_sus"]


def test_consistencia_dados_base_sintetica() -> None:
    checks = v.consistencia_dados(gerar_regioes(), meses_oferta=12)
    assert all(check.passou for check in checks), [
        str(check) for check in checks if not check.passou
    ]


def test_relatorio_gera_texto() -> None:
    texto = v.gerar_relatorio(gerar_regioes(), meses_oferta=12)
    assert "VEREDITO" in texto
    assert "LSI 2020" in texto
