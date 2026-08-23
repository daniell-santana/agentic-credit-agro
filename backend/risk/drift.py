"""
Model Drift Detection — Equacao 7 do artigo (ARTICLE-SPECIFIED)

D = |Mt - Mt-1|
Se D > gamma -> Feedback Learning Agent inicia reinforcement adjustment.

A metrica M (accuracy neste projeto) e escolha operacional documentada
(secao 26 do PLANO.md): IMPLEMENTATION CHOICE.
"""
from __future__ import annotations


def compute_drift(metric_t: float, metric_t_minus_1: float) -> float:
    """D = |Mt - Mt-1|  (Equacao 7)."""
    return abs(metric_t - metric_t_minus_1)


def drift_triggered(drift_value: float, gamma: float) -> bool:
    return drift_value > gamma
