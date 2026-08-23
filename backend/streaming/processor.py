"""
Pipeline / orquestrador do ciclo completo (secao 2, 23, 42 do PLANO.md).

Continuous Data Stream -> Data Acquisition -> Normalization -> Streaming
Window -> Feature Transformation -> Risk Scoring -> Explainability ->
Decision -> (outcome observado) -> Feedback Learning -> Drift ->
Reinforcement Adjustment -> novo ciclo.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import csv
import os
import random
import time

from backend.config import FEATURE_NAMES, TAU_0, ETA, GAMMA, MC_SAMPLES, NOISE_STD, SEED
from backend.models.contracts import CycleState, new_id, now_iso
from backend.features.normalizer import Normalizer
from backend.features.adaptive_weights import AdaptiveWeights
from backend.features.nonlinear_fusion import default_alpha
from backend.risk.pd_model import LogisticPDModel
from backend.agents.data_acquisition_agent import DataAcquisitionAgent
from backend.agents.risk_scoring_agent import RiskScoringAgent
from backend.agents.explainability_agent import ExplainabilityAgent
from backend.agents.decision_agent import DecisionAgent, decide
from backend.agents.feedback_learning_agent import FeedbackLearningAgent
from backend.feedback.outcome_store import OutcomeStore
from backend.streaming.generator import SyntheticStreamGenerator
from backend.state import persistence


class AgenticCreditPipeline:
    """Orquestra o fluxo completo e mantem o estado adaptativo entre ciclos."""

    def __init__(self, data_dir: str = "data/synthetic", state_path: str = "data/adaptive_state.json",
                 outcome_path: str = "data/outcomes.json"):
        self.data_dir = data_dir
        self.state_path = state_path
        self.rng = random.Random(SEED)

        normalizer = Normalizer()
        self._fit_normalizer(normalizer)

        self.weights = AdaptiveWeights(FEATURE_NAMES)
        self.pd_model = LogisticPDModel(FEATURE_NAMES)
        self._fit_pd_model()

        self.data_agent = DataAcquisitionAgent(normalizer)
        self.risk_agent = RiskScoringAgent(FEATURE_NAMES, self.pd_model, self.weights,
                                            default_alpha(FEATURE_NAMES), threshold=TAU_0)
        self.explain_agent = ExplainabilityAgent(self.pd_model, mc_samples=MC_SAMPLES, noise_std=NOISE_STD, seed=SEED)
        self.decision_agent = DecisionAgent()
        self.outcome_store = OutcomeStore(path=outcome_path)
        self.feedback_agent = FeedbackLearningAgent(self.weights, self.outcome_store, eta=ETA, gamma=GAMMA)

        self.stream = SyntheticStreamGenerator(data_dir=data_dir, seed=SEED)

        self.agent_status = {
            "data_acquisition_agent": "ACTIVE", "feature_transformation": "ACTIVE",
            "risk_scoring_agent": "ACTIVE", "explainability_agent": "ACTIVE",
            "decision_agent": "ACTIVE", "feedback_learning_agent": "ACTIVE",
        }
        self.running = False
        self.cycles: List[Dict[str, Any]] = []
        self.pending_macro_shock: Optional[Dict[str, float]] = None
        self.pending_climate_shock: Optional[Dict[str, float]] = None
        self.counters = {"applications": 0, "approved": 0, "review": 0, "rejected": 0}

        self.restored_from_disk = self._load_persisted_state()

    def _fit_normalizer(self, normalizer: Normalizer):
        path = os.path.join(self.data_dir, "applications.csv")
        with open(path) as f:
            rows = list(csv.DictReader(f))
        sample = self.rng.sample(rows, min(500, len(rows)))
        feature_rows = [{f: float(r.get(f, 0.0)) for f in FEATURE_NAMES} for r in sample]
        normalizer.fit(feature_rows, FEATURE_NAMES)
        self._normalizer_fit_rows = feature_rows

    def _fit_pd_model(self):
        path = os.path.join(self.data_dir, "applications.csv")
        with open(path) as f:
            rows = list(csv.DictReader(f))
        sample = self.rng.sample(rows, min(600, len(rows)))
        targets = [1 if self.rng.random() < float(r["true_default_probability"]) else 0 for r in sample]
        feature_rows = [{f: float(r.get(f, 0.0)) for f in FEATURE_NAMES} for r in sample]
        # normaliza antes de treinar, coerente com o fluxo do pipeline
        norm = Normalizer()
        norm.fit(feature_rows, FEATURE_NAMES)
        norm_rows = [norm.transform(r) for r in feature_rows]
        self.pd_model.fit_simple(norm_rows, targets, lr=0.1, epochs=150, seed=SEED)

    def _load_persisted_state(self) -> bool:
        """Carrega estado adaptativo salvo em disco (secao 43 do PLANO.md), se existir.
        Retorna True se um estado anterior foi restaurado (vs. cold start)."""
        state = persistence.load(self.state_path)
        if not state:
            return False
        try:
            if "normalizer" in state:
                self.data_agent.normalizer.load_state(state["normalizer"])
            if "weights" in state:
                self.weights.load_state(state["weights"])
            if "pd_model" in state:
                self.pd_model.load_state(state["pd_model"])
            if "threshold" in state:
                self.risk_agent.set_threshold(state["threshold"])
            if "feedback" in state:
                self.feedback_agent._state.update(state["feedback"])
            if "counters" in state:
                self.counters.update(state["counters"])
            return True
        except (KeyError, TypeError, ValueError):
            # Estado incompativel (ex.: schema antigo) -> ignora e segue com cold start,
            # nunca derruba a inicializacao do pipeline.
            return False

    def _persist_state(self) -> None:
        state = {
            "meta": {"seed": SEED, "state_schema_version": 1},
            "normalizer": self.data_agent.normalizer.state(),
            "weights": self.weights.state(),
            "pd_model": self.pd_model.state(),
            "threshold": self.risk_agent._state["threshold"],
            "feedback": {k: v for k, v in self.feedback_agent._state.items()},
            "counters": self.counters,
        }
        try:
            persistence.save(state, self.state_path)
        except OSError:
            pass  # falha de IO no disco nunca derruba o ciclo de streaming

    def reset_adaptive_state(self) -> None:
        """Restaura pesos/threshold/feedback para os valores iniciais e apaga o
        estado persistido em disco (usado pelo endpoint POST /api/state/reset)."""
        persistence.reset(self.state_path)
        self.weights = AdaptiveWeights(FEATURE_NAMES)
        self.risk_agent.weights = self.weights
        self.risk_agent.set_threshold(TAU_0)
        self.feedback_agent.weights = self.weights
        self.feedback_agent._state.update({
            "previous_loss": 0.0, "previous_metric": 0.5, "iteration": 0,
            "eta": ETA, "gamma": GAMMA, "y_true_window": [], "y_pred_window": [],
        })
        self.counters = {"applications": 0, "approved": 0, "review": 0, "rejected": 0}
        self.cycles = []
        self.restored_from_disk = False

    def apply_macro_shock(self, selic_delta=0.0, fx_delta=0.0, commodity_pct=0.0):
        self.pending_macro_shock = {"selic_delta": selic_delta, "usd_brl_delta": fx_delta,
                                     "commodity_index_pct": commodity_pct}

    def apply_climate_shock(self, rainfall_pct=0.0, drought_delta=0.0):
        self.pending_climate_shock = {"rainfall_pct": rainfall_pct, "drought_index_delta": drought_delta}

    def preview_shock(self, operations: List[Dict[str, Any]], macro_shock: Optional[Dict[str, float]] = None,
                       climate_shock: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        "E se": recalcula o PD de operacoes JA CONHECIDAS (raw_features
        recebidos do cliente, que os guardou de ciclos anteriores) sob um
        cenario de choque hipotetico -- usando o modelo e os pesos ATUAIS
        do pipeline, mas SEM alterar nenhum estado (nao mexe em
        pending_macro_shock/pending_climate_shock, nao passa pelo Feedback
        Learning, nao persiste nada). E uma leitura, nao uma escrita.

        Classificacao: IMPLEMENTATION CHOICE / EXTENSAO — o artigo nao
        descreve um modo "what-if"; e a resposta a duvida de UX de "qual o
        objetivo de simular?": mostrar, operacao a operacao, como o PD
        mudaria sob o cenario, para o analista decidir o que revisar.
        """
        threshold = self.risk_agent._state["threshold"]
        results = []
        for op in operations:
            raw = dict(op.get("raw_features") or {})
            shocked = dict(raw)
            if macro_shock:
                shocked["selic"] = shocked.get("selic", 10.0) + macro_shock.get("selic_delta", 0.0)
                shocked["usd_brl"] = shocked.get("usd_brl", 5.0) + macro_shock.get("fx_delta", 0.0)
                shocked["commodity_index"] = shocked.get("commodity_index", 100.0) * (
                    1 + macro_shock.get("commodity_pct", 0.0) / 100.0)
            if climate_shock:
                shocked["rainfall"] = max(0.0, shocked.get("rainfall", 100.0) * (
                    1 + climate_shock.get("rainfall_pct", 0.0) / 100.0))
                shocked["drought_index"] = min(1.0, shocked.get("drought_index", 0.1) +
                                                climate_shock.get("drought_delta", 0.0))

            norm_current = self.data_agent.normalizer.transform(raw)
            weighted_current = self.weights.apply(norm_current)
            pd_current = self.pd_model.predict(weighted_current)

            norm_sim = self.data_agent.normalizer.transform(shocked)
            weighted_sim = self.weights.apply(norm_sim)
            pd_sim = self.pd_model.predict(weighted_sim)

            results.append({
                "application_id": op.get("application_id"),
                "producer_id": op.get("producer_id"),
                "pd_current": round(pd_current, 4),
                "pd_simulated": round(pd_sim, 4),
                "delta": round(pd_sim - pd_current, 4),
                "decision_current": decide(pd_current, threshold),
                "decision_simulated": decide(pd_sim, threshold),
                "threshold": threshold,
            })
        return results

    def _shocked_features(self, raw: Dict[str, float]) -> Dict[str, float]:
        raw = dict(raw)
        if self.pending_macro_shock:
            raw["selic"] = raw.get("selic", 10.0) + self.pending_macro_shock["selic_delta"]
            raw["usd_brl"] = raw.get("usd_brl", 5.0) + self.pending_macro_shock["usd_brl_delta"]
            raw["commodity_index"] = raw.get("commodity_index", 100.0) * (
                1 + self.pending_macro_shock["commodity_index_pct"] / 100.0)
        if self.pending_climate_shock:
            raw["rainfall"] = max(0.0, raw.get("rainfall", 100.0) * (
                1 + self.pending_climate_shock["rainfall_pct"] / 100.0))
            raw["drought_index"] = min(1.0, raw.get("drought_index", 0.1) +
                                        self.pending_climate_shock["drought_index_delta"])
        return raw

    def run_one_cycle(self) -> Dict[str, Any]:
        t_start = time.perf_counter()
        ev = self.stream.next_application_event()
        cycle_id = new_id("cyc")
        raw = self._shocked_features(ev.payload)

        state = CycleState(cycle_id=cycle_id, application_id=ev.payload.get("application_id", "N/A"),
                            producer_id=ev.producer_id)
        # Campos de contexto NAO numericos (UF, cultura, finalidade): usados
        # apenas para exibicao na UI (tabela de previsoes), nunca alimentam
        # o modelo -- o Data Acquisition Agent so recebe FEATURE_NAMES.
        state.context = {
            "state": ev.payload.get("state"),
            "crop_type": ev.payload.get("crop_type"),
            "purpose": ev.payload.get("purpose"),
        }

        msg1 = self.data_agent.run(cycle_id, "stream", {"raw_features": raw})
        state.agent_messages.append(msg1.to_dict())
        state.raw_features = msg1.payload["raw_features"]
        state.normalized_features = msg1.payload["normalized_features"]
        state.latencies_ms["data_acquisition"] = msg1.payload["_latency_ms"]

        msg2 = self.risk_agent.run(cycle_id, "data_acquisition_agent",
                                    {"normalized_features": state.normalized_features})
        state.agent_messages.append(msg2.to_dict())
        state.weights = msg2.payload["weights"]
        state.weighted_features = msg2.payload["weighted_features"]
        state.fusion_score = msg2.payload["fusion_score"]
        state.pd = msg2.payload["pd"]
        state.threshold = msg2.payload["threshold"]
        state.latencies_ms["risk_scoring"] = msg2.payload["_latency_ms"]

        msg3 = self.explain_agent.run(cycle_id, "risk_scoring_agent",
                                       {"weighted_features": state.weighted_features})
        state.agent_messages.append(msg3.to_dict())
        state.attributions = msg3.payload["attributions"]
        state.confidence = msg3.payload["confidence"]
        state.latencies_ms["explainability"] = msg3.payload["_latency_ms"]

        msg4 = self.decision_agent.run(cycle_id, "explainability_agent",
                                        {"pd": state.pd, "threshold": state.threshold})
        state.agent_messages.append(msg4.to_dict())
        state.decision = msg4.payload["decision"]
        state.latencies_ms["decision"] = msg4.payload["_latency_ms"]

        # Outcome: como o dataset ja tem o payment associado, observamos "instantaneamente"
        # para fins de demonstracao continua (streaming perpetuo sobre dados historicos).
        pay_ev = self.stream.payment_event_for(ev.payload.get("application_id", ""), ev.producer_id)
        realized_default = None
        loss_amount = 0.0
        if pay_ev:
            realized_default = 1 if pay_ev.event_type == "DEFAULT" else 0
            loss_amount = float(pay_ev.payload.get("loss_amount", 0.0)) / max(1.0, state.raw_features.get(
                "requested_amount", 1.0))

        msg5 = self.feedback_agent.run(cycle_id, "decision_agent", {
            "pd": state.pd, "threshold": state.threshold, "decision": state.decision,
            "realized_default": realized_default, "loss_amount": loss_amount,
            "attributions": state.attributions,
        })
        state.agent_messages.append(msg5.to_dict())
        state.latencies_ms["feedback"] = msg5.payload.get("_latency_ms", 0.0)

        if msg5.payload.get("feedback_applied"):
            state.outcome = {"realized_default": realized_default, "loss_amount": loss_amount}
            state.loss = msg5.payload["loss"]
            state.metric = msg5.payload["metric"]
            state.drift = msg5.payload["drift"]
            state.iteration = msg5.payload["iteration"]
            self.risk_agent.set_threshold(msg5.payload["new_threshold"])

        state.latencies_ms["end_to_end"] = (time.perf_counter() - t_start) * 1000.0

        self.counters["applications"] += 1
        if state.decision == "APPROVE":
            self.counters["approved"] += 1
        elif state.decision == "REVIEW":
            self.counters["review"] += 1
        else:
            self.counters["rejected"] += 1

        cycle_dict = state.to_dict()
        self.cycles.append(cycle_dict)
        self.cycles = self.cycles[-500:]
        self._persist_state()
        return cycle_dict

    def status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "agents": self.agent_status,
            "counters": self.counters,
            "current_threshold": self.risk_agent._state["threshold"],
            "iteration": self.feedback_agent._state["iteration"],
            "window": self.data_agent._state,
            "restored_from_disk": self.restored_from_disk,
            "state_path": self.state_path,
        }
