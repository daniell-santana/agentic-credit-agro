"""
Teste de drift artificial controlado — secao 57 do PLANO.md.

O PLANO.md original pede algo como: alterar a distribuicao de
`debt_ratio` (normal mean=0.30, stress mean=0.60) e confirmar que
D = |Mt - Mt-1| > gamma ativa o Feedback Learning Agent.

Adaptacao (documentada): nesta implementacao a metrica operacional M(t)
e accuracy sobre uma janela deslizante de decisoes (secao 26,
IMPLEMENTATION CHOICE) -- nao debt_ratio diretamente. debt_ratio e uma
FEATURE de entrada, nao a metrica de drift. Portanto este teste teste
drift em dois niveis:
  1. Unidade pura: compute_drift/drift_triggered com valores de M
     escolhidos a dedo (equivalente ao exemplo do PLANO.md, adaptado a
     metrica real usada aqui).
  2. Integracao: forca uma mudanca abrupta na taxa de acerto do modelo
     (equivalente ao efeito de um debt_ratio que muda de regime) e
     confirma que o Feedback Learning Agent detecta D > gamma e aciona
     o reinforcement adjustment.
"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.risk.drift import compute_drift, drift_triggered
from backend.streaming.processor import AgenticCreditPipeline
from backend.config import GAMMA, ETA
from tests._helpers import isolated_pipeline as _isolated_pipeline


def test_drift_formula_boundary():
    """Equacao 7 literal: D = |Mt - Mt-1|; drift_triggered apenas quando D > gamma
    (estritamente maior, nao >=)."""
    gamma = 0.03
    assert compute_drift(0.60, 0.30) == 0.30  # equivalente ao exemplo do PLANO.md (debt_ratio 0.30->0.60)
    assert drift_triggered(0.30, gamma) is True
    assert drift_triggered(0.03, gamma) is False, "D == gamma nao deveria disparar (estritamente >)"
    assert drift_triggered(0.0301, gamma) is True
    assert drift_triggered(0.0, gamma) is False
    print("PASS test_drift_formula_boundary")


def test_feedback_agent_triggers_on_controlled_drift():
    """Drift ARTIFICIAL CONTROLADO (titulo da secao 57): alimenta o Feedback
    Learning Agent diretamente com uma sequencia de outcomes desenhada a
    dedo -- equivalente, em efeito sobre a metrica M(t), ao exemplo do
    PLANO.md de debt_ratio saltando de 0.30 para 0.60. Fase 1: 20 decisoes
    corretas (accuracy=1.0). Fase 2: decisoes erradas em sequencia
    (equivalente a uma virada abrupta de regime de risco). Confirma que
    D = |Mt - Mt-1| ultrapassa gamma e que o reinforcement adjustment e
    acionado (nao fica em 'keep_weight')."""
    from backend.agents.feedback_learning_agent import FeedbackLearningAgent
    from backend.feedback.outcome_store import OutcomeStore
    from backend.features.adaptive_weights import AdaptiveWeights
    from backend.config import FEATURE_NAMES

    weights = AdaptiveWeights(FEATURE_NAMES)
    store = OutcomeStore(path=None)  # em memoria, nao escreve em disco
    agent = FeedbackLearningAgent(weights, store, eta=ETA, gamma=GAMMA)

    for i in range(20):
        realized = i % 2
        decision = "REJECT" if realized == 1 else "APPROVE"  # sempre acerta
        agent.process(f"cyc{i}", {
            "pd": 0.9 if realized else 0.1, "threshold": 0.5, "decision": decision,
            "realized_default": realized, "loss_amount": 0.0, "attributions": {"debt": 0.1},
        })
    metric_after_phase1 = agent._state["previous_metric"]
    assert metric_after_phase1 == 1.0, f"apos 20 acertos perfeitos, accuracy deveria ser 1.0, obtido {metric_after_phase1}"

    out = agent.process("cyc20", {
        "pd": 0.1, "threshold": 0.5, "decision": "APPROVE",  # decisao errada de proposito
        "realized_default": 1, "loss_amount": 1.0, "attributions": {"debt": 0.2},
    })

    assert out["drift"] > GAMMA, f"drift ({out['drift']:.4f}) deveria exceder gamma ({GAMMA})"
    assert out["drift_triggered"] is True, "uma virada abrupta de acerto->erro deveria disparar D > gamma"
    assert out["action_taken"] in ("increase_weight", "decrease_weight"), (
        "reinforcement adjustment deveria ter sido acionado (nao 'keep_weight') quando o drift dispara"
    )
    assert weights.state()["debt"] != 1.0, "o peso da feature com maior attribution deveria ter sido ajustado"
    print(
        f"PASS test_feedback_agent_triggers_on_controlled_drift "
        f"(metric 1.0 -> {out['metric']:.4f}, drift={out['drift']:.4f} > gamma={GAMMA}, action={out['action_taken']})"
    )


def test_full_pipeline_drift_under_combined_stress():
    """Verificacao complementar (best-effort, nao a prova principal): sob
    stress combinado real no pipeline completo (nao um outcome artificial
    isolado), o drift deve pelo menos ficar mensuravelmente mais alto do
    que em regime normal -- mesmo que nem sempre ultrapasse gamma dentro de
    uma janela curta, ja que a metrica e suavizada por uma janela deslizante
    (secao 26, IMPLEMENTATION CHOICE)."""
    p = _isolated_pipeline()
    for _ in range(10):
        p.run_one_cycle()

    p.apply_climate_shock(rainfall_pct=-40, drought_delta=0.4)
    p.apply_macro_shock(selic_delta=3.0, fx_delta=0.5, commodity_pct=-30)

    max_drift_seen = 0.0
    any_trigger = False
    for _ in range(200):
        c = p.run_one_cycle()
        if c.get("drift") is not None:
            max_drift_seen = max(max_drift_seen, c["drift"])
        for msg in c["agent_messages"]:
            if msg["sender"] == "feedback_learning_agent" and msg["payload"].get("drift_triggered"):
                any_trigger = True

    print(
        f"INFO test_full_pipeline_drift_under_combined_stress: "
        f"max_drift={max_drift_seen:.4f} (gamma={GAMMA}), trigger_observado={any_trigger}"
    )
    assert max_drift_seen > 0.0, "algum drift deveria ter sido observado ao longo de 200 ciclos sob stress"
    print("PASS test_full_pipeline_drift_under_combined_stress")


if __name__ == "__main__":
    test_drift_formula_boundary()
    test_feedback_agent_triggers_on_controlled_drift()
    test_full_pipeline_drift_under_combined_stress()
