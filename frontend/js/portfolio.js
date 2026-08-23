/**
 * Estado central da carteira (secao 42 do plano de redesenho).
 *
 * Classificacao: IMPLEMENTATION CHOICE / EXTENSAO DE UX — o artigo nao
 * especifica agregacoes de carteira. Todas as agregacoes aqui sao
 * calculadas no cliente a partir dos ciclos JA DECIDIDOS PELO BACKEND
 * (PD, threshold, decision, confidence, attributions) — o frontend nunca
 * recalcula PD, nunca inventa decisao, apenas agrega o que ja veio pronto
 * (regra 1 e 2 da secao 43 do plano).
 *
 * "Aumentou de risco" usa o limiar de 5 p.p. sugerido no exemplo do plano
 * (secao 7): variacao de PD >= 5 pontos percentuais desde a ultima
 * observacao do MESMO produtor.
 */
const Portfolio = {
  operations: [],   // registros processados nesta sessao (mais antigo -> mais novo)
  byProducer: {},   // producer_id -> { lastPd, history: [{pd, threshold, timestamp}] }
  riskHistory: [],  // pontos para o grafico de evolucao da Aba 1

  DELTA_THRESHOLD: 0.05, // 5 p.p. — "aumentou de risco" (secao 7 do plano, exemplo)

  reset() {
    this.operations = [];
    this.byProducer = {};
    this.riskHistory = [];
  },

  riskBand(pd, threshold) {
    if (pd < threshold * 0.6) return "baixo";
    if (pd <= threshold) return "medio";
    return "alto";
  },

  situacao(pd, threshold, decision, delta) {
    if (decision === "REJECT" || decision === "REVIEW") return "analisar";
    if (delta != null && delta >= this.DELTA_THRESHOLD) return "acompanhar";
    if (delta != null && delta < 0) return "reduziu";
    return "sem_alteracao";
  },

  ingest(cycle) {
    const prevEntry = this.byProducer[cycle.producer_id];
    const prevPd = prevEntry ? prevEntry.lastPd : null;
    const delta = prevPd != null ? cycle.pd - prevPd : null;
    const ctx = cycle.context || {};

    const record = {
      cycle_id: cycle.cycle_id,
      application_id: cycle.application_id,
      producer_id: cycle.producer_id,
      timestamp: cycle.timestamp,
      state: ctx.state || null,
      crop_type: ctx.crop_type || null,
      requested_amount: (cycle.raw_features && cycle.raw_features.requested_amount) || 0,
      raw_features: cycle.raw_features || {},
      pd: cycle.pd,
      pdAnterior: prevPd,
      delta,
      threshold: cycle.threshold,
      confidence: cycle.confidence,
      decision: cycle.decision,
      attributions: cycle.attributions || {},
    };
    record.band = this.riskBand(record.pd, record.threshold);
    record.situacao = this.situacao(record.pd, record.threshold, record.decision, delta);

    this.operations.push(record);
    // Sem cap artificial: o dataset sintetico tem ~2000 aplicacoes no
    // total (ver scripts/generate_synthetic_data.py), entao um teto bem
    // acima disso e equivalente, na pratica, a "mostrar todas".
    if (this.operations.length > 5000) this.operations.shift();

    const prevHistory = prevEntry ? prevEntry.history : [];
    const history = [...prevHistory, { pd: record.pd, threshold: record.threshold, timestamp: record.timestamp }].slice(-30);
    this.byProducer[cycle.producer_id] = { lastPd: cycle.pd, history };
    record.producerHistory = history;

    const highRisk = this.operations.filter((o) => o.band === "alto");
    const pdAvg = this.operations.reduce((a, o) => a + o.pd, 0) / this.operations.length;
    this.riskHistory.push({
      iteration: this.operations.length,
      pdAvg,
      highRiskCount: highRisk.length,
      highRiskExposure: highRisk.reduce((a, o) => a + o.requested_amount, 0),
    });
    if (this.riskHistory.length > 200) this.riskHistory.shift();

    return record;
  },

  distribution() {
    const counts = { baixo: 0, medio: 0, alto: 0 };
    this.operations.forEach((o) => counts[o.band]++);
    const total = this.operations.length || 1;
    return {
      baixo: counts.baixo / total, medio: counts.medio / total, alto: counts.alto / total,
      counts, total: this.operations.length,
    };
  },

  kpis() {
    const total = this.operations.length;
    const valorTotal = this.operations.reduce((a, o) => a + o.requested_amount, 0);
    const pdMedia = total ? this.operations.reduce((a, o) => a + o.pd, 0) / total : 0;
    const altoRisco = this.operations.filter((o) => o.band === "alto").length;
    const aumentaram = this.operations.filter((o) => o.delta != null && o.delta >= this.DELTA_THRESHOLD).length;
    const emAnalise = this.operations.filter((o) => o.situacao === "analisar").length;
    return { total, valorTotal, pdMedia, altoRisco, aumentaram, emAnalise };
  },

  changes() {
    const up = this.operations.filter((o) => o.delta != null && o.delta > 0).length;
    const warn = this.operations.filter(
      (o) => o.pd > o.threshold && !(o.pdAnterior != null && o.pdAnterior > o.threshold)
    ).length;
    const down = this.operations.filter((o) => o.delta != null && o.delta < 0).length;
    return { up, warn, down };
  },

  clientChanges(limit = 8) {
    return this.operations
      .filter((o) => o.delta != null)
      .slice()
      .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
      .slice(0, limit);
  },

  regionChanges() {
    const byState = {};
    this.operations.forEach((o) => {
      if (!o.state) return;
      (byState[o.state] = byState[o.state] || []).push(o.pd);
    });
    const rows = [];
    Object.entries(byState).forEach(([state, pds]) => {
      if (pds.length < 4) return;
      const mid = Math.floor(pds.length / 2);
      const before = pds.slice(0, mid).reduce((a, b) => a + b, 0) / mid;
      const after = pds.slice(mid).reduce((a, b) => a + b, 0) / (pds.length - mid);
      rows.push({ state, before, after, delta: after - before });
    });
    rows.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
    return rows.slice(0, 5);
  },

  filtered(filters) {
    return this.operations
      .filter((o) => {
        if (filters.search) {
          const q = filters.search.toLowerCase();
          if (!o.producer_id.toLowerCase().includes(q) && !o.application_id.toLowerCase().includes(q)) return false;
        }
        if (filters.state && o.state !== filters.state) return false;
        if (filters.situacao && o.situacao !== filters.situacao) return false;
        if (filters.risco && o.band !== filters.risco) return false;
        return true;
      })
      .slice()
      .reverse();
  },

  byId(cycleId) {
    return this.operations.find((o) => o.cycle_id === cycleId);
  },

  /** Media da magnitude de atribuicao (|Ai|) por variavel, sobre as N
   * operacoes mais recentes -- usada para acompanhar quais variaveis mais
   * influenciam o PD em media, e detectar mudanca de comportamento das
   * variaveis ao longo do tempo (Aba 3). */
  averageAttributions(n = 60) {
    const recent = this.operations.slice(-n);
    if (!recent.length) return [];
    const sums = {}, counts = {};
    recent.forEach((o) => {
      Object.entries(o.attributions || {}).forEach(([k, v]) => {
        sums[k] = (sums[k] || 0) + Math.abs(v);
        counts[k] = (counts[k] || 0) + 1;
      });
    });
    return Object.entries(sums)
      .map(([feature, sum]) => ({ feature, avg: sum / counts[feature] }))
      .sort((a, b) => b.avg - a.avg);
  },
};
