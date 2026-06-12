"""Valida o mart operacional versionado em ``data/outputs_2024``.

``scripts/probe.py`` valida o motor em uma base sintetica offline por padrao.
Este runner olha os CSVs reais/versionados e separa checks bloqueantes de
alertas metodologicos esperados, como tensao entre oferta por estabelecimento
e parque LINAC real por UF (censo RT2030).
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
    "sensibilidade_throughput.csv",
    "resumo_nacional.csv",
    "auditoria_base.csv",
    "procedencia.csv",
    "plano_nacional.csv",
    "cenarios_parque.csv",
}
ANCHORS = {
    "demanda_reprimida": 66_539,
    "deficit_linacs": 86,
    "lsi_nacional": 112.5,
    "grades_base": [8, 5, 11, 0, 3],
    "utilizacao_nacional": 1.125,
    "ufs_fila_divergente": 19,
    "ufs_drenaveis": 8,
    "tempo_espera_mediano_meses": 6.6,
    "deficit_fisico_medico": 86,
    "deficit_radio_oncologista": 162,
    "deficit_tecnico_rtt": 258,
    "deficit_profissionais_total": 506,
    "plano_meta_1_linacs": 86,
    "plano_meta_1_profissionais": 506,
    "plano_meta_1_investimento": 860_000_000,
    "plano_meta_08_linacs": 183,
    "plano_meta_08_profissionais": 1_070,
    "plano_meta_08_investimento": 1_830_000_000,
    "parque_base_exp_0_deficit": 86,
    "parque_base_exp_40_deficit": 56,
    "parque_base_exp_121_deficit": 0,
    "parque_superior_exp_0_deficit": 196,
    "parque_superior_exp_40_deficit": 167,
    "parque_superior_exp_121_deficit": 86,
    "throughput_deficits": [201, 126, 86, 59, 44],
    "throughput_ufs_fila": [24, 22, 19, 18, 17],
    "throughput_lsi": [144.7, 126.6, 112.5, 101.3, 92.1],
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
    plano = pd.read_csv(pasta / "plano_nacional.csv")
    cenarios_parque = pd.read_csv(pasta / "cenarios_parque.csv")
    sensibilidade_thr = pd.read_csv(pasta / "sensibilidade_throughput.csv")
    painel_validacao = _ler_csv_opcional(pasta / "painel_validacao.csv")
    painel_regional = _ler_csv_opcional(pasta / "painel_validacao_regional.csv")

    resumo_idx = resumo.set_index("metrica")["valor"]
    proc_idx = procedencia.set_index("metrica")["valor"]
    linha_base = sensibilidade.loc[sensibilidade["cenario"] == "base"].iloc[0]
    plano_meta_1 = _linha_plano(plano, 1.0)
    plano_meta_08 = _linha_plano(plano, 0.8)
    parque_base_0 = _linha_cenario_parque(cenarios_parque, "base", 0)
    parque_base_40 = _linha_cenario_parque(cenarios_parque, "base", 40)
    parque_base_121 = _linha_cenario_parque(cenarios_parque, "base", 121)
    parque_sup_0 = _linha_cenario_parque(cenarios_parque, "superior", 0)
    parque_sup_40 = _linha_cenario_parque(cenarios_parque, "superior", 40)
    parque_sup_121 = _linha_cenario_parque(cenarios_parque, "superior", 121)
    sensibilidade_thr = sensibilidade_thr.sort_values("throughput").reset_index(drop=True)
    grades_base = [
        int(linha_base[f"ufs_grade_{grade}"])
        for grade in range(5)
    ]
    anchors = {
        "demanda_reprimida": int(float(resumo_idx["demanda_reprimida"])),
        "deficit_linacs": int(float(resumo_idx["deficit_linacs"])),
        "lsi_nacional": round(float(resumo_idx["lsi_nacional"]), 1),
        "grades_base": grades_base,
        "utilizacao_nacional": round(float(resumo_idx["utilizacao_nacional"]), 3),
        "ufs_fila_divergente": int(float(resumo_idx["ufs_fila_divergente"])),
        "ufs_drenaveis": int(float(resumo_idx["ufs_drenaveis"])),
        "tempo_espera_mediano_meses": round(float(resumo_idx["tempo_espera_mediano_meses"]), 1),
        "deficit_fisico_medico": int(float(resumo_idx["deficit_fisico_medico"])),
        "deficit_radio_oncologista": int(float(resumo_idx["deficit_radio_oncologista"])),
        "deficit_tecnico_rtt": int(float(resumo_idx["deficit_tecnico_rtt"])),
        "deficit_profissionais_total": int(float(resumo_idx["deficit_profissionais_total"])),
        "plano_meta_1_linacs": int(float(plano_meta_1["linacs_a_instalar"])),
        "plano_meta_1_profissionais": int(float(plano_meta_1["profissionais_total"])),
        "plano_meta_1_investimento": int(float(plano_meta_1["investimento_reais"])),
        "plano_meta_08_linacs": int(float(plano_meta_08["linacs_a_instalar"])),
        "plano_meta_08_profissionais": int(float(plano_meta_08["profissionais_total"])),
        "plano_meta_08_investimento": int(float(plano_meta_08["investimento_reais"])),
        "parque_base_exp_0_deficit": int(float(parque_base_0["deficit_residual"])),
        "parque_base_exp_40_deficit": int(float(parque_base_40["deficit_residual"])),
        "parque_base_exp_121_deficit": int(float(parque_base_121["deficit_residual"])),
        "parque_superior_exp_0_deficit": int(float(parque_sup_0["deficit_residual"])),
        "parque_superior_exp_40_deficit": int(float(parque_sup_40["deficit_residual"])),
        "parque_superior_exp_121_deficit": int(float(parque_sup_121["deficit_residual"])),
        "throughput_deficits": [
            int(valor) for valor in sensibilidade_thr["deficit_linacs"].tolist()
        ],
        "throughput_ufs_fila": [
            int(valor) for valor in sensibilidade_thr["ufs_fila_divergente"].tolist()
        ],
        "throughput_lsi": [
            round(float(valor), 1) for valor in sensibilidade_thr["lsi_nacional"].tolist()
        ],
        "procedencia": proc_idx.to_dict(),
    }
    if painel_regional is not None:
        anchors["painel_spearman_regional"] = round(
            _spearman_series(
                painel_regional["rho_medio"],
                painel_regional["pct_ate_60d_medio"],
            ),
            3,
        )

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
            "real (RT2030)",
        ),
        _check_anchor_approx("utilizacao nacional", anchors["utilizacao_nacional"], ANCHORS["utilizacao_nacional"], tol=0.005),
        _check_anchor("UFs fila divergente", anchors["ufs_fila_divergente"], ANCHORS["ufs_fila_divergente"]),
        _check_anchor("UFs drenaveis", anchors["ufs_drenaveis"], ANCHORS["ufs_drenaveis"]),
        _check_anchor_approx("tempo espera mediano (meses)", anchors["tempo_espera_mediano_meses"], ANCHORS["tempo_espera_mediano_meses"], tol=0.2),
        _check_anchor(
            "deficit fisico-medico",
            anchors["deficit_fisico_medico"],
            ANCHORS["deficit_fisico_medico"],
        ),
        _check_anchor(
            "deficit radio-oncologista",
            anchors["deficit_radio_oncologista"],
            ANCHORS["deficit_radio_oncologista"],
        ),
        _check_anchor(
            "deficit tecnico RTT",
            anchors["deficit_tecnico_rtt"],
            ANCHORS["deficit_tecnico_rtt"],
        ),
        _check_anchor(
            "deficit profissionais total",
            anchors["deficit_profissionais_total"],
            ANCHORS["deficit_profissionais_total"],
        ),
        _check_anchor(
            "plano meta 1.0 LINACs",
            anchors["plano_meta_1_linacs"],
            ANCHORS["plano_meta_1_linacs"],
        ),
        _check_anchor(
            "plano meta 1.0 profissionais",
            anchors["plano_meta_1_profissionais"],
            ANCHORS["plano_meta_1_profissionais"],
        ),
        _check_anchor(
            "plano meta 1.0 investimento",
            anchors["plano_meta_1_investimento"],
            ANCHORS["plano_meta_1_investimento"],
        ),
        _check_anchor(
            "plano meta 0.8 LINACs",
            anchors["plano_meta_08_linacs"],
            ANCHORS["plano_meta_08_linacs"],
        ),
        _check_anchor(
            "plano meta 0.8 profissionais",
            anchors["plano_meta_08_profissionais"],
            ANCHORS["plano_meta_08_profissionais"],
        ),
        _check_anchor(
            "plano meta 0.8 investimento",
            anchors["plano_meta_08_investimento"],
            ANCHORS["plano_meta_08_investimento"],
        ),
        _check_anchor(
            "parque base +0 deficit residual",
            anchors["parque_base_exp_0_deficit"],
            ANCHORS["parque_base_exp_0_deficit"],
        ),
        _check_anchor(
            "parque base +40 deficit residual",
            anchors["parque_base_exp_40_deficit"],
            ANCHORS["parque_base_exp_40_deficit"],
        ),
        _check_anchor(
            "parque base +121 deficit residual",
            anchors["parque_base_exp_121_deficit"],
            ANCHORS["parque_base_exp_121_deficit"],
        ),
        _check_anchor(
            "parque superior +0 deficit residual",
            anchors["parque_superior_exp_0_deficit"],
            ANCHORS["parque_superior_exp_0_deficit"],
        ),
        _check_anchor(
            "parque superior +40 deficit residual",
            anchors["parque_superior_exp_40_deficit"],
            ANCHORS["parque_superior_exp_40_deficit"],
        ),
        _check_anchor(
            "parque superior +121 deficit residual",
            anchors["parque_superior_exp_121_deficit"],
            ANCHORS["parque_superior_exp_121_deficit"],
        ),
        _check_throughput_schema(sensibilidade_thr),
        _check_anchor(
            "sensibilidade throughput: deficit LINACs",
            anchors["throughput_deficits"],
            ANCHORS["throughput_deficits"],
        ),
        _check_anchor(
            "sensibilidade throughput: UFs rho >= 1",
            anchors["throughput_ufs_fila"],
            ANCHORS["throughput_ufs_fila"],
        ),
        _check_anchor(
            "sensibilidade throughput: LSI nacional",
            anchors["throughput_lsi"],
            ANCHORS["throughput_lsi"],
        ),
        *_checks_painel_opcional(
            painel_validacao,
            painel_regional,
            anchors.get("painel_spearman_regional"),
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


def _ler_csv_opcional(caminho: Path) -> pd.DataFrame | None:
    if not caminho.exists():
        return None
    return pd.read_csv(caminho)


def _checks_painel_opcional(
    painel_validacao: pd.DataFrame | None,
    painel_regional: pd.DataFrame | None,
    spearman_regional: object,
) -> list[v.Check]:
    if painel_validacao is None and painel_regional is None:
        return []
    checks: list[v.Check] = []
    if painel_validacao is None or painel_regional is None:
        return [
            v.Check(
                "PAINEL-Oncologia: arquivos opcionais consistentes",
                False,
                "painel_validacao.csv e painel_validacao_regional.csv devem existir juntos",
            )
        ]

    colunas_uf = {"uf", "regiao", "utilizacao", "grade", "pct_ate_60d"}
    colunas_regiao = {"regiao", "rho_medio", "pct_ate_60d_medio"}
    schema_ok = (
        colunas_uf <= set(painel_validacao.columns)
        and colunas_regiao <= set(painel_regional.columns)
        and len(painel_validacao) == 27
    )
    checks.append(
        v.Check(
            "PAINEL-Oncologia: arquivos opcionais consistentes",
            schema_ok,
            f"UFs={len(painel_validacao)}; regioes={len(painel_regional)}",
        )
    )

    passou = pd.notna(spearman_regional) and float(spearman_regional) < 0
    checks.append(
        v.Check(
            "PAINEL-Oncologia: correlacao regional externa",
            bool(passou),
            f"Spearman={spearman_regional}; esperado negativo",
        )
    )
    return checks


def _check_throughput_schema(tabela: pd.DataFrame) -> v.Check:
    colunas = [
        "throughput",
        "deficit_linacs",
        "ufs_fila_divergente",
        "lsi_nacional",
    ]
    passou = list(tabela.columns) == colunas and tabela["throughput"].tolist() == [
        350,
        400,
        450,
        500,
        550,
    ]
    return v.Check(
        "Sensibilidade throughput: schema e faixa",
        passou,
        f"throughputs={tabela['throughput'].tolist()}",
    )


def _spearman_series(x: pd.Series, y: pd.Series) -> float:
    pares = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(pares) < 2:
        return float("nan")
    return float(
        pares["x"].rank(method="average").corr(
            pares["y"].rank(method="average"),
            method="pearson",
        )
    )


def _linha_plano(plano: pd.DataFrame, meta: float) -> pd.Series:
    """Seleciona a linha de plano nacional por meta de utilizacao."""
    linhas = plano.loc[(plano["meta_utilizacao"].astype(float) - meta).abs() < 1e-9]
    if linhas.empty:
        raise ValueError(f"plano_nacional.csv sem meta_utilizacao={meta}")
    return linhas.iloc[0]


def _linha_cenario_parque(
    cenarios: pd.DataFrame,
    cenario_demanda: str,
    expansao: int,
) -> pd.Series:
    """Seleciona a linha da auditoria de parque por cenario e expansao."""
    linhas = cenarios.loc[
        (cenarios["cenario_demanda"] == cenario_demanda)
        & (cenarios["expansao"].astype(int) == expansao)
    ]
    if linhas.empty:
        raise ValueError(
            "cenarios_parque.csv sem "
            f"cenario_demanda={cenario_demanda!r}, expansao={expansao}"
        )
    return linhas.iloc[0]


def _check_anchor(nome: str, observado: object, esperado: object) -> v.Check:
    return v.Check(
        f"Anchor: {nome}",
        observado == esperado,
        f"observado={observado} | esperado={esperado}",
    )


def _check_anchor_approx(nome: str, observado: float, esperado: float, tol: float) -> v.Check:
    passou = abs(observado - esperado) <= tol
    return v.Check(
        f"Anchor: {nome}",
        passou,
        f"observado={observado} | esperado={esperado} (tol+/-{tol})",
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
            "residencia do paciente."
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
