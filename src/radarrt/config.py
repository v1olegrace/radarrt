"""Parametros cientificos e cenarios do motor RadarRT."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True)
class Params:
    """Parametros imutaveis injetados nas formulas do motor."""

    rur: float = 0.50
    sus_share: float = 0.80
    linac_throughput: float = 450.0
    nome: str = "base"

    def __post_init__(self) -> None:
        """Valida parametros logo apos a criacao do dataclass imutavel."""
        self._validar_fracao("rur", self.rur)
        self._validar_fracao("sus_share", self.sus_share)

        if (
            isinstance(self.linac_throughput, bool)
            or not isinstance(self.linac_throughput, Real)
            or not math.isfinite(float(self.linac_throughput))
            or self.linac_throughput <= 0
        ):
            raise ValueError("linac_throughput deve ser um numero finito e positivo")

        if not isinstance(self.nome, str) or not self.nome.strip():
            raise ValueError("nome deve ser uma string nao vazia")

    @staticmethod
    def _validar_fracao(nome: str, valor: float) -> None:
        """Garante que fracoes cientificas estejam no intervalo (0, 1]."""
        if (
            isinstance(valor, bool)
            or not isinstance(valor, Real)
            or not math.isfinite(float(valor))
            or not 0.0 < valor <= 1.0
        ):
            raise ValueError(f"{nome} deve estar em (0, 1]")

    @property
    def fracao_efetiva_rt(self) -> float:
        """Fracao da incidencia que vira demanda de RT no SUS."""
        return self.rur * self.sus_share


CENARIOS: dict[str, Params] = {
    "conservador": Params(rur=0.483, sus_share=0.652, nome="conservador"),
    "base": Params(rur=0.50, sus_share=0.80, nome="base"),
    "superior": Params(rur=0.64, sus_share=0.80, nome="superior"),
}

# Throughput (cursos/maquina/ano) para analise de sensibilidade.
# 350 cobalto/antigo; 400 IAEA; 450 Lancet adotado; 500 Lancet maquina; 550 otimista.
THROUGHPUTS_SENSIBILIDADE: tuple[int, ...] = (350, 400, 450, 500, 550)


@dataclass(frozen=True)
class RazoesEquipe:
    """Profissionais por LINAC (Lancet Global Health 2024; IAEA Pub.1296).

    Derivadas das razoes por paciente/ano divididas pelo throughput de 450:
    radio-oncologista 1:250, fisico-medico 1:450, tecnico (RTT) 1:150.
    """

    fisico_medico: float = 1.0
    radio_oncologista: float = 1.8
    tecnico_rtt: float = 3.0

    def __post_init__(self) -> None:
        """Valida razoes positivas e finitas para dimensionamento de equipe."""
        for nome, valor in (
            ("fisico_medico", self.fisico_medico),
            ("radio_oncologista", self.radio_oncologista),
            ("tecnico_rtt", self.tecnico_rtt),
        ):
            if (
                isinstance(valor, bool)
                or not isinstance(valor, Real)
                or not math.isfinite(float(valor))
                or valor <= 0
            ):
                raise ValueError(f"{nome} deve ser numero finito positivo")


RAZOES_EQUIPE_PADRAO = RazoesEquipe()
