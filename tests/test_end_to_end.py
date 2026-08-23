"""Teste end-to-end (secao 53) e teste de adaptacao (secao 54) do PLANO.md."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tests._helpers import isolated_pipeline as _isolated_pipeline


def test_end_to_end_cycle():
    p = _isolated_pipeline()
    cycle = p.run_one_cycle()
    assert cycle["pd"] is not None
    assert cycle["threshold"] is not None
    assert cycle["decision"] in ("APPROVE", "REVIEW", "REJECT")
    assert "attributions" in cycle
    assert cycle["confidence"] is not None
    print("PASS test_end_to_end_cycle")


def test_adaptation_under_stress():
    p = _isolated_pipeline()
    for _ in range(100):
        p.run_one_cycle()
    threshold_before = p.risk_agent._state["threshold"]
    iteration_before = p.feedback_agent._state["iteration"]

    p.apply_climate_shock(rainfall_pct=-30, drought_delta=0.3)
    p.apply_macro_shock(selic_delta=2.0, fx_delta=0.3, commodity_pct=-20)

    drift_seen = False
    for _ in range(100):
        c = p.run_one_cycle()
        if c.get("drift") and c["drift"] > 0:
            drift_seen = True

    threshold_after = p.risk_agent._state["threshold"]
    iteration_after = p.feedback_agent._state["iteration"]

    assert iteration_after > iteration_before
    assert drift_seen, "drift deveria ter sido observado ao longo de 100 ciclos de stress"
    print(f"PASS test_adaptation_under_stress (threshold {threshold_before:.4f} -> {threshold_after:.4f})")


if __name__ == "__main__":
    test_end_to_end_cycle()
    test_adaptation_under_stress()
