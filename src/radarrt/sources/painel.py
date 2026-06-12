"""Ingestao do PAINEL-Oncologia (DATASUS) para validacao externa.

O PAINEL-Oncologia e um painel derivado do DATASUS. Para validar a camada de
tempo do RadarRT, usamos a saida oficial do TabNet e materializamos um cache
versionado por ano. O PAINEL valida a inferencia, mas nao entra no calculo da
fila, do deficit ou do LSI.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import requests

from .. import geo

TABNET_DEF = "PAINEL_ONCO/PAINEL_ONCOLOGIABR.def"
TABNET_BASE = f"http://tabnet.datasus.gov.br/cgi/dhdat.exe?{TABNET_DEF}"
TABNET_POST = f"http://tabnet.datasus.gov.br/cgi/webtabx.exe?{TABNET_DEF}"
CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "painel_onco"
JANELA_PADRAO: tuple[int, ...] = (2019, 2020, 2021, 2022, 2023, 2024)
COLUNAS_CACHE = [
    "uf",
    "casos_0_30",
    "casos_31_60",
    "casos_mais_60",
    "casos_sem_info",
]


@dataclass(frozen=True)
class ConsultaPainel:
    """Parametros da consulta ao PAINEL que entram no sidecar de procedencia."""

    ano: int
    modalidade: str = "radioterapia"
    linha: str = "UF do tratamento"
    coluna: str = "Tempo Tratamento"


@dataclass(frozen=True)
class _Opcao:
    texto: str
    valor: str


@dataclass(frozen=True)
class _Select:
    nome: str
    opcoes: tuple[_Opcao, ...]


class _FormParser(HTMLParser):
    """Extrai selects/options do formulario antigo do TabNet."""

    def __init__(self) -> None:
        super().__init__()
        self.selects: list[_Select] = []
        self._select_nome: str | None = None
        self._opcoes: list[_Opcao] = []
        self._opcao_valor: str | None = None
        self._opcao_texto: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        dados = {chave.lower(): valor or "" for chave, valor in attrs}
        if tag.lower() == "select":
            self._commit_option()
            self._select_nome = dados.get("name")
            self._opcoes = []
        elif tag.lower() == "option" and self._select_nome is not None:
            self._commit_option()
            self._opcao_valor = dados.get("value", "")
            self._opcao_texto = []

    def handle_data(self, data: str) -> None:
        if self._opcao_valor is not None:
            self._opcao_texto.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "option":
            self._commit_option()
        elif tag.lower() == "select" and self._select_nome is not None:
            self._commit_option()
            self.selects.append(_Select(self._select_nome, tuple(self._opcoes)))
            self._select_nome = None
            self._opcoes = []

    def _commit_option(self) -> None:
        if self._opcao_valor is None:
            return
        self._opcoes.append(
            _Opcao(
                texto="".join(self._opcao_texto).strip(),
                valor=self._opcao_valor,
            )
        )
        self._opcao_valor = None
        self._opcao_texto = []


def _normalizar(texto: object) -> str:
    sem_soft_hyphen = str(texto).replace("\xad", "")
    forma = unicodedata.normalize("NFKD", sem_soft_hyphen)
    return "".join(
        caractere for caractere in forma if not unicodedata.combining(caractere)
    ).lower()


def _request_text(
    metodo: str,
    url: str,
    *,
    body: bytes | None = None,
    timeout: int = 60,
) -> str:
    headers = {
        "User-Agent": "RadarRT/0.1 (+https://github.com/v1olegrace/radarrt)",
        "Accept": "text/html,application/xhtml+xml,*/*",
    }
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    ultimo_erro: Exception | None = None
    for _ in range(3):
        try:
            resposta = requests.request(
                metodo,
                url,
                data=body,
                headers=headers,
                timeout=timeout,
            )
            resposta.raise_for_status()
            return resposta.content.decode("latin-1", errors="replace")
        except requests.RequestException as exc:
            ultimo_erro = exc
    raise RuntimeError(f"falha ao consultar PAINEL-Oncologia: {ultimo_erro}") from ultimo_erro


def _parsear_formulario(html: str) -> list[_Select]:
    parser = _FormParser()
    parser.feed(html)
    return parser.selects


def _select_por_nome(selects: Iterable[_Select], nome: str) -> _Select:
    alvo = _normalizar(nome)
    for select in selects:
        if alvo in _normalizar(select.nome):
            return select
    raise ValueError(f"select do TabNet nao encontrado: {nome}")


def _opcao_por_texto(select: _Select, texto: str) -> str:
    alvo = _normalizar(texto)
    for opcao in select.opcoes:
        if alvo in _normalizar(opcao.texto):
            return opcao.valor
    raise ValueError(f"opcao do TabNet nao encontrada em {select.nome}: {texto}")


def _fetch_tabnet(consulta: ConsultaPainel, timeout: int = 60) -> str:
    """POST no TabNet e retorna o HTML cru da tabela.

    O formulario usa campos com acentos em ISO-8859-1. Por isso o payload e
    percent-encoded em latin-1; com UTF-8 o TabNet ignora filtros como ano e
    modalidade, gerando uma tabela aparentemente valida, mas metodologicamente
    errada.
    """
    formulario = _request_text("GET", TABNET_BASE, timeout=timeout)
    selects = _parsear_formulario(formulario)
    periodo = _select_por_nome(selects, "PAno do diagnostico")
    modalidade = _select_por_nome(selects, "Modalidade Terapeutica")
    payload = {
        "Linha": _opcao_por_texto(_select_por_nome(selects, "Linha"), consulta.linha),
        "Coluna": _opcao_por_texto(_select_por_nome(selects, "Coluna"), consulta.coluna),
        "Incremento": _opcao_por_texto(_select_por_nome(selects, "Incremento"), "Casos"),
        periodo.nome: _opcao_por_texto(periodo, str(consulta.ano)),
        modalidade.nome: _opcao_por_texto(modalidade, consulta.modalidade),
        "nomedef": TABNET_DEF,
    }
    body = urlencode(payload, encoding="latin-1").encode("ascii")
    return _request_text("POST", TABNET_POST, body=body, timeout=timeout)


def _uf_de_rotulo(rotulo: str) -> str | None:
    if _normalizar(rotulo).startswith("total"):
        return None
    match = re.match(r"\s*(\d{2})\b", rotulo)
    if match is None:
        return None
    return geo.COD_IBGE_PARA_UF.get(match.group(1))


def _campo_de_coluna(coluna: str) -> str | None:
    normalizada = _normalizar(coluna)
    if "ate 30" in normalizada:
        return "casos_0_30"
    if "31" in normalizada and "60" in normalizada:
        return "casos_31_60"
    if "mais de 60" in normalizada:
        return "casos_mais_60"
    if "sem informacao" in normalizada:
        return "casos_sem_info"
    return None


def _parsear(html: str) -> pd.DataFrame:
    """Extrai a tabela UF x faixa de tempo do retorno do TabNet."""
    colunas = re.findall(r"data\.addColumn\('number','([^']+)'\)", html)
    campos = [_campo_de_coluna(coluna) for coluna in colunas]
    bloco = re.search(r"data\.addRows\(\[(?P<linhas>.*?)\]\);", html, flags=re.S)
    if bloco is None:
        raise ValueError("retorno do PAINEL sem bloco data.addRows")

    linhas = {
        uf: {
            "uf": uf,
            "casos_0_30": 0,
            "casos_31_60": 0,
            "casos_mais_60": 0,
            "casos_sem_info": 0,
        }
        for uf in geo.UFS
    }
    encontrou_uf = False
    padrao_linha = re.compile(r'\[\s*"(?P<rotulo>[^"]+)"\s*,(?P<valores>.*?)\]', re.S)
    for match in padrao_linha.finditer(bloco.group("linhas")):
        uf = _uf_de_rotulo(match.group("rotulo"))
        if uf is None:
            continue
        valores = [
            int(float(valor))
            for valor in re.findall(
                r"\{v:\s*([-+]?\d+(?:\.\d+)?)",
                match.group("valores"),
            )
        ]
        for campo, valor in zip(campos, valores, strict=False):
            if campo is not None:
                linhas[uf][campo] = valor
        encontrou_uf = True

    if not encontrou_uf:
        raise ValueError("retorno do PAINEL sem linhas de UF")
    return pd.DataFrame(linhas.values(), columns=COLUNAS_CACHE)


def ingerir_painel(consulta: ConsultaPainel, usar_cache: bool = True) -> pd.DataFrame:
    """Retorna casos de RT por UF/faixa de tempo e materializa cache + sidecar."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    csv = CACHE_DIR / f"painel_rt_{consulta.ano}.csv"
    sidecar = CACHE_DIR / f"painel_rt_{consulta.ano}.meta.json"
    if usar_cache and csv.exists():
        return pd.read_csv(csv)

    html = _fetch_tabnet(consulta)
    df = _parsear(html)
    df.to_csv(csv, index=False)
    sidecar.write_text(
        json.dumps(
            {
                "fonte": "PAINEL-Oncologia (DATASUS)",
                "url": TABNET_BASE,
                "url_post": TABNET_POST,
                "ano": consulta.ano,
                "modalidade": consulta.modalidade,
                "linha": consulta.linha,
                "coluna": consulta.coluna,
                "extraido_em": date.today().isoformat(),
                "janela_valida": "2019-2024",
                "observacao": (
                    "Sem informacao de tratamento fica fora do denominador de "
                    "pct_ate_60d; quando ausente no retorno filtrado por "
                    "radioterapia, e materializada como zero."
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return df


def cache_disponivel(anos: Iterable[int] = JANELA_PADRAO) -> bool:
    """Indica se todos os CSVs anuais da janela estao materializados."""
    return all((CACHE_DIR / f"painel_rt_{ano}.csv").exists() for ano in anos)


def anos_cache_faltantes(anos: Iterable[int] = JANELA_PADRAO) -> list[int]:
    """Lista anos esperados ainda sem cache local."""
    return [
        ano
        for ano in anos
        if not (CACHE_DIR / f"painel_rt_{ano}.csv").exists()
    ]


def consolidar_cache(anos: Iterable[int] = JANELA_PADRAO) -> pd.DataFrame:
    """Soma os caches anuais do PAINEL em uma janela unica por UF."""
    frames = []
    for ano in anos:
        caminho = CACHE_DIR / f"painel_rt_{ano}.csv"
        if not caminho.exists():
            raise FileNotFoundError(f"cache do PAINEL ausente: {caminho}")
        frame = pd.read_csv(caminho)
        faltando = [coluna for coluna in COLUNAS_CACHE if coluna not in frame.columns]
        if faltando:
            raise ValueError(f"cache do PAINEL sem colunas {faltando}: {caminho}")
        frames.append(frame[COLUNAS_CACHE])
    consolidado = pd.concat(frames, ignore_index=True)
    return (
        consolidado.groupby("uf", as_index=False)[COLUNAS_CACHE[1:]]
        .sum()
        .sort_values("uf")
        .reset_index(drop=True)
    )


def pct_ate_60d(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula % <=60 dias por UF, excluindo sem informacao do denominador."""
    faltando = [coluna for coluna in COLUNAS_CACHE if coluna not in df.columns]
    if faltando:
        raise ValueError(f"painel sem colunas obrigatorias: {faltando}")
    out = df.copy()
    denom = out["casos_0_30"] + out["casos_31_60"] + out["casos_mais_60"]
    out["pct_ate_60d"] = (
        (out["casos_0_30"] + out["casos_31_60"]) / denom.where(denom > 0)
    )
    return out[["uf", "pct_ate_60d"]]
