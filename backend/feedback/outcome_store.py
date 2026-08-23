"""Outcome Store (secao 25 do PLANO.md)."""
from __future__ import annotations
from typing import Any, Dict, List
import json
import os


class OutcomeStore:
    def __init__(self, path: str | None = None):
        self.path = path
        self._records: List[Dict[str, Any]] = []
        if path and os.path.exists(path):
            with open(path) as f:
                self._records = json.load(f)

    def add(self, record: Dict[str, Any]) -> None:
        self._records.append(record)
        if self.path:
            with open(self.path, "w") as f:
                json.dump(self._records, f, indent=2)

    def all(self) -> List[Dict[str, Any]]:
        return list(self._records)

    def recent(self, n: int = 50) -> List[Dict[str, Any]]:
        return self._records[-n:]
