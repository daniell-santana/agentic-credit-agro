"""
Dynamic Threshold — Equacao 6 do artigo (ARTICLE-SPECIFIED)

tau_t = tau_{t-1} + eta * (Loss_t - Loss_{t-1})

tau0 e eta NAO sao especificados pelo artigo -> hiperparametros de
implementacao (IMPLEMENTATION CHOICE), documentados em config.py.
"""
from __future__ import annotations


def update_threshold(previous_threshold: float, current_loss: float, previous_loss: float, eta: float,
                      tau_min: float = 0.05, tau_max: float = 0.95) -> float:
    """tau_t = tau_{t-1} + eta*(Loss_t - Loss_{t-1})  (Equacao 6)."""
    tau = previous_threshold + eta * (current_loss - previous_loss)
    return max(tau_min, min(tau_max, tau))
