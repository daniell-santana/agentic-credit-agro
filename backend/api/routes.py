"""API minima (secao 41 do PLANO.md) + WebSocket para streaming em tempo real."""
from __future__ import annotations
import asyncio
import csv
import json
import os
from typing import Any, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Body

router = APIRouter()

# injecao simples de dependencia via modulo (mantido leve para a MVP)
from backend.streaming.processor import AgenticCreditPipeline  # noqa: E402
from backend.llm import narrative_agent  # noqa: E402

pipeline = AgenticCreditPipeline()
_ws_clients: List[WebSocket] = []
_stream_task: asyncio.Task | None = None


@router.get("/api/health")
def health():
    return {"status": "ok", "service": "agentic-credit-agro"}


@router.post("/api/stream/start")
async def stream_start(interval_ms: int = 900):
    global _stream_task
    pipeline.running = True
    if _stream_task is None or _stream_task.done():
        _stream_task = asyncio.create_task(_stream_loop(interval_ms))
    return {"running": True}


@router.post("/api/stream/stop")
async def stream_stop():
    pipeline.running = False
    return {"running": False}


@router.get("/api/stream/status")
def stream_status():
    return pipeline.status()


@router.get("/api/applications")
def list_applications(limit: int = 50):
    return {"cycles": pipeline.cycles[-limit:]}


@router.get("/api/applications/{application_id}")
def get_application(application_id: str):
    for c in reversed(pipeline.cycles):
        if c["application_id"] == application_id:
            return c
    return {"error": "not_found"}


@router.get("/api/risk/{application_id}")
def get_risk(application_id: str):
    for c in reversed(pipeline.cycles):
        if c["application_id"] == application_id:
            return {
                "pd": c["pd"], "threshold": c["threshold"],
                "confidence": c["confidence"], "decision": c["decision"],
                "attributions": c["attributions"],
            }
    return {"error": "not_found"}


@router.get("/api/monitoring/monthly")
def monitoring_monthly():
    """PD medio previsto vs taxa de default realizada, por mes de vencimento
    (ver backend/risk/monitoring.py para a metodologia completa)."""
    from backend.risk.monitoring import monthly_predicted_vs_actual
    return monthly_predicted_vs_actual()


@router.get("/api/state/status")
def state_status():
    """Estado adaptativo persistido (secao 43 do PLANO.md): existe? foi restaurado
    nesta inicializacao do processo? quando foi salvo pela ultima vez?"""
    from backend.state import persistence as _persist
    saved = _persist.load(pipeline.state_path)
    return {
        "restored_from_disk": pipeline.restored_from_disk,
        "state_path": pipeline.state_path,
        "persisted_state_exists": saved is not None,
        "last_saved_at": saved.get("saved_at") if saved else None,
        "persisted_iteration": saved.get("feedback", {}).get("iteration") if saved else None,
    }


@router.post("/api/state/reset")
def state_reset():
    """Apaga o estado adaptativo persistido e reinicia pesos/threshold/feedback
    para os valores iniciais (nao afeta o outcome_store historico)."""
    pipeline.reset_adaptive_state()
    return {"reset": True, "status": pipeline.status()}


@router.get("/api/agents/status")
def agents_status():
    return pipeline.status()


@router.get("/api/feedback/status")
def feedback_status():
    hist = pipeline.outcome_store.recent(1)
    return hist[0] if hist else {}


@router.get("/api/feedback/history")
def feedback_history(limit: int = 100):
    return {"history": pipeline.outcome_store.recent(limit)}


@router.get("/api/producers/map")
def producers_map(limit: int = 400):
    """Agrega risco medio por estado a partir dos ciclos recentes + coordenadas fixas dos estados."""
    from scripts.generate_synthetic_data import STATES
    coords = {s[0]: {"name": s[1], "lat": s[3], "lon": s[4]} for s in STATES}
    agg: Dict[str, Dict[str, Any]] = {}
    for c in pipeline.cycles[-limit:]:
        state = c["raw_features"].get("state") if isinstance(c["raw_features"].get("state"), str) else None
    # raw_features nao guarda "state" (nao e feature numerica); usar producers.csv como fallback
    path = os.path.join("data", "synthetic", "applications.csv")
    by_state: Dict[str, List[float]] = {}
    if os.path.exists(path):
        with open(path) as f:
            for row in csv.DictReader(f):
                by_state.setdefault(row["state"], []).append(float(row["true_default_probability"]))
    result = []
    for code, info in coords.items():
        probs = by_state.get(code, [])
        avg_risk = sum(probs) / len(probs) if probs else 0.0
        result.append({
            "state": code, "name": info["name"], "lat": info["lat"], "lon": info["lon"],
            "avg_risk": round(avg_risk, 4), "applications": len(probs),
        })
    return {"states": result}


@router.post("/api/stress/preview")
def stress_preview(payload: Dict[str, Any] = Body(...)):
    """
    Modo "e se": recalcula o PD de uma lista de operacoes sob um cenario de
    choque hipotetico, sem alterar nenhum estado do pipeline (ver
    AgenticCreditPipeline.preview_shock). Espera:
    {
      "selic_delta": 2, "fx_delta": 0, "commodity_pct": -20,
      "rainfall_pct": -30, "drought_delta": 0.15,
      "operations": [{"application_id":..., "producer_id":..., "raw_features": {...}}, ...]
    }
    """
    macro_shock = {
        "selic_delta": payload.get("selic_delta", 0.0),
        "fx_delta": payload.get("fx_delta", 0.0),
        "commodity_pct": payload.get("commodity_pct", 0.0),
    }
    climate_shock = {
        "rainfall_pct": payload.get("rainfall_pct", 0.0),
        "drought_delta": payload.get("drought_delta", 0.0),
    }
    operations = payload.get("operations", [])
    results = pipeline.preview_shock(operations, macro_shock, climate_shock)
    return {"results": results}


@router.post("/api/stress/macro")
async def stress_macro(selic_delta: float = 0.0, fx_delta: float = 0.0, commodity_pct: float = 0.0):
    pipeline.apply_macro_shock(selic_delta, fx_delta, commodity_pct)
    return {"applied": True, "selic_delta": selic_delta, "fx_delta": fx_delta, "commodity_pct": commodity_pct}


@router.post("/api/stress/climate")
async def stress_climate(rainfall_pct: float = 0.0, drought_delta: float = 0.0):
    pipeline.apply_climate_shock(rainfall_pct, drought_delta)
    return {"applied": True, "rainfall_pct": rainfall_pct, "drought_delta": drought_delta}


@router.get("/api/experiments")
def experiments():
    """Resultados PUBLICADOS NO ARTIGO (referencia), nunca resultado da MVP (secao 48/50)."""
    from backend.state import persistence as _persist
    mvp_comparison_path = os.path.join("experiments", "results.json")
    mvp_comparison = None
    if os.path.exists(mvp_comparison_path):
        with open(mvp_comparison_path, encoding="utf-8") as f:
            mvp_comparison = json.load(f)
    return {
        "article_reference": {
            "note": "Valores publicados no artigo original (Kubam, 2024). NAO sao resultado desta MVP.",
            "decision_accuracy": {
                "agentic_ai": {"accuracy": 94.2, "precision": 91.5, "recall": 92.3},
                "conventional_ml": {"accuracy": 87.6, "precision": 84.1, "recall": 85.9},
            },
            "explainability": {
                "agentic_ai": {"explanation_completeness": 0.92, "interpretability_score": 0.88,
                                "compliance_readiness": "High"},
                "conventional_ml": {"explanation_completeness": 0.61, "interpretability_score": 0.55,
                                      "compliance_readiness": "Medium"},
            },
        },
        "mvp_comparison_experiment": mvp_comparison if mvp_comparison else {
            "note": "Ainda nao gerado. Rode: python scripts/run_experiment_comparison.py",
        },
        "mvp_live_metrics": {
            "note": "Metricas calculadas em tempo real sobre o stream sintetico desta MVP.",
            "counters": pipeline.counters,
            "iteration": pipeline.feedback_agent._state["iteration"],
            "current_threshold": pipeline.risk_agent._state["threshold"],
        },
    }


@router.get("/api/llm/status")
def llm_status():
    """Informa se o hook opcional de LLM (secao 39) esta ativo (OPENAI_API_KEY definida)."""
    return {"enabled": narrative_agent.is_enabled()}


@router.post("/api/narrative/decision")
def narrative_decision(payload: Dict[str, Any] = Body(...)):
    """
    Resumo (com recomendacao prescritiva quando o caso pede) de uma
    decisao. Recebe o contexto JA CALCULADO diretamente do cliente —
    incluindo pd_anterior/delta, que sao derivados client-side (o backend
    nao guarda historico por produtor entre ciclos nao consecutivos) —
    para o LLM poder recomendar acao com base na tendencia, nao so no
    PD isolado. Nunca recalcula PD/threshold/decisao, so traduz.
    """
    if not narrative_agent.is_enabled():
        return {"enabled": False, "summary": None,
                "message": "LLM opcional desativado. Defina OPENAI_API_KEY para habilitar."}
    return {"enabled": True, "summary": narrative_agent.summarize_decision(payload)}


@router.get("/api/narrative/{cycle_id}")
def narrative(cycle_id: str):
    """
    Resumo em linguagem natural de uma decisao JA CALCULADA (gerado sob
    demanda, nunca automaticamente, para nao inflar custo/latencia do
    pipeline principal). O nucleo matematico nao depende deste endpoint.
    """
    for c in reversed(pipeline.cycles):
        if c["cycle_id"] == cycle_id:
            if not narrative_agent.is_enabled():
                return {"enabled": False, "summary": None,
                        "message": "LLM opcional desativado. Defina OPENAI_API_KEY para habilitar."}
            return {"enabled": True, "summary": narrative_agent.summarize_decision(c)}
    return {"error": "not_found"}


@router.post("/api/narrative/portfolio")
def narrative_portfolio(payload: Dict[str, Any] = Body(...)):
    """
    Resumo em linguagem natural de um agregado de carteira JA CALCULADO NO
    CLIENTE (distribuicao de risco, evolucao, ou risco por estado do mapa —
    Aba 1). O backend nunca recalcula nada, so traduz numeros prontos.
    Espera {"chart_name": str, "stats": {...}}.
    """
    if not narrative_agent.is_enabled():
        return {"enabled": False, "summary": None,
                "message": "LLM opcional desativado. Defina OPENAI_API_KEY para habilitar."}
    chart_name = payload.get("chart_name", "gráfico")
    stats = payload.get("stats", {})
    return {"enabled": True, "summary": narrative_agent.summarize_portfolio(chart_name, stats)}


async def _broadcast(message: Dict[str, Any]):
    dead = []
    for ws in _ws_clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


async def _stream_loop(interval_ms: int):
    while pipeline.running:
        try:
            cycle = pipeline.run_one_cycle()
            await _broadcast({"type": "cycle", "data": cycle, "status": pipeline.status()})
        except Exception as e:  # nunca derruba o loop de streaming
            await _broadcast({"type": "error", "message": str(e)})
        await asyncio.sleep(interval_ms / 1000.0)


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    await websocket.send_json({"type": "status", "data": pipeline.status()})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)
