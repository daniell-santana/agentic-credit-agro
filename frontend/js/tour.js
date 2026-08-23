/**
 * Tour guiado passo a passo — substitui o antigo modal estático de
 * "Como usar". Percorre as 3 abas, destacando cada seção/gráfico com uma
 * explicação curta e controles Próximo/Anterior/Pular.
 *
 * Classificacao: IMPLEMENTATION CHOICE / EXTENSAO DE UX — nao especificado
 * pelo artigo. Vanilla JS, sem dependencia nova (mesma filosofia de
 * vendorizar so o essencial).
 */
const TOUR_STEPS = [
  { tab: "carteira", selector: "#introCards", title: "Bem-vindo a Gestão Preditiva da Carteira de Crédito FarmTech",
    text: "Este painel simula uma gestão de carteira de crédito agropecuário em tempo real, com 3 abas: Visão da Carteira, Operações e Aprendizado do Sistema. Vamos percorrer os principais pontos de cada uma." },
  { tab: "carteira", selector: "#kpiRowCarteira", title: "Indicadores de negócio",
    text: "Operações, valor total, PD média da carteira, quantas estão em alto risco, quantas aumentaram de risco e quantas exigem análise — tudo atualizado em tempo real conforme a simulação roda." },
  { tab: "carteira", selector: "#riskDistribution", title: "Distribuição do risco",
    text: "Proporção da carteira em cada faixa: baixo, intermediário e alto risco. O botão \"Explicar com IA\" ao lado resume esse gráfico em um parágrafo." },
  { tab: "carteira", selector: "#evolutionChart", title: "Evolução do risco",
    text: "Acompanhe PD média, operações de alto risco, ou exposição em alto risco ao longo do tempo — use os botões acima do gráfico para alternar a métrica." },
  { tab: "carteira", selector: "#regionChangesBody", title: "O que mudou?",
    text: "Os produtores com maior variação de PD entre a observação atual e a anterior. Clique numa linha para abrir o detalhe completo daquela operação." },
  { tab: "carteira", selector: "#mapBrazil", title: "Mapa de risco por estado",
    text: "Cada estado é colorido pelo risco médio relativo — quanto mais vermelho, maior o risco em comparação aos outros estados com dados." },
  { tab: "carteira", selector: "#attentionList", title: "Atenção agora",
    text: "Resumo do que precisa de ação agora. O botão \"Ver operações\" leva direto para a Aba 2 já filtrada pelo que exige análise." },

  { tab: "operacoes", selector: ".ops-filters", title: "Filtrar operações",
    text: "Busque por produtor ou código, ou filtre por estado, situação e faixa de risco — todos os filtros combinam entre si." },
  { tab: "operacoes", selector: "#operationsBody", title: "Tabela de operações",
    text: "Clique em qualquer linha para abrir o detalhe: PD atual e anterior, variação, limite de decisão, confiança, evolução individual e os fatores que mais pesaram na decisão." },
  { tab: "operacoes", selector: ".stress-panel", title: "Simular cenário (\"e se?\")",
    text: "Escolha um preset ou ajuste os campos e clique em \"Simular impacto\": o sistema recalcula o PD das operações recentes sob esse cenário hipotético e mostra uma tabela comparando PD atual vs. simulado — sem alterar nada de verdade na carteira." },

  { tab: "aprendizado", selector: "#kpiRowTecnico", title: "Indicadores técnicos",
    text: "Acurácia, limite de decisão, mudança detectada, iteração e latência — a visão técnica do que está acontecendo por trás das decisões." },
  { tab: "aprendizado", selector: "#driftStatusPanel", title: "Mudança no comportamento",
    text: "Um selo simples (Estável / Ajuste acionado) mostra se o sistema acabou de se recalibrar por causa de uma mudança relevante no desempenho." },
  { tab: "aprendizado", selector: "#featureImportanceList", title: "Importância das variáveis",
    text: "Quais variáveis mais influenciam o PD em média, nas últimas operações — acompanhar essa ordem ao longo do tempo ajuda a perceber se o comportamento das variáveis está mudando." },
  { tab: "aprendizado", selector: "#pipelineFlow", title: "Fluxo dos agentes",
    text: "Os 6 agentes do artigo original. Passe o mouse sobre qualquer um para ver exatamente o que ele faz e qual equação usa." },
  { tab: "aprendizado", selector: ".feedback-panel", title: "Aprendizado ao longo das iterações",
    text: "Como acurácia, limite de decisão e mudança detectada evoluem. O card de interpretação abaixo explica, com exemplo, como o sistema reage quando detecta uma mudança relevante." },
  { tab: "aprendizado", selector: ".monitoring-panel", title: "Previsto vs. Realizado",
    text: "Linha sólida = histórico (previsto e real, já aconteceram). Linha tracejada = projeção do PD médio futuro — sem \"realizado\", porque isso ainda não aconteceu." },
  { tab: "aprendizado", selector: "#streamLog", title: "Eventos em tempo real",
    text: "O log técnico de tudo que passa pelo pipeline — solicitações, pagamentos, inadimplências e choques de cenário, com timestamp." },
];

const Tour = {
  idx: 0,
  active: false,

  start() {
    this.idx = 0;
    this.active = true;
    document.body.classList.add("tour-active");
    this._showStep();
  },

  end() {
    this.active = false;
    document.body.classList.remove("tour-active");
    document.querySelectorAll(".tour-highlight, .tour-tooltip").forEach((el) => el.remove());
  },

  next() {
    if (this.idx < TOUR_STEPS.length - 1) { this.idx++; this._showStep(); }
    else this.end();
  },

  prev() {
    if (this.idx > 0) { this.idx--; this._showStep(); }
  },

  _showStep() {
    document.querySelectorAll(".tour-highlight, .tour-tooltip").forEach((el) => el.remove());
    const step = TOUR_STEPS[this.idx];
    if (step.tab) switchTab(step.tab);

    requestAnimationFrame(() => {
      const el = document.querySelector(step.selector);
      if (!el) { this.next(); return; }
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      setTimeout(() => this._renderOverlay(el, step), 280);
    });
  },

  _renderOverlay(el, step) {
    const rect = el.getBoundingClientRect();
    const pad = 8;

    const highlight = document.createElement("div");
    highlight.className = "tour-highlight";
    highlight.style.top = `${rect.top - pad}px`;
    highlight.style.left = `${rect.left - pad}px`;
    highlight.style.width = `${rect.width + pad * 2}px`;
    highlight.style.height = `${rect.height + pad * 2}px`;
    document.body.appendChild(highlight);

    const tooltip = document.createElement("div");
    tooltip.className = "tour-tooltip";
    const isLast = this.idx === TOUR_STEPS.length - 1;
    tooltip.innerHTML = `
      <div class="tour-step-count">Passo ${this.idx + 1} de ${TOUR_STEPS.length}</div>
      <h4>${step.title}</h4>
      <p>${step.text}</p>
      <div class="tour-controls">
        <button class="btn btn-ghost btn-small" id="tourSkip">Pular tour</button>
        <div class="tour-nav">
          ${this.idx > 0 ? '<button class="btn btn-ghost btn-small" id="tourPrev">← Anterior</button>' : ""}
          <button class="btn btn-primary btn-small" id="tourNext">${isLast ? "Concluir" : "Próximo →"}</button>
        </div>
      </div>
    `;
    document.body.appendChild(tooltip);

    // posiciona abaixo do elemento; se nao couber, posiciona acima
    const spaceBelow = window.innerHeight - rect.bottom;
    const tooltipHeight = tooltip.offsetHeight;
    let top;
    if (spaceBelow > tooltipHeight + 24) {
      top = rect.bottom + pad + 12;
    } else if (rect.top - tooltipHeight - 24 > 0) {
      top = rect.top - tooltipHeight - pad - 12;
    } else {
      top = Math.max(12, window.innerHeight / 2 - tooltipHeight / 2);
    }
    let left = Math.min(Math.max(12, rect.left), window.innerWidth - tooltip.offsetWidth - 12);
    tooltip.style.top = `${top}px`;
    tooltip.style.left = `${left}px`;

    document.getElementById("tourNext").addEventListener("click", () => this.next());
    document.getElementById("tourSkip").addEventListener("click", () => this.end());
    const prevBtn = document.getElementById("tourPrev");
    if (prevBtn) prevBtn.addEventListener("click", () => this.prev());
  },
};

document.addEventListener("keydown", (e) => {
  if (!Tour.active) return;
  if (e.key === "Escape") Tour.end();
  if (e.key === "ArrowRight") Tour.next();
  if (e.key === "ArrowLeft") Tour.prev();
});
