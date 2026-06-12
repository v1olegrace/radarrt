"""Vocabulario controlado do parser de intencao.

O agente nao usa LLM. Toda compreensao vem destes dicionarios, normalizacao de
texto e regras explicitas em ``intent.py``.
"""

from __future__ import annotations

import unicodedata

from .. import schemas


def normalizar(texto: str) -> str:
    """Converte para minusculas, remove acentos e colapsa espacos."""
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


# Nome completo normalizado -> sigla. "para" fica fora para nao colidir com a
# preposicao; o Para deve ser consultado pela sigla PA ou "estado do para".
NOME_PARA_UF: dict[str, str] = {
    "acre": "AC",
    "amapa": "AP",
    "amazonas": "AM",
    "estado do para": "PA",
    "rondonia": "RO",
    "roraima": "RR",
    "tocantins": "TO",
    "alagoas": "AL",
    "bahia": "BA",
    "ceara": "CE",
    "maranhao": "MA",
    "paraiba": "PB",
    "pernambuco": "PE",
    "piaui": "PI",
    "rio grande do norte": "RN",
    "sergipe": "SE",
    "distrito federal": "DF",
    "goias": "GO",
    "mato grosso": "MT",
    "mato grosso do sul": "MS",
    "espirito santo": "ES",
    "minas gerais": "MG",
    "rio de janeiro": "RJ",
    "sao paulo": "SP",
    "parana": "PR",
    "rio grande do sul": "RS",
    "santa catarina": "SC",
}

NOME_PARA_REGIAO: dict[str, str] = {
    "norte": "Norte",
    "nordeste": "Nordeste",
    "centro oeste": "Centro-Oeste",
    "centro-oeste": "Centro-Oeste",
    "sudeste": "Sudeste",
    "sul": "Sul",
}

# As chaves sao varridas da mais longa para a mais curta para evitar que
# "demanda" capture "demanda reprimida".
SINONIMOS_METRICA: dict[str, str] = {
    "demanda reprimida": schemas.COL_DEMANDA_REPRIMIDA,
    "fila reprimida": schemas.COL_DEMANDA_REPRIMIDA,
    "fila": schemas.COL_DEMANDA_REPRIMIDA,
    "reprimida": schemas.COL_DEMANDA_REPRIMIDA,
    "deficit de linacs": schemas.COL_DEFICIT_LINACS,
    "deficit de aceleradores": schemas.COL_DEFICIT_LINACS,
    "aceleradores faltando": schemas.COL_DEFICIT_LINACS,
    "maquinas faltando": schemas.COL_DEFICIT_LINACS,
    "profissionais a formar": schemas.COL_DEF_PROFISSIONAIS,
    "deficit de profissionais": schemas.COL_DEF_PROFISSIONAIS,
    "formacao especializada": schemas.COL_DEF_PROFISSIONAIS,
    "formacao": schemas.COL_DEF_PROFISSIONAIS,
    "fisicos medicos": schemas.COL_DEF_FISICO,
    "fisico medico": schemas.COL_DEF_FISICO,
    "fisicos": schemas.COL_DEF_FISICO,
    "radio oncologistas": schemas.COL_DEF_ONCO,
    "radio-oncologistas": schemas.COL_DEF_ONCO,
    "radio oncologista": schemas.COL_DEF_ONCO,
    "oncologistas": schemas.COL_DEF_ONCO,
    "tecnicos rtt": schemas.COL_DEF_TECNICO,
    "tecnicos": schemas.COL_DEF_TECNICO,
    "rtt": schemas.COL_DEF_TECNICO,
    "deficit": schemas.COL_DEFICIT_LINACS,
    "indice de escassez": schemas.COL_LSI,
    "lsi": schemas.COL_LSI,
    "indice": schemas.COL_LSI,
    "aceleradores instalados": schemas.COL_LINACS,
    "linacs instalados": schemas.COL_LINACS,
    "parque": schemas.COL_LINACS,
    "linacs": schemas.COL_LINACS,
    "aceleradores": schemas.COL_LINACS,
    "maquinas": schemas.COL_LINACS,
    "demanda de rt": schemas.COL_DEMANDA_RT,
    "demanda": schemas.COL_DEMANDA_RT,
    "necessidade": schemas.COL_DEMANDA_RT,
    "oferta": schemas.COL_OFERTA_APAC,
    "tratados": schemas.COL_OFERTA_APAC,
    "cursos": schemas.COL_OFERTA_APAC,
    "grade": schemas.COL_GRADE,
    "prioridade": schemas.COL_GRADE,
    "incidencia": schemas.COL_INCIDENCIA_SEM_PNM,
    "casos": schemas.COL_INCIDENCIA_SEM_PNM,
    "populacao": schemas.COL_POP,
    "habitantes": schemas.COL_POP,
}

ROTULO_METRICA: dict[str, str] = {
    schemas.COL_DEMANDA_REPRIMIDA: "demanda reprimida",
    schemas.COL_DEFICIT_LINACS: "deficit de aceleradores",
    schemas.COL_DEF_FISICO: "fisicos medicos a formar",
    schemas.COL_DEF_ONCO: "radio-oncologistas a formar",
    schemas.COL_DEF_TECNICO: "tecnicos RTT a formar",
    schemas.COL_DEF_PROFISSIONAIS: "profissionais a formar",
    schemas.COL_LSI: "LSI",
    schemas.COL_LINACS: "aceleradores instalados",
    schemas.COL_DEMANDA_RT: "demanda de RT no SUS",
    schemas.COL_OFERTA_APAC: "pacientes tratados",
    schemas.COL_GRADE: "grade",
    schemas.COL_INCIDENCIA_SEM_PNM: "incidencia excluindo pele nao melanoma",
    schemas.COL_POP: "populacao",
}
