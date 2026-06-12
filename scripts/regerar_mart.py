"""Regenera o mart operacional em ``data/outputs_2024`` de forma offline.

Por que existe: ``radarrt.cli`` reconstroi a base via ``construir_base``, que
re-baixa SIA/INCA do DATASUS (precisa de rede). Quando incidencia e oferta ja
estao congeladas em ``base_canonica.csv``, este runner recompoe os CSVs
derivados deterministicamente, sem rede para SIA/INCA.

Reusa exatamente as mesmas funcoes do ``cli`` (mesmo formato de saida) e a
mesma logica de procedencia do ``sources.parque``.

Uso:
    python scripts/regerar_mart.py
    python scripts/regerar_mart.py --output-dir data/outputs_2024 \
        --parque data/parque_linacs_2030.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from radarrt import (  # noqa: E402
    auditar_base,
    avaliar_cenarios,
    cenario_parque,
    plano_nacional,
    preparar_datamart,
    ranking_prioridade,
    resumo_nacional,
    schemas,
    sensibilidade_throughput,
)
from radarrt import (  # noqa: E402
    validation as validation_mod,
)
from radarrt.config import CENARIOS  # noqa: E402
from radarrt.sources import painel as painel_mod  # noqa: E402
from radarrt.sources import parque as parque_mod  # noqa: E402


def _metrics_to_frame(metricas: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(
        {"metrica": list(metricas), "valor": list(metricas.values())}
    )


def regerar(output_dir: Path, csv_parque: Path) -> dict[str, object]:
    """Recomputa o mart a partir da base congelada e do parque informado."""
    base = pd.read_csv(output_dir / "base_canonica.csv")
    parque = pd.read_csv(csv_parque)

    # Substitui apenas a coluna de LINACs (incidencia e oferta permanecem reais).
    novo_linacs = dict(zip(parque["uf"], parque["linacs_sus"], strict=True))
    base[schemas.COL_LINACS] = base[schemas.COL_UF].map(novo_linacs).astype(int)

    # Mesmo contrato de entrada que o pipeline real exige.
    schemas.validar_entrada(base)

    params = CENARIOS["base"]
    calc = preparar_datamart(base, params)
    ranking = ranking_prioridade(calc, n=10)
    sensibilidade = avaliar_cenarios(base)
    sensibilidade_thr = sensibilidade_throughput(base, params=params)
    resumo = resumo_nacional(calc, params)
    auditoria = auditar_base(base)
    plano = pd.DataFrame(
        [
            plano_nacional(calc, params, meta_utilizacao=1.0),
            plano_nacional(calc, params, meta_utilizacao=0.8),
        ]
    )
    cenarios_parque = _cenarios_parque(base)
    validacao_painel, validacao_painel_regional, aviso_painel = _validacao_painel(calc)

    # Procedencia derivada da coluna 'fonte' do parque (igual ao pipeline).
    qualidade = parque_mod.classificar_qualidade(parque)
    linacs_proc = (
        "estimado (parque publicado)"
        if qualidade == "estimado"
        else "real (RT2030)"
    )
    avisos: list[str] = []
    aviso = parque_mod.aviso_qualidade(qualidade)
    if aviso:
        avisos.append(aviso)

    output_dir.mkdir(parents=True, exist_ok=True)
    base.to_csv(output_dir / "base_canonica.csv", index=False)
    calc.to_csv(output_dir / "indicadores_base.csv", index=False)
    ranking.to_csv(output_dir / "ranking_prioridade.csv", index=False)
    sensibilidade.to_csv(output_dir / "sensibilidade_cenarios.csv", index=False)
    sensibilidade_thr.to_csv(
        output_dir / "sensibilidade_throughput.csv",
        index=False,
    )
    plano.to_csv(output_dir / "plano_nacional.csv", index=False)
    cenarios_parque.to_csv(output_dir / "cenarios_parque.csv", index=False)
    if validacao_painel is not None and validacao_painel_regional is not None:
        validacao_painel.to_csv(output_dir / "painel_validacao.csv", index=False)
        validacao_painel_regional.to_csv(
            output_dir / "painel_validacao_regional.csv",
            index=False,
        )
    _metrics_to_frame(resumo).to_csv(output_dir / "resumo_nacional.csv", index=False)
    _metrics_to_frame(auditoria).to_csv(
        output_dir / "auditoria_base.csv", index=False
    )
    _metrics_to_frame(
        {
            "incidencia": "real",
            "oferta": "real",
            "linacs": linacs_proc,
            "avisos": " | ".join(avisos),
        }
    ).to_csv(output_dir / "procedencia.csv", index=False)

    return {
        "parque_nacional": int(base[schemas.COL_LINACS].sum()),
        "demanda_reprimida": int(resumo["demanda_reprimida"]),
        "deficit_linacs": int(resumo["deficit_linacs"]),
        "lsi_nacional": round(float(resumo["lsi_nacional"]), 1),
        "deficit_fisico_medico": int(resumo["deficit_fisico_medico"]),
        "deficit_radio_oncologista": int(resumo["deficit_radio_oncologista"]),
        "deficit_tecnico_rtt": int(resumo["deficit_tecnico_rtt"]),
        "deficit_profissionais_total": int(resumo["deficit_profissionais_total"]),
        "procedencia_linacs": linacs_proc,
        "painel_onco": aviso_painel or "validacao externa gerada",
    }


def _cenarios_parque(base: pd.DataFrame) -> pd.DataFrame:
    """Gera matriz demanda x expansao para auditoria do parque."""
    linhas: list[dict[str, object]] = []
    for cenario_nome in ("base", "superior"):
        params = CENARIOS[cenario_nome]
        for expansao in (0, 40, 121):
            resultado = cenario_parque(base, expansao, params)
            linhas.append(
                {
                    "cenario_demanda": cenario_nome,
                    "expansao": expansao,
                    **resultado,
                }
            )
    return pd.DataFrame(linhas)


def _validacao_painel(
    indicadores: pd.DataFrame,
) -> tuple[pd.DataFrame | None, pd.DataFrame | None, str | None]:
    """Gera validacao externa contra o PAINEL quando o cache existe."""
    anos = painel_mod.JANELA_PADRAO
    faltantes = painel_mod.anos_cache_faltantes(anos)
    if faltantes:
        aviso = (
            "cache PAINEL-Oncologia ausente; pulei painel_validacao "
            f"(anos faltantes: {faltantes})"
        )
        return None, None, aviso

    painel = painel_mod.consolidar_cache(anos)
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
    return validacao, regional, None


def main(argv: list[str] | None = None) -> int:
    """Executa a regeneracao offline do mart."""
    parser = argparse.ArgumentParser(description="Regenera data/outputs_2024 offline.")
    parser.add_argument("--output-dir", default="data/outputs_2024", type=Path)
    parser.add_argument("--parque", default="data/parque_linacs_2030.csv", type=Path)
    args = parser.parse_args(argv)

    resumo = regerar(args.output_dir, args.parque)
    print("Mart regenerado offline:")
    for chave, valor in resumo.items():
        print(f"  {chave}: {valor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
