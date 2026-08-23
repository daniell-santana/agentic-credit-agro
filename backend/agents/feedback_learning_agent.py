"""
Feedback Learning Agent (secao 24 do PLANO.md).

1. recebe resultado do credito
2. calcula loss
3. calcula metrica atual (accuracy - IMPLEMENTATION CHOICE)
4. compara com metrica anterior
5. calcula drift D = |Mt - Mt-1| (Equacao 7)
6. verifica D > gamma
7. inicia reinforcement adjustment quando necessario
8. persiste novo estado (threshold via Equacao 6)
9. alimenta o proximo ciclo
"""
from __future__ import annotations
from typing import Any, Dict, List

from backend.agents.base_agent import BaseAgent
from backend.risk.drift import compute_drift, drift_triggered
from backend.risk.threshold import update_threshold
from backend.risk.metrics import accuracy
from backend.feedback.reinforcement import reward_from_outcome, apply_reinforcement
from backend.feedback.outcome_store import OutcomeStore


class FeedbackLearningAgent(BaseAgent):
    name = "feedback_learning_agent"

    def __init__(self, adaptive_weights, outcome_store: OutcomeStore, eta: float = 0.08, gamma: float = 0.03):
        super().__init__()
        self.weights = adaptive_weights
        self.store = outcome_store
        self._state = {
            "previous_loss": 0.0,
            "previous_metric": 0.5,
            "iteration": 0,
            "eta": eta,
            "gamma": gamma,
            "y_true_window": [],
            "y_pred_window": [],
        }

    def process(self, cycle_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        pd = payload.get("pd", 0.0)
        threshold = payload.get("threshold", 0.5)
        decision = payload.get("decision", "REVIEW")
        realized_default = payload.get("realized_default")
        loss_amount = payload.get("loss_amount", 0.0)
        attributions = payload.get("attributions", {})

        if realized_default is None:
            return {"feedback_applied": False, "reason": "outcome_not_yet_observed"}

        loss = float(loss_amount)
        predicted_default = 1 if decision == "REJECT" else 0

        window_true: List[int] = self._state["y_true_window"]
        window_pred: List[int] = self._state["y_pred_window"]
        window_true.append(int(realized_default))
        window_pred.append(predicted_default)
        window_true[:] = window_true[-200:]
        window_pred[:] = window_pred[-200:]

        current_metric = accuracy(window_true, window_pred)
        previous_metric = self._state["previous_metric"]
        previous_loss = self._state["previous_loss"]

        drift = compute_drift(current_metric, previous_metric)
        gamma = self._state["gamma"]
        triggered = drift_triggered(drift, gamma)

        action_taken = "keep_weight"
        if triggered:
            reward = reward_from_outcome(pd, int(realized_default), loss)
            action_taken = apply_reinforcement(self.weights, attributions, reward)

        new_threshold = update_threshold(threshold, loss, previous_loss, self._state["eta"])

        self._state["previous_loss"] = loss
        self._state["previous_metric"] = current_metric
        self._state["iteration"] += 1

        self.store.add({
            "cycle_id": cycle_id,
            "iteration": self._state["iteration"],
            "pd": pd,
            "threshold": threshold,
            "decision": decision,
            "realized_default": realized_default,
            "loss": loss,
            "metric": current_metric,
            "drift": drift,
            "drift_triggered": triggered,
            "action_taken": action_taken,
            "new_threshold": new_threshold,
        })

        return {
            "feedback_applied": True,
            "loss": loss,
            "metric": current_metric,
            "drift": drift,
            "drift_triggered": triggered,
            "action_taken": action_taken,
            "new_threshold": new_threshold,
            "iteration": self._state["iteration"],
            "weights": self.weights.state(),
        }
