"""
Adaptive Feature Weights — Equacao 3 do artigo (ARTICLE-SPECIFIED)

Fi' = wi . Fi

wi e recalibrado por ciclos de reinforcement learning (secao 13 do PLANO,
IMPLEMENTATION CHOICE para a politica de RL em si; a equacao 3 e literal).
"""
from __future__ import annotations
from typing import Dict, List


class AdaptiveWeights:
    def __init__(self, feature_names: List[str], initial_weight: float = 1.0):
        self.weights: Dict[str, float] = {f: initial_weight for f in feature_names}

    def apply(self, normalized_features: Dict[str, float]) -> Dict[str, float]:
        """Fi' = wi . Fi"""
        return {
            name: weighted_feature(value, self.weights.get(name, 1.0))
            for name, value in normalized_features.items()
        }

    def adjust(self, feature_name: str, delta: float, w_min: float = 0.05, w_max: float = 5.0) -> None:
        w = self.weights.get(feature_name, 1.0) + delta
        self.weights[feature_name] = max(w_min, min(w_max, w))

    def state(self) -> Dict[str, float]:
        return dict(self.weights)

    def load_state(self, state: Dict[str, float]) -> None:
        self.weights.update(state)


def weighted_feature(f_i: float, w_i: float) -> float:
    """Fi' = wi . Fi  (Equacao 3)."""
    return w_i * f_i
