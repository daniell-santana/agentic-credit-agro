"""
Risk Scoring Agent (secao 15 do PLANO.md).

Recebe features normalizadas -> aplica pesos adaptativos (Eq. 3) ->
fusao nao-linear (Eq. 4) -> Probability of Default (Eq. 5) -> retorna
risco e threshold atual (Eq. 6, aplicado pelo Feedback/Decision layer).
"""
from __future__ import annotations
from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.features.adaptive_weights import AdaptiveWeights
from backend.features.nonlinear_fusion import nonlinear_fusion, default_alpha
from backend.risk.pd_model import LogisticPDModel


class RiskScoringAgent(BaseAgent):
    name = "risk_scoring_agent"

    def __init__(self, feature_names, pd_model: LogisticPDModel, adaptive_weights: AdaptiveWeights,
                 alpha: Dict[str, float] | None = None, threshold: float = 0.5):
        super().__init__()
        self.feature_names = list(feature_names)
        self.pd_model = pd_model
        self.weights = adaptive_weights
        self.alpha = alpha or default_alpha(self.feature_names)
        self._state = {"threshold": threshold}

    def process(self, cycle_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = payload.get("normalized_features", {})
        weighted = self.weights.apply(normalized)
        fusion_score = nonlinear_fusion(weighted, self.alpha)
        pd = self.pd_model.predict(weighted)
        return {
            "weights": self.weights.state(),
            "weighted_features": weighted,
            "fusion_score": fusion_score,
            "pd": pd,
            "threshold": self._state["threshold"],
        }

    def set_threshold(self, tau: float) -> None:
        self._state["threshold"] = tau
