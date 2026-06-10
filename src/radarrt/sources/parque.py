"""Ingestao do parque instalado de LINACs a partir de censo publicado.

Enquanto o codigo novo do CNES-EQ (TP_EQUIP=12) esta em transicao
(Portaria 3.695/2026, migracao incompleta nos primeiros meses), a capacidade
instalada deve vir de um censo publicado e curado - analogo ao tratamento da
incidencia do INCA. Fonte recomendada: RT2030 (Rosa et al., Lancet Oncology
2023) ou SBRT/DIRAC. O CSV e preenchido manualmente a partir da tabela do paper.

Formato esperado do CSV: colunas ``uf`` e ``linacs_sus`` (uma linha por UF).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .. import geo, schemas

# Total nacional de referencia para checagem de sanidade.
# RT2030 (censo 2019): ~409 maquinas de teleterapia (SUS + privado);
# parque SUS estimado na ordem de ~360. Ajuste conforme a fonte adotada.
BENCHMARK_PARQUE_NACIONAL = 360
TOLERANCIA_BENCHMARK = 0.40  # +-40% antes de emitir aviso
COL_FONTE = "fonte"
TERMOS_ESTIMATIVA = ("proporcional", "estimad")


def carregar_parque(caminho_csv: str | Path) -> pd.DataFrame:
    """Le o CSV do parque publicado e delega a validacao ao normalizador."""
    return normalizar_parque(pd.read_csv(caminho_csv))


def normalizar_parque(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normaliza o parque para ``[uf, linacs_sus]`` com validacao estrita."""
    df = df_raw.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]

    obrigatorias = [schemas.COL_UF, schemas.COL_LINACS]
    faltando = [col for col in obrigatorias if col not in df.columns]
    if faltando:
        raise ValueError(f"CSV do parque sem colunas obrigatorias: {faltando}")

    df[schemas.COL_UF] = df[schemas.COL_UF].astype("string").str.upper().str.strip()
    if df[schemas.COL_UF].isna().any() or (df[schemas.COL_UF] == "").any():
        raise ValueError("CSV do parque contem UF vazia")
    invalidas = sorted(set(df[schemas.COL_UF]) - set(geo.UFS))
    if invalidas:
        raise ValueError(f"UFs invalidas no CSV do parque: {invalidas}")
    duplicadas = sorted(
        df.loc[df[schemas.COL_UF].duplicated(), schemas.COL_UF].unique()
    )
    if duplicadas:
        raise ValueError(f"UFs duplicadas no CSV do parque: {duplicadas}")

    valores = pd.to_numeric(df[schemas.COL_LINACS], errors="coerce")
    if not np.isfinite(valores.to_numpy(dtype=float)).all():
        raise ValueError(
            "CSV do parque contem linacs_sus ausente - preencha o template "
            "com os numeros do RT2030 para todas as UFs"
        )
    if (valores < 0).any():
        raise ValueError("CSV do parque contem linacs_sus negativo")
    if not np.equal(valores, np.floor(valores)).all():
        raise ValueError("CSV do parque contem linacs_sus fracionario")

    df[schemas.COL_LINACS] = valores.astype(int)
    out = df[[schemas.COL_UF, schemas.COL_LINACS]].reset_index(drop=True)
    out.attrs["qualidade"] = classificar_qualidade(df)
    return out


def classificar_qualidade(df_raw: pd.DataFrame) -> str:
    """Classifica o parque como curado ou estimado a partir da coluna fonte."""
    df = df_raw.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]
    if COL_FONTE not in df.columns:
        return "curado"
    fontes = df[COL_FONTE].astype("string").str.lower().fillna("")
    if fontes.map(
        lambda valor: any(termo in valor for termo in TERMOS_ESTIMATIVA)
    ).any():
        return "estimado"
    return "curado"


def aviso_qualidade(qualidade: str) -> str | None:
    """Retorna aviso quando o parque nao deve ser vendido como censo real."""
    if qualidade != "estimado":
        return None
    return (
        "parque LINAC contem valores estimados/distribuidos proporcionalmente; "
        "use para exploracao e sensibilidade, nao como censo real por UF"
    )


def checar_benchmark(
    total_linacs: int,
    benchmark: int = BENCHMARK_PARQUE_NACIONAL,
    tolerancia: float = TOLERANCIA_BENCHMARK,
) -> str | None:
    """Compara o total de LINACs com o benchmark. Retorna aviso ou None.

    Pega automaticamente o caso 'CNES em transicao' (ex.: 27 LINACs vs ~360),
    que produziria LSI e deficit absurdos.
    """
    if benchmark <= 0:
        return None
    desvio = abs(total_linacs - benchmark) / benchmark
    if desvio > tolerancia:
        return (
            f"parque de {total_linacs} LINACs diverge {desvio:.0%} do "
            f"benchmark ~{benchmark} (RT2030) - possivel migracao incompleta "
            f"do CNES ou CSV desatualizado; LSI/deficit podem estar distorcidos"
        )
    return None
