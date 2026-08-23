# Experimento comparativo — Conventional ML vs Agentic vs Agentic + Feedback

Seções 44–46 do PLANO.md. Reproduzível via:

```bash
python scripts/run_experiment_comparison.py
```

Gera `experiments/results.json`, também servido em `GET /api/experiments` →
`mvp_comparison_experiment`.

## Metodologia

- **Split temporal**: treino = aplicações com `application_date < 2025-01-01`
  (1251 aplicações, regime majoritariamente normal); teste = `>= 2025-01-01`
  (783 aplicações, cobrindo os regimes `stress_macro` e `stress_combinado`
  definidos em `scripts/generate_synthetic_data.py`). Isso é **decisão de
  implementação** — o artigo não define um split; o PLANO.md seção 7 apenas
  sugere a existência de períodos de treino/validação/simulação/feedback.
- **Conventional ML** (seção 44): `Normalizer` + `LogisticPDModel` treinados
  uma única vez no treino (gradient descent determinístico, seed=42, sem
  scikit-learn). Threshold fixo em 0.5. Decisão binária (sem REVIEW, sem
  pesos adaptativos, sem streaming, sem feedback, sem Explainability/Decision
  Agent) — literal à seção 44.
- **Agentic sem feedback** (seção 45): mesmo modelo treinado, envolto pelos
  agentes (pesos adaptativos, fusão não linear, Explainability Agent,
  Decision Agent 3 vias), mas sem o Feedback Learning Agent.
- **Agentic + feedback** (seção 46): pipeline completo processando o
  conjunto de teste sequencialmente, com o Feedback Learning Agent ativo a
  cada ciclo (drift via Eq. 7, reinforcement dos pesos quando `D > γ`,
  threshold dinâmico via Eq. 6).

## Resultado 1 — `agentic_no_feedback` ≈ `conventional_ml`

As métricas dos dois são **idênticas**. Isso é esperado e intencional: os
pesos adaptativos começam em `w=1.0` e, sem feedback, nunca mudam — logo
`Fi' = 1.0 · Fi = Fi`, o fusion score não altera a entrada do modelo, e o
threshold permanece fixo em `τ0 = 0.5`, igual ao baseline. **Achado
honesto**: o "wrapper agêntico" por si só (ter agentes, explicabilidade,
decisão em 3 vias) não gera nenhum ganho preditivo. Qualquer vantagem real
tem que vir do loop de feedback — não da arquitetura em si.

## Resultado 2 — `agentic_with_feedback` (Eq. 6 literal) fica PIOR que o baseline

| Métrica | Conventional ML | Agentic + Feedback (Eq. 6 literal) |
|---|---|---|
| Accuracy | 0.5453 | 0.5172 |
| Recall | 0.2767 | 0.1772 |
| High-risk recall | 0.5064 | 0.3397 |

Isso se repete em **todos** os sub-períodos testados (2025 H1, 2025 H2,
2026 stress combinado) — não é ruído de agregação, é sistemático.

**Causa raiz identificada**: a Equação 6 do artigo, tomada ao pé da letra —

```
τt = τt-1 + η(Losst − Losst-1)
```

— faz o threshold **subir** (ficar mais permissivo, aprovando mais) logo
após um aumento de loss, em vez de ficar mais conservador. Isso é o oposto
do que se esperaria de um sistema de risco de crédito prudente: acabou de
tomar um prejuízo e o modelo relaxa o critério de aprovação. Os ajustes de
peso via reinforcement learning (seção 13) são marginais nesta configuração
(apenas 16 de 783 ciclos disparam `D > γ`, e o passo de ajuste é pequeno) —
não compensam o efeito do threshold.

Este é um **achado da réplica estrita ao artigo**, não um bug de
implementação: a Equação 6 é literal, o sinal de `η` é positivo por
convenção (taxa de aprendizado), e o resultado é matematicamente correto
dado o que o artigo publicou. O artigo em si não inclui uma implementação
de referência para validar essa dinâmica — apenas a fórmula em prosa.

## Resultado 3 — extensão (fora do artigo): sinal do threshold invertido

`agentic_with_feedback_EXTENSION_conservative_threshold_sign` no
`results.json` testa a hipótese óbvia: e se o threshold reagir na direção
economicamente esperada?

```
τt = τt-1 − η(Losst − Losst-1)     ← EXTENSÃO, não é a Eq. 6 do artigo
```

| Métrica | Conventional ML | Agentic + Feedback (extensão) |
|---|---|---|
| Accuracy | 0.5453 | **0.5683** (+2.3pp) |
| Precision | 0.6628 | 0.6468 (−1.6pp) |
| Recall | 0.2767 | **0.3956** (+11.9pp) |
| High-risk recall | 0.5064 | **0.6282** (+12.2pp) |
| False positive rate | 0.1563 | 0.2399 (+8.4pp) |

Com essa única mudança de sinal, o sistema agêntico **supera** o baseline
de forma consistente — ganha bastante em recall (detecta mais defaults
reais) e high-risk recall (o ponto central da tese do artigo — seção IV,
"superior... specifically in the freedom of identifying high-dangerous
actions"), com uma queda pequena de precisão e um aumento de falsos
positivos (trade-off esperado ao ficar mais conservador).

**Conclusão honesta**: a arquitetura agêntica (loop de feedback + detecção
de drift + reinforcement) tem o potencial estrutural correto para superar
um modelo estático — mas a fórmula de threshold publicada no artigo,
implementada literalmente, não entrega esse potencial neste dataset. A
extensão mostra que o potencial é real quando a direção do ajuste é
corrigida.

## Classificação (seção 63 do PLANO.md)

| Item | Classificação |
|---|---|
| Equações 1–10, decisão de 3 vias | ARTICLE-SPECIFIED |
| Split temporal, sample_cap, épocas do gradient descent | IMPLEMENTATION CHOICE |
| Sinal invertido do threshold (`conservative_threshold_sign`) | EXTENSION (explicitamente NÃO reivindicada como o artigo) |
| Dataset, join produtor↔aplicação, regimes de stress | BRAZILIAN/AGRO DOMAIN ADAPTATION |

## Limitações deste experimento

- Amostra de teste modesta (783 aplicações) — resultados têm variância
  considerável entre sub-períodos.
- O rótulo `realized_default` vem do gerador sintético (seção 4 do
  PLANO.md), não de um banco real — os números não devem ser lidos como
  evidência de desempenho em produção.
- `high_risk_recall` usa `true_default_probability` (rótulo latente do
  gerador) apenas para *definir a coorte* de alto risco na avaliação; nunca
  é usado para treinar o modelo.
- Uma única seed (42) e um único split — não há intervalo de confiança.
  Rodar com seeds diferentes é o próximo passo natural para validar a
  robustez do achado da seção anterior.
