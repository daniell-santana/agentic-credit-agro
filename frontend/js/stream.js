const EVENT_TYPE_LABELS = {
  NEW_APPLICATION: "NOVA SOLICITAÇÃO",
  PAYMENT: "🟢 PAGAMENTO",
  DEFAULT: "🔴 INADIMPLÊNCIA",
  MACRO_UPDATE: "ATUALIZAÇÃO MACRO",
  CLIMATE_UPDATE: "ATUALIZAÇÃO CLIMA",
  COMMODITY_UPDATE: "ATUALIZAÇÃO COMMODITY",
};

const StreamLog = {
  maxRows: 60,

  push(eventType, timestamp, extra) {
    const log = document.getElementById("streamLog");
    const row = document.createElement("div");
    row.className = "stream-log-row";
    const time = new Date(timestamp || Date.now()).toLocaleTimeString("pt-BR");
    const label = EVENT_TYPE_LABELS[eventType] || eventType;
    row.innerHTML = `
      <span class="stream-log-time">${time}</span>
      <span class="stream-log-type type-${eventType}">${label}</span>
      <span class="stream-log-extra">${extra || ""}</span>
    `;
    log.appendChild(row);
    while (log.children.length > this.maxRows) log.removeChild(log.firstChild);
    log.scrollTop = log.scrollHeight;
  },
};
