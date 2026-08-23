"""
Monitoramento mensal: PD medio previsto vs taxa de default realizada,
por mes (secao de "Historico Predito vs Real" pedida pelo usuario).

Classificacao: IMPLEMENTATION CHOICE / EXTENSAO DE MONITORAMENTO —
o artigo original nao descreve este tipo de painel; e uma adaptacao
pensada para o publico de gerente de carteira de credito, que precisa
comparar a previsao do modelo com o resultado real observado mes a mes
(a inadimplencia so e confirmada quando o pagamento vence, e os
vencimentos no dataset sintetico sao mensais).

Reusa o mesmo modelo treinado por scripts/run_experiment_comparison.py
(Normalizer + LogisticPDModel, gradient descent local, seed fixa) para
gerar o PD medio previsto de cada mes, e compara com a taxa de default
realmente observada nesse mes (a partir de payments.csv).

HONESTIDADE TEMPORAL (correcao pedida pelo usuario): meses APOS a data
atual do servidor nao podem ter "taxa real observada" -- esse resultado
ainda nao aconteceu. Para esses meses, mostramos apenas uma PROJECAO do
PD medio previsto, via um ajuste linear simples (minimos quadrados)
sobre os ultimos 12 meses historicos conhecidos, limitada a ~18 meses a
frente. Nao usamos o rotulo sintetico "realized_default" desses meses
futuros mesmo que ele exista no dataset -- isso seria emprestar
conhecimento do futuro que um sistema real nunca teria.
"""
from __future__ import annotations
import csv
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.config import FEATURE_NAMES, SEED
from backend.features.normalizer import Normalizer
from backend.risk.pd_model import LogisticPDModel

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "synthetic")
FORECAST_MONTHS_AHEAD = 18
FORECAST_TRAIN_WINDOW = 12


def _load_joined_rows() -> List[Dict[str, Any]]:
    with open(os.path.join(DATA_DIR, "producers.csv")) as f:
        producers = {r["producer_id"]: r for r in csv.DictReader(f)}
    with open(os.path.join(DATA_DIR, "applications.csv")) as f:
        applications = list(csv.DictReader(f))
    with open(os.path.join(DATA_DIR, "payments.csv")) as f:
        payments = {r["application_id"]: r for r in csv.DictReader(f)}

    rows = []
    for app in applications:
        prod = producers.get(app["producer_id"])
        pay = payments.get(app["application_id"])
        if not prod or not pay:
            continue
        features = {f: float(app.get(f, prod.get(f, 0.0))) for f in FEATURE_NAMES if f not in
                    ("annual_revenue", "annual_cost", "equity", "debt", "farm_size_ha", "years_farming")}
        for f in ("annual_revenue", "annual_cost", "equity", "debt", "farm_size_ha", "years_farming"):
            features[f] = float(prod.get(f, 0.0))
        rows.append({
            "application_date": app["application_date"],
            "due_date": pay["due_date"],
            "payment_date": pay["payment_date"],
            "features": features,
            "realized_default": int(pay["default_flag"]),
        })
    return rows


def _fit_model(rows: List[Dict[str, Any]], seed: int = SEED) -> tuple[Normalizer, LogisticPDModel]:
    import random
    rng = random.Random(seed)
    sample = rng.sample(rows, min(900, len(rows)))
    feature_rows = [r["features"] for r in sample]
    targets = [r["realized_default"] for r in sample]
    normalizer = Normalizer()
    normalizer.fit(feature_rows, FEATURE_NAMES)
    norm_rows = [normalizer.transform(r) for r in feature_rows]
    model = LogisticPDModel(FEATURE_NAMES)
    model.fit_simple(norm_rows, targets, lr=0.1, epochs=150, seed=seed)
    return normalizer, model


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


def _linear_forecast(values: List[float], n_ahead: int) -> List[float]:
    """Minimos quadrados (grau 1), em Python puro (sem numpy -- o nucleo
    deste projeto e intencionalmente livre de dependencias pesadas, ver
    requirements.txt), sobre os ultimos valores conhecidos, extrapolado
    n_ahead pontos a frente. Classificacao: IMPLEMENTATION CHOICE — modelo
    de projecao simples, nao um forecaster de serie temporal sofisticado
    (ex.: ARIMA/Prophet), suficiente para dar uma tendencia direcional
    honesta sem fingir precisao que a MVP nao tem."""
    n = len(values)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    num = sum((xs[i] - mean_x) * (values[i] - mean_y) for i in range(n))
    den = sum((x - mean_x) ** 2 for x in xs) or 1.0
    slope = num / den
    intercept = mean_y - slope * mean_x
    forecast = [slope * (n + i) + intercept for i in range(n_ahead)]
    return [max(0.02, min(0.98, v)) for v in forecast]


_cache: Dict[str, Any] = {}


def monthly_predicted_vs_actual(now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Agrupa por mes de VENCIMENTO do pagamento (due_date) -- e nesse mes que
    a inadimplencia daquele contrato e de fato conhecida/realizada.

    Meses <= mes atual do servidor: "historico" (predicted_pd_avg E
    actual_default_rate, os dois conhecidos retrospectivamente).
    Meses > mes atual: "projecao" (apenas predicted_pd_avg, via ajuste
    linear simples; actual_default_rate = None, pois ainda nao aconteceu).
    """
    now = now or datetime.now(timezone.utc)
    current_month_key = f"{now.year:04d}-{now.month:02d}"

    if "result" in _cache and _cache.get("current_month_key") == current_month_key:
        return _cache["result"]

    rows = _load_joined_rows()
    normalizer, model = _fit_model(rows)

    by_month: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: {"pd": [], "actual": []})
    for r in rows:
        month_key = r["due_date"][:7]  # YYYY-MM
        if month_key > current_month_key:
            continue  # nao usamos dados de meses futuros nem para treinar a projecao
        norm = normalizer.transform(r["features"])
        pd = model.predict(norm)
        by_month[month_key]["pd"].append(pd)
        by_month[month_key]["actual"].append(float(r["realized_default"]))

    months = sorted(by_month.keys())
    series = []
    for m in months:
        pds = by_month[m]["pd"]
        actuals = by_month[m]["actual"]
        series.append({
            "month": m,
            "predicted_pd_avg": round(sum(pds) / len(pds), 4),
            "actual_default_rate": round(sum(actuals) / len(actuals), 4),
            "n_contracts": len(pds),
            "is_forecast": False,
        })

    if len(series) >= 4:
        window = series[-FORECAST_TRAIN_WINDOW:]
        forecast_values = _linear_forecast([p["predicted_pd_avg"] for p in window], FORECAST_MONTHS_AHEAD)
        last_year, last_month = (int(x) for x in months[-1].split("-"))
        for i, val in enumerate(forecast_values, start=1):
            fy, fm = _add_months(last_year, last_month, i)
            series.append({
                "month": f"{fy:04d}-{fm:02d}",
                "predicted_pd_avg": round(val, 4),
                "actual_default_rate": None,
                "n_contracts": 0,
                "is_forecast": True,
            })

    result = {
        "classification": "IMPLEMENTATION CHOICE / EXTENSAO DE MONITORAMENTO — nao especificado "
                           "pelo artigo original. Agrupado pelo mes de VENCIMENTO do contrato "
                           "(quando a inadimplencia e de fato conhecida), nao pelo mes da aplicacao.",
        "current_month": current_month_key,
        "forecast_method": "Ajuste linear (minimos quadrados) sobre os ultimos "
                            f"{FORECAST_TRAIN_WINDOW} meses historicos do PD medio previsto, "
                            f"projetado {FORECAST_MONTHS_AHEAD} meses a frente. Meses futuros NAO "
                            "mostram 'taxa real observada' -- esse dado ainda nao existe.",
        "series": series,
    }
    _cache["result"] = result
    _cache["current_month_key"] = current_month_key
    return result
