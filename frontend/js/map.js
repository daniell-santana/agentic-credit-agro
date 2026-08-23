const MapModule = {
  map: null,
  geojsonLayer: null,
  statesData: {},
  geojson: null,

  init() {
    this.map = L.map("mapBrazil", { zoomControl: true, attributionControl: false })
      .setView([-14.2, -51.9], 4);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 8,
    }).addTo(this.map);
    this._addLegend();
    // Leaflet mede o container no momento do init; se o layout ainda estiver
    // se ajustando (fontes carregando, grid recalculando), o mapa fica
    // desalinhado ("fora de esquadro"). invalidateSize() corrige isso.
    setTimeout(() => this.map.invalidateSize(), 150);
    window.addEventListener("resize", () => this.map && this.map.invalidateSize());
  },

  // Escala de cor RELATIVA ao intervalo observado nos dados (nao faixas
  // fixas) -- com pouca variancia geografica no dataset sintetico, faixas
  // fixas (ex.: <35%/35-50%/>50%) faziam quase todo estado cair no mesmo
  // bucket "medio" (amarelo). Interpolando entre o minimo e o maximo
  // observados, a diferenciacao visual aparece mesmo quando os valores
  // absolutos estao proximos uns dos outros.
  _colorScale(t) {
    // verde (baixo) -> amarelo (medio) -> vermelho (alto), t em [0,1]
    const stops = [
      [0.00, [52, 211, 153]],
      [0.50, [251, 191, 36]],
      [1.00, [248, 113, 113]],
    ];
    let a = stops[0], b = stops[stops.length - 1];
    for (let i = 0; i < stops.length - 1; i++) {
      if (t >= stops[i][0] && t <= stops[i + 1][0]) { a = stops[i]; b = stops[i + 1]; break; }
    }
    const span = b[0] - a[0] || 1;
    const localT = (t - a[0]) / span;
    const rgb = a[1].map((c, i) => Math.round(c + (b[1][i] - c) * localT));
    return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
  },

  _riskRange() {
    const values = Object.values(this.statesData).map((s) => s.avg_risk);
    if (!values.length) return { min: 0, max: 1 };
    const min = Math.min(...values), max = Math.max(...values);
    return max - min < 0.02 ? { min: min - 0.05, max: max + 0.05 } : { min, max };
  },

  _addLegend() {
    const legend = L.control({ position: "bottomright" });
    legend.onAdd = () => {
      const div = L.DomUtil.create("div", "map-legend");
      div.innerHTML = `
        <div class="map-legend-title">Risco médio (PD)</div>
        <div class="map-legend-gradient"></div>
        <div class="map-legend-scale"><span id="legendMin">–</span><span id="legendMax">–</span></div>
        <div class="map-legend-note">Escala relativa aos estados com dados</div>
      `;
      return div;
    };
    legend.addTo(this.map);
  },

  async _loadGeojson() {
    if (this.geojson) return this.geojson;
    const res = await fetch("data/brazil-states.geojson");
    this.geojson = await res.json();
    return this.geojson;
  },

  _colorFor(sigla) {
    const s = this.statesData[sigla];
    if (!s) return "#232B37";
    const { min, max } = this._riskRange();
    const t = Math.min(1, Math.max(0, (s.avg_risk - min) / (max - min || 1)));
    return this._colorScale(t);
  },

  _styleFor(sigla) {
    const s = this.statesData[sigla];
    const color = this._colorFor(sigla);
    return {
      fillColor: color,
      fillOpacity: s ? 0.65 : 0.15,
      color: color,
      weight: 1.2,
      opacity: s ? 0.95 : 0.3,
    };
  },

  _popupFor(sigla) {
    const s = this.statesData[sigla];
    if (!s) return `<b>${sigla}</b><br>Sem aplicações no dataset.`;
    return `<b>${s.name}</b><br>Risco médio (PD): ${(s.avg_risk * 100).toFixed(1)}%<br>Aplicações: ${s.applications}`;
  },

  _updateLegendScale() {
    const { min, max } = this._riskRange();
    const elMin = document.getElementById("legendMin");
    const elMax = document.getElementById("legendMax");
    if (elMin) elMin.textContent = `${(min * 100).toFixed(0)}%`;
    if (elMax) elMax.textContent = `${(max * 100).toFixed(0)}%`;
  },

  async refresh() {
    const data = await API.producersMap();
    this.statesData = {};
    (data.states || []).forEach((s) => { this.statesData[s.state] = s; });

    const geojson = await this._loadGeojson();
    this._updateLegendScale();

    if (this.geojsonLayer) {
      this.geojsonLayer.eachLayer((layer) => {
        const sigla = layer.feature.properties.sigla;
        layer.setStyle(this._styleFor(sigla));
        layer.unbindPopup();
        layer.bindPopup(this._popupFor(sigla));
      });
      if (this.map) this.map.invalidateSize();
      return;
    }

    this.geojsonLayer = L.geoJSON(geojson, {
      style: (feature) => this._styleFor(feature.properties.sigla),
      onEachFeature: (feature, layer) => {
        layer.bindPopup(this._popupFor(feature.properties.sigla));
        layer.on("mouseover", () => layer.setStyle({ weight: 2.5, fillOpacity: 0.85 }));
        layer.on("mouseout", () => layer.setStyle(this._styleFor(feature.properties.sigla)));
      },
    }).addTo(this.map);
    if (this.map) this.map.invalidateSize();
  },
};
