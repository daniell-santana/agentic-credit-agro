const AGENT_NODE_ORDER = [
  "data_acquisition_agent",
  "feature_transformation",
  "risk_scoring_agent",
  "explainability_agent",
  "decision_agent",
  "feedback_learning_agent",
];

const Agents = {
  pulseSequence() {
    AGENT_NODE_ORDER.forEach((name, i) => {
      const el = document.querySelector(`.pf-node[data-node="${name}"]`);
      if (!el) return;
      setTimeout(() => {
        el.classList.add("pulse");
        setTimeout(() => el.classList.remove("pulse"), 480);
      }, i * 110);
    });
  },

  currentCycleId: null,
  currentRecord: null,

  /** Renderiza os fatores de risco (attribution) num container qualquer — reusado
   * tanto no modal de detalhe da operacao (Aba 2) quanto, se necessario, em outros lugares. */
  renderFactors(containerId, attributions) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const attrs = Object.entries(attributions || {});
    if (!attrs.length) {
      container.innerHTML = '<div class="empty-state">Sem fatores de risco para esta operação.</div>';
      return;
    }
    attrs.sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
    const maxAbs = Math.max(...attrs.map(([, v]) => Math.abs(v)), 1e-6);
    container.innerHTML = attrs
      .slice(0, 8)
      .map(([name, val]) => {
        const pct = Math.min(100, (Math.abs(val) / maxAbs) * 100);
        const cls = val >= 0 ? "pos" : "neg";
        return `<div class="explain-row">
          <span class="explain-name">${labelFeature(name)}</span>
          <span class="explain-bar-track"><span class="explain-bar ${cls}" style="width:${pct}%"></span></span>
          <span class="explain-val">${val >= 0 ? "+" : ""}${val.toFixed(3)}</span>
        </div>`;
      })
      .join("");
  },

  /** Abre o modal de detalhe de uma operacao (secao 18 do plano). Recebe um
   * registro do Portfolio (ja com pdAnterior/delta/situacao calculados). */
  openOperationDetail(record) {
    this.currentCycleId = record.cycle_id;
    this.currentRecord = record;
    document.getElementById("opDetailTitle").textContent =
      `Produtor ${record.producer_id} — ${record.application_id}`;
    document.getElementById("opDetailValor").textContent =
      currencyFmt(record.requested_amount);
    document.getElementById("opDetailPdAtual").textContent = fmtPct(record.pd);
    document.getElementById("opDetailPdAnterior").textContent =
      record.pdAnterior != null ? fmtPct(record.pdAnterior) : "Sem observação anterior";
    document.getElementById("opDetailVariacao").textContent =
      record.delta != null ? fmtDeltaPP(record.delta) : "–";
    document.getElementById("opDetailLimite").textContent = fmtPct(record.threshold);
    document.getElementById("opDetailConfianca").textContent = fmtPct(record.confidence);

    const tag = document.getElementById("opDetailSituacao");
    tag.textContent = decisionLabel(record.decision);
    tag.className = `decision-tag ${record.decision}`;

    this.renderFactors("opDetailFactors", record.attributions);
    Charts.renderOperationEvolution(record.producerHistory);

    const box = document.getElementById("narrativeBox");
    box.classList.add("hidden");
    box.textContent = "";

    document.getElementById("operationDetailModal").classList.remove("hidden");
  },

  maxOperationRows: 5000, // sem cap artificial visivel (ver Portfolio.operations) — a tabela deve mostrar todas as operações

  pushOperationRow(record) {
    const tbody = document.getElementById("operationsBody");
    if (!tbody) return;
    if (tbody.querySelector(".empty-state")) tbody.innerHTML = "";

    const time = new Date(record.timestamp || Date.now()).toLocaleString("pt-BR", {
      day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
    const deltaHtml = record.delta != null
      ? `<span class="delta-chip ${record.delta > 0 ? "delta-up" : record.delta < 0 ? "delta-down" : ""}">${fmtDeltaPP(record.delta)}</span>`
      : "<span class=\"delta-chip\">—</span>";

    const row = document.createElement("tr");
    row.dataset.cycleId = record.cycle_id;
    row.dataset.state = record.state || "";
    row.dataset.situacao = record.situacao;
    row.dataset.band = record.band;
    row.dataset.search = `${record.producer_id} ${record.application_id}`.toLowerCase();
    row.tabIndex = 0;
    row.setAttribute("role", "button");
    row.setAttribute("aria-label", `Ver detalhe da operação ${record.application_id}, produtor ${record.producer_id}, PD ${fmtPct(record.pd)}`);
    row.innerHTML = `
      <td data-label="Data/Hora">${time}</td>
      <td data-label="Código">${record.application_id}</td>
      <td data-label="Produtor">${record.producer_id}</td>
      <td data-label="UF">${record.state || "–"}</td>
      <td data-label="Cultura">${labelCrop(record.crop_type)}</td>
      <td data-label="Valor">${currencyFmt(record.requested_amount)}</td>
      <td data-label="PD anterior">${record.pdAnterior != null ? fmtPct(record.pdAnterior) : "—"}</td>
      <td data-label="PD atual">${fmtPct(record.pd)}</td>
      <td data-label="Mudança">${deltaHtml}</td>
      <td data-label="Situação"><span class="decision-pill situacao-${record.situacao}">${situacaoLabel(record.situacao)}</span></td>
    `;
    row.addEventListener("click", () => Agents.openOperationDetail(record));
    row.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        Agents.openOperationDetail(record);
      }
    });
    tbody.insertBefore(row, tbody.firstChild);
    while (tbody.children.length > Agents.maxOperationRows) tbody.removeChild(tbody.lastChild);
    return row;
  },
};

function decisionLabel(d) {
  return { APPROVE: "APROVADO", REVIEW: "REQUER ANÁLISE", REJECT: "REQUER ANÁLISE" }[d] || d || "—";
}

function situacaoLabel(s) {
  return { analisar: "Analisar", acompanhar: "Acompanhar", reduziu: "Risco reduzido", sem_alteracao: "Sem alteração" }[s] || s;
}

function fmtPct(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  return `${(v * 100).toFixed(1)}%`;
}

function fmtDeltaPP(delta) {
  const pp = delta * 100;
  const sign = pp > 0 ? "+" : "";
  return `${sign}${pp.toFixed(1)} p.p.`;
}

function currencyFmt(amount) {
  if (amount == null) return "–";
  return amount.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function labelFeature(name) {
  const map = {
    requested_amount: "Valor solicitado", term_months: "Prazo (meses)",
    interest_rate: "Taxa de juros", collateral_value: "Garantia",
    annual_revenue: "Receita anual", annual_cost: "Custo anual",
    equity: "Patrimônio", debt: "Endividamento", farm_size_ha: "Área (ha)",
    years_farming: "Anos de atividade", rainfall: "Chuva", temperature: "Temperatura",
    drought_index: "Índice de seca", crop_price: "Preço da commodity",
    selic: "Taxa básica (SELIC)", inflation: "IPCA", usd_brl: "USD/BRL", commodity_index: "Índice de commodity",
  };
  return map[name] || name;
}

function labelCrop(crop) {
  const map = {
    soja: "Soja", milho: "Milho", algodao: "Algodão", cafe: "Café",
    "cana-de-acucar": "Cana-de-açúcar", pecuaria: "Pecuária",
  };
  return map[crop] || crop || "–";
}
