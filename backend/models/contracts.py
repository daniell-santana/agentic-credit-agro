"""
Contratos de dados / protocolo de comunicacao entre agentes (secao 23, 42 do PLANO.md).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class AgentMessage:
    cycle_id: str
    sender: str
    receiver: str
    payload: Dict[str, Any] = field(default_factory=dict)
    confidence: Optional[float] = None
    timestamp: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "payload": self.payload,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class CycleState:
    """Estado completo de um ciclo do pipeline (secao 42 do PLANO.md)."""
    cycle_id: str
    application_id: str
    producer_id: str
    timestamp: str = field(default_factory=now_iso)
    agent_messages: List[Dict[str, Any]] = field(default_factory=list)
    raw_features: Dict[str, float] = field(default_factory=dict)
    normalized_features: Dict[str, float] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    weighted_features: Dict[str, float] = field(default_factory=dict)
    fusion_score: Optional[float] = None
    pd: Optional[float] = None
    threshold: Optional[float] = None
    attributions: Dict[str, float] = field(default_factory=dict)
    confidence: Optional[float] = None
    decision: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    outcome: Optional[Dict[str, Any]] = None
    loss: Optional[float] = None
    metric: Optional[float] = None
    drift: Optional[float] = None
    iteration: int = 0
    latencies_ms: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "application_id": self.application_id,
            "producer_id": self.producer_id,
            "timestamp": self.timestamp,
            "agent_messages": self.agent_messages,
            "raw_features": self.raw_features,
            "normalized_features": self.normalized_features,
            "weights": self.weights,
            "weighted_features": self.weighted_features,
            "fusion_score": self.fusion_score,
            "pd": self.pd,
            "threshold": self.threshold,
            "attributions": self.attributions,
            "confidence": self.confidence,
            "decision": self.decision,
            "context": self.context,
            "outcome": self.outcome,
            "loss": self.loss,
            "metric": self.metric,
            "drift": self.drift,
            "iteration": self.iteration,
            "latencies_ms": self.latencies_ms,
        }
