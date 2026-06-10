"""Gerador e validador de SQL SELECT-only para o agente."""

from __future__ import annotations

import re

from .intent import Intent

TABELA = "indicadores"

_PROIBIDO = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|copy|pragma|"
    r"replace|truncate|grant|revoke|vacuum|merge)\b",
    re.IGNORECASE,
)
_REFERENCIA_TABELA = re.compile(
    r"\b(?:from|join)\s+([a-zA-Z_][\w]*)",
    re.IGNORECASE,
)


class SQLInvalido(ValueError):
    """SQL reprovado pelo validador SELECT-only."""


def validar_select(sql: str) -> str:
    """Permite somente um SELECT sobre a tabela ``indicadores``."""
    limpo = sql.strip().rstrip(";").strip()
    if ";" in limpo:
        raise SQLInvalido("apenas um statement e permitido")
    if "--" in limpo or "/*" in limpo:
        raise SQLInvalido("comentarios nao sao permitidos")
    if not re.match(r"(?is)^\s*select\b", limpo):
        raise SQLInvalido("apenas SELECT e permitido")
    if _PROIBIDO.search(limpo):
        raise SQLInvalido("palavra-chave proibida na query")

    tabelas = _REFERENCIA_TABELA.findall(limpo)
    if not tabelas:
        raise SQLInvalido(f"a query deve consultar a tabela '{TABELA}'")
    if any(tabela.lower() != TABELA for tabela in tabelas):
        raise SQLInvalido(f"so a tabela '{TABELA}' e permitida")
    return limpo


def build_sql(intent: Intent) -> str:
    """Constroi SQL para uma intencao reconhecida."""
    metrica = intent.metrica
    if intent.tipo == "ranking":
        ordem = "DESC" if intent.ordem == "desc" else "ASC"
        sql = (
            f"SELECT uf, regiao, {metrica} FROM {TABELA} "
            f"ORDER BY {metrica} {ordem} LIMIT {int(intent.n)}"
        )
    elif intent.tipo == "valor_uf":
        uf = intent.ufs[0]
        sql = f"SELECT uf, {metrica} FROM {TABELA} WHERE uf = '{uf}'"
    elif intent.tipo == "comparacao":
        lista = ", ".join(f"'{uf}'" for uf in intent.ufs)
        sql = (
            f"SELECT uf, {metrica} FROM {TABELA} "
            f"WHERE uf IN ({lista}) ORDER BY {metrica} DESC"
        )
    elif intent.tipo == "filtro_grade":
        metrica_grade = metrica if (metrica and metrica != "grade") else "lsi"
        sql = (
            f"SELECT uf, regiao, {metrica_grade}, grade FROM {TABELA} "
            f"WHERE grade = {int(intent.grade)} ORDER BY lsi DESC"
        )
    elif intent.tipo == "agregado":
        if intent.regiao:
            sql = (
                f"SELECT SUM({metrica}) AS total FROM {TABELA} "
                f"WHERE regiao = '{intent.regiao}'"
            )
        else:
            sql = f"SELECT SUM({metrica}) AS total FROM {TABELA}"
    else:
        raise SQLInvalido(f"intent nao gera SQL: {intent.tipo}")
    return validar_select(sql)
