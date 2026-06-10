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
    construir_base,
    preparar_datamart,
    ranking_prioridade,
    resumo_nacional,
)


def _metrics_to_frame(valores: dict[str, object]) -> pd.DataFrame:
    """Convert key-value metrics into the flat CSV shape used by outputs."""
    return pd.DataFrame(
        [{"metrica": chave, "valor": valor} for chave, valor in valores.items()]
    )


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
    resumo = resumo_nacional(calc, CENARIOS["base"])
    auditoria = auditar_base(base.dados)

    export_dir = Path(args.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    base.dados.to_csv(export_dir / "base_canonica.csv", index=False)
    calc.to_csv(export_dir / "indicadores_base.csv", index=False)
    ranking.to_csv(export_dir / "ranking_prioridade.csv", index=False)
    sensibilidade.to_csv(export_dir / "sensibilidade_cenarios.csv", index=False)
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

    print("\n=== TOP 10 PRIORIDADE ===")
    print(ranking.to_string(index=False))

    print(f"\nArquivos exportados em: {export_dir}")
    return 0
