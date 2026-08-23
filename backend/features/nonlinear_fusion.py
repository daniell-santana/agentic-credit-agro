"""
Nonlinear Feature Fusion — Equacao 4 do artigo (ARTICLE-SPECIFIED)

S = sum_i alpha_i * Fi^2
"""
from __future__ import annotations
from typing import Dict, List


def nonlinear_fusion(weighted_features: Dict[str, float], alpha: Dict[str, float]) -> float:
    """S = sum(alpha_i * Fi^2)  (Equacao 4)."""
    return sum(alpha.get(name, 1.0) * (value ** 2) for name, value in weighted_features.items())


def default_alpha(feature_names: List[str], value: float = 1.0) -> Dict[str, float]:
    return {f: value for f in feature_names}
