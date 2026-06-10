"""Valida o mart operacional versionado em ``data/outputs_2024``.

``scripts/probe.py`` valida o motor em uma base sintetica offline por padrao.
Este runner olha os CSVs reais/versionados e separa checks bloqueantes de
alertas metodologicos esperados, como tensao entre oferta por estabelecimento
e parque LINAC estimado por UF.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from radarrt import schemas  # noqa: E402
from radarrt import validation as v  # noqa: E402
from radarrt.config import CENARIOS  # noqa: E402

ARQUIVOS_ESPERADOS = {
    "base_canonica.csv",
    "indicadores_base.csv",
    "ranking_prioridade.csv",
    "sensibilidade_cenarios.csv",
    "resumo_nacional.csv",
    "auditoria_base.csv",
    "procedencia.csv",
}
ANCHORS = {
    "demanda_reprimida": 66_539,
    "deficit_linacs": 109,
    "lsi_nacional": 126.8,
    "grades_base": [1, 6, 18, 0, 2],
}


@dataclass(frozen=True)
class ProbeOutputs:
    """Resultado estruturado da validacao do mart operacional."""

    checks: list[v.Check]
    alertas: list[v.Check]
    anchors: dict[str, object]

    @property
    def passou(self) -> bool:
        """Indica se todos os checks bloqueantes passaram."""
        return all(check.passou for check in self.checks)


def auditar_outputs(output_dir: str | Path = "data/outputs_2024") -> ProbeOutputs:
    """Audita os CSVs versionados sem baixar dados nem recalcular o mart."""
    pasta = Path(output_dir)
    base = pd.read_csv(pasta / "base_canonica.csv")
    resumo = pd.read_csv(pasta / "resumo_nacional.csv")
    sensibilidade = pd.read_csv(pasta / "sensibilidade_cenarios.csv")
    procedencia = pd.read_csv(pasta / "procedencia.csv")

    resumo_idx = resumo.set_index("metrica")["valor"]
    proc_idx = procedencia.set_index("metrica")["valor"]
    linha_base = sensibilidade.loc[sensibilidade["cenario"] == "base"].iloc[0]
    grades_base = [
        int(linha_base[f"ufs_grade_{grade}"])
        for grade in range(5)
    ]
    anchors = {
        "demanda_reprimida": int(float(resumo_idx["demanda_reprimida"])),
        "deficit_linacs": int(float(resumo_idx["deficit_linacs"])),
        "lsi_nacional": round(float(resumo_idx["lsi_nacional"]), 1),
        "grades_base": grades_base,
        "procedencia": proc_idx.to_dict(),
    }

    checks = [
        _check_arquivos(pasta),
        _check_schema(base),
        _check_anchor("demanda reprimida", anchors["demanda_reprimida"], ANCHORS["demanda_reprimida"]),
        _check_anchor("deficit estrutural de LINACs", anchors["deficit_linacs"], ANCHORS["deficit_linacs"]),
        _check_anchor("LSI nacional", anchors["lsi_nacional"], ANCHORS["lsi_nacional"]),
        _check_anchor("distribuicao de grades", anchors["grades_base"], ANCHORS["grades_base"]),
        _check_anchor("procedencia da oferta", proc_idx["oferta"], "real"),
        _check_anchor(
            "procedencia do parque",
            proc_idx["linacs"],
            "estimado (parque publicado)",
        ),
        v.reproduzir_benchmark_2020(CENARIOS["base"]),
        *v.invariantes(base, CENARIOS["base"]),
    ]
    alertas = [
        check
        for check in v.consistencia_dados(base, meses_oferta=12, params=CENARIOS["base"])
        if not check.passou
    ]
    return ProbeOutputs(checks=checks, alertas=alertas, anchors=anchors)


def _check_arquivos(pasta: Path) -> v.Check:
    existentes = {path.name for path in pasta.glob("*.csv")}
    faltando = sorted(ARQUIVOS_ESPERADOS - existentes)
    return v.Check(
        "Arquivos esperados do mart operacional",
        not faltando,
        "ok" if not faltando else f"faltando: {faltando}",
    )


def _check_schema(base: pd.DataFrame) -> v.Check:
    try:
        schemas.validar_entrada(base)
    except Exception as exc:  # noqa: BLE001 - fronteira de relatorio
        return v.Check("Schema canonico da base", False, str(exc))
    passou = len(base) == 27 and base[schemas.COL_UF].nunique() == 27
    return v.Check(
        "Schema canonico da base",
        passou,
        f"{len(base)} linhas, {base[schemas.COL_UF].nunique()} UFs",
    )


def _check_anchor(nome: str, observado: object, esperado: object) -> v.Check:
    return v.Check(
        f"Anchor: {nome}",
        observado == esperado,
        f"observado={observado} | esperado={esperado}",
    )


def _render(resultado: ProbeOutputs, output_dir: Path) -> str:
    linhas = [
        "=" * 64,
        "PROBE DO MART OPERACIONAL RadarRT",
        "=" * 64,
        f"Diretorio: {output_dir}",
        "",
        "1. CHECKS BLOQUEANTES",
    ]
    linhas.extend(f"   {check}" for check in resultado.checks)

    linhas.append("")
    linhas.append("2. NUMEROS-ANCORA")
    for chave, valor in resultado.anchors.items():
        if chave == "procedencia":
            continue
        linhas.append(f"   {chave}: {valor}")

    linhas.append("")
    linhas.append("3. ALERTAS METODOLOGICOS")
    if resultado.alertas:
        linhas.extend(f"   [ALERTA] {check.nome} - {check.detalhe}" for check in resultado.alertas)
    else:
        linhas.append("   Nenhum alerta metodologico.")

    falhas = [check for check in resultado.checks if not check.passou]
    linhas.append("")
    linhas.append("=" * 64)
    linhas.append(
        f"VEREDITO OPERACIONAL: {len(resultado.checks) - len(falhas)}/"
        f"{len(resultado.checks)} checks bloqueantes OK; "
        f"{len(resultado.alertas)} alerta(s) metodologico(s)."
    )
    if resultado.alertas:
        linhas.append(
            "Interprete rankings por UF como exploratorios ate haver matriz por "
            "residencia e censo real de LINACs por UF."
        )
    linhas.append("=" * 64)
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    """Executa o probe operacional e retorna codigo de saida apropriado."""
    parser = argparse.ArgumentParser(description="Valida data/outputs_2024.")
    parser.add_argument("--output-dir", default="data/outputs_2024")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Trata alertas metodologicos como falha de execucao.",
    )
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    resultado = auditar_outputs(output_dir)
    print(_render(resultado, output_dir))
    if not resultado.passou:
        return 1
    if args.strict and resultado.alertas:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
