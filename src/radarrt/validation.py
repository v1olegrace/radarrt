"""Validacao cientifica offline do motor RadarRT.

O modulo "palpa" o motor em quatro frentes:

1. validacao externa contra o LSI nacional 2020 publicado;
2. invariantes matematicos do motor;
3. sensibilidade dos cenarios;
4. consistencia fisica da base regional.
5. validacao externa opcional contra o PAINEL-Oncologia.

As funcoes sao puras em relacao ao ambiente: recebem DataFrames/parametros e
devolvem checks, tabelas ou texto. Nao fazem rede nem I/O.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from . import engine, geo, schemas
from .config import CENARIOS, Params
from .sources import parque

# Referencias da literatura usadas como ancoras de validacao externa.
LSI_2020_PUBLICADO = 221.0
CASOS_2020 = 625_370
LINACS_2020 = 252
SEM_ACESSO_ANO_SBRT = 73_000
GAP_LINACS_LITERATURA = (90, 160)


@dataclass(frozen=True)
class Check:
    """Resultado de uma verificacao cientifica/operacional."""

    nome: str
    passou: bool
    detalhe: str

    def __str__(self) -> str:
        """Formata o check para relatorios CLI legiveis."""
        marca = "OK" if self.passou else "FALHA"
        return f"[{marca}] {self.nome} - {self.detalhe}"


def reproduzir_benchmark_2020(params: Params = CENARIOS["base"]) -> Check:
    """Verifica se o motor reproduz LSI nacional 2020 ~= 221."""
    pacientes = CASOS_2020 * params.fracao_efetiva_rt
    lsi = engine.linac_shortage_index(pacientes, LINACS_2020, params)
    passou = abs(lsi - LSI_2020_PUBLICADO) < 3.0
    return Check(
        "Reproducao do LSI 2020 (Viani et al.)",
        passou,
        f"motor={lsi:.1f} vs publicado={LSI_2020_PUBLICADO:.0f}",
    )


def invariantes(
    df_base: pd.DataFrame,
    params: Params = CENARIOS["base"],
) -> list[Check]:
    """Executa propriedades que devem valer para qualquer base valida."""
    calc = engine.calcular_indicadores(df_base, params)
    resumo = engine.resumo_nacional(calc, params)
    checks: list[Check] = []

    checks.append(
        Check(
            "Demanda reprimida nunca negativa",
            bool((calc[schemas.COL_DEMANDA_REPRIMIDA] >= 0).all()),
            f"min={calc[schemas.COL_DEMANDA_REPRIMIDA].min():.0f}",
        )
    )

    soma_regional = float(calc[schemas.COL_DEMANDA_RT].sum())
    checks.append(
        Check(
            "Conservacao: soma regional = demanda nacional",
            math.isclose(soma_regional, resumo["demanda_rt_sus"], rel_tol=1e-9),
            f"regional={soma_regional:.0f} | nacional={resumo['demanda_rt_sus']:.0f}",
        )
    )

    lsi_100 = engine.linac_shortage_index(100_000, 100, params)
    lsi_200 = engine.linac_shortage_index(100_000, 200, params)
    checks.append(
        Check(
            "Monotonicidade: mais LINACs reduz LSI",
            lsi_200 < lsi_100,
            f"100 LINACs={lsi_100:.0f}; 200 LINACs={lsi_200:.0f}",
        )
    )

    demanda_rur_baixo = engine.demanda_rt_sus(
        100_000,
        Params(rur=0.40, sus_share=0.80),
    )
    demanda_rur_alto = engine.demanda_rt_sus(
        100_000,
        Params(rur=0.60, sus_share=0.80),
    )
    checks.append(
        Check(
            "Monotonicidade: maior RUR aumenta demanda",
            demanda_rur_alto > demanda_rur_baixo,
            f"RUR 0.40={demanda_rur_baixo:.0f}; RUR 0.60={demanda_rur_alto:.0f}",
        )
    )

    lsi_sem_linac = engine.linac_shortage_index(1_000, 0, params)
    checks.append(
        Check(
            "Caso-limite: sem LINAC gera LSI infinito e grade 4",
            math.isinf(lsi_sem_linac)
            and engine.grade_prioridade(lsi_sem_linac, 0) == 4,
            "n_linacs=0",
        )
    )

    deficit_regional = float(calc[schemas.COL_DEFICIT_LINACS].sum())
    deficit_agregado = engine.deficit_linacs(
        resumo["demanda_rt_sus"],
        int(resumo["linacs_instalados"]),
        params,
    )
    checks.append(
        Check(
            "Deficit regional >= deficit agregado",
            deficit_regional >= deficit_agregado,
            f"regional={deficit_regional:.0f} | agregado={deficit_agregado}",
        )
    )

    total_equipes = float(calc[schemas.COL_DEF_PROFISSIONAIS].sum())
    soma_categorias = float(
        calc[schemas.COL_DEF_FISICO].sum()
        + calc[schemas.COL_DEF_ONCO].sum()
        + calc[schemas.COL_DEF_TECNICO].sum()
    )
    checks.append(
        Check(
            "Formacao: total nacional = fisico + onco + tecnico",
            math.isclose(total_equipes, soma_categorias, rel_tol=1e-9),
            f"total={total_equipes:.0f} | categorias={soma_categorias:.0f}",
        )
    )

    exemplos_formacao = [
        sum(engine.deficit_profissionais(n).values())
        for n in range(0, 11)
    ]
    formacao_monotonica = all(
        posterior >= anterior
        for anterior, posterior in zip(
            exemplos_formacao[:-1],
            exemplos_formacao[1:],
            strict=True,
        )
    )
    checks.append(
        Check(
            "Formacao: mais deficit de LINACs nao reduz profissionais",
            formacao_monotonica,
            f"totais 0..10 LINACs={exemplos_formacao}",
        )
    )

    sem_deficit = calc[schemas.COL_DEFICIT_LINACS] == 0
    if sem_deficit.any():
        zero_ok = bool(
            (
                calc.loc[
                    sem_deficit,
                    [
                        schemas.COL_DEF_FISICO,
                        schemas.COL_DEF_ONCO,
                        schemas.COL_DEF_TECNICO,
                        schemas.COL_DEF_PROFISSIONAIS,
                    ],
                ]
                == 0
            )
            .all()
            .all()
        )
    else:
        zero_ok = True
    checks.append(
        Check(
            "Formacao: deficit LINAC zero implica profissionais zero",
            zero_ok,
            f"{sem_deficit.sum()} UFs sem deficit de LINAC",
        )
    )

    ordem_categorias = bool(
        (
            calc[schemas.COL_DEF_TECNICO] >= calc[schemas.COL_DEF_ONCO]
        ).all()
        and (
            calc[schemas.COL_DEF_ONCO] >= calc[schemas.COL_DEF_FISICO]
        ).all()
    )
    checks.append(
        Check(
            "Formacao: tecnico >= onco >= fisico em toda UF",
            ordem_categorias,
            "ok" if ordem_categorias else "ordem violada",
        )
    )

    import numpy as np  # noqa: PLC0415 - importacao local para evitar dependencia circular no topo

    util_col = calc[schemas.COL_UTILIZACAO]
    lsi_col = calc[schemas.COL_LSI]
    finitos = np.isfinite(util_col.to_numpy(float)) & np.isfinite(lsi_col.to_numpy(float))
    if finitos.any():
        consistente = bool(
            pd.Series(util_col[finitos].to_numpy(float) * 100).round(6).equals(
                pd.Series(lsi_col[finitos].to_numpy(float)).round(6)
            )
        )
    else:
        consistente = True
    checks.append(
        Check(
            "Consistencia rho x LSI: util*100 == lsi (finitos)",
            consistente,
            "ok" if consistente else "divergencia encontrada",
        )
    )

    espera100 = engine.tempo_espera_meses(1000.0, 9000.0, 20, params)
    espera105 = engine.tempo_espera_meses(1000.0, 9000.0, 25, params)
    checks.append(
        Check(
            "Monotonicidade da espera: mais LINACs nunca aumenta",
            espera105 <= espera100,
            f"20 LINACs={espera100:.2f}m; 25 LINACs={espera105:.2f}m",
        )
    )

    espera_uf = calc[schemas.COL_TEMPO_ESPERA_MESES]
    prazo_uf = calc[schemas.COL_PRAZO_60D]
    rho_uf = calc[schemas.COL_UTILIZACAO]
    divergentes = rho_uf >= 1.0
    divergencia_ok = bool(
        (espera_uf[divergentes].apply(math.isinf)).all()
        and (~prazo_uf[divergentes]).all()
    )
    checks.append(
        Check(
            "Divergencia: rho >= 1 => espera=inf e prazo_60d=False",
            divergencia_ok,
            f"{divergentes.sum()} UFs com rho >= 1",
        )
    )

    sem_linac = calc[schemas.COL_LINACS] == 0
    if sem_linac.any():
        sl_ok = bool(
            calc.loc[sem_linac, schemas.COL_UTILIZACAO].apply(math.isinf).all()
            and calc.loc[sem_linac, schemas.COL_TEMPO_ESPERA_MESES].apply(math.isinf).all()
            and (~calc.loc[sem_linac, schemas.COL_PRAZO_60D]).all()
            and (calc.loc[sem_linac, schemas.COL_GRADE] == engine.GRADE_SEM_LINAC).all()
        )
    else:
        sl_ok = True
    checks.append(
        Check(
            "Sem LINAC: util=inf, espera=inf, prazo=False, grade=4",
            sl_ok,
            f"{sem_linac.sum()} UFs sem LINAC",
        )
    )

    return checks


def sensibilidade(df_base: pd.DataFrame) -> pd.DataFrame:
    """Varre os cenarios e retorna os numeros nacionais principais."""
    linhas: list[dict[str, object]] = []
    for nome, params in CENARIOS.items():
        calc = engine.calcular_indicadores(df_base, params)
        resumo = engine.resumo_nacional(calc, params)
        linhas.append(
            {
                "cenario": nome,
                "rur": params.rur,
                "sus_share": params.sus_share,
                "demanda_rt_sus": round(resumo["demanda_rt_sus"]),
                "deficit_linacs": round(resumo["deficit_linacs"]),
                "lsi_nacional": round(resumo["lsi_nacional"], 1),
            }
        )
    return pd.DataFrame(linhas)


def resumo_regional_painel(
    indicadores: pd.DataFrame,
    painel: pd.DataFrame,
) -> pd.DataFrame:
    """Agrega rho e cumprimento da Lei dos 60 dias por regiao.

    O percentual regional e ponderado pelo denominador observavel do PAINEL:
    casos ate 30 + 31-60 + mais de 60 dias. "Sem informacao" fica fora.
    """
    joined = _juntar_painel(indicadores, painel)
    colunas_contagem = ["casos_0_30", "casos_31_60", "casos_mais_60"]
    if joined[colunas_contagem].isna().all().all():
        return (
            joined.groupby(schemas.COL_REGIAO, as_index=False)
            .agg(
                rho_medio=(schemas.COL_UTILIZACAO, "mean"),
                pct_ate_60d_medio=("pct_ate_60d", "mean"),
            )
            [[schemas.COL_REGIAO, "rho_medio", "pct_ate_60d_medio"]]
        )
    agrupado = joined.groupby(schemas.COL_REGIAO, as_index=False).agg(
        rho_medio=(schemas.COL_UTILIZACAO, "mean"),
        casos_0_30=("casos_0_30", "sum"),
        casos_31_60=("casos_31_60", "sum"),
        casos_mais_60=("casos_mais_60", "sum"),
    )
    denom = (
        agrupado["casos_0_30"]
        + agrupado["casos_31_60"]
        + agrupado["casos_mais_60"]
    )
    agrupado["pct_ate_60d_medio"] = (
        (agrupado["casos_0_30"] + agrupado["casos_31_60"])
        / denom.where(denom > 0)
    )
    return agrupado[[schemas.COL_REGIAO, "rho_medio", "pct_ate_60d_medio"]]


def validar_contra_painel(
    indicadores: pd.DataFrame,
    painel: pd.DataFrame,
) -> list[Check]:
    """Cruza utilizacao rho por UF com % <=60 dias do PAINEL.

    Regional e a afirmacao forte: Spearman entre rho medio regional e
    pct_ate_60d regional deve ser negativo. UF e exploratorio, com caveat de
    UF de tratamento e fluxo interestadual.
    """
    regional = resumo_regional_painel(indicadores, painel)
    spearman_regional = _spearman(
        regional["rho_medio"],
        regional["pct_ate_60d_medio"],
    )
    regional_passou = pd.notna(spearman_regional) and spearman_regional < 0

    uf = _juntar_painel(indicadores, painel)
    spearman_uf = _spearman(uf[schemas.COL_UTILIZACAO], uf["pct_ate_60d"])
    return [
        Check(
            "PAINEL-Oncologia regional: rho x pct <=60d",
            bool(regional_passou),
            (
                f"Spearman={spearman_regional:.3f}; "
                "esperado negativo (mais escassez, menor cumprimento)"
            )
            if pd.notna(spearman_regional)
            else "Spearman indisponivel",
        ),
        Check(
            "PAINEL-Oncologia UF exploratorio: rho x pct <=60d",
            True,
            (
                f"Spearman={spearman_uf:.3f}; detalhe por UF tem caveat de "
                "UF do tratamento e fluxo interestadual"
            )
            if pd.notna(spearman_uf)
            else "Spearman indisponivel; detalhe por UF continua exploratorio",
        ),
    ]


def _juntar_painel(indicadores: pd.DataFrame, painel: pd.DataFrame) -> pd.DataFrame:
    """Prepara o join UF entre indicadores RadarRT e PAINEL."""
    painel_pct = _painel_com_pct(painel)
    colunas_indicadores = [
        schemas.COL_UF,
        schemas.COL_REGIAO,
        schemas.COL_UTILIZACAO,
        schemas.COL_GRADE,
    ]
    faltando = [col for col in colunas_indicadores if col not in indicadores.columns]
    if faltando:
        raise ValueError(f"indicadores sem colunas obrigatorias: {faltando}")
    joined = indicadores[colunas_indicadores].merge(painel_pct, on=schemas.COL_UF, how="inner")
    if joined.empty:
        raise ValueError("validacao PAINEL sem UFs em comum")
    return joined


def _painel_com_pct(painel: pd.DataFrame) -> pd.DataFrame:
    """Garante pct_ate_60d e contagens necessarias para ponderacao regional."""
    colunas_contagem = ["casos_0_30", "casos_31_60", "casos_mais_60"]
    faltando_contagem = [col for col in colunas_contagem if col not in painel.columns]
    if "pct_ate_60d" not in painel.columns and faltando_contagem:
        raise ValueError(
            "painel precisa trazer pct_ate_60d ou contagens de tempo de tratamento"
        )

    out = painel.copy()
    if "pct_ate_60d" not in out.columns:
        denom = out["casos_0_30"] + out["casos_31_60"] + out["casos_mais_60"]
        out["pct_ate_60d"] = (
            (out["casos_0_30"] + out["casos_31_60"]) / denom.where(denom > 0)
        )

    for coluna in colunas_contagem:
        if coluna not in out.columns:
            out[coluna] = pd.NA
    return out[
        [
            schemas.COL_UF,
            "casos_0_30",
            "casos_31_60",
            "casos_mais_60",
            "pct_ate_60d",
        ]
    ]


def _spearman(x: pd.Series, y: pd.Series) -> float:
    """Calcula Spearman sem scipy; infinitos entram no maior rank."""
    pares = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(pares) < 2:
        return math.nan
    rank_x = pares["x"].rank(method="average")
    rank_y = pares["y"].rank(method="average")
    return float(rank_x.corr(rank_y, method="pearson"))


def anualizar(oferta_parcial: float | pd.Series, meses_observados: int) -> float | pd.Series:
    """Projeta uma oferta parcial para 12 meses por regra de tres simples."""
    if not 1 <= meses_observados <= 12:
        raise ValueError("meses_observados deve estar entre 1 e 12")
    return oferta_parcial / meses_observados * 12.0


def consistencia_dados(
    df_base: pd.DataFrame,
    meses_oferta: int = 12,
    params: Params = CENARIOS["base"],
) -> list[Check]:
    """Verifica cobertura e plausibilidade fisica da base regional."""
    df = df_base.copy()
    checks: list[Check] = []

    checks.append(
        Check(
            "Cobertura: 27 UFs sem valores ausentes",
            len(df) == len(geo.UFS) and not df.isna().any().any(),
            f"{len(df)} UFs",
        )
    )

    total_linacs = int(df[schemas.COL_LINACS].sum())
    aviso_benchmark = parque.checar_benchmark(total_linacs)
    checks.append(
        Check(
            "Parque nacional dentro do benchmark RT2030 (409)",
            aviso_benchmark is None,
            aviso_benchmark or f"{total_linacs} LINACs",
        )
    )

    capacidade = df[schemas.COL_LINACS] * params.linac_throughput
    oferta_anual = anualizar(df[schemas.COL_OFERTA_APAC], meses_oferta)
    excede = df.loc[oferta_anual > capacidade * 1.2, schemas.COL_UF].tolist()
    checks.append(
        Check(
            "Oferta anualizada <= capacidade instalada x1.2",
            not excede,
            "ok" if not excede else f"excede em: {excede}",
        )
    )

    demanda = df[schemas.COL_INCIDENCIA_SEM_PNM] * params.fracao_efetiva_rt
    suspeitos = df.loc[
        (demanda > 2_000) & (df[schemas.COL_OFERTA_APAC] < demanda * 0.05),
        schemas.COL_UF,
    ].tolist()
    checks.append(
        Check(
            "Atribuicao: sem UF com demanda alta e oferta quase zero",
            not suspeitos,
            "ok" if not suspeitos else f"investigar atribuicao/residencia: {suspeitos}",
        )
    )
    return checks


def diagnostico_nacional(
    df_base: pd.DataFrame,
    meses_oferta: int,
    params: Params = CENARIOS["base"],
) -> dict[str, float]:
    """Separa demanda anual, oferta observada e oferta anualizada."""
    calc = engine.calcular_indicadores(df_base, params)
    resumo = engine.resumo_nacional(calc, params)
    oferta_anual = float(anualizar(resumo["oferta_realizada"], meses_oferta))
    reprimida_honesta = max(resumo["demanda_rt_sus"] - oferta_anual, 0.0)
    return {
        "demanda_anual": resumo["demanda_rt_sus"],
        "oferta_observada": resumo["oferta_realizada"],
        "meses_oferta": float(meses_oferta),
        "oferta_anualizada": oferta_anual,
        "demanda_reprimida_honesta": reprimida_honesta,
        "linacs": resumo["linacs_instalados"],
        "deficit_linacs": resumo["deficit_linacs"],
        "lsi_nacional": resumo["lsi_nacional"],
    }


def gerar_relatorio(
    df_base: pd.DataFrame,
    meses_oferta: int = 12,
    params: Params = CENARIOS["base"],
) -> str:
    """Monta um laudo textual com todos os checks de validacao."""
    linhas: list[str] = []
    add = linhas.append

    add("=" * 64)
    add("LAUDO DE VALIDACAO DO MOTOR RadarRT")
    add("=" * 64)

    add("\n1. VALIDACAO EXTERNA")
    add("   " + str(reproduzir_benchmark_2020(params)))

    add("\n2. INVARIANTES DO MOTOR")
    for check in invariantes(df_base, params):
        add("   " + str(check))

    add("\n3. SENSIBILIDADE")
    for linha in sensibilidade(df_base).to_string(index=False).splitlines():
        add("   " + linha)

    add("\n4. CONSISTENCIA DO DADO")
    for check in consistencia_dados(df_base, meses_oferta, params):
        add("   " + str(check))

    add("\n5. NUMEROS-ANCORA HONESTOS")
    diag = diagnostico_nacional(df_base, meses_oferta, params)
    add(f"   Demanda anual de RT no SUS .... {diag['demanda_anual']:>10,.0f}")
    add(f"   Oferta observada ({int(diag['meses_oferta'])}m) ...... {diag['oferta_observada']:>10,.0f}")
    add(f"   Oferta anualizada ............. {diag['oferta_anualizada']:>10,.0f}")
    add(f"   Demanda reprimida honesta ..... {diag['demanda_reprimida_honesta']:>10,.0f}")
    add(f"   LINACs instalados ............. {diag['linacs']:>10,.0f}")
    add(f"   Deficit para fila zero ........ {diag['deficit_linacs']:>10,.0f}")
    add(f"   LSI nacional .................. {diag['lsi_nacional']:>10,.1f}")

    todos = (
        [reproduzir_benchmark_2020(params)]
        + invariantes(df_base, params)
        + consistencia_dados(df_base, meses_oferta, params)
    )
    falhas = [check for check in todos if not check.passou]
    add("\n" + "=" * 64)
    add(f"VEREDITO: {len(todos) - len(falhas)}/{len(todos)} verificacoes OK")
    if falhas:
        add("Pendencias:")
        for check in falhas:
            add("   - " + check.nome + ": " + check.detalhe)
    add("=" * 64)
    return "\n".join(linhas)
