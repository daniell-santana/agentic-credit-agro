"""
Gerador de eventos de streaming a partir do dataset sintetico
(secao 29 do PLANO.md). Reproduz aplicacoes/pagamentos existentes e
injeta eventos MACRO_UPDATE / CLIMATE_UPDATE / COMMODITY_UPDATE.
"""
from __future__ import annotations
import csv
import json
import os
import random
from typing import Iterator

from backend.streaming.event import StreamEvent


class SyntheticStreamGenerator:
    def __init__(self, data_dir: str = "data/synthetic", seed: int = 42):
        self.data_dir = data_dir
        self.rng = random.Random(seed)
        self.applications = self._load_csv("applications.csv")
        self.payments = self._load_csv("payments.csv")
        self.producers = self._load_csv("producers.csv")
        self.producers_by_id = {p["producer_id"]: p for p in self.producers}
        self.payments_by_app = {p["application_id"]: p for p in self.payments}
        self.rng.shuffle(self.applications)
        self._idx = 0

    PRODUCER_JOIN_FIELDS = [
        "annual_revenue", "annual_cost", "equity", "debt", "farm_size_ha", "years_farming",
    ]
    PRODUCER_CONTEXT_FIELDS = ["crop_type", "municipality"]  # so para exibicao na UI, nao entram no modelo

    def _load_csv(self, name: str):
        path = os.path.join(self.data_dir, name)
        with open(path) as f:
            return list(csv.DictReader(f))

    def next_application_event(self) -> StreamEvent | None:
        if self._idx >= len(self.applications):
            self._idx = 0  # loop continuo (streaming perpetuo)
        app = self.applications[self._idx]
        self._idx += 1
        payload = {k: (float(v) if _is_float(v) else v) for k, v in app.items()}
        # Join explícito com producers.csv: sem isso, campos financeiros do
        # produtor (patrimônio, dívida, área) nunca chegam ao Data Acquisition
        # Agent e o ciclo é marcado como inválido (bug corrigido nesta revisão).
        producer = self.producers_by_id.get(app["producer_id"])
        if producer:
            for field in self.PRODUCER_JOIN_FIELDS:
                payload[field] = float(producer.get(field, 0.0)) if _is_float(producer.get(field)) else 0.0
            for field in self.PRODUCER_CONTEXT_FIELDS:
                payload[field] = producer.get(field)
        return StreamEvent(event_type="NEW_APPLICATION", producer_id=app["producer_id"], payload=payload)

    def payment_event_for(self, application_id: str, producer_id: str) -> StreamEvent | None:
        pay = self.payments_by_app.get(application_id)
        if not pay:
            return None
        event_type = "DEFAULT" if pay["default_flag"] == "1" else "PAYMENT"
        payload = {k: (float(v) if _is_float(v) else v) for k, v in pay.items()}
        return StreamEvent(event_type=event_type, producer_id=producer_id, payload=payload)

    def macro_shock_event(self, selic_delta=0.0, fx_delta=0.0, commodity_pct=0.0) -> StreamEvent:
        return StreamEvent(event_type="MACRO_UPDATE", producer_id="MACRO",
                            payload={"selic_delta": selic_delta, "usd_brl_delta": fx_delta,
                                      "commodity_index_pct": commodity_pct})

    def climate_shock_event(self, rainfall_pct=0.0, drought_delta=0.0) -> StreamEvent:
        return StreamEvent(event_type="CLIMATE_UPDATE", producer_id="CLIMATE",
                            payload={"rainfall_pct": rainfall_pct, "drought_index_delta": drought_delta})


def _is_float(v: str) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False
