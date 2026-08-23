"""
Data Acquisition Agent (secao 8 do PLANO.md).

Responsabilidades: ingerir, validar, normalizar dados, atualizar a
Streaming Window (Equacao 2) e produzir mensagem para o proximo estagio.
"""
from __future__ import annotations
from typing import Any, Dict
from datetime import datetime, timezone

from backend.agents.base_agent import BaseAgent
from backend.features.normalizer import Normalizer


def update_window(w_t_minus_1: float, delta_t: float) -> float:
    """Wt = Wt-1 + delta_t  (Equacao 2)."""
    return w_t_minus_1 + delta_t


class DataAcquisitionAgent(BaseAgent):
    name = "data_acquisition_agent"

    REQUIRED_FIELDS = [
        "requested_amount", "term_months", "interest_rate", "collateral_value",
        "annual_revenue", "annual_cost", "equity", "debt", "farm_size_ha",
        "years_farming", "rainfall", "temperature", "drought_index",
        "crop_price", "selic", "inflation", "usd_brl", "commodity_index",
    ]

    def __init__(self, normalizer: Normalizer | None = None):
        super().__init__()
        self.normalizer = normalizer or Normalizer()
        self._state = {"window_start": None, "window_current": 0.0, "events_processed": 0}

    def validate(self, raw: Dict[str, Any]) -> bool:
        return all(f in raw and raw[f] is not None for f in self.REQUIRED_FIELDS)

    def process(self, cycle_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw = payload.get("raw_features", {})
        valid = self.validate(raw)
        if self._state.get("window_start") is None:
            self._state["window_start"] = datetime.now(timezone.utc).isoformat()
        self._state["window_current"] = update_window(self._state.get("window_current", 0.0), 1.0)
        self._state["events_processed"] = self._state.get("events_processed", 0) + 1

        features = {f: float(raw.get(f, 0.0)) for f in self.REQUIRED_FIELDS}
        normalized = self.normalizer.transform(features)
        return {
            "valid": valid,
            "raw_features": features,
            "normalized_features": normalized,
            "window": {
                "start": self._state["window_start"],
                "current": self._state["window_current"],
                "events_processed": self._state["events_processed"],
            },
        }
