"""Ingestao CNES-EQ: aceleradores lineares em uso e disponiveis ao SUS."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from .. import geo, schemas

# Portaria SAES/MS 3.695/2026, Anexo I:
# tipo 12 Radioterapia; equipamentos 01 e 02 sao aceleradores lineares.
TIPO_RADIOTERAPIA = "12"
COD_ACELERADOR_LINEAR: frozenset[str] = frozenset({"01", "02"})
COMPETENCIA_INICIAL_EQ_LINAC = (2026, 2)

_COL_MUNICIPIO = "CODUFMUN"
_COL_TIPO = "TP_EQUIP"
_COL_CODEQUIP = "CODEQUIP"
_COL_QT_USO = "QT_USO"
_COL_IND_SUS = "IND_SUS"


def baixar_cnes_eq(ufs: list[str], ano: int, mes: int) -> pd.DataFrame:
    """Baixa CNES-EQ via FTP do DATASUS usando PySUS 2.x.

    A API de alto nivel (pysus.cnes) roteia pelo catalogo DuckLake/S3 vazio.
    O CNES tem estrutura hierarquica no FTP: content() retorna grupos (DC, EE,
    EQ...), e cada grupo contem os arquivos. Alem disso, em competencias
    2026+, o campo TP_EQUIP foi renomeado para TIPEQUIP pelo DATASUS;
    normalizamos aqui para manter o contrato com normalizar_cnes_eq().
    """
    if (ano, mes) < COMPETENCIA_INICIAL_EQ_LINAC:
        raise ValueError(
            "LINACs so passaram a integrar CNES-EQ em 2026-02 pela "
            "Portaria SAES/MS 3.695/2026; competencias anteriores nao "
            "podem ser inferidas de CODEQUIP"
        )

    import asyncio  # import tardio: dependencia opcional

    _configurar_cache_pysus()
    from pysus.api.client import PySUS
    from pysus.api.ftp.databases import CNES as PySUSCNES

    ufs_set = set(ufs)

    async def _baixar() -> pd.DataFrame:
        """Baixa os arquivos EQ alvo e concatena os parquets retornados."""
        pysus = PySUS()
        ftp = await pysus.get_ftp()
        try:
            cnes = PySUSCNES(client=ftp)
            grupos = await cnes.content
            eq_group = next((g for g in grupos if g.name == "EQ"), None)
            if eq_group is None:
                raise RuntimeError("Grupo EQ nao encontrado no CNES-FTP")
            eq_files = await eq_group.content
            alvos = [
                f for f in eq_files
                if f.state in ufs_set and f.year == ano and f.month == mes
            ]
            sem_dados = [uf for uf in ufs if not any(f.state == uf for f in alvos)]
            if sem_dados:
                raise RuntimeError(
                    f"CNES-EQ sem dados para UFs solicitadas: {sem_dados}"
                )
            frames: list[pd.DataFrame] = []
            for arquivo in alvos:
                parquet = await pysus.download_to_parquet(arquivo)
                df = pd.read_parquet(parquet.path)
                # DATASUS renomeou TP_EQUIP para TIPEQUIP a partir de 2026
                if "TIPEQUIP" in df.columns and "TP_EQUIP" not in df.columns:
                    df = df.rename(columns={"TIPEQUIP": "TP_EQUIP"})
                frames.append(df)
            return pd.concat(frames, ignore_index=True)
        finally:
            await ftp.close()
            pysus.engine.dispose()

    return asyncio.run(_baixar())


def normalizar_cnes_eq(
    df_raw: pd.DataFrame,
    ufs: list[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Soma LINACs do tipo 12/codigos 01-02, em uso e disponiveis ao SUS."""
    esperadas = (_COL_MUNICIPIO, _COL_TIPO, _COL_CODEQUIP, _COL_QT_USO, _COL_IND_SUS)
    faltando = [col for col in esperadas if col not in df_raw.columns]
    if faltando:
        raise ValueError(f"CNES-EQ sem colunas esperadas: {faltando}")

    df = df_raw.copy()
    df[_COL_TIPO] = _normalizar_codigo(df[_COL_TIPO])
    df[_COL_CODEQUIP] = _normalizar_codigo(df[_COL_CODEQUIP])
    df = df[
        (df[_COL_TIPO] == TIPO_RADIOTERAPIA)
        & df[_COL_CODEQUIP].isin(COD_ACELERADOR_LINEAR)
    ].copy()

    df[_COL_IND_SUS] = pd.to_numeric(df[_COL_IND_SUS], errors="coerce")
    df[_COL_QT_USO] = pd.to_numeric(df[_COL_QT_USO], errors="coerce")
    if df[[_COL_IND_SUS, _COL_QT_USO]].isna().any().any():
        raise ValueError("CNES-EQ contem IND_SUS ou QT_USO invalido para LINAC")
    if (df[_COL_QT_USO] < 0).any():
        raise ValueError("CNES-EQ contem QT_USO negativo para LINAC")
    if not np.equal(df[_COL_QT_USO], np.floor(df[_COL_QT_USO])).all():
        raise ValueError("CNES-EQ contem QT_USO fracionario para LINAC")

    df = df[df[_COL_IND_SUS] == 1]
    df[schemas.COL_UF] = df[_COL_MUNICIPIO].map(geo.uf_de_codigo_municipio)
    agrupado = (
        df.dropna(subset=[schemas.COL_UF])
        .groupby(schemas.COL_UF, sort=False)[_COL_QT_USO]
        .sum()
        .astype(int)
    )
    if ufs is not None:
        agrupado = agrupado.reindex(geo.normalizar_ufs(ufs), fill_value=0)
    agrupado.index.name = schemas.COL_UF
    return agrupado.rename(schemas.COL_LINACS).reset_index()


def _normalizar_codigo(serie: pd.Series) -> pd.Series:
    """Normaliza codigos CNES numericos ou string para dois digitos."""
    return (
        serie.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(2)
    )


def _configurar_cache_pysus() -> None:
    """Isola o cache PySUS por processo para evitar locks locais."""
    os.environ.setdefault(
        "PYSUS_CACHEPATH",
        str(Path(tempfile.gettempdir()) / f"radarrt_pysus_{os.getpid()}"),
    )
