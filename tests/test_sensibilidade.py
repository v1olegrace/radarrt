from __future__ import annotations

import pandas as pd
import pytest

from radarrt import schemas
from radarrt.config import CENARIOS, Params
from radarrt.engine import calcular_indicadores, sensibilidade_throughput

BASE = pd.read_csv("data/outputs_2024/base_canonica.csv")


def test_throughput_450_bate_ancora() -> None:
    tabela = sensibilidade_throughput(BASE)
    linha = tabela.loc[tabela["throughput"] == 450].iloc[0]

    assert int(linha["deficit_linacs"]) == 86
    assert int(linha["ufs_fila_divergente"]) == 19
    assert float(linha["lsi_nacional"]) == 112.5


def test_monotonia_deficit() -> None:
    tabela = sensibilidade_throughput(BASE)
    deficits = tabela["deficit_linacs"].tolist()

    assert deficits == sorted(deficits, reverse=True)


def test_extremos() -> None:
    tabela = sensibilidade_throughput(BASE).set_index("throughput")

    assert int(tabela.loc[350, "deficit_linacs"]) == 201
    assert int(tabela.loc[550, "deficit_linacs"]) == 44


def test_reprimida_invariante() -> None:
    reprimidas = []
    for throughput in (350, 400, 450, 500, 550):
        params = Params(
            rur=CENARIOS["base"].rur,
            sus_share=CENARIOS["base"].sus_share,
            linac_throughput=throughput,
            nome=f"throughput_{throughput}",
        )
        calc = calcular_indicadores(BASE, params)
        reprimidas.append(round(float(calc[schemas.COL_DEMANDA_REPRIMIDA].sum())))

    assert reprimidas == [66_539] * 5


@pytest.mark.parametrize("throughput", [0, -1])
def test_throughput_invalido(throughput: int) -> None:
    with pytest.raises(ValueError, match="throughput deve ser positivo"):
        sensibilidade_throughput(BASE, throughputs=(throughput,))
