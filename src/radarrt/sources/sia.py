"""Ingestao SIA-AR: cursos de radioterapia externa realizados."""

from __future__ import annotations

import logging
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from .. import geo, schemas

logger = logging.getLogger(__name__)

# Procedimentos principais vigentes desde maio de 2019 para radioterapia
# externa de neoplasias malignas. Braquiterapia e doencas benignas ficam fora
# porque nao consomem LINAC ou nao pertencem a incidencia oncologica usada.
PROC_RADIOTERAPIA_EXTERNA_LABELS: dict[str, str] = {
    "0304010367": "Radioterapia de cabeca e pescoco",
    "0304010375": "Radioterapia de aparelho digestivo",
    "0304010383": "Radioterapia de torax",
    "0304010391": "Radioterapia de ossos/cartilagens/partes moles",
    "0304010405": "Radioterapia de pele",
    "0304010413": "Radioterapia de mama",
    "0304010421": "Radioterapia de cancer ginecologico",
    "0304010448": "Radioterapia de penis",
    "0304010456": "Radioterapia de prostata",
    "0304010472": "Radioterapia de aparelho urinario",
    "0304010480": "Radioterapia de olhos e anexos",
    "0304010502": "Radioterapia de sistema nervoso central",
    "0304010510": "Radioterapia estereotaxica",
    "0304010529": "Radioterapia de metastase em sistema nervoso central",
    "0304010537": "Radioterapia de plasmocitoma/mieloma/metastases",
    "0304010545": "Radioterapia de cadeia linfatica",
    "0304010553": "Radioterapia de linfoma e leucemia",
    "0304010561": "Radioterapia de corpo inteiro",
}
PROC_RADIOTERAPIA_EXTERNA: frozenset[str] = frozenset(
    PROC_RADIOTERAPIA_EXTERNA_LABELS
)

_COL_MUNICIPIO = "AP_UFMUN"
_COL_PROC = "AP_PRIPAL"
_COL_PACIENTE = "AP_CNSPCN"


def baixar_sia_ar(ufs: list[str], ano: int, meses: list[int]) -> pd.DataFrame:
    """Baixa SIA-AR via FTP do DATASUS usando PySUS 2.x.

    A API de alto nivel (pysus.sia) roteia pelo catalogo DuckLake/S3, que nao
    tem dados SIA-AR indexados. Alem disso, search(group='AR') compara um
    objeto Group com a string 'AR' - nunca iguala. Por isso usamos o cliente
    FTP diretamente e filtramos por f.group.name manualmente.
    """
    if ano < 2019:
        raise ValueError(
            "O normalizador SIA suporta anos completos a partir de 2019, "
            "apos a mudanca do modelo de radioterapia do SIGTAP"
        )

    import asyncio  # import tardio: dependencia opcional

    _configurar_cache_pysus()
    from pysus.api.client import PySUS
    from pysus.api.ftp.databases import SIA as PySUSSIA

    ufs_set = set(ufs)
    meses_set = set(meses)

    async def _baixar() -> pd.DataFrame:
        """Baixa os arquivos AR alvo e concatena os parquets retornados."""
        pysus = PySUS()
        ftp = await pysus.get_ftp()
        try:
            sia = PySUSSIA(client=ftp)
            contents = await sia.content
            alvos = [
                f for f in contents
                if getattr(f, "group", None) and f.group.name == "AR"
                and f.state in ufs_set
                and f.year == ano
                and f.month in meses_set
            ]
            sem_dados = [uf for uf in ufs if not any(f.state == uf for f in alvos)]
            if sem_dados:
                if not alvos:
                    raise RuntimeError(
                        f"SIA-AR sem dados para nenhuma UF solicitada: {sem_dados}"
                    )
                # UFs sem arquivo (ex: estados sem servico RT registrado no DATASUS)
                # ficam com 0 apos normalizar_sia_ar._completar_ufs()
                logger.warning(
                    "SIA-AR sem arquivos para UFs: %s - serao zeradas",
                    sem_dados,
                )
            frames: list[pd.DataFrame] = []
            for arquivo in alvos:
                parquet = await pysus.download_to_parquet(arquivo)
                frames.append(pd.read_parquet(parquet.path))
            out = pd.concat(frames, ignore_index=True)
            out.attrs["ufs_sem_arquivo"] = sem_dados
            return out
        finally:
            await ftp.close()
            pysus.engine.dispose()

    return asyncio.run(_baixar())


def normalizar_sia_ar(
    df_raw: pd.DataFrame,
    ufs: list[str] | tuple[str, ...] | None = None,
    codigos: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Conta CNS distintos por UF entre procedimentos de RT externa."""
    faltando = [
        col
        for col in (_COL_MUNICIPIO, _COL_PROC, _COL_PACIENTE)
        if col not in df_raw.columns
    ]
    if faltando:
        raise ValueError(f"SIA-AR sem colunas esperadas: {faltando}")

    df = df_raw.copy()
    df[_COL_PROC] = _normalizar_codigo(df[_COL_PROC], largura=10)
    df[_COL_PACIENTE] = df[_COL_PACIENTE].astype("string").str.strip()
    df[_COL_PACIENTE] = df[_COL_PACIENTE].replace("", pd.NA)
    df[schemas.COL_UF] = df[_COL_MUNICIPIO].map(geo.uf_de_codigo_municipio)

    codigos_alvo = _normalizar_codigos(codigos or PROC_RADIOTERAPIA_EXTERNA)
    df = df[
        df[_COL_PROC].isin(codigos_alvo)
        & df[_COL_PACIENTE].notna()
        & df[schemas.COL_UF].notna()
    ]
    agrupado = (
        df.groupby(schemas.COL_UF, sort=False)[_COL_PACIENTE]
        .nunique()
        .astype(int)
    )
    return _completar_ufs(agrupado, schemas.COL_OFERTA_APAC, ufs)


def codigos_presentes_sia_ar(
    df_raw: pd.DataFrame,
    codigos: Iterable[str] | None = None,
) -> set[str]:
    """Lista codigos de procedimento presentes no SIA-AR bruto."""
    if _COL_PROC not in df_raw.columns:
        raise ValueError(f"SIA-AR sem coluna esperada: {_COL_PROC}")

    presentes = set(_normalizar_codigo(df_raw[_COL_PROC], largura=10).dropna())
    if codigos is None:
        return presentes
    return presentes & _normalizar_codigos(codigos)


def _normalizar_codigo(serie: pd.Series, largura: int) -> pd.Series:
    """Normaliza codigos SIA preservando zeros a esquerda."""
    return (
        serie.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(largura)
    )


def _normalizar_codigos(codigos: Iterable[str]) -> frozenset[str]:
    """Normaliza um conjunto de codigos SIA para comparacoes."""
    return frozenset(pd.Series(list(codigos), dtype="string").str.strip().str.zfill(10))


def _configurar_cache_pysus() -> None:
    """Isola o cache PySUS por processo para evitar locks locais."""
    os.environ.setdefault(
        "PYSUS_CACHEPATH",
        str(Path(tempfile.gettempdir()) / f"radarrt_pysus_{os.getpid()}"),
    )


def _completar_ufs(
    serie: pd.Series,
    nome: str,
    ufs: list[str] | tuple[str, ...] | None,
) -> pd.DataFrame:
    """Completa UFs ausentes com zero e retorna o contrato canonico."""
    if ufs is not None:
        serie = serie.reindex(geo.normalizar_ufs(ufs), fill_value=0)
    serie.index.name = schemas.COL_UF
    return serie.rename(nome).reset_index()
