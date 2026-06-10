"""Runner do laudo de validacao do RadarRT.

Sem argumentos, usa a base sintetica offline. Com --ano e fontes opcionais,
constroi a base pelo pipeline real e emite o mesmo laudo.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from radarrt import construir_base, gerar_regioes  # noqa: E402
from radarrt import validation as v  # noqa: E402
from radarrt.config import CENARIOS  # noqa: E402


def main() -> int:
    """Render the validation report for synthetic or ingested data."""
    parser = argparse.ArgumentParser(description="Laudo de validacao do RadarRT")
    parser.add_argument("--ano", type=int, default=None)
    parser.add_argument("--csv-inca", default=None)
    parser.add_argument(
        "--fonte-capacidade",
        default="cnes_novo",
        choices=["cnes_novo", "parque_publicado"],
    )
    parser.add_argument("--csv-parque", default=None)
    parser.add_argument("--meses", type=int, nargs="+", default=None)
    parser.add_argument(
        "--cenario",
        default="base",
        choices=["conservador", "base", "superior"],
    )
    args = parser.parse_args()
    params = CENARIOS[args.cenario]

    if args.ano is None:
        print(">> Sem --ano: usando base SINTETICA offline.\n")
        base_df = gerar_regioes()
        meses_oferta = 12
    else:
        resultado = construir_base(
            ano=args.ano,
            csv_inca=args.csv_inca,
            meses=args.meses,
            fonte_capacidade=args.fonte_capacidade,
            csv_parque=args.csv_parque,
        )
        base_df = resultado.dados
        meses_oferta = len(args.meses) if args.meses else 12
        proc = resultado.procedencia
        print(
            f">> Procedencia: incidencia={proc.incidencia} | "
            f"oferta={proc.oferta} | linacs={proc.linacs} | "
            f"tudo_real={proc.tudo_real}"
        )
        for aviso in proc.avisos:
            print(f"   aviso: {aviso}")
        print()

    print(v.gerar_relatorio(base_df, meses_oferta=meses_oferta, params=params))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
