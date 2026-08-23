# Fidelidade científica — classificação de cada componente

Conforme exigido na seção 63 do PLANO.md, cada elemento é classificado como:

- **ARTICLE-SPECIFIED** — fórmula ou conceito citado explicitamente no artigo (Kubam, 2024).
- **IMPLEMENTATION CHOICE** — decisão de engenharia necessária para tornar o artigo executável, não publicada no texto original.
- **BRAZILIAN/AGRO DOMAIN ADAPTATION** — mudança de domínio (dados/rótulos), sem alterar a arquitetura.

| Componente | Classificação | Nota |
|---|---|---|
| Xnorm = (X−μ)/σ (Eq. 1) | ARTICLE-SPECIFIED | `backend/features/normalizer.py` |
| Wt = Wt-1 + Δt (Eq. 2) | ARTICLE-SPECIFIED | `backend/agents/data_acquisition_agent.py` |
| Fi' = wi·Fi (Eq. 3) | ARTICLE-SPECIFIED | `backend/features/adaptive_weights.py` |
| S = Σαi·Fi² (Eq. 4) | ARTICLE-SPECIFIED | `backend/features/nonlinear_fusion.py` |
| PD = sigmoid(σ0+βx) (Eq. 5) | ARTICLE-SPECIFIED | `backend/risk/pd_model.py` |
| τt = τt-1+η(Losst−Losst-1) (Eq. 6) | ARTICLE-SPECIFIED (fórmula) / τ0 e η são IMPLEMENTATION CHOICE | `backend/risk/threshold.py`, `backend/config.py` |
| D = \|Mt−Mt-1\| (Eq. 7) | ARTICLE-SPECIFIED (fórmula) / métrica M = accuracy é IMPLEMENTATION CHOICE | `backend/risk/drift.py`, `backend/risk/metrics.py` |
| Ai = ∂PD/∂Fi (Eq. 8) | ARTICLE-SPECIFIED | `backend/risk/pd_model.py::attribution` |
| C = 1 − Var(PD) (Eq. 9) | ARTICLE-SPECIFIED (fórmula) / estratégia Monte Carlo para gerar Var(PD) é IMPLEMENTATION CHOICE | `backend/agents/explainability_agent.py` |
| Decision (Eq. 10) | ARTICLE-SPECIFIED | `backend/agents/decision_agent.py` |
| Política de RL para ajuste de wi | IMPLEMENTATION CHOICE (o artigo afirma mas não publica a fórmula) | `backend/feedback/reinforcement.py` |
| Regressão logística como núcleo de PD (não LightGBM) | ARTICLE-SPECIFIED (decisão explícita da réplica estrita) | `backend/risk/pd_model.py` |
| Variáveis brasileiras/agropecuárias (SELIC, chuva, safra etc.) | BRAZILIAN/AGRO DOMAIN ADAPTATION | `scripts/generate_synthetic_data.py` |
| Dataset sintético (seed 42) | BRAZILIAN/AGRO DOMAIN ADAPTATION | `data/synthetic/` |
| Mapa do Brasil | BRAZILIAN/AGRO DOMAIN ADAPTATION | `frontend/js/map.js` |
| Resultados 94,2%/91,5%/92,3% etc. | Citação do artigo, nunca resultado da MVP | `GET /api/experiments` |
| Persistência do estado adaptativo em disco (JSON) | IMPLEMENTATION CHOICE (artigo não especifica mecanismo de persistência) | `backend/state/persistence.py` |
| Hook de LLM (OpenAI) para resumo em linguagem natural | IMPLEMENTATION CHOICE, explicitamente opcional (seção 39: núcleo não depende de LLM) | `backend/llm/narrative_agent.py` |
| Split temporal treino/teste do experimento comparativo (2025-01-01) | IMPLEMENTATION CHOICE | `scripts/run_experiment_comparison.py` |
| Sinal invertido do threshold dinâmico (`conservative_threshold_sign=True`) | **EXTENSION** — explicitamente NÃO é a Eq. 6 do artigo, ver `docs/experiments.md` | `scripts/run_experiment_comparison.py` |

## Componentes explicitamente fora do núcleo (conforme seção 1 do PLANO.md)

Contraditório Agent, Counterfactual Agent, FarmScore, HHI, Policy Engine, RAG central, Champion/Challenger,
comitê humano obrigatório, agentes independentes de clima/commodity/satélite — nenhum foi incorporado ao
fluxo principal desta réplica.
