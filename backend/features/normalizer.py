"""
Normalization — Equacao 1 do artigo (ARTICLE-SPECIFIED)

Xnorm = (X - mu) / sigma
"""
from __future__ import annotations
from typing import Dict, List
import math


class Normalizer:
    """Mantem mu/sigma por feature e aplica a normalizacao z-score do artigo."""

    def __init__(self, mean: Dict[str, float] | None = None, std: Dict[str, float] | None = None):
        self.mean: Dict[str, float] = dict(mean or {})
        self.std: Dict[str, float] = dict(std or {})

    def fit(self, rows: List[Dict[str, float]], feature_names: List[str]) -> None:
        n = len(rows)
        if n == 0:
            return
        for f in feature_names:
            values = [r[f] for r in rows]
            mu = sum(values) / n
            var = sum((v - mu) ** 2 for v in values) / n
            sigma = math.sqrt(var) if var > 1e-12 else 1.0
            self.mean[f] = mu
            self.std[f] = sigma

    def transform(self, features: Dict[str, float]) -> Dict[str, float]:
        out = {}
        for name, value in features.items():
            mu = self.mean.get(name, 0.0)
            sigma = self.std.get(name, 1.0) or 1.0
            out[name] = normalize_features(value, mu, sigma)
        return out

    def state(self) -> Dict[str, Dict[str, float]]:
        return {"mean": self.mean, "std": self.std}

    def load_state(self, state: Dict[str, Dict[str, float]]) -> None:
        self.mean = dict(state.get("mean", {}))
        self.std = dict(state.get("std", {}))


def normalize_features(x: float, mean: float, std: float) -> float:
    """Xnorm = (X - mu) / sigma  (Equacao 1)."""
    sigma = std if std and abs(std) > 1e-12 else 1.0
    return (x - mean) / sigma
