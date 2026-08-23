# Arquitetura

Fluxo (idêntico ao Fig. 1 do artigo, seção 2 do PLANO.md):

```
Continuous Data Stream
   -> Data Acquisition Agent
   -> Normalization (Eq. 1)
   -> Streaming Window Wt (Eq. 2)
   -> Weighted Feature Synthesis (Eq. 3)
   -> Nonlinear Feature Fusion (Eq. 4)
   -> Risk Scoring Agent -> PD (Eq. 5)
   -> Dynamic Threshold τt (Eq. 6)
   -> Explainability Agent -> Attribution (Eq. 8) + Confidence (Eq. 9)
   -> Decision Agent (Eq. 10)
   -> Realized Loan Outcome
   -> Feedback Learning Agent -> Drift (Eq. 7) -> Reinforcement Adjustment
   -> novo ciclo
```

Cada agente implementa `input / processing / state / output` (`backend/agents/base_agent.py`)
e comunica-se via `AgentMessage` (`backend/models/contracts.py`), conforme seção 23 do PLANO.md.

O orquestrador (`backend/streaming/processor.py`) executa um ciclo completo por evento de
streaming, mantendo o estado adaptativo (pesos, threshold, normalização) entre ciclos.

## Limitações reconhecidas (seção 64 do PLANO.md)

Qualidade de dados em tempo real, demanda computacional, necessidade de monitoramento contínuo,
limitações de interpretabilidade em perfis complexos, diferenças regulatórias entre jurisdições, e
questões éticas de viés/equidade/autonomia responsável — todas herdadas do artigo original e
válidas também para esta réplica. Esta é uma demonstração arquitetural sobre dados sintéticos,
não um sistema de produção.
