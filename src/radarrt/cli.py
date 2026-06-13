"""Command-line interface for reproducible RadarRT exports."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from . import (
    CENARIOS,
    auditar_base,
    avaliar_cenarios,
    cenario_parque,
    construir_base,
    plano_nacional,
    preparar_datamart,
    ranking_prioridade,
    resumo_nacional,
    schemas,
    sensibilidade_throughput,
    serie_temporal_oferta,
)
from . import validation as validation_mod
from .sources import painel as painel_mod
from .sources import sia_temporal as sia_temporal_mod


def _metrics_to_frame(valores: dict[str, object]) -> pd.DataFrame:
    """Convert key-value metrics into the flat CSV shape used by outputs."""
    return pd.DataFrame(
        [{"metrica": chave, "valor": valor} for chave, valor in valores.items()]
    )


def _cenarios_parque(base: pd.DataFrame) -> pd.DataFrame:
    """Build the fixed expansion-scenario audit matrix."""
    linhas: list[dict[str, object]] = []
    for cenario_nome in ("base", "superior"):
        params = CENARIOS[cenario_nome]
        for expansao in (0, 40, 121):
            linhas.append(
                {
                    "cenario_demanda": cenario_nome,
                    "expansao": expansao,
                    **cenario_parque(base, expansao, params),
                }
            )
    return pd.DataFrame(linhas)


def _validacao_painel(
    indicadores: pd.DataFrame,
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Return PAINEL validation tables when the local cache is available."""
    if painel_mod.anos_cache_faltantes(painel_mod.JANELA_PADRAO):
        return None, None

    painel = painel_mod.consolidar_cache(painel_mod.JANELA_PADRAO)
    pct = painel_mod.pct_ate_60d(painel)
    validacao = (
        indicadores[
            [
                schemas.COL_UF,
                schemas.COL_REGIAO,
                schemas.COL_UTILIZACAO,
                schemas.COL_GRADE,
            ]
        ]
        .merge(pct, on=schemas.COL_UF, how="left")
        .rename(
            columns={
                schemas.COL_UF: "uf",
                schemas.COL_REGIAO: "regiao",
                schemas.COL_UTILIZACAO: "utilizacao",
                schemas.COL_GRADE: "grade",
            }
        )
        .sort_values("uf")
        .reset_index(drop=True)
    )
    regional = (
        validation_mod.resumo_regional_painel(indicadores, painel)
        .rename(columns={schemas.COL_REGIAO: "regiao"})
        .sort_values("regiao")
        .reset_index(drop=True)
    )
    return validacao, regional


def _serie_temporal(base: pd.DataFrame, resumo: dict[str, float]) -> pd.DataFrame:
    """Generate the 2019-2024 national offer-vs-demand series."""
    anos = sia_temporal_mod.ANOS_SERIE_TEMPORAL
    codigos = sia_temporal_mod.CODIGOS_RADIOTERAPIA_EXTERNA
    ausentes = sia_temporal_mod.checar_consistencia_codigos(anos, codigos)
    oferta_anual = sia_temporal_mod.ingerir_oferta_anual(anos, codigos)

    oferta_2024 = base[[schemas.COL_UF, schemas.COL_OFERTA_APAC]].rename(
        columns={schemas.COL_OFERTA_APAC: "oferta_realizada"}
    )
    oferta_2024.insert(0, "ano", 2024)
    oferta_anual = pd.concat(
        [
            oferta_anual.loc[oferta_anual["ano"].astype(int) != 2024],
            oferta_2024,
        ],
        ignore_index=True,
    )
    ausentes[2024] = []

    serie = serie_temporal_oferta(
        oferta_anual,
        demanda_esperada=float(resumo["demanda_rt_sus"]),
        params=CENARIOS["base"],
    )
    serie["codigos_ausentes"] = serie["ano"].map(
        lambda ano: ";".join(ausentes.get(int(ano), []))
    )
    return serie[
        [
            "ano",
            "oferta_realizada",
            "demanda_esperada",
            "gap",
            "pandemia",
            "codigos_ausentes",
        ]
    ]


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser shared by scripts and console entry points."""
    parser = argparse.ArgumentParser(description="Executa indicadores RadarRT.")
    parser.add_argument("--ano", type=int, default=2024)
    parser.add_argument("--csv-inca", default="data/incidencia_inca_2026.csv")
    parser.add_argument("--fonte-capacidade", default="parque_publicado")
    parser.add_argument("--csv-parque", default="data/parque_linacs_2030.csv")
    parser.add_argument("--export-dir", default="data/outputs_2024")
    parser.add_argument(
        "--allow-fallback",
        action="store_true",
        help=(
            "Permite substituir fontes indisponiveis por dados sinteticos. "
            "Por padrao, a exportacao operacional falha para evitar sobrescrever "
            "outputs reais com dados de demonstracao."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run ingestion, indicators, audits and CSV export for one data vintage."""
    args = build_parser().parse_args(argv)

    base = construir_base(
        ano=args.ano,
        csv_inca=args.csv_inca,
        fonte_capacidade=args.fonte_capacidade,
        csv_parque=args.csv_parque,
        permitir_fallback=args.allow_fallback,
    )
    calc = preparar_datamart(base.dados, CENARIOS["base"])
    ranking = ranking_prioridade(calc, n=10)
    sensibilidade = avaliar_cenarios(base.dados)
    sensibilidade_thr = sensibilidade_throughput(base.dados)
    resumo = resumo_nacional(calc, CENARIOS["base"])
    auditoria = auditar_base(base.dados)
    plano = pd.DataFrame(
        [
            plano_nacional(calc, CENARIOS["base"], meta_utilizacao=1.0),
            plano_nacional(calc, CENARIOS["base"], meta_utilizacao=0.8),
        ]
    )
    cenarios_parque = _cenarios_parque(base.dados)
    serie_temporal = _serie_temporal(base.dados, resumo)
    painel_validacao, painel_regional = _validacao_painel(calc)

    export_dir = Path(args.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    base.dados.to_csv(export_dir / "base_canonica.csv", index=False)
    calc.to_csv(export_dir / "indicadores_base.csv", index=False)
    ranking.to_csv(export_dir / "ranking_prioridade.csv", index=False)
    sensibilidade.to_csv(export_dir / "sensibilidade_cenarios.csv", index=False)
    sensibilidade_thr.to_csv(export_dir / "sensibilidade_throughput.csv", index=False)
    plano.to_csv(export_dir / "plano_nacional.csv", index=False)
    cenarios_parque.to_csv(export_dir / "cenarios_parque.csv", index=False)
    serie_temporal.to_csv(export_dir / "serie_temporal.csv", index=False)
    if painel_validacao is not None and painel_regional is not None:
        painel_validacao.to_csv(export_dir / "painel_validacao.csv", index=False)
        painel_regional.to_csv(export_dir / "painel_validacao_regional.csv", index=False)
    _metrics_to_frame(resumo).to_csv(export_dir / "resumo_nacional.csv", index=False)
    _metrics_to_frame(auditoria).to_csv(export_dir / "auditoria_base.csv", index=False)
    _metrics_to_frame(
        {
            "incidencia": base.procedencia.incidencia,
            "oferta": base.procedencia.oferta,
            "linacs": base.procedencia.linacs,
            "avisos": " | ".join(base.procedencia.avisos),
        }
    ).to_csv(export_dir / "procedencia.csv", index=False)

    print("=== PROCEDENCIA ===")
    print(f"  incidencia : {base.procedencia.incidencia}")
    print(f"  oferta     : {base.procedencia.oferta}")
    print(f"  linacs     : {base.procedencia.linacs}")
    for aviso in base.procedencia.avisos:
        print(f"  aviso: {aviso}")

    print("\n=== AUDITORIA DA BASE ===")
    for chave, valor in auditoria.items():
        print(f"  {chave}: {valor}")

    print("\n=== RESUMO NACIONAL - CENARIO BASE ===")
    for chave, valor in resumo.items():
        print(f"  {chave}: {valor}")

    print("\n=== SENSIBILIDADE ===")
    print(sensibilidade.to_string(index=False))

    print("\n=== SENSIBILIDADE THROUGHPUT ===")
    print(sensibilidade_thr.to_string(index=False))

    print("\n=== TOP 10 PRIORIDADE ===")
    print(ranking.to_string(index=False))

    print(f"\nArquivos exportados em: {export_dir}")
    return 0
