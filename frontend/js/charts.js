const Charts = {
  feedbackChart: null,
  monitoringChart: null,
  evolutionChart: null,
  evolutionMetric: "pd",

  initFeedbackChart() {
    const ctx = document.getElementById("feedbackChart");
    this.feedbackChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          { label: "Desempenho (acurácia)", data: [], borderColor: "#4FD1C5", backgroundColor: "rgba(79,209,197,0.08)", tension: 0.3, pointRadius: 0, yAxisID: "y" },
          { label: "Limite de decisão", data: [], borderColor: "#D4A24C", backgroundColor: "rgba(212,162,76,0.08)", tension: 0.3, pointRadius: 0, yAxisID: "y" },
          { label: "Mudança detectada", data: [], borderColor: "#F87171", backgroundColor: "rgba(248,113,113,0.08)", tension: 0.3, pointRadius: 0, yAxisID: "y" },
        ],
      },
      options: {
        responsive: true,
        animation: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { color: "#8B96A5", font: { size: 11 } } },
        },
        scales: {
          x: {
            title: { display: true, text: "Iteração (cada resultado real observado)", color: "#8B96A5", font: { size: 11 } },
            ticks: { color: "#5B6472", font: { size: 10 } }, grid: { color: "#1B212B" },
          },
          y: {
            title: { display: true, text: "Valor (0 a 1)", color: "#8B96A5", font: { size: 11 } },
            min: 0, max: 1, ticks: { color: "#5B6472", font: { size: 10 } }, grid: { color: "#1B212B" },
          },
        },
      },
    });
  },

  setFeedbackVisibleMetric(which) {
    if (!this.feedbackChart) return;
    const idx = { metric: 0, threshold: 1, drift: 2 };
    this.feedbackChart.data.datasets.forEach((ds, i) => {
      ds.hidden = which === "all" ? false : i !== idx[which];
    });
    this.feedbackChart.update("none");
  },

  pushFeedback(iteration, metric, threshold, drift) {
    if (!this.feedbackChart) return;
    const d = this.feedbackChart.data;
    d.labels.push(iteration);
    d.datasets[0].data.push(metric);
    d.datasets[1].data.push(threshold);
    d.datasets[2].data.push(drift);
    const maxPoints = 60;
    if (d.labels.length > maxPoints) {
      d.labels.shift();
      d.datasets.forEach((ds) => ds.data.shift());
    }
    this.feedbackChart.update("none");
    this.updateFeedbackInterpretation(metric, threshold, drift);
  },

  updateFeedbackInterpretation(metric, threshold, drift) {
    const el = document.getElementById("feedbackInterpretationText");
    if (!el) return;
    const GAMMA = 0.03; // mesmo valor de backend/config.py
    const metricPct = (metric * 100).toFixed(1);
    let msg;
    if (drift > GAMMA) {
      msg = `⚠️ Mudança de ${(drift * 100).toFixed(1)}% detectada (acima do limite de ${(GAMMA * 100).toFixed(0)}%). ` +
            `Na prática, o Agente de Aprendizado por Feedback fez duas coisas neste ciclo: (1) recalculou o ` +
            `limite de decisão com base na perda mais recente (Equação 6); (2) reforçou os pesos: ele olha para ` +
            `a decisão mais recente — se ela acertou o resultado real, aumenta o peso das variáveis que mais ` +
            `influenciaram aquela decisão (proporcional à contribuição de cada uma); se errou, diminui o peso ` +
            `dessas mesmas variáveis na mesma proporção. Por exemplo: se "Endividamento" foi a variável mais ` +
            `influente numa decisão que acertou o resultado, o peso de "Endividamento" sobe um pouco — o modelo ` +
            `passa a confiar mais nela. Desempenho recente: ${metricPct}%.`;
    } else if (metric >= 0.6) {
      msg = `✅ Estável. Desempenho recente de ${metricPct}%, mudança dentro do esperado (abaixo de ${(GAMMA * 100).toFixed(0)}%). ` +
            `Nenhum reajuste de peso foi necessário neste ciclo — o sistema só reforça pesos quando a mudança ` +
            `ultrapassa o limite γ; abaixo disso, ele considera que é apenas ruído normal, não uma mudança real de regime.`;
    } else {
      msg = `🟡 Desempenho recente de ${metricPct}% — abaixo do ideal, mas sem um salto abrupto ainda (mudança ` +
            `dentro do limite γ). Se cair mais rápido, o sistema reage automaticamente no próximo ciclo assim: ` +
            `identifica quais variáveis mais pesaram na decisão (maior |∂PD/∂Fi|) e ajusta o peso delas para cima ` +
            `ou para baixo, na mesma direção para todas, dependendo se a decisão acertou ou errou o resultado real ` +
            `— um ajuste pequeno e incremental (5% por ciclo), não um retreinamento completo do modelo.`;
    }
    el.textContent = msg;
  },

  initEvolutionChart() {
    const ctx = document.getElementById("evolutionChart");
    if (!ctx || typeof Chart === "undefined") return;
    this.evolutionChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          { label: "PD média da carteira", data: [], borderColor: "#4FD1C5", backgroundColor: "rgba(79,209,197,0.08)", tension: 0.3, pointRadius: 0, borderWidth: 2 },
        ],
      },
      options: {
        responsive: true,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { title: { display: true, text: "Operações processadas", color: "#8B96A5", font: { size: 11 } },
               ticks: { color: "#5B6472", font: { size: 10 }, maxTicksLimit: 10 }, grid: { color: "#1B212B" } },
          y: { title: { display: true, text: "PD média", color: "#8B96A5", font: { size: 11 } },
               min: 0, ticks: { color: "#5B6472", font: { size: 10 } }, grid: { color: "#1B212B" } },
        },
      },
    });
  },

  setEvolutionMetric(metric) {
    this.evolutionMetric = metric;
    this.redrawEvolution();
  },

  redrawEvolution() {
    if (!this.evolutionChart) return;
    const history = Portfolio.riskHistory.slice(-80);
    const label = { pd: "PD média da carteira", count: "Operações de alto risco", exposure: "Exposição em alto risco (R$)" }[this.evolutionMetric];
    const field = { pd: "pdAvg", count: "highRiskCount", exposure: "highRiskExposure" }[this.evolutionMetric];
    this.evolutionChart.data.labels = history.map((h) => h.iteration);
    this.evolutionChart.data.datasets[0].label = label;
    this.evolutionChart.data.datasets[0].data = history.map((h) => h[field]);
    this.evolutionChart.options.scales.y.title.text = label;
    this.evolutionChart.options.scales.y.max = this.evolutionMetric === "pd" ? 1 : undefined;
    this.evolutionChart.update("none");
  },

  initMonitoringChart(series) {
    const ctx = document.getElementById("monitoringChart");
    if (!ctx || typeof Chart === "undefined") return;
    const labels = series.map((s) => s.month);
    const firstForecastIdx = series.findIndex((s) => s.is_forecast);
    // segmentacao: linha solida no historico, tracejada na projecao (Chart.js segment styling)
    const dashSegment = (ctx2) => (ctx2.p0DataIndex >= firstForecastIdx - 1 ? [5, 4] : undefined);

    this.monitoringChart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "PD médio previsto", data: series.map((s) => s.predicted_pd_avg),
            borderColor: "#4FD1C5", backgroundColor: "rgba(79,209,197,0.08)", tension: 0.25, pointRadius: 0, borderWidth: 2,
            segment: firstForecastIdx >= 0 ? { borderDash: dashSegment } : undefined,
          },
          {
            label: "Inadimplência real observada", data: series.map((s) => s.actual_default_rate),
            borderColor: "#F87171", backgroundColor: "rgba(248,113,113,0.08)", tension: 0.25, pointRadius: 0, borderWidth: 2,
            spanGaps: false,
          },
        ],
      },
      options: {
        responsive: true,
        animation: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { color: "#8B96A5", font: { size: 11 } } },
          annotation: undefined,
        },
        scales: {
          x: {
            title: { display: true, text: "Mês de vencimento do contrato", color: "#8B96A5", font: { size: 11 } },
            ticks: { color: "#5B6472", font: { size: 9 }, maxRotation: 60, minRotation: 60, autoSkip: true, maxTicksLimit: 24 },
            grid: { display: false },
          },
          y: {
            title: { display: true, text: "Taxa (0 a 1)", color: "#8B96A5", font: { size: 11 } },
            min: 0, ticks: { color: "#5B6472", font: { size: 10 } }, grid: { color: "#1B212B" },
          },
        },
      },
    });
    this.updateMonitoringInterpretation(series);
  },

  updateMonitoringInterpretation(series) {
    const el = document.getElementById("monitoringInterpretationText");
    if (!el || !series.length) return;
    const historical = series.filter((s) => !s.is_forecast);
    const forecastCount = series.length - historical.length;
    if (!historical.length) { el.textContent = "Sem dados históricos suficientes ainda."; return; }

    const recent = historical.slice(-6);
    const avgPred = recent.reduce((a, s) => a + s.predicted_pd_avg, 0) / recent.length;
    const avgActual = recent.reduce((a, s) => a + s.actual_default_rate, 0) / recent.length;
    const gap = avgActual - avgPred;
    let msg;
    if (Math.abs(gap) < 0.03) {
      msg = `Nos últimos 6 meses com dados reais, o modelo está bem calibrado: PD médio previsto ${(avgPred * 100).toFixed(1)}% ` +
            `vs. inadimplência real ${(avgActual * 100).toFixed(1)}%. Nenhuma ação adicional recomendada.`;
    } else if (gap > 0) {
      msg = `⚠️ Atenção: nos últimos 6 meses a inadimplência real (${(avgActual * 100).toFixed(1)}%) veio ` +
            `${(gap * 100).toFixed(1)} p.p. ACIMA do que o modelo previa (${(avgPred * 100).toFixed(1)}%) — o modelo está ` +
            `subestimando o risco recente. Recomenda-se ao time de carteira revisar os contratos mais recentes ` +
            `e considerar antecipar contatos de renegociação.`;
    } else {
      msg = `O modelo está superestimando o risco: previu ${(avgPred * 100).toFixed(1)}% de PD médio, mas a ` +
            `inadimplência real ficou em ${(avgActual * 100).toFixed(1)}% nos últimos 6 meses. Isso pode indicar ` +
            `espaço para aprovar um pouco mais sem aumentar a perda esperada.`;
    }
    if (forecastCount > 0) {
      msg += ` A linha tracejada dos próximos ${forecastCount} meses é uma PROJEÇÃO (ajuste linear simples sobre ` +
             `o histórico) — ainda não sabemos a inadimplência real desses meses, por isso não há linha vermelha ali.`;
    }
    el.textContent = msg;
  },

  opEvolutionChart: null,

  renderOperationEvolution(history) {
    const canvas = document.getElementById("opEvolutionChart");
    const emptyMsg = document.getElementById("opEvolutionEmpty");
    if (!canvas || typeof Chart === "undefined") return;

    if (!history || history.length < 2) {
      canvas.classList.add("hidden");
      if (emptyMsg) emptyMsg.classList.remove("hidden");
      return;
    }
    canvas.classList.remove("hidden");
    if (emptyMsg) emptyMsg.classList.add("hidden");

    const labels = history.map((h, i) => `Obs. ${i + 1}`);
    const pdData = history.map((h) => h.pd);
    const thresholdData = history.map((h) => h.threshold);

    if (this.opEvolutionChart) {
      this.opEvolutionChart.data.labels = labels;
      this.opEvolutionChart.data.datasets[0].data = pdData;
      this.opEvolutionChart.data.datasets[1].data = thresholdData;
      this.opEvolutionChart.update("none");
      return;
    }
    this.opEvolutionChart = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "PD", data: pdData, borderColor: "#4FD1C5", backgroundColor: "rgba(79,209,197,0.08)", tension: 0.25, pointRadius: 3, borderWidth: 2 },
          { label: "Limite de decisão", data: thresholdData, borderColor: "#D4A24C", backgroundColor: "transparent", borderDash: [4, 4], tension: 0.1, pointRadius: 0, borderWidth: 1.5 },
        ],
      },
      options: {
        responsive: true,
        animation: false,
        plugins: { legend: { labels: { color: "#8B96A5", font: { size: 10 } } } },
        scales: {
          x: { ticks: { color: "#5B6472", font: { size: 9 } }, grid: { display: false } },
          y: { min: 0, max: 1, ticks: { color: "#5B6472", font: { size: 10 } }, grid: { color: "#1B212B" } },
        },
      },
    });
  },
};
