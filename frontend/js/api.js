const API = {
  base: window.location.origin,

  async get(path) {
    const res = await fetch(`${this.base}${path}`);
    return res.json();
  },
  async post(path, body) {
    const opts = { method: "POST" };
    if (body !== undefined) {
      opts.headers = { "Content-Type": "application/json" };
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(`${this.base}${path}`, opts);
    return res.json();
  },

  health: () => API.get("/api/health"),
  streamStart: (intervalMs = 900) => API.post(`/api/stream/start?interval_ms=${intervalMs}`),
  streamStop: () => API.post("/api/stream/stop"),
  streamStatus: () => API.get("/api/stream/status"),
  producersMap: () => API.get("/api/producers/map"),
  feedbackHistory: (limit = 100) => API.get(`/api/feedback/history?limit=${limit}`),
  experiments: () => API.get("/api/experiments"),
  stressMacro: (selicDelta, fxDelta, commodityPct) =>
    API.post(`/api/stress/macro?selic_delta=${selicDelta}&fx_delta=${fxDelta}&commodity_pct=${commodityPct}`),
  stressClimate: (rainfallPct, droughtDelta) =>
    API.post(`/api/stress/climate?rainfall_pct=${rainfallPct}&drought_delta=${droughtDelta}`),
  stressPreview: (payload) => API.post("/api/stress/preview", payload),
  llmStatus: () => API.get("/api/llm/status"),
  narrativeDecision: (payload) => API.post("/api/narrative/decision", payload),
  narrativePortfolio: (chartName, stats) => API.post("/api/narrative/portfolio", { chart_name: chartName, stats }),
  monitoringMonthly: () => API.get("/api/monitoring/monthly"),

  wsUrl() {
    const proto = this.base.startsWith("https") ? "wss" : "ws";
    const host = this.base.replace(/^https?:\/\//, "");
    return `${proto}://${host}/ws`;
  },
};
