"""Testes unitarios matematicos (secao 52 do PLANO.md)."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.features.normalizer import normalize_features
from backend.agents.data_acquisition_agent import update_window
from backend.features.adaptive_weights import weighted_feature
from backend.features.nonlinear_fusion import nonlinear_fusion
from backend.risk.pd_model import LogisticPDModel
from backend.risk.threshold import update_threshold
from backend.risk.drift import compute_drift, drift_triggered
from backend.agents.explainability_agent import confidence_from_variance
from backend.agents.decision_agent import decide


def test_normalization():
    assert normalize_features(10, mean=10, std=2) == 0.0
    assert normalize_features(12, mean=10, std=2) == 1.0
    assert normalize_features(8, mean=10, std=2) == -1.0


def test_stream_window():
    assert update_window(0.0, 1.0) == 1.0
    assert update_window(5.0, 1.0) == 6.0


def test_weighted_feature():
    assert weighted_feature(2.0, 3.0) == 6.0


def test_nonlinear_fusion():
    s = nonlinear_fusion({"a": 2.0, "b": 3.0}, {"a": 1.0, "b": 2.0})
    assert s == (1.0 * 4.0) + (2.0 * 9.0)


def test_pd():
    m = LogisticPDModel(["S"], sigma0=0.0, beta={"S": 1.0})
    assert abs(m.score(0.0) - 0.5) < 1e-9
    assert m.score(100) > 0.999
    assert m.score(-100) < 0.001


def test_dynamic_threshold():
    tau = update_threshold(previous_threshold=0.5, current_loss=0.6, previous_loss=0.4, eta=0.1)
    assert abs(tau - 0.52) < 1e-9


def test_drift():
    d = compute_drift(0.8, 0.75)
    assert abs(d - 0.05) < 1e-9
    assert drift_triggered(d, gamma=0.03) is True
    assert drift_triggered(d, gamma=0.1) is False


def test_attribution():
    m = LogisticPDModel(["x"], sigma0=0.0, beta={"x": 2.0})
    attr = m.attribution({"x": 0.0})
    # em x=0, PD=0.5, deriv = 0.5*0.5*beta = 0.25*2 = 0.5
    assert abs(attr["x"] - 0.5) < 1e-6


def test_confidence():
    assert confidence_from_variance(0.0) == 1.0
    assert confidence_from_variance(1.5) == 0.0
    assert abs(confidence_from_variance(0.2) - 0.8) < 1e-9


def test_decision():
    assert decide(pd=0.3, threshold=0.5) == "APPROVE"
    assert decide(pd=0.7, threshold=0.5) == "REJECT"
    assert decide(pd=0.5, threshold=0.5) == "REVIEW"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests)-failed}/{len(tests)} passaram")
    sys.exit(1 if failed else 0)
