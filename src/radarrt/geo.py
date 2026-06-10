"""Mapeamentos geograficos canonicos usados por todas as camadas."""

from __future__ import annotations

COD_IBGE_PARA_UF: dict[str, str] = {
    "11": "RO",
    "12": "AC",
    "13": "AM",
    "14": "RR",
    "15": "PA",
    "16": "AP",
    "17": "TO",
    "21": "MA",
    "22": "PI",
    "23": "CE",
    "24": "RN",
    "25": "PB",
    "26": "PE",
    "27": "AL",
    "28": "SE",
    "29": "BA",
    "31": "MG",
    "32": "ES",
    "33": "RJ",
    "35": "SP",
    "41": "PR",
    "42": "SC",
    "43": "RS",
    "50": "MS",
    "51": "MT",
    "52": "GO",
    "53": "DF",
}

UF_PARA_REGIAO: dict[str, str] = {
    "AC": "Norte",
    "AP": "Norte",
    "AM": "Norte",
    "PA": "Norte",
    "RO": "Norte",
    "RR": "Norte",
    "TO": "Norte",
    "AL": "Nordeste",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "MA": "Nordeste",
    "PB": "Nordeste",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste",
    "GO": "Centro-Oeste",
    "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",
    "ES": "Sudeste",
    "MG": "Sudeste",
    "RJ": "Sudeste",
    "SP": "Sudeste",
    "PR": "Sul",
    "RS": "Sul",
    "SC": "Sul",
}

UFS: tuple[str, ...] = tuple(UF_PARA_REGIAO)


def normalizar_ufs(ufs: list[str] | tuple[str, ...] | None = None) -> list[str]:
    """Normaliza e valida uma selecao de UFs, preservando a ordem."""
    if ufs is None:
        return list(UFS)

    normalizadas = [str(uf).strip().upper() for uf in ufs]
    if not normalizadas:
        raise ValueError("ufs deve conter ao menos uma UF")
    invalidas = sorted(set(normalizadas) - set(UFS))
    if invalidas:
        raise ValueError(f"UFs invalidas: {invalidas}")
    if len(normalizadas) != len(set(normalizadas)):
        raise ValueError("ufs nao pode conter duplicatas")
    return normalizadas


def uf_de_codigo_municipio(cod_municipio: object) -> str | None:
    """Extrai a UF do prefixo de um codigo IBGE de municipio."""
    return COD_IBGE_PARA_UF.get(str(cod_municipio).strip()[:2])


def regiao_de_uf(uf: str) -> str:
    """Retorna a macrorregiao de uma UF valida."""
    return UF_PARA_REGIAO[uf.strip().upper()]
