"""Evento de streaming (secao 29 do PLANO.md)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict
from backend.models.contracts import new_id, now_iso

EVENT_TYPES = [
    "NEW_APPLICATION", "PAYMENT", "LATE_PAYMENT", "DEFAULT",
    "MACRO_UPDATE", "CLIMATE_UPDATE", "COMMODITY_UPDATE",
]


@dataclass
class StreamEvent:
    event_type: str
    producer_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: new_id("evt"))
    timestamp: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id, "timestamp": self.timestamp,
            "producer_id": self.producer_id, "event_type": self.event_type,
            "payload": self.payload,
        }
