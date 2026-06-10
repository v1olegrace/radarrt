"""Parser de intencao para perguntas em portugues.

Cobre ranking, valor por UF, comparacao, filtro por grade e agregado
nacional/regional, sem chamar rede nem modelo generativo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .. import geo, schemas
from . import nomes

_PALAVRAS_DESC = ("maior", "maiores", "mais", "top", "piores", "pior", "ranking")
_PALAVRAS_ASC = ("menor", "menores", "menos", "melhores", "melhor")
_PALAVRAS_TOTAL = ("total", "totais", "soma", "somar", "nacional", "brasil", "pais")

# Siglas que colidem com palavras comuns do portugues (ex.: "SE" x "se").
# Elas so contam como UF quando aparecem em caixa alta no texto original.
_SIGLAS_AMBIGUAS = frozenset({"SE"})


@dataclass(frozen=True)
class Intent:
    """Intencao estruturada extraida da pergunta."""

    tipo: str
    metrica: str | None = None
    ufs: list[str] = field(default_factory=list)
    regiao: str | None = None
    grade: int | None = None
    n: int = 5
    ordem: str = "desc"


def _detectar_metrica(texto: str) -> str | None:
    """Procura sinonimos de metrica, priorizando expressoes mais longas."""
    for frase in sorted(nomes.SINONIMOS_METRICA, key=len, reverse=True):
        if re.search(rf"\b{re.escape(frase)}\b", texto):
            return nomes.SINONIMOS_METRICA[frase]
    return None


def _detectar_ufs(pergunta_original: str, texto_norm: str) -> list[str]:
    """Detecta UFs por sigla literal e por nomes normalizados."""
    achadas: list[str] = []

    alvo_upper = pergunta_original.upper()
    for sigla in geo.UFS:
        if not re.search(rf"\b{sigla}\b", alvo_upper):
            continue
        if sigla in _SIGLAS_AMBIGUAS and not re.search(
            rf"\b{sigla}\b",
            pergunta_original,
        ):
            continue
        achadas.append(sigla)

    for nome in sorted(nomes.NOME_PARA_UF, key=len, reverse=True):
        if re.search(rf"\b{re.escape(nome)}\b", texto_norm):
            sigla = nomes.NOME_PARA_UF[nome]
            if sigla not in achadas:
                achadas.append(sigla)
    return achadas


def _detectar_regiao(texto: str) -> str | None:
    """Detecta macrorregiao brasileira a partir do vocabulario controlado."""
    for nome in sorted(nomes.NOME_PARA_REGIAO, key=len, reverse=True):
        if re.search(rf"\b{re.escape(nome)}\b", texto):
            return nomes.NOME_PARA_REGIAO[nome]
    return None


def _detectar_grade(texto: str) -> int | None:
    """Extrai filtros do tipo `grade 0` ate `grade 4`."""
    match = re.search(r"grade\s*([0-4])", texto)
    return int(match.group(1)) if match else None


def _detectar_n(texto: str, padrao: int = 5) -> int:
    """Extrai tamanho de ranking sem confundir o numero da grade."""
    sem_grade = re.sub(r"grade\s*[0-4]", " ", texto)
    match = re.search(r"\b(\d{1,2})\b", sem_grade)
    return int(match.group(1)) if match else padrao


def parse(pergunta: str) -> Intent:
    """Converte pergunta livre em uma intencao conhecida ou desconhecida."""
    texto = nomes.normalizar(pergunta)
    metrica = _detectar_metrica(texto)
    ufs = _detectar_ufs(pergunta, texto)
    regiao = _detectar_regiao(texto)
    grade = _detectar_grade(texto)
    quer_total = any(
        re.search(rf"\b{re.escape(palavra)}\b", texto)
        for palavra in _PALAVRAS_TOTAL
    )
    quer_ranking = any(
        re.search(rf"\b{palavra}\b", texto)
        for palavra in _PALAVRAS_DESC + _PALAVRAS_ASC
    )
    ordem = (
        "asc"
        if any(re.search(rf"\b{palavra}\b", texto) for palavra in _PALAVRAS_ASC)
        else "desc"
    )

    if grade is not None and not ufs:
        return Intent(tipo="filtro_grade", metrica=metrica, grade=grade)

    if len(ufs) >= 2:
        return Intent(
            tipo="comparacao",
            metrica=metrica or schemas.COL_DEMANDA_REPRIMIDA,
            ufs=ufs,
        )

    if len(ufs) == 1:
        return Intent(
            tipo="valor_uf",
            metrica=metrica or schemas.COL_DEMANDA_REPRIMIDA,
            ufs=ufs,
        )

    if quer_total and metrica:
        return Intent(tipo="agregado", metrica=metrica, regiao=regiao)

    if quer_ranking or metrica:
        return Intent(
            tipo="ranking",
            metrica=metrica or schemas.COL_DEMANDA_REPRIMIDA,
            n=_detectar_n(texto),
            ordem=ordem,
        )

    return Intent(tipo="desconhecido")
