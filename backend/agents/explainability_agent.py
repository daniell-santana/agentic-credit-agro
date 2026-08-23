"""
Explainability Agent (secao 18 do PLANO.md).

Gerado DURANTE o fluxo de decisao (nao post-hoc), conforme o artigo.
Attribution: Ai = dPD/dFi (Equacao 8, derivada analitica da logistica).
Confidence: C = 1 - Var(PD) (Equacao 9).
"""
from __future__ import annotations
from typing import Any, Dict, List
import statistics
import random

from backend.agents.base_agent import BaseAgent
from backend.risk.pd_model import LogisticPDModel


class ExplainabilityAgent(BaseAgent):
    name = "explainability_agent"

    def __init__(self, pd_model: LogisticPDModel, mc_samples: int = 12, noise_std: float = 0.03, seed: int = 42):
        super().__init__()
        self.pd_model = pd_model
        self.mc_samples = mc_samples
        self.noise_std = noise_std
        self._rng = random.Random(seed)

    def _mc_pd_variance(self, weighted_features: Dict[str, float]) -> float:
        """Estrategia operacional (IMPLEMENTATION CHOICE, secao 20) para obter
        Var(PD): Monte Carlo com perturbacao gaussiana nas features ponderadas,
        alimentando a mesma formula PD (Equacao 5) multiplas vezes."""
        samples = []
        for _ in range(self.mc_samples):
            perturbed = {
                k: v + self._rng.gauss(0, self.noise_std) for k, v in weighted_features.items()
            }
            samples.append(self.pd_model.predict(perturbed))
        if len(samples) < 2:
            return 0.0
        return statistics.pvariance(samples)

    def process(self, cycle_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        weighted = payload.get("weighted_features", {})
        attributions = self.pd_model.attribution(weighted)
        variance = self._mc_pd_variance(weighted)
        confidence = confidence_from_variance(variance)

        direction_list = [
            {"feature": f, "value": weighted.get(f, 0.0), "attribution": a,
             "direction": "increases_risk" if a > 0 else "decreases_risk"}
            for f, a in sorted(attributions.items(), key=lambda kv: abs(kv[1]), reverse=True)
        ]
        return {
            "attributions": attributions,
            "attribution_ranked": direction_list,
            "pd_variance": variance,
            "confidence": confidence,
        }


def confidence_from_variance(variance: float) -> float:
    """C = 1 - Var(PD)  (Equacao 9)."""
    return max(0.0, min(1.0, 1.0 - variance))
