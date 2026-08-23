"""Base Agent — interface comum: input / processing / state / output (secao 39)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict
import time

from backend.models.contracts import AgentMessage


class BaseAgent(ABC):
    name: str = "base_agent"

    def __init__(self):
        self._state: Dict[str, Any] = {}

    @abstractmethod
    def process(self, cycle_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Recebe payload, processa e retorna payload de saida."""

    def run(self, cycle_id: str, sender: str, payload: Dict[str, Any]) -> AgentMessage:
        t0 = time.perf_counter()
        out = self.process(cycle_id, payload)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        out["_latency_ms"] = latency_ms
        return AgentMessage(cycle_id=cycle_id, sender=self.name, receiver="pipeline", payload=out)

    def state(self) -> Dict[str, Any]:
        return dict(self._state)

    def load_state(self, state: Dict[str, Any]) -> None:
        self._state.update(state or {})
