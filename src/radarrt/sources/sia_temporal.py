"""Serie temporal de oferta SIA-AR para radioterapia externa."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from functools import cache

import pandas as pd

from .. import geo, schemas
from . import sia

logger = logging.getLogger(__name__)

ANOS_SERIE_TEMPORAL: tuple[int, ...] = (2019, 2020, 2021, 2022, 2023, 2024)
MESES_ANO_COMPLETO: tuple[int, ...] = tuple(range(1, 13))

# Mesmo conjunto usado no mart principal de 2024. Os tres codigos de modalidade
# de teleterapia legada nao entram aqui porque nao compoem a ancora 141.715.
CODIGOS_RADIOTERAPIA_EXTERNA: Mapping[str, str] = sia.PROC_RADIOTERAPIA_EXTERNA_LABELS


def ingerir_oferta_anual(
    anos: Sequence[int],
    codigos: Mapping[str, str],
) -> pd.DataFrame:
    """Oferta de teleterapia externa (pacientes/ano) por UF e ano, do SIA-AR.

    Reusa o normalizador de oferta do mart principal, apenas parametrizando o
    ano e o conjunto de codigos. Falhas por ano entram como oferta ausente para
    permitir degradacao honesta da serie.
    """
    codigos_alvo = list(codigos)
    linhas: list[pd.DataFrame] = []
    for ano in _normalizar_anos(anos):
        try:
            raw = _baixar_sia_ar_ano(ano)
            oferta = sia.normalizar_sia_ar(raw, list(geo.UFS), codigos=codigos_alvo)
            oferta = oferta.rename(columns={schemas.COL_OFERTA_APAC: "oferta_realizada"})
        except Exception as exc:  # noqa: BLE001 - fronteira de degradacao
            logger.warning("SIA-AR %s falhou na serie temporal: %s", ano, exc)
            oferta = pd.DataFrame(
                {
                    schemas.COL_UF: list(geo.UFS),
                    "oferta_realizada": pd.NA,
                }
            )
        oferta.insert(0, "ano", ano)
        linhas.append(oferta[["ano", schemas.COL_UF, "oferta_realizada"]])

    if not linhas:
        return pd.DataFrame(columns=["ano", schemas.COL_UF, "oferta_realizada"])
    return pd.concat(linhas, ignore_index=True)


def checar_consistencia_codigos(
    anos: Sequence[int],
    codigos: Mapping[str, str],
) -> dict[int, list[str]]:
    """Para cada ano, lista codigos ausentes no SIA-AR daquele ano.

    Quando a extracao de um ano falha, todos os codigos entram como ausentes.
    Isso impede comparacao silenciosa de anos incompletos.
    """
    codigos_alvo = list(codigos)
    ausentes_por_ano: dict[int, list[str]] = {}
    for ano in _normalizar_anos(anos):
        try:
            raw = _baixar_sia_ar_ano(ano)
            presentes = sia.codigos_presentes_sia_ar(raw, codigos_alvo)
            ausentes = [codigo for codigo in codigos_alvo if codigo not in presentes]
        except Exception as exc:  # noqa: BLE001 - fronteira de degradacao
            logger.warning("SIA-AR %s falhou na checagem de codigos: %s", ano, exc)
            ausentes = codigos_alvo.copy()
        ausentes_por_ano[ano] = ausentes
    return ausentes_por_ano


def _normalizar_anos(anos: Sequence[int]) -> list[int]:
    normalizados = [int(ano) for ano in anos]
    if not normalizados:
        raise ValueError("anos deve conter ao menos um ano")
    if len(normalizados) != len(set(normalizados)):
        raise ValueError("anos nao pode conter duplicatas")
    return normalizados


@cache
def _baixar_sia_ar_ano(ano: int) -> pd.DataFrame:
    """Baixa um ano completo uma vez por processo."""
    return sia.baixar_sia_ar(list(geo.UFS), ano, list(MESES_ANO_COMPLETO))
