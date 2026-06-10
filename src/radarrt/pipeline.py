"""Orquestracao da ingestao para produzir o schema canonico do motor."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from . import geo, ibge, schemas, synthetic
from .sources import cnes, inca, parque, sia

FONTES_CAPACIDADE = ("cnes_novo", "parque_publicado")

logger = logging.getLogger(__name__)


@dataclass
class Procedencia:
    """Rastreia a origem de cada componente da base."""

    incidencia: str = "-"
    oferta: str = "-"
    linacs: str = "-"
    avisos: list[str] = field(default_factory=list)

    @property
    def tudo_real(self) -> bool:
        """Indica se incidencia, oferta e capacidade vieram de fontes reais."""
        return all(
            origem == "real"
            for origem in (self.incidencia, self.oferta, self.linacs)
        )


@dataclass
class BaseRadarRT:
    """Resultado da ingestao: dados canonicos e procedencia."""

    dados: pd.DataFrame
    procedencia: Procedencia


def construir_base(
    ano: int,
    *,
    csv_inca: str | Path | None = None,
    ufs: list[str] | tuple[str, ...] | None = None,
    meses: list[int] | tuple[int, ...] | None = None,
    mes_cnes: int | None = None,
    fonte_capacidade: str = "cnes_novo",
    csv_parque: str | Path | None = None,
    permitir_fallback: bool = True,
) -> BaseRadarRT:
    """Constroi uma base valida, usando fallback isolado por fonte."""
    if fonte_capacidade not in FONTES_CAPACIDADE:
        raise ValueError(
            f"fonte_capacidade deve ser uma de {FONTES_CAPACIDADE}"
        )
    selecionadas = geo.normalizar_ufs(ufs)
    competencias_sia = _normalizar_meses(meses)
    competencia_cnes = mes_cnes if mes_cnes is not None else max(competencias_sia)
    if competencia_cnes not in range(1, 13):
        raise ValueError("mes_cnes deve estar entre 1 e 12")

    proc = Procedencia()
    base = ibge.populacao_por_uf(selecionadas)
    sintetico = (
        synthetic.gerar_regioes(ufs=selecionadas) if permitir_fallback else None
    )

    incidencia = _ingerir_incidencia(csv_inca, selecionadas, sintetico, proc)
    oferta = _ingerir_oferta(
        selecionadas,
        ano,
        competencias_sia,
        sintetico,
        proc,
    )
    linacs = _ingerir_linacs(
        selecionadas,
        ano,
        competencia_cnes,
        fonte_capacidade,
        csv_parque,
        sintetico,
        proc,
    )

    dados = (
        base.merge(
            incidencia,
            on=schemas.COL_UF,
            how="left",
            validate="one_to_one",
        )
        .merge(
            oferta,
            on=schemas.COL_UF,
            how="left",
            validate="one_to_one",
        )
        .merge(
            linacs,
            on=schemas.COL_UF,
            how="left",
            validate="one_to_one",
        )
    )
    dados = dados[schemas.COLUNAS_ENTRADA]

    if dados.isna().any().any():
        ausentes = dados.columns[dados.isna().any()].tolist()
        raise RuntimeError(f"Pipeline produziu cobertura incompleta: {ausentes}")
    schemas.validar_entrada(dados)
    if proc.linacs != "sintetico" and len(dados) == len(geo.UFS):
        aviso = parque.checar_benchmark(int(dados[schemas.COL_LINACS].sum()))
        if aviso:
            logger.warning(aviso)
            proc.avisos.append(aviso)
    return BaseRadarRT(dados=dados, procedencia=proc)


def _normalizar_meses(meses: list[int] | tuple[int, ...] | None) -> list[int]:
    """Normaliza competencias SIA e rejeita listas vazias ou invalidas."""
    normalizados = list(range(1, 13)) if meses is None else list(meses)
    if not normalizados:
        raise ValueError("meses deve conter ao menos uma competencia")
    if any(mes not in range(1, 13) for mes in normalizados):
        raise ValueError("meses deve conter apenas valores entre 1 e 12")
    if len(normalizados) != len(set(normalizados)):
        raise ValueError("meses nao pode conter duplicatas")
    return normalizados


def _ingerir_incidencia(
    csv_inca: str | Path | None,
    ufs: list[str],
    sintetico: pd.DataFrame | None,
    proc: Procedencia,
) -> pd.DataFrame:
    """Ingere INCA curado ou recorta a incidencia sintetica de fallback."""
    cols = [
        schemas.COL_UF,
        schemas.COL_INCIDENCIA,
        schemas.COL_INCIDENCIA_SEM_PNM,
    ]
    if csv_inca is not None:
        try:
            df = inca.carregar_incidencia(csv_inca)
            _garantir_cobertura(df, ufs, "INCA")
            proc.incidencia = "real"
            return df[df[schemas.COL_UF].isin(ufs)][cols].copy()
        except Exception as exc:  # noqa: BLE001 - fronteira de fallback
            _avisar(proc, f"INCA falhou ({exc}); usando sintetico", sintetico)
    else:
        _avisar(proc, "INCA nao informado; usando sintetico", sintetico)
    proc.incidencia = "sintetico"
    return _recortar_sintetico(sintetico, cols)


def _ingerir_oferta(
    ufs: list[str],
    ano: int,
    meses: list[int],
    sintetico: pd.DataFrame | None,
    proc: Procedencia,
) -> pd.DataFrame:
    """Ingere SIA-AR real ou recorta a oferta sintetica de fallback."""
    cols = [schemas.COL_UF, schemas.COL_OFERTA_APAC]
    try:
        raw = sia.baixar_sia_ar(ufs, ano, meses)
        df = sia.normalizar_sia_ar(raw, ufs)
        sem_arquivo = raw.attrs.get("ufs_sem_arquivo", [])
        if sem_arquivo:
            aviso = (
                f"SIA-AR sem arquivos para UFs {sem_arquivo}; "
                "oferta zerada na base canonica"
            )
            logger.warning(aviso)
            proc.avisos.append(aviso)
        proc.oferta = "real"
        return df
    except Exception as exc:  # noqa: BLE001 - fronteira de fallback
        _avisar(proc, f"SIA-AR falhou ({exc}); usando sintetico", sintetico)
    proc.oferta = "sintetico"
    return _recortar_sintetico(sintetico, cols)


def _ingerir_linacs(
    ufs: list[str],
    ano: int,
    mes: int,
    fonte_capacidade: str,
    csv_parque: str | Path | None,
    sintetico: pd.DataFrame | None,
    proc: Procedencia,
) -> pd.DataFrame:
    """Ingere capacidade por CNES/parque publicado ou usa fallback sintetico."""
    cols = [schemas.COL_UF, schemas.COL_LINACS]
    try:
        if fonte_capacidade == "parque_publicado":
            if csv_parque is None:
                raise ValueError(
                    "fonte_capacidade='parque_publicado' exige csv_parque"
                )
            df = parque.carregar_parque(csv_parque)
            _garantir_cobertura(df, ufs, "Parque")
            qualidade = df.attrs.get("qualidade", "curado")
            df = df[df[schemas.COL_UF].isin(ufs)][cols].reset_index(drop=True)
            proc.linacs = (
                "estimado (parque publicado)"
                if qualidade == "estimado"
                else "real (parque publicado)"
            )
            aviso_qualidade = parque.aviso_qualidade(qualidade)
            if aviso_qualidade:
                logger.warning(aviso_qualidade)
                proc.avisos.append(aviso_qualidade)
            return df
        raw = cnes.baixar_cnes_eq(ufs, ano, mes)
        df = cnes.normalizar_cnes_eq(raw, ufs)
        proc.linacs = "real"
        return df
    except Exception as exc:  # noqa: BLE001 - fronteira de fallback
        _avisar(proc, f"Capacidade ({fonte_capacidade}) falhou ({exc}); "
                f"usando sintetico", sintetico)
    proc.linacs = "sintetico"
    return _recortar_sintetico(sintetico, cols)


def _garantir_cobertura(df: pd.DataFrame, ufs: list[str], fonte: str) -> None:
    """Confirma que a fonte trouxe todas as UFs solicitadas."""
    presentes = set(df[schemas.COL_UF])
    faltando = [uf for uf in ufs if uf not in presentes]
    if faltando:
        raise ValueError(f"{fonte} sem cobertura para UFs: {faltando}")


def _recortar_sintetico(
    sintetico: pd.DataFrame | None,
    cols: list[str],
) -> pd.DataFrame:
    """Seleciona colunas do fallback sintetico ou falha se ele estiver off."""
    if sintetico is None:
        raise RuntimeError("fallback sintetico esta desativado")
    return sintetico[cols].copy()


def _avisar(
    proc: Procedencia,
    mensagem: str,
    sintetico: pd.DataFrame | None,
) -> None:
    """Registra aviso ou transforma a falha em erro quando fallback esta off."""
    if sintetico is None:
        raise RuntimeError(f"{mensagem}; fallback sintetico esta desativado")
    logger.warning(mensagem)
    proc.avisos.append(mensagem)
