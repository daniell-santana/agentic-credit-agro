"""
Hook opcional de LLM — secao 39 do PLANO.md.

O artigo NAO exige que os agentes sejam LLMs; o nucleo (Data Acquisition,
Feature Transformation, Risk Scoring, Explainability, Decision, Feedback
Learning) e 100% matematico/computacional e roda igual com ou sem este
modulo.

Este agente e estritamente um tradutor de saida-para-linguagem-natural:
recebe uma decisao JA CALCULADA (PD, threshold, confidence, attributions,
decision) e gera um resumo textual em portugues para apoiar o analista de
credito humano. Ele NUNCA recebe poder de alterar PD, threshold ou a
decisao final — isso violaria a auditabilidade do pipeline.

Classificacao: IMPLEMENTATION CHOICE (nao especificado pelo artigo).

Ativado apenas se a variavel de ambiente OPENAI_API_KEY estiver definida.
Sem a chave, is_enabled() retorna False e o endpoint correspondente
responde de forma graciosa (sem quebrar o pipeline principal).
"""
from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional

_MODEL = os.environ.get("OPENAI_NARRATIVE_MODEL", "gpt-4o-mini")

# Espelha frontend/js/agents.js:labelFeature() -- nomes em portugues para o
# LLM nunca precisar "traduzir" um nome de coluna tecnico (requested_amount)
# por conta propria, o que poderia gerar inconsistencia com o resto da UI.
FEATURE_LABELS = {
    "requested_amount": "valor solicitado", "term_months": "prazo em meses",
    "interest_rate": "taxa de juros", "collateral_value": "valor da garantia",
    "annual_revenue": "receita anual", "annual_cost": "custo anual",
    "equity": "patrimônio", "debt": "endividamento", "farm_size_ha": "área da propriedade",
    "years_farming": "anos de atividade", "rainfall": "índice de chuva", "temperature": "temperatura",
    "drought_index": "índice de seca", "crop_price": "preço das culturas",
    "selic": "taxa básica de juros (SELIC)", "inflation": "IPCA", "usd_brl": "câmbio USD/BRL",
    "commodity_index": "índice de commodities",
}
DECISION_LABELS_PT = {"APPROVE": "aprovada", "REVIEW": "colocada em análise", "REJECT": "rejeitada"}


def is_enabled() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _top_attributions(attributions: Any, k: int = 5) -> List[Dict[str, Any]]:
    """cycle['attributions'] e um dict {feature: Ai} (ver explainability_agent.py)."""
    if isinstance(attributions, dict):
        items = sorted(attributions.items(), key=lambda kv: abs(kv[1]), reverse=True)[:k]
        return [{"feature": FEATURE_LABELS.get(f, f), "attribution": round(a, 4)} for f, a in items]
    if isinstance(attributions, list):
        return sorted(attributions, key=lambda a: abs(a.get("attribution", 0.0)), reverse=True)[:k]
    return []


def summarize_decision(cycle: Dict[str, Any]) -> Optional[str]:
    """
    Gera um resumo textual de uma decisao ja tomada pelo pipeline, e,
    quando o caso pede (PD subiu, ou PD esta alto/perto do limite),
    ACRESCENTA uma recomendacao pratica de proxima acao — na perspectiva
    de um analista de credito/gerente de carteira (renegociar, pedir
    garantia adicional, aumentar frequencia de acompanhamento etc.).

    A prescricao e sempre uma SUGESTAO em linguagem natural para o humano
    decidir — nunca uma acao executada automaticamente, e nunca altera
    PD/threshold/decisao (regra 2 do plano: o frontend/LLM nunca inventa
    nem altera a decisao real).

    Retorna None se o hook estiver desabilitado (sem OPENAI_API_KEY) ou se
    a biblioteca `openai` nao estiver instalada.
    """
    if not is_enabled():
        return None
    try:
        from openai import OpenAI  # import tardio: dependencia opcional
    except ImportError:
        return "[LLM indisponivel: pacote 'openai' nao instalado. Rode: pip install openai]"

    top = _top_attributions(cycle.get("attributions"))
    positivos = [t["feature"] for t in top if t["attribution"] > 0]
    negativos = [t["feature"] for t in top if t["attribution"] < 0]
    pd = cycle.get("pd") or 0.0
    threshold = cycle.get("threshold") or 0.5
    pd_pct = round(pd * 100, 2)
    threshold_pct = round(threshold * 100, 2)
    confidence_pct = round((cycle.get("confidence") or 0) * 100, 3)
    decisao_pt = DECISION_LABELS_PT.get(cycle.get("decision"), cycle.get("decision"))

    pd_anterior = cycle.get("pd_anterior")
    delta = cycle.get("delta")

    # Mesmo sistema de faixas usado em Portfolio.riskBand() no frontend
    # (frontend/js/portfolio.js): baixo = PD < 60% do limite; medio = ate
    # o limite; alto = acima do limite. A primeira versao deste gatilho so
    # cobria "ate 5 p.p. do limite", que excluia faixas medias legitimas
    # (ex.: PD 40% com limite 55% ja e risco "medio", nao "baixo") --
    # corrigido para cobrir toda a faixa media/alta, nao so a borda.
    faixa_baixo_limite = threshold * 0.6
    DELTA_RELEVANTE = 0.05  # mesmo limiar de Portfolio.DELTA_THRESHOLD no frontend
    precisa_prescricao = (
        (delta is not None and delta >= DELTA_RELEVANTE)  # tendencia de piora relevante
        or pd >= faixa_baixo_limite  # ja esta na faixa media ou alta (nao mais "baixo risco")
    )

    contexto_tendencia = ""
    if pd_anterior is not None and delta is not None:
        contexto_tendencia = (
            f"PD anterior (observação passada do mesmo produtor): {round(pd_anterior * 100, 2)}%\n"
            f"Variação desde a última observação: {'+' if delta >= 0 else ''}{round(delta * 100, 2)} p.p.\n"
        )

    if precisa_prescricao:
        motivo = []
        if delta is not None and delta >= DELTA_RELEVANTE:
            motivo.append("tendência de piora relevante (PD subiu 5 p.p. ou mais)")
        if pd >= threshold:
            motivo.append("PD já está ACIMA do limite de decisão")
        elif pd >= faixa_baixo_limite:
            motivo.append("PD está em faixa de risco média/alta, mesmo abaixo do limite")
        instrucao_prescricao = (
            f"\nEste caso PRECISA de uma recomendação prática — motivo: {'; '.join(motivo)}. "
            "Termine sua resposta com uma linha começando exatamente por \"Recomendação:\" seguida "
            "de 1 a 3 ações concretas, na perspectiva de um analista de crédito / gerente de "
            "carteira, pensando em ANTECIPAR uma possível inadimplência futura — não apenas descrever "
            "o caso. Adapte a ação à gravidade: se o PD subiu mas ainda está bem abaixo do limite, "
            "sugira contato preventivo com o produtor e aumento da frequência de acompanhamento; se "
            "está em faixa média/alta ou perto do limite, sugira ações mais concretas e específicas "
            "(ex.: renegociar prazo ou taxa, solicitar garantia adicional, revisar o limite de crédito "
            "da linha, agendar reavaliação presencial, condicionar novo desembolso a comprovação de "
            "safra). Cite pelo menos um fator específico desta decisão (dos fatores que aumentam o "
            "risco) para justificar a ação. NÃO decida por conta própria — deixe claro que é uma "
            "sugestão para o analista avaliar.\n"
        )
    else:
        instrucao_prescricao = (
            "\nEste caso está estável (risco baixo e sem aumento relevante) — NÃO acrescente "
            "recomendação de ação, apenas a descrição objetiva.\n"
        )

    prompt = (
        "Voce e um assistente que resume, em portugues do Brasil, uma decisao de credito "
        "agropecuario JA TOMADA por um pipeline matematico (regressao logistica + atribuicao "
        "por derivada parcial). NAO sugira mudar a decisao JA TOMADA, NAO invente numeros novos "
        "— use apenas os fornecidos. Siga o estilo objetivo do exemplo abaixo para a parte "
        "descritiva (decisao, PD, threshold, confianca, fatores).\n\n"
        "Exemplo de estilo esperado (parte descritiva):\n"
        "\"A decisão de crédito para o produtor PRD000305 e a aplicação APP0000775 foi "
        "rejeitada, com uma probabilidade de default de 50,08%, acima do threshold dinâmico "
        "de 50%. A previsão apresentou confiança de 99,999%. O índice de seca e o preço das "
        "culturas contribuíram para aumentar a probabilidade de inadimplência, elevando o "
        "risco do crédito. Por outro lado, o valor da garantia e o índice de commodities "
        "tiveram contribuições negativas para a PD, ajudando a reduzir o risco estimado.\"\n"
        f"{instrucao_prescricao}\n"
        "Dados reais desta decisão:\n"
        f"Produtor: {cycle.get('producer_id')}\n"
        f"Aplicação: {cycle.get('application_id')}\n"
        f"Decisão: {decisao_pt}\n"
        f"Probabilidade de default (PD) atual: {pd_pct}%\n"
        f"{contexto_tendencia}"
        f"Threshold dinâmico: {threshold_pct}%\n"
        f"Confiança: {confidence_pct}%\n"
        f"Fatores que mais AUMENTAM o risco (atribuição positiva, em ordem de importância): {positivos}\n"
        f"Fatores que mais REDUZEM o risco (atribuição negativa, em ordem de importância): {negativos}\n"
    )
    try:
        client = OpenAI()
        resp = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=380,
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:  # nunca derruba a API principal por falha do LLM
        return f"[LLM indisponivel no momento: {e}]"


def summarize_portfolio(chart_name: str, stats: Dict[str, Any]) -> Optional[str]:
    """
    Resume, em linguagem natural, um agregado JA CALCULADO no cliente
    (distribuicao de risco, evolucao da carteira, ou risco por estado no
    mapa) — nunca recebe dados brutos nem recalcula nada, apenas traduz
    numeros ja prontos em um paragrafo interpretativo. Mesmo isolamento de
    responsabilidade de summarize_decision() acima.
    """
    if not is_enabled():
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return "[LLM indisponivel: pacote 'openai' nao instalado. Rode: pip install openai]"

    prompt = (
        "Voce e um assistente que resume, em portugues do Brasil, no maximo 4 frases, "
        "um grafico ou painel de gestao de carteira de credito agropecuario. "
        "Os dados sao SINTETICOS (simulacao). NAO invente numeros — use apenas os fornecidos. "
        "Seja direto e pratico, como se estivesse explicando para um gestor de carteira "
        "que nao tem tempo de interpretar o grafico sozinho.\n\n"
        f"Grafico: {chart_name}\n"
        f"Dados: {json.dumps(stats, ensure_ascii=False)}\n"
    )
    try:
        client = OpenAI()
        resp = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=220,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[LLM indisponivel no momento: {e}]"
