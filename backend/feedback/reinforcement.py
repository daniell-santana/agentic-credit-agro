"""
Reinforcement adjustment dos pesos adaptativos (secao 13 do PLANO.md).

O artigo AFIRMA que os pesos sao recalibrados via reinforcement learning
mas nao publica a formula. Portanto esta politica e uma
IMPLEMENTATION CHOICE, deterministica sob a mesma seed, e documentada
como tal (nao e reivindicada como formula do artigo).

Estado: features atuais, PD atual, loss atual, regime macro.
Acao: increase_weight | keep_weight | decrease_weight
Reward: funcao baseada no desempenho/loss observado.
"""
from __future__ import annotations
from typing import Dict


LEARNING_STEP = 0.05


def reward_from_outcome(pd: float, realized_default: int, loss: float) -> float:
    """Reward positivo quando o modelo previu corretamente (PD alto -> default,
    PD baixo -> adimplencia); negativo quando erra, escalado pela loss."""
    correct_direction = (pd >= 0.5 and realized_default == 1) or (pd < 0.5 and realized_default == 0)
    base = 1.0 if correct_direction else -1.0
    return base - loss


def choose_action(reward: float, dead_zone: float = 0.05) -> str:
    if reward > dead_zone:
        return "increase_weight"
    if reward < -dead_zone:
        return "decrease_weight"
    return "keep_weight"


def apply_reinforcement(weights_module, attributions: Dict[str, float], reward: float,
                         step: float = LEARNING_STEP) -> str:
    """Ajusta wi por feature proporcionalmente ao sinal/direcao da attribution
    e ao reward observado. Features com maior |attribution| recebem maior ajuste."""
    action = choose_action(reward)
    if action == "keep_weight":
        return action
    sign = 1.0 if action == "increase_weight" else -1.0
    for feature, attribution in attributions.items():
        magnitude = min(1.0, abs(attribution))
        delta = sign * step * magnitude
        weights_module.adjust(feature, delta)
    return action
