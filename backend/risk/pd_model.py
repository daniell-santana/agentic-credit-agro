"""
Probability of Default — Equacao 5 do artigo (ARTICLE-SPECIFIED)

PD = 1 / (1 + e^-(sigma0 + beta.x))

O nucleo da replica estrita usa regressao logistica (nao LightGBM),
conforme secao 16 do PLANO.md.
"""
from __future__ import annotations
from typing import Dict, List
import math
import random


class LogisticPDModel:
    """Regressao logistica simples: PD = sigmoid(sigma0 + sum(beta_i * x_i))."""

    def __init__(self, feature_names: List[str], sigma0: float = 0.0, beta: Dict[str, float] | None = None):
        self.feature_names = list(feature_names)
        self.sigma0 = sigma0
        self.beta: Dict[str, float] = dict(beta or {f: 0.0 for f in feature_names})

    def score(self, x: float) -> float:
        """PD = 1 / (1 + e^-x)  (parte da Equacao 5)."""
        x = max(-35.0, min(35.0, x))
        return 1.0 / (1.0 + math.exp(-x))

    def linear_term(self, fused_or_features) -> float:
        if isinstance(fused_or_features, dict):
            return self.sigma0 + sum(self.beta.get(k, 0.0) * v for k, v in fused_or_features.items())
        return self.sigma0 + self.beta.get("S", 1.0) * float(fused_or_features)

    def predict(self, features: Dict[str, float]) -> float:
        z = self.linear_term(features)
        return self.score(z)

    def predict_from_fusion(self, s_value: float) -> float:
        """Aplica a formula PD = sigmoid(sigma0 + beta*S) usando o score de fusao S (Eq. 4 -> Eq. 5)."""
        z = self.sigma0 + self.beta.get("S", 1.0) * s_value
        return self.score(z)

    def fit_simple(self, rows: List[Dict[str, float]], targets: List[int], lr: float = 0.05, epochs: int = 200,
                    seed: int = 42) -> None:
        """Gradient descent minimal e determinístico (IMPLEMENTATION CHOICE) para calibrar sigma0/beta
        a partir do dataset sintetico, mantendo a formula (Eq. 5) literal do artigo."""
        rng = random.Random(seed)
        n = len(rows)
        if n == 0:
            return
        for f in self.feature_names:
            self.beta.setdefault(f, rng.uniform(-0.05, 0.05))
        for _ in range(epochs):
            grad_sigma0 = 0.0
            grad_beta = {f: 0.0 for f in self.feature_names}
            for row, y in zip(rows, targets):
                z = self.sigma0 + sum(self.beta[f] * row.get(f, 0.0) for f in self.feature_names)
                p = self.score(z)
                err = p - y
                grad_sigma0 += err
                for f in self.feature_names:
                    grad_beta[f] += err * row.get(f, 0.0)
            self.sigma0 -= lr * grad_sigma0 / n
            for f in self.feature_names:
                self.beta[f] -= lr * grad_beta[f] / n

    def attribution(self, features: Dict[str, float]) -> Dict[str, float]:
        """Ai = dPD/dFi  (Equacao 8) -- derivada analitica da logistica.
        dPD/dFi = PD*(1-PD)*beta_i
        """
        pd = self.predict(features)
        deriv = pd * (1 - pd)
        return {f: deriv * self.beta.get(f, 0.0) for f in features}

    def state(self) -> Dict:
        return {"sigma0": self.sigma0, "beta": dict(self.beta), "feature_names": list(self.feature_names)}

    def load_state(self, state: Dict) -> None:
        self.sigma0 = state.get("sigma0", self.sigma0)
        self.beta.update(state.get("beta", {}))
