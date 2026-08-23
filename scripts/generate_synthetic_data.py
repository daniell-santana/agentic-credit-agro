"""
Gerador de dados sinteticos (secao 4-7 do PLANO.md). SEED = 42.

Gera: producers.csv, applications.csv, payments.csv, agriculture.csv,
macro.csv, stream_events.jsonl.

Todos os dados sao 100% sinteticos, marcados como tal, sem qualquer
relacao com produtores, bancos ou operacoes reais.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import random
from datetime import date, timedelta

SEED = 42

STATES = [
    ("MT", "Mato Grosso", "Centro-Oeste", -12.6, -55.9),
    ("GO", "Goias", "Centro-Oeste", -15.9, -49.8),
    ("RS", "Rio Grande do Sul", "Sul", -30.0, -53.0),
    ("PR", "Parana", "Sul", -24.9, -51.5),
    ("MS", "Mato Grosso do Sul", "Centro-Oeste", -20.7, -54.7),
    ("BA", "Bahia", "Nordeste", -12.9, -41.7),
    ("MG", "Minas Gerais", "Sudeste", -18.9, -44.6),
    ("SP", "Sao Paulo", "Sudeste", -22.2, -48.6),
    ("TO", "Tocantins", "Norte", -10.2, -48.3),
    ("PI", "Piaui", "Nordeste", -7.7, -42.7),
]
CROPS = ["soja", "milho", "algodao", "cafe", "cana-de-acucar", "pecuaria"]
PURPOSES = ["custeio", "investimento", "comercializacao", "industrializacao"]

REGIMES = [
    ("normal", date(2022, 1, 1), date(2023, 12, 31)),
    ("stress_agricola", date(2024, 1, 1), date(2024, 6, 30)),
    ("stress_macro", date(2024, 7, 1), date(2024, 12, 31)),
    ("stress_combinado", date(2025, 1, 1), date(2025, 6, 30)),
    ("normal", date(2025, 7, 1), date(2025, 12, 31)),
    ("normal", date(2026, 1, 1), date(2026, 12, 31)),
]


def daterange_months(d0: date, d1: date):
    cur = date(d0.year, d0.month, 1)
    while cur <= d1:
        yield cur
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)


def regime_for_date(d: date) -> str:
    for name, start, end in REGIMES:
        if start <= d <= end:
            return name
    return "normal"


def gen_producers(rng: random.Random, n: int):
    rows = []
    for i in range(n):
        st = rng.choice(STATES)
        farm_size = round(rng.lognormvariate(4.0, 0.9), 1)
        years = rng.randint(1, 35)
        revenue = round(max(20000, rng.lognormvariate(12.2, 0.7)), 2)
        cost = round(revenue * rng.uniform(0.55, 0.9), 2)
        equity = round(max(10000, rng.lognormvariate(11.8, 0.8)), 2)
        debt = round(equity * rng.uniform(0.05, 1.3), 2)
        rows.append({
            "producer_id": f"PRD{i+1:06d}",
            "age": rng.randint(22, 75),
            "state": st[0],
            "municipality": f"{st[1]} - Municipio {rng.randint(1,40)}",
            "region": st[2],
            "farm_size_ha": farm_size,
            "years_farming": years,
            "crop_type": rng.choice(CROPS),
            "annual_revenue": revenue,
            "annual_cost": cost,
            "equity": equity,
            "debt": debt,
        })
    return rows


def gen_agriculture(rng: random.Random):
    rows = []
    for st in STATES:
        base_price = rng.uniform(50, 200)
        for d in daterange_months(date(2022, 1, 1), date(2026, 12, 1)):
            regime = regime_for_date(d)
            rainfall = rng.uniform(60, 220)
            temperature = rng.uniform(18, 34)
            drought = rng.uniform(0.0, 0.3)
            price = base_price * rng.uniform(0.9, 1.1)
            yield_index = rng.uniform(0.85, 1.15)
            cost_index = rng.uniform(0.9, 1.1)
            if regime in ("stress_agricola", "stress_combinado"):
                rainfall *= 0.65
                drought = min(1.0, drought + rng.uniform(0.3, 0.5))
                yield_index *= 0.75
                cost_index *= 1.15
                price *= rng.uniform(0.75, 0.9)
            rows.append({
                "date": d.isoformat(), "state": st[0], "crop_price": round(price, 2),
                "rainfall": round(rainfall, 1), "temperature": round(temperature, 1),
                "drought_index": round(drought, 3), "yield_index": round(yield_index, 3),
                "production_cost_index": round(cost_index, 3), "regime": regime,
            })
    return rows


def gen_macro(rng: random.Random):
    rows = []
    selic, infl, fx, commodity, agri_input = 10.5, 4.5, 5.0, 100.0, 100.0
    for d in daterange_months(date(2022, 1, 1), date(2026, 12, 1)):
        regime = regime_for_date(d)
        selic += rng.uniform(-0.15, 0.15)
        infl += rng.uniform(-0.1, 0.1)
        fx += rng.uniform(-0.05, 0.05)
        commodity += rng.uniform(-1.5, 1.5)
        agri_input += rng.uniform(-1.0, 1.0)
        if regime in ("stress_macro", "stress_combinado"):
            selic += rng.uniform(0.3, 0.6)
            infl += rng.uniform(0.2, 0.4)
            fx += rng.uniform(0.1, 0.25)
            commodity -= rng.uniform(1.0, 2.5)
            agri_input += rng.uniform(0.5, 1.5)
        selic = max(2.0, min(20.0, selic))
        infl = max(1.0, min(15.0, infl))
        fx = max(3.0, min(8.0, fx))
        commodity = max(50.0, commodity)
        agri_input = max(50.0, agri_input)
        rows.append({
            "date": d.isoformat(), "selic": round(selic, 2), "inflation": round(infl, 2),
            "usd_brl": round(fx, 3), "commodity_index": round(commodity, 2),
            "agri_input_index": round(agri_input, 2), "regime": regime,
        })
    return rows


def logistic(x):
    import math
    return 1 / (1 + math.exp(-x))


def gen_applications_and_payments(rng: random.Random, producers, agriculture, macro):
    agri_by_state_month = {}
    for r in agriculture:
        agri_by_state_month[(r["state"], r["date"][:7])] = r
    macro_by_month = {r["date"][:7]: r for r in macro}

    applications, payments = [], []
    app_counter = 0
    for p in producers:
        n_apps = rng.randint(1, 4)
        for _ in range(n_apps):
            d = date(2022, 1, 1) + timedelta(days=rng.randint(0, 1795))
            month_key = f"{d.year:04d}-{d.month:02d}"
            agri = agri_by_state_month.get((p["state"], month_key))
            macro_row = macro_by_month.get(month_key)
            if not agri or not macro_row:
                continue
            app_counter += 1
            requested = round(max(5000, rng.lognormvariate(10.5, 0.8)), 2)
            term = rng.choice([6, 12, 18, 24, 36])
            rate = round(rng.uniform(6.5, 18.0), 2)
            collateral = round(requested * rng.uniform(0.6, 1.8), 2)

            debt_ratio = p["debt"] / max(1.0, p["equity"])
            revenue_gap = (p["annual_cost"] - p["annual_revenue"]) / max(1.0, p["annual_revenue"])
            macro_pressure = (macro_row["selic"] - 8) / 10 + (macro_row["inflation"] - 4) / 10
            agro_pressure = agri["drought_index"] + (1 - agri["yield_index"])
            z = (-2.2 + 1.6 * debt_ratio + 1.1 * max(0, revenue_gap) + 0.9 * macro_pressure
                 + 0.8 * agro_pressure - 0.4 * (collateral / max(1.0, requested) - 1))
            default_prob = logistic(z)
            default_flag = 1 if rng.random() < default_prob else 0

            applications.append({
                "application_id": f"APP{app_counter:07d}",
                "producer_id": p["producer_id"],
                "application_date": d.isoformat(),
                "requested_amount": requested,
                "term_months": term,
                "interest_rate": rate,
                "collateral_value": collateral,
                "purpose": rng.choice(PURPOSES),
                "state": p["state"],
                "rainfall": agri["rainfall"], "temperature": agri["temperature"],
                "drought_index": agri["drought_index"], "crop_price": agri["crop_price"],
                "selic": macro_row["selic"], "inflation": macro_row["inflation"],
                "usd_brl": macro_row["usd_brl"], "commodity_index": macro_row["commodity_index"],
                "true_default_probability": round(default_prob, 4),
            })

            due = d + timedelta(days=30 * term)
            days_late = 0
            loss_amount = 0.0
            if default_flag:
                days_late = rng.randint(31, 400)
                loss_amount = round(requested * rng.uniform(0.2, 0.85), 2)
            payments.append({
                "payment_id": f"PAY{app_counter:07d}",
                "application_id": applications[-1]["application_id"],
                "due_date": due.isoformat(),
                "payment_date": (due + timedelta(days=days_late)).isoformat(),
                "amount": requested,
                "days_late": days_late,
                "default_flag": default_flag,
                "loss_amount": loss_amount,
            })
    return applications, payments


def write_csv(path, rows, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--n_producers", type=int, default=1200)
    ap.add_argument("--outdir", type=str, default="data/synthetic")
    args = ap.parse_args()

    rng = random.Random(args.seed)

    producers = gen_producers(rng, args.n_producers)
    agriculture = gen_agriculture(rng)
    macro = gen_macro(rng)
    applications, payments = gen_applications_and_payments(rng, producers, agriculture, macro)

    write_csv(f"{args.outdir}/producers.csv", producers, list(producers[0].keys()))
    write_csv(f"{args.outdir}/agriculture.csv", agriculture, list(agriculture[0].keys()))
    write_csv(f"{args.outdir}/macro.csv", macro, list(macro[0].keys()))
    write_csv(f"{args.outdir}/applications.csv", applications, list(applications[0].keys()))
    write_csv(f"{args.outdir}/payments.csv", payments, list(payments[0].keys()))

    stream_path = f"{args.outdir}/stream_events.jsonl"
    with open(stream_path, "w") as f:
        for app, pay in zip(applications, payments):
            ev = {
                "event_id": f"EVT{app['application_id']}",
                "timestamp": app["application_date"],
                "producer_id": app["producer_id"],
                "event_type": "NEW_APPLICATION",
                "payload": app,
            }
            f.write(json.dumps(ev) + "\n")
            ev2 = {
                "event_id": f"EVT{pay['payment_id']}",
                "timestamp": pay["payment_date"],
                "producer_id": app["producer_id"],
                "event_type": "DEFAULT" if pay["default_flag"] else "PAYMENT",
                "payload": {**pay, "application_id": app["application_id"]},
            }
            f.write(json.dumps(ev2) + "\n")

    print(f"producers={len(producers)} applications={len(applications)} "
          f"payments={len(payments)} agriculture_rows={len(agriculture)} macro_rows={len(macro)}")
    print(f"Escrito em: {args.outdir}")


if __name__ == "__main__":
    main()
