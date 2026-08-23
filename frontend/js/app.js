let ws = null;
let streaming = false;
const GAMMA = 0.03; // mesmo valor de backend/config.py

const UF_LIST = ["MT", "GO", "PR", "RS", "SP", "MG", "BA", "MS", "TO", "PA"];

const opFilters = { search: "", state: "", situacao: "", risco: "" };

function setConn(on) {
  const dot = document.getElementById("connStatus");
  dot.className = `conn-dot ${on ? "conn-on" : "conn-off"}`;
  dot.setAttribute("aria-label", `Status da conexão: ${on ? "conectado" : "desconectado"}`);
}

/* ===== ABA 3 — indicadores tecnicos (status geral do stream) ===== */
function updateKpisTecnicos(status) {
  document.getElementById("kpiLimiteDecisao").textContent = fmtPct(status.current_threshold);
  document.getElementById("kpiIteracao").textContent = status.iteration ?? 0;
}

function updateKpisFromCycle(cycle) {
  if (cycle.metric !== null && cycle.metric !== undefined) {
    document.getElementById("kpiAcuracia").textContent = fmtPct(cycle.metric);
  }
  document.getElementById("kpiMudanca").textContent =
    cycle.drift !== null && cycle.drift !== undefined ? cycle.drift.toFixed(4) : "–";
  const lat = cycle.latencies_ms && cycle.latencies_ms.end_to_end;
  document.getElementById("kpiLatenciaTecnica").textContent = lat ? `${lat.toFixed(1)}` : "–";
  renderDriftStatus(cycle);
}

function renderDriftStatus(cycle) {
  const badge = document.getElementById("driftBadge");
  const drift = cycle.drift ?? 0;
  document.getElementById("driftMedida").textContent = drift.toFixed(4);
  document.getElementById("driftLimite").textContent = GAMMA.toFixed(2);
  if (drift > GAMMA) {
    badge.textContent = "⚠ Ajuste acionado";
    badge.className = "drift-badge drift-triggered";
    document.getElementById("driftIntensidade").textContent = drift > GAMMA * 2 ? "Alta" : "Moderada";
  } else {
    badge.textContent = "✅ Estável";
    badge.className = "drift-badge drift-stable";
    document.getElementById("driftIntensidade").textContent = "Baixa";
  }
}

function renderFeatureImportance() {
  const container = document.getElementById("featureImportanceList");
  if (!container) return;
  const items = Portfolio.averageAttributions(60);
  if (!items.length) {
    container.innerHTML = '<div class="empty-state">Aguardando operações suficientes…</div>';
    return;
  }
  const maxAvg = Math.max(...items.map((i) => i.avg), 1e-6);
  container.innerHTML = items.slice(0, 8).map((i) => {
    const pct = Math.min(100, (i.avg / maxAvg) * 100);
    return `<div class="explain-row">
      <span class="explain-name">${labelFeature(i.feature)}</span>
      <span class="explain-bar-track"><span class="explain-bar importance" style="width:${pct}%"></span></span>
      <span class="explain-val">${i.avg.toFixed(3)}</span>
    </div>`;
  }).join("");
}

/* ===== ABA 1 — indicadores e blocos de negocio (calculados via Portfolio) ===== */
function renderCarteira() {
  const k = Portfolio.kpis();
  document.getElementById("kpiOperacoes").textContent = k.total;
  document.getElementById("kpiValorTotal").textContent = currencyFmt(k.valorTotal);
  document.getElementById("kpiPdMediaCarteira").textContent = k.total ? fmtPct(k.pdMedia) : "–";
  document.getElementById("kpiAltoRisco").textContent = k.altoRisco;
  document.getElementById("kpiAumentaramRisco").textContent = k.aumentaram;
  document.getElementById("kpiEmAnalise").textContent = k.emAnalise;

  renderDistribution();
  renderChanges();
  renderRegionChanges();
  renderAttention(k);
  Charts.redrawEvolution();
}

function renderDistribution() {
  const el = document.getElementById("riskDistribution");
  const dist = Portfolio.distribution();
  if (!dist.total) {
    el.innerHTML = '<div class="empty-state">Inicie a simulação para ver a distribuição.</div>';
    return;
  }
  const rows = [
    { label: "Baixo", pct: dist.baixo, cls: "band-baixo" },
    { label: "Intermediário", pct: dist.medio, cls: "band-medio" },
    { label: "Alto", pct: dist.alto, cls: "band-alto" },
  ];
  el.innerHTML = rows.map((r) => `
    <div class="dist-row">
      <span class="dist-label">${r.label}</span>
      <span class="dist-track"><span class="dist-bar ${r.cls}" style="width:${(r.pct * 100).toFixed(1)}%"></span></span>
      <span class="dist-pct">${(r.pct * 100).toFixed(0)}%</span>
    </div>`).join("");
}

function renderChanges() {
  const c = Portfolio.changes();
  document.getElementById("changeUp").textContent = c.up;
  document.getElementById("changeWarn").textContent = c.warn;
  document.getElementById("changeDown").textContent = c.down;
}

function renderRegionChanges() {
  const tbody = document.getElementById("regionChangesBody");
  const rows = Portfolio.clientChanges();
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state">Sem dados suficientes ainda.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map((r) => `
    <tr class="clickable-row" data-cycle-id="${r.cycle_id}">
      <td data-label="Produtor">${r.producer_id} <span class="row-hint">(${r.application_id})</span></td>
      <td data-label="PD anterior">${fmtPct(r.pdAnterior)}</td>
      <td data-label="PD atual">${fmtPct(r.pd)}</td>
      <td data-label="Variação" class="${r.delta >= 0 ? "delta-up" : "delta-down"}">${fmtDeltaPP(r.delta)}</td>
    </tr>`).join("");
  tbody.querySelectorAll("tr[data-cycle-id]").forEach((tr) => {
    tr.addEventListener("click", () => {
      const rec = Portfolio.byId(tr.dataset.cycleId);
      if (rec) { switchTab("operacoes"); Agents.openOperationDetail(rec); }
    });
  });
}

function renderAttention(k) {
  document.getElementById("attRedCount").textContent = k.emAnalise;
  document.getElementById("attYellowCount").textContent = k.aumentaram;
  const regions = Portfolio.regionChanges().filter((r) => Math.abs(r.delta) >= 0.03);
  const row = document.getElementById("attRegionRow");
  if (regions.length) {
    row.innerHTML = `<span>${regions.length}</span> região(ões) com mudança acima do padrão observado: ${regions.map((r) => r.state).join(", ")}`;
  } else {
    row.innerHTML = "Nenhuma região com mudança acima do padrão observado";
  }
}

/* ===== ABA 2 — tabela de operacoes com filtros ===== */
function renderOperationsTable() {
  const tbody = document.getElementById("operationsBody");
  // Sem limite: a tabela mostra TODAS as operações que passam nos filtros
  // (o contêiner já tem scroll próprio — ver .predictions-table-wrap no CSS).
  const rows = Portfolio.filtered(opFilters);
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="10" class="empty-state">Nenhuma operação encontrada com estes filtros.</td></tr>';
    return;
  }
  tbody.innerHTML = "";
  // pushOperationRow insere cada linha no TOPO (comportamento certo para
  // chegada ao vivo, uma linha por vez); para renderizar a lista inteira
  // de uma vez, iteramos em ordem inversa para o resultado final ficar
  // com a mais recente no topo (sem isso, a ordem saía invertida).
  rows.slice().reverse().forEach((record) => Agents.pushOperationRow(record));
}

function applyOpFilters() {
  opFilters.search = document.getElementById("opFilterSearch").value.trim();
  opFilters.state = document.getElementById("opFilterState").value;
  opFilters.situacao = document.getElementById("opFilterSituacao").value;
  opFilters.risco = document.getElementById("opFilterRisco").value;
  renderOperationsTable();
}

/* ===== WebSocket / stream ===== */
function connectWs() {
  ws = new WebSocket(API.wsUrl());
  ws.onopen = () => setConn(true);
  ws.onclose = () => { setConn(false); setTimeout(connectWs, 1500); };
  ws.onerror = () => setConn(false);
  ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);
    if (msg.type === "status") {
      updateKpisTecnicos(msg.data);
    } else if (msg.type === "cycle") {
      const cycle = msg.data;
      updateKpisTecnicos(msg.status);
      updateKpisFromCycle(cycle);

      const record = Portfolio.ingest(cycle);
      renderCarteira();
      // so re-renderiza a tabela filtrada se a operacao nova passa nos filtros (evita "pulos" visuais desnecessarios)
      renderOperationsTable();
      renderFeatureImportance();

      Agents.pulseSequence();

      StreamLog.push("NEW_APPLICATION", cycle.timestamp, `${cycle.application_id} · PD ${fmtPct(cycle.pd)} · ${decisionLabel(cycle.decision)}`);
      if (cycle.outcome) {
        const loss = cycle.loss ?? 0;
        const isDefault = cycle.outcome.realized_default;
        const detail = isDefault
          ? `entrou em inadimplência e deixou ${(loss * 100).toFixed(1)}% do empréstimo em aberto`
          : `quitado sem perdas (pagamento em dia)`;
        StreamLog.push(isDefault ? "DEFAULT" : "PAYMENT", cycle.timestamp, `${cycle.application_id} · ${detail}`);
      }

      if (cycle.metric !== null && cycle.metric !== undefined) {
        Charts.pushFeedback(cycle.iteration, cycle.metric, cycle.threshold, cycle.drift ?? 0);
      }
    }
  };
}

async function toggleStream() {
  const btn = document.getElementById("btnStreamToggle");
  try {
    if (!streaming) {
      await API.streamStart(900);
      streaming = true;
      btn.textContent = "Parar simulação";
      btn.classList.add("is-active");
    } else {
      await API.streamStop();
      streaming = false;
      btn.textContent = "Iniciar simulação";
      btn.classList.remove("is-active");
    }
  } catch (e) {
    console.error("Falha ao iniciar/parar a simulação:", e);
    alert("Não foi possível falar com o backend agora. Verifique se o servidor (uvicorn) está rodando e recarregue a página.");
  }
}

async function sendStress() {
  const btn = document.getElementById("btnSendStress");
  const originalText = btn.textContent;

  if (!Portfolio.operations.length) {
    showToast("Ainda não há operações processadas para simular. Inicie a simulação primeiro, deixe algumas operações chegarem, e então teste o cenário.", "error");
    return;
  }

  // Simula TODAS as operações que passam nos filtros atuais da tabela de
  // Operações (mesmo conjunto de dados que a tabela está mostrando).
  const targetOps = Portfolio.filtered(opFilters);
  if (!targetOps.length) {
    showToast("Nenhuma operação corresponde aos filtros atuais da tabela. Ajuste ou limpe os filtros e tente de novo.", "error");
    return;
  }

  try {
    const commodity = parseFloat(document.getElementById("stressCommodity").value) || 0;
    const rainfall = parseFloat(document.getElementById("stressRainfall").value) || 0;
    const selic = parseFloat(document.getElementById("stressSelic").value) || 0;
    const drought = Math.abs(rainfall) > 0 ? 0.15 : 0;

    btn.disabled = true;
    btn.textContent = "Calculando…";

    const sample = targetOps.map((o) => ({
      application_id: o.application_id, producer_id: o.producer_id, raw_features: o.raw_features,
    }));
    const res = await API.stressPreview({
      selic_delta: selic, fx_delta: 0, commodity_pct: commodity,
      rainfall_pct: rainfall, drought_delta: drought,
      operations: sample,
    });
    renderStressPreview(res.results || [], targetOps);
    showToast(`Simulação concluída sobre ${sample.length} operação(ões) — veja a tabela de comparação abaixo.`, "success");
  } catch (e) {
    console.error("Falha ao simular cenário:", e);
    showToast("Não foi possível calcular a simulação agora. Verifique se o servidor está rodando.", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

function renderStressPreview(results, sourceOps) {
  const section = document.getElementById("stressPreviewSection");
  const tbody = document.getElementById("stressPreviewBody");
  const summary = document.getElementById("stressPreviewSummary");
  if (!results.length) {
    section.classList.add("hidden");
    return;
  }
  section.classList.remove("hidden");

  const byAppId = {};
  (sourceOps || []).forEach((o) => { byAppId[o.application_id] = o; });

  // Mesma regra de "Atencao agora": risco ABSOLUTO (decisao/PD vs limite)
  // e risco de TENDENCIA (variacao >= 5 p.p.), aplicada aqui tanto para a
  // situacao atual (variacao real historica) quanto para a situacao
  // simulada (variacao hipotetica = pd_simulado - pd_atual).
  const enriched = results.map((r) => {
    const src = byAppId[r.application_id];
    const situacaoAtual = Portfolio.situacao(r.pd_current, r.threshold, r.decision_current, src ? src.delta : null);
    const deltaSimulado = r.pd_simulated - r.pd_current;
    const situacaoSimulada = Portfolio.situacao(r.pd_simulated, r.threshold, r.decision_simulated, deltaSimulado);
    return { ...r, situacaoAtual, situacaoSimulada, deltaSimulado };
  });

  const flips = enriched.filter((r) => r.situacaoAtual !== r.situacaoSimulada);
  const avgDelta = enriched.reduce((a, r) => a + r.delta, 0) / enriched.length;
  summary.innerHTML = `${enriched.length} operação(ões) simuladas. Em média, o PD mudaria <b>${avgDelta >= 0 ? "+" : ""}${(avgDelta * 100).toFixed(1)} p.p.</b> sob este cenário.
    ${flips.length > 0 ? `<b>${flips.length} operação(ões)</b> mudariam de situação de atenção (destacadas abaixo).` : "Nenhuma operação mudaria de situação de atenção com este cenário."}`;

  const sorted = enriched.slice().sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  tbody.innerHTML = sorted.map((r) => {
    const flipped = r.situacaoAtual !== r.situacaoSimulada;
    return `<tr class="${flipped ? "row-flipped" : ""}">
      <td data-label="Código">${r.application_id}</td>
      <td data-label="Produtor">${r.producer_id}</td>
      <td data-label="PD atual">${fmtPct(r.pd_current)}</td>
      <td data-label="PD simulado">${fmtPct(r.pd_simulated)}</td>
      <td data-label="Variação"><span class="delta-chip ${r.delta > 0 ? "delta-up" : r.delta < 0 ? "delta-down" : ""}">${fmtDeltaPP(r.delta)}</span></td>
      <td data-label="Situação atual"><span class="decision-pill situacao-${r.situacaoAtual}">${situacaoLabel(r.situacaoAtual)}</span></td>
      <td data-label="Situação simulada"><span class="decision-pill situacao-${r.situacaoSimulada}">${situacaoLabel(r.situacaoSimulada)}</span></td>
    </tr>`;
  }).join("");
}

let toastTimer = null;
function showToast(message, type = "success") {
  let toast = document.getElementById("appToast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "appToast";
    document.body.appendChild(toast);
  }
  toast.className = `app-toast app-toast-${type} show`;
  toast.textContent = message;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 4500);
}

const STRESS_PRESETS = {
  normal: { commodity: 0, rainfall: 0, selic: 0 },
  commodity: { commodity: -25, rainfall: 0, selic: 0 },
  seca: { commodity: 0, rainfall: -40, selic: 0 },
  macro: { commodity: 0, rainfall: 0, selic: 3 },
  combinado: { commodity: -20, rainfall: -30, selic: 2 },
};

function initInfoTooltips() {
  document.querySelectorAll(".info-icon").forEach((icon) => {
    icon.addEventListener("click", (e) => {
      e.stopPropagation();
      const wasOpen = icon.classList.contains("tt-open");
      document.querySelectorAll(".info-icon.tt-open").forEach((i) => i.classList.remove("tt-open"));
      if (!wasOpen) icon.classList.add("tt-open");
    });
  });
  document.addEventListener("click", () => {
    document.querySelectorAll(".info-icon.tt-open").forEach((i) => i.classList.remove("tt-open"));
  });
}

function initTabs() {
  document.querySelectorAll(".main-tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });
  document.getElementById("btnVerOperacoes").addEventListener("click", () => {
    document.getElementById("opFilterSituacao").value = "analisar";
    applyOpFilters();
    switchTab("operacoes");
  });
}

function switchTab(tabName) {
  document.querySelectorAll(".main-tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === tabName));
  document.querySelectorAll(".tab-content").forEach((c) => c.classList.toggle("hidden", c.id !== `tab-${tabName}`));
}

function initOpFilters() {
  const stateSelect = document.getElementById("opFilterState");
  UF_LIST.forEach((uf) => {
    const opt = document.createElement("option");
    opt.value = uf; opt.textContent = uf;
    stateSelect.appendChild(opt);
  });
  ["opFilterSearch", "opFilterState", "opFilterSituacao", "opFilterRisco"].forEach((id) => {
    document.getElementById(id).addEventListener("input", applyOpFilters);
    document.getElementById(id).addEventListener("change", applyOpFilters);
  });
  document.getElementById("btnClearOpFilters").addEventListener("click", () => {
    document.getElementById("opFilterSearch").value = "";
    document.getElementById("opFilterState").value = "";
    document.getElementById("opFilterSituacao").value = "";
    document.getElementById("opFilterRisco").value = "";
    applyOpFilters();
  });
}

function initOperationDetailModal() {
  const modal = document.getElementById("operationDetailModal");
  document.getElementById("btnCloseOpDetail").setAttribute("aria-label", "Fechar detalhe da operação");
  document.getElementById("btnCloseOpDetail").addEventListener("click", () => modal.classList.add("hidden"));
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.add("hidden"); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") modal.classList.add("hidden");
  });
  document.getElementById("btnShowFormula").addEventListener("click", () => {
    document.getElementById("formulaExplanation").classList.toggle("hidden");
  });
}

function initEvolutionSelector() {
  document.querySelectorAll("#evolutionSelector .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#evolutionSelector .chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      Charts.setEvolutionMetric(chip.dataset.metric);
    });
  });
}

function initFeedbackSelector() {
  document.querySelectorAll("#feedbackSelector .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#feedbackSelector .chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      Charts.setFeedbackVisibleMetric(chip.dataset.metric);
    });
  });
}

function initStressPresets() {
  document.querySelectorAll("#stressPresets .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#stressPresets .chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      const p = STRESS_PRESETS[chip.dataset.preset];
      document.getElementById("stressCommodity").value = p.commodity;
      document.getElementById("stressRainfall").value = p.rainfall;
      document.getElementById("stressSelic").value = p.selic;
    });
  });
}

function wireChartNarrativeButton(btnId, boxId, chartName, statsFn) {
  const btn = document.getElementById(btnId);
  const box = document.getElementById(boxId);
  if (!btn || !box) return;
  btn.addEventListener("click", async () => {
    box.classList.remove("hidden");
    box.textContent = "Gerando resumo…";
    try {
      const stats = statsFn();
      const res = await API.narrativePortfolio(chartName, stats);
      if (!res.enabled) {
        box.textContent = res.message || "LLM opcional desativado (defina OPENAI_API_KEY).";
      } else {
        box.textContent = res.summary || "Sem resumo disponível.";
      }
    } catch (e) {
      box.textContent = "Não foi possível gerar o resumo agora.";
    }
  });
}

function initChartNarrativeButtons() {
  wireChartNarrativeButton("btnExplainDistribution", "distributionNarrativeBox", "Distribuição do risco da carteira", () => {
    const dist = Portfolio.distribution();
    return {
      total_operacoes: dist.total,
      pct_baixo_risco: Math.round(dist.baixo * 100),
      pct_intermediario: Math.round(dist.medio * 100),
      pct_alto_risco: Math.round(dist.alto * 100),
    };
  });

  wireChartNarrativeButton("btnExplainEvolution", "evolutionNarrativeBox", "Evolução do risco da carteira ao longo das operações", () => {
    const history = Portfolio.riskHistory.slice(-30);
    if (!history.length) return { aviso: "sem dados ainda" };
    const first = history[0], last = history[history.length - 1];
    return {
      metrica_selecionada: Charts.evolutionMetric,
      pd_media_inicio: Math.round(first.pdAvg * 1000) / 10,
      pd_media_fim: Math.round(last.pdAvg * 1000) / 10,
      operacoes_alto_risco_fim: last.highRiskCount,
      exposicao_alto_risco_fim: Math.round(last.highRiskExposure),
      pontos_observados: history.length,
    };
  });

  wireChartNarrativeButton("btnExplainMap", "mapNarrativeBox", "Mapa de risco médio por estado", () => {
    const states = Object.values(MapModule.statesData || {})
      .sort((a, b) => b.avg_risk - a.avg_risk)
      .slice(0, 6)
      .map((s) => ({ estado: s.name, risco_medio_pct: Math.round(s.avg_risk * 1000) / 10, aplicacoes: s.applications }));
    return { estados_mais_arriscados: states };
  });
}

async function initNarrativeButton() {
  const btn = document.getElementById("btnNarrative");
  let llmEnabled = false;
  try {
    const status = await API.llmStatus();
    llmEnabled = !!status.enabled;
  } catch (e) { /* backend antigo sem o endpoint: mantem desabilitado */ }

  btn.disabled = false;
  btn.title = llmEnabled
    ? "Gera um resumo em linguagem natural da decisão já calculada (não altera PD/limite/decisão)."
    : "Desativado: defina OPENAI_API_KEY no backend para habilitar (ver .env.example). O núcleo matemático funciona igual sem isso.";

  btn.addEventListener("click", async () => {
    const record = Agents.currentRecord;
    const box = document.getElementById("narrativeBox");
    if (!record) return;
    box.classList.remove("hidden");
    box.textContent = "Gerando resumo…";
    try {
      const payload = {
        producer_id: record.producer_id,
        application_id: record.application_id,
        decision: record.decision,
        pd: record.pd,
        pd_anterior: record.pdAnterior,
        delta: record.delta,
        threshold: record.threshold,
        confidence: record.confidence,
        attributions: record.attributions,
      };
      const res = await API.narrativeDecision(payload);
      if (!res.enabled) {
        box.textContent = res.message || "LLM opcional desativado (defina OPENAI_API_KEY).";
      } else {
        box.textContent = res.summary || "Sem resumo disponível.";
      }
    } catch (e) {
      box.textContent = "Não foi possível gerar o resumo agora.";
    }
  });
}

async function init() {
  // 1) Prioridade maxima: navegacao e controles essenciais, sincronos,
  // sem depender de rede ou biblioteca externa.
  initTabs();
  document.getElementById("btnStreamToggle").addEventListener("click", toggleStream);
  document.getElementById("btnSendStress").addEventListener("click", sendStress);
  initStressPresets();
  initOpFilters();
  initOperationDetailModal();
  initEvolutionSelector();
  initFeedbackSelector();
  initChartNarrativeButtons();

  const archModal = document.getElementById("architectureModal");
  const badgeArch = document.getElementById("badgeArchitecture");
  badgeArch.setAttribute("aria-label", "Abrir diagrama completo da arquitetura");
  badgeArch.addEventListener("click", () => archModal.classList.remove("hidden"));
  badgeArch.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); archModal.classList.remove("hidden"); }
  });
  document.getElementById("btnCloseArchitecture").setAttribute("aria-label", "Fechar diagrama de arquitetura");
  document.getElementById("btnCloseArchitecture").addEventListener("click", () => archModal.classList.add("hidden"));
  archModal.addEventListener("click", (e) => { if (e.target === archModal) archModal.classList.add("hidden"); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") archModal.classList.add("hidden");
  });

  try {
    Tutorial.init();
  } catch (e) {
    console.error("Falha ao iniciar o tutorial ('Como usar'):", e);
  }

  initInfoTooltips();

  try {
    connectWs();
  } catch (e) {
    console.error("Falha ao conectar WebSocket:", e);
  }

  try {
    if (typeof Chart === "undefined") throw new Error("Chart.js nao carregou (CDN bloqueado?)");
    Charts.initFeedbackChart();
    Charts.initEvolutionChart();
  } catch (e) {
    console.error("Falha ao iniciar os graficos:", e);
  }

  try {
    if (typeof L === "undefined") throw new Error("Leaflet nao carregou (CDN bloqueado?)");
    MapModule.init();
    await MapModule.refresh();
    setInterval(() => MapModule.refresh().catch((e) => console.error("Falha ao atualizar mapa:", e)), 15000);
  } catch (e) {
    console.error("Falha ao iniciar o mapa do Brasil:", e);
    const el = document.getElementById("mapBrazil");
    if (el) el.innerHTML = '<p class="empty-state">Mapa indisponível (falha ao carregar Leaflet via CDN ou API).</p>';
  }

  try {
    await initNarrativeButton();
  } catch (e) {
    console.error("Falha ao iniciar o botao de narrativa por IA:", e);
  }

  try {
    if (typeof Chart === "undefined") throw new Error("Chart.js nao carregou");
    const monitoring = await API.monitoringMonthly();
    Charts.initMonitoringChart(monitoring.series || []);
  } catch (e) {
    console.error("Falha ao carregar o historico previsto vs realizado:", e);
    const el = document.getElementById("monitoringInterpretationText");
    if (el) el.textContent = "Não foi possível carregar o histórico agora.";
  }
}

init();
