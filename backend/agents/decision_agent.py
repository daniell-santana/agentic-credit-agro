"""
Decision Agent (secao 21 do PLANO.md) — Equacao 10, literal.

PD < tau_t -> APPROVE
PD = tau_t -> REVIEW
PD > tau_t -> REJECT
"""
from __future__ import annotations
from typing import Any, Dict

from backend.agents.base_agent import BaseAgent


def decide(pd: float, threshold: float, epsilon: float = 1e-6) -> str:
    """Equacao 10, literal do artigo."""
    if abs(pd - threshold) <= epsilon:
        return "REVIEW"
    if pd < threshold:
        return "APPROVE"
    return "REJECT"


class DecisionAgent(BaseAgent):
    name = "decision_agent"

    def process(self, cycle_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        pd = payload.get("pd", 0.0)
        threshold = payload.get("threshold", 0.5)
        decision = decide(pd, threshold)
        return {"decision": decision, "pd": pd, "threshold": threshold}
