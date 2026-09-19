const MINUTE_COLORS = ["#1b5e20", "#66a756", "#cddc39", "#f59120", "#b71c1c", "#67000d"];
const MINUTE_LABELS = ["≤ 5 min", "5–10 min", "10–15 min", "15–30 min", "30–60 min", "60+ min"];
const MINUTE_STOPS = [5, 10, 15, 30, 60];
const FILL_OPACITY = 204 / 255;
const CLINIC = "#b22222";
const SCHOOL = "#195078";
const INK = "#1c1916";
const WARD_LINE = "rgba(90,84,78,0.65)";
const PLACE_INK = "#37322e";
const HALO = "#fafafa";
const GLYPHS = "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf";
const LIBERTY = "https://tiles.openfreemap.org/styles/liberty";

const EMPTY = { type: "FeatureCollection", features: [] };

const RASTER = {
  gray: {
    light: {
      tiles: ["https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"],
      labels: "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
    },
    dark: {
      tiles: ["https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"],
      labels: "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
    },
    maxzoom: 16,
    attribution: "Tiles © Esri · GRID3 clinics and schools · OSM streets",
  },
  imagery: {
    tiles: ["https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
    labels: "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    maxzoom: 19,
    attribution: "Tiles © Esri · GRID3 clinics and schools · OSM streets",
  },
};

const fmt = (n) => {
  if (n == null || n === "" || Number.isNaN(Number(n))) return "n/a";
  return Number(n).toLocaleString("en-US");
};
const pct = (n) => (n == null || Number.isNaN(Number(n)) ? "n/a" : `${Number(n).toFixed(1)}%`);
const minutes = (n) => (n == null || Number.isNaN(Number(n)) ? "n/a" : `${Number(n).toFixed(1)} min`);
const nonempty = (s) => (s && String(s).trim() && String(s).trim() !== "nan" ? String(s).trim() : "");

function isDark() {
  return document.documentElement.classList.contains("calcite-mode-dark");
}

function rasterSpec(key) {
  if (key === "gray") {
    const tone = isDark() ? RASTER.gray.dark : RASTER.gray.light;
    return { ...tone, maxzoom: RASTER.gray.maxzoom, attribution: RASTER.gray.attribution };
  }
  return RASTER.imagery;
}

function minuteColor(field) {
  return [
    "case",
    ["==", ["get", field], null],
    "#b1b1b1",
    ["step", ["get", field], MINUTE_COLORS[0], MINUTE_STOPS[0], MINUTE_COLORS[1], MINUTE_STOPS[1], MINUTE_COLORS[2], MINUTE_STOPS[2], MINUTE_COLORS[3], MINUTE_STOPS[3], MINUTE_COLORS[4], MINUTE_STOPS[4], MINUTE_COLORS[5]],
  ];
}

function peopleColor(breaks) {
  if (!breaks?.length) {
    return ["interpolate", ["linear"], ["get", "people"], 0, "#ffeda0", 400, "#fed976", 1000, "#feb24c", 2000, "#fd8d3c", 4000, "#e31a1c", 8000, "#800026"];
  }
  const expr = ["step", ["get", "people"], breaks[0].color];
  for (let i = 1; i < breaks.length; i += 1) expr.push(breaks[i].lo, breaks[i].color);
  return expr;
}

function fieldFor(theme) {
  if (theme === "clinic") return "clinic_min";
  if (theme === "school") return "school_min";
  return "minutes";
}

function rasterStyle(key) {
  const spec = rasterSpec(key);
  const layers = [
    { id: "bg", type: "background", paint: { "background-color": isDark() ? "#1a1a1a" : "#e5e5e5" } },
    { id: "basemap", type: "raster", source: "basemap", paint: { "raster-opacity": 1, "raster-fade-duration": 0 } },
  ];
  const sources = {
    basemap: { type: "raster", tiles: spec.tiles, tileSize: 256, maxzoom: spec.maxzoom, attribution: spec.attribution },
  };
  if (spec.labels) {
    sources.labels = { type: "raster", tiles: [spec.labels], tileSize: 256, maxzoom: spec.maxzoom };
    layers.push({ id: "basemap-labels", type: "raster", source: "labels", paint: { "raster-opacity": 1, "raster-fade-duration": 0 } });
  }
  return { version: 8, glyphs: GLYPHS, sources, layers };
}

function hexPaint(theme, breaks) {
  const color = theme === "people" ? peopleColor(breaks) : minuteColor(fieldFor(theme));
  return {
    "fill-color": color,
    "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.92, FILL_OPACITY],
    "fill-outline-color": "rgba(255,255,255,0.16)",
  };
}

function rasterIcon(draw, size = 32) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (typeof ctx.roundRect !== "function") {
    ctx.roundRect = function roundRect(x, y, w, h) {
      this.rect(x, y, w, h);
    };
  }
  draw(ctx, size);
  return ctx.getImageData(0, 0, size, size);
}

function addIcons(map) {
  const clinic = rasterIcon((ctx, size) => {
    const r = 5;
    ctx.fillStyle = CLINIC;
    ctx.strokeStyle = "rgba(255,255,255,0.92)";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.roundRect(2, 2, size - 4, size - 4, r);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#fff";
    const arm = 4;
    const bar = 12;
    ctx.fillRect((size - arm) / 2, (size - bar) / 2, arm, bar);
    ctx.fillRect((size - bar) / 2, (size - arm) / 2, bar, arm);
  });
  const school = rasterIcon((ctx, size) => {
    ctx.fillStyle = SCHOOL;
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 2 - 1.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.92)";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.fillStyle = "#fff";
    ctx.beginPath();
    ctx.moveTo(size / 2, 7);
    ctx.lineTo(23, 14);
    ctx.lineTo(9, 14);
    ctx.closePath();
    ctx.fill();
    ctx.fillRect(11, 14, 10, 9);
    ctx.fillRect(14.5, 17, 3, 6);
    ctx.fillRect(size / 2 - 0.7, 5.5, 1.4, 3);
  });
  if (map.hasImage("clinic-mark")) map.removeImage("clinic-mark");
  if (map.hasImage("school-mark")) map.removeImage("school-mark");
  map.addImage("clinic-mark", clinic);
  map.addImage("school-mark", school);
}

function row(label, value) {
  return `<dt>${label}</dt><dd>${value}</dd>`;
}

function wardBlock(props, city, { heading = true } = {}) {
  if (!props) return "";
  const name = props.label || props.name || "Ward";
  const lga = nonempty(props.lga);
  const rank =
    props.rank != null && props.of != null
      ? `${fmt(props.rank)} of ${fmt(props.of)} wards by share within 15 minutes`
      : "";
  const vs =
    city && props.f15 != null
      ? `City score is ${pct(city.f15)}. Typical city walk is ${minutes(city.pt)}.`
      : "";
  return `${heading ? `<div class="popup-head ward">${name}</div>` : ""}
    <div class="popup-body">
      ${props.reading ? `<p class="popup-reading">${props.reading}</p>` : ""}
      <dl>
        ${lga ? row("Local government", lga) : ""}
        ${row("People living here", fmt(props.people))}
        ${props.share != null ? row("Share of the city", pct(props.share)) : ""}
        ${row("Within a 15-minute walk", pct(props.f15))}
        ${row("Typical walk", minutes(props.walk))}
        ${row("To a clinic", `${pct(props.f15_health)} · ${minutes(props.walk_clinic)}`)}
        ${row("To a school", `${pct(props.f15_school)} · ${minutes(props.walk_school)}`)}
        ${row("People still beyond 15 minutes", fmt(props.beyond))}
        ${row("GRID3 clinics in this ward", fmt(props.clinics))}
        ${row("GRID3 schools in this ward", fmt(props.schools))}
        ${props.off_pct != null ? row("People off mapped streets", pct(props.off_pct)) : ""}
        ${props.gini != null ? row("How uneven the walks are (Gini)", Number(props.gini).toFixed(3)) : ""}
        ${rank ? row("Standing in this city", rank) : ""}
      </dl>
      ${vs ? `<div class="popup-compare">${vs}</div>` : ""}
    </div>`;
}

function popupHTML(kind, props, city, wardLookup) {
  if (kind === "hexes") {
    const flag = props.within_15 ? "Inside 15 minutes" : "Beyond 15 minutes";
    const clinicN = props.k_clinic == null ? "" : ` (${fmt(props.k_clinic)} of 5 reached)`;
    const schoolN = props.k_school == null ? "" : ` (${fmt(props.k_school)} of 5 reached)`;
    const ward = wardLookup?.get(props.ward);
    const wardName = ward?.label || nonempty(props.ward);
    return `<div class="popup-head">${flag}</div>
      <div class="popup-body">
        <dl>
          ${row("Walk to clinics and schools", props.minutes == null ? "No route" : minutes(props.minutes))}
          ${row("To a clinic", `${minutes(props.clinic_min)}${clinicN}`)}
          ${row("To a school", `${minutes(props.school_min)}${schoolN}`)}
          ${row("People in this neighbourhood", fmt(props.people))}
          ${nonempty(props.lga) ? row("Local government", props.lga) : ""}
          ${props.off_street ? row("Street map", "This tile sits off the mapped walk network") : ""}
        </dl>
      </div>
      ${ward ? wardBlock(ward, city) : wardName ? `<div class="popup-head ward">${wardName}</div><div class="popup-body">No ward score attached to this tile.</div>` : ""}`;
  }
  if (kind === "wards" || kind === "wards-fill" || kind === "labels-wards") {
    return wardBlock(props, city);
  }
  if (kind === "clinics") {
    return `<div class="popup-head clinic">GRID3 clinic</div>
      <div class="popup-body">
        <dl>
          ${row("Name", nonempty(props.name) || "Unnamed")}
          ${nonempty(props.kind_detail) ? row("Type", props.kind_detail) : ""}
          ${nonempty(props.level) ? row("Level", props.level) : ""}
          ${nonempty(props.ownership) ? row("Ownership", props.ownership) : ""}
          ${nonempty(props.ward) ? row("Ward", props.ward) : ""}
          ${nonempty(props.lga) ? row("Local government", props.lga) : ""}
        </dl>
      </div>`;
  }
  if (kind === "schools") {
    return `<div class="popup-head school">GRID3 school</div>
      <div class="popup-body">
        <dl>
          ${row("Name", nonempty(props.name) || "Unnamed")}
          ${nonempty(props.kind_detail) ? row("Type", props.kind_detail) : ""}
          ${nonempty(props.level) ? row("Education", props.level) : ""}
          ${nonempty(props.ownership) ? row("Management", props.ownership) : ""}
          ${nonempty(props.ward) ? row("Ward", props.ward) : ""}
          ${nonempty(props.lga) ? row("Local government", props.lga) : ""}
        </dl>
      </div>`;
  }
  if (kind === "labels-places" || kind === "labels-places-pinned") {
    return `<div class="popup-head">${props.label || props.name}</div>
      <div class="popup-body">${nonempty(props.place) ? props.place : "Named place"}</div>`;
  }
  return "";
}

function renderLegend(theme) {
  const box = document.getElementById("legend");
  const note = document.getElementById("legend-note");
  box.innerHTML = "";
  const add = (html) => {
    const rowEl = document.createElement("div");
    rowEl.className = "legend-row";
    rowEl.innerHTML = html;
    box.appendChild(rowEl);
  };
  if (theme === "people") {
    const city = window.__city;
    (city?.people_breaks || []).forEach((item) => add(`<span class="swatch" style="background:${item.color}"></span>${item.label}`));
    note.textContent = "People living in each 200 m neighbourhood. Tiles with five people or fewer are omitted from the map, not from the city scores.";
    return;
  }
  MINUTE_COLORS.forEach((color, i) => add(`<span class="swatch" style="background:${color}"></span>${MINUTE_LABELS[i]}`));
  add(`<span class="swatch cross"></span>Clinic`);
  add(`<span class="swatch school"></span>School`);
  note.textContent =
    theme === "clinic"
      ? "Walk along mapped streets at 5 km/h to the five nearest clinics."
      : theme === "school"
        ? "Walk along mapped streets at 5 km/h to the five nearest schools."
        : "From each tile: average walk to five clinics, then to five schools, then the mean of those two. Green through yellow is 15 minutes or less.";
}

function renderScores(city) {
  window.__city = city;
  const cards = [
    [pct(city.f15), "People within 15 minutes"],
    [`${city.pt} min`, "Typical walk"],
    [fmt(city.pop), "People on this map"],
    [fmt(city.clinics), `GRID3 clinics (${fmt(city.schools)} schools)`],
  ];
  document.getElementById("score-grid").innerHTML = cards
    .map(([value, label]) => `<div class="score"><div class="score-value">${value}</div><div class="score-label">${label}</div></div>`)
    .join("");
  document.getElementById("city-blurb").textContent = city.blurb;
  const panel = document.getElementById("side-panel");
  panel.heading = city.name;
  panel.description = city.frame ? `${city.frame} · 5 km/h walk` : "Walking at 5 km/h";
  const note = document.getElementById("frame-note");
  if (city.frame_note) {
    note.hidden = false;
    note.textContent = city.frame_note;
  } else {
    note.hidden = true;
    note.textContent = "";
  }
}

function setVisibility(map, id, on) {
  if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
}

function showLoader(on) {
  const el = document.getElementById("boot-loader");
  if (on) {
    el.removeAttribute("hidden");
    el.style.display = "";
  } else {
    el.setAttribute("hidden", "");
    el.style.display = "none";
  }
}

async function loadJSON(path, tries = 3) {
  let last;
  for (let i = 0; i < tries; i += 1) {
    try {
      const res = await fetch(path);
      if (!res.ok) throw new Error(`${path} ${res.status}`);
      return await res.json();
    } catch (err) {
      last = err;
      await new Promise((resolve) => setTimeout(resolve, 250 * (i + 1)));
    }
  }
  throw last;
}

async function main() {
  const meta = await loadJSON("./data/metrics.json");
  document.title = meta.title;
  const cityCache = new Map();
  let loadGen = 0;
  let current = "lagos";
  let theme = "walk";
  let basemap = "gray";
  let hovered = null;
  let wardLookup = new Map();
  let lastBundle = null;

  const map = new maplibregl.Map({
    container: "map",
    style: rasterStyle("gray"),
    center: [8.1, 9.2],
    zoom: 5.6,
    attributionControl: true,
    maxPitch: 60,
    pitch: 0,
  });
  window.__map = map;
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
  map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");

  const popup = new maplibregl.Popup({ closeButton: true, maxWidth: "320px" });

  const cityLayerIds = [
    "labels-clinics",
    "labels-schools",
    "labels-wards",
    "labels-places",
    "labels-places-pinned",
    "clinics",
    "clinics-cluster",
    "schools",
    "schools-cluster",
    "boundary",
    "wards",
    "hexes-line",
    "hexes",
    "wards-fill",
  ];

  const removeCityLayers = () => {
    cityLayerIds.forEach((id) => {
      if (map.getLayer(id)) map.removeLayer(id);
    });
    ["clinics", "schools", "boundary", "wards", "hexes", "places"].forEach((id) => {
      if (map.getSource(id)) map.removeSource(id);
    });
  };

  const beyondFilter = () => {
    const beyond = document.getElementById("beyond-switch").checked;
    return beyond ? ["!", ["to-boolean", ["get", "within_15"]]] : null;
  };

  const applyTheme = () => {
    if (!map.getLayer("hexes")) return;
    const paint = hexPaint(theme, meta.cities[current].people_breaks);
    map.setPaintProperty("hexes", "fill-color", paint["fill-color"]);
    const filter = beyondFilter();
    map.setFilter("hexes", filter);
    map.setFilter("hexes-line", filter);
    renderLegend(theme);
  };

  const applyOverlays = () => {
    const hexesOn = document.getElementById("lyr-hexes").checked;
    setVisibility(map, "hexes", hexesOn);
    setVisibility(map, "hexes-line", hexesOn);
    const clinicsOn = document.getElementById("lyr-clinics").checked;
    setVisibility(map, "clinics", clinicsOn);
    setVisibility(map, "clinics-cluster", clinicsOn);
    setVisibility(map, "labels-clinics", clinicsOn);
    const schoolsOn = document.getElementById("lyr-schools").checked;
    setVisibility(map, "schools", schoolsOn);
    setVisibility(map, "schools-cluster", schoolsOn);
    setVisibility(map, "labels-schools", schoolsOn);
    const wardsOn = document.getElementById("lyr-wards").checked;
    setVisibility(map, "wards", wardsOn);
    setVisibility(map, "wards-fill", wardsOn);
    setVisibility(map, "labels-wards", wardsOn);
    const placesOn = document.getElementById("lyr-places").checked;
    setVisibility(map, "labels-places", placesOn);
    setVisibility(map, "labels-places-pinned", placesOn);
    setVisibility(map, "boundary", document.getElementById("lyr-boundary").checked);
  };

  const insertBefore = () => {
    if (map.getLayer("building-3d")) return "building-3d";
    if (map.getLayer("basemap-labels")) return "basemap-labels";
    const firstSymbol = map.getStyle()?.layers?.find((layer) => layer.type === "symbol");
    return firstSymbol?.id;
  };

  const addCityLayers = (slug, bundle) => {
    lastBundle = bundle;
    removeCityLayers();
    addIcons(map);
    const sparse = slug === "abuja";
    const add = (id, data, extra = {}) => {
      map.addSource(id, { type: "geojson", data: data || EMPTY, generateId: true, ...extra });
    };
    add("hexes", bundle.hexes);
    add("wards", bundle.wards);
    add("boundary", bundle.boundary);
    add("places", bundle.places);
    add("clinics", bundle.clinics, { cluster: true, clusterRadius: 46, clusterMaxZoom: 12 });
    add("schools", bundle.schools, { cluster: true, clusterRadius: 46, clusterMaxZoom: 12 });

    const markSize = sparse
      ? ["interpolate", ["linear"], ["zoom"], 10, 0.42, 14, 0.62, 16, 0.78]
      : ["interpolate", ["linear"], ["zoom"], 10, 0.36, 14, 0.52, 16, 0.68];
    const before = insertBefore();
    const layers = [
      {
        id: "wards-fill",
        type: "fill",
        source: "wards",
        paint: { "fill-color": "#37322e", "fill-opacity": 0 },
      },
      {
        id: "hexes",
        type: "fill",
        source: "hexes",
        paint: hexPaint(theme, meta.cities[slug].people_breaks),
      },
      {
        id: "hexes-line",
        type: "line",
        source: "hexes",
        paint: { "line-color": "#ffffff", "line-opacity": 0.16, "line-width": 0.4 },
      },
      {
        id: "wards",
        type: "line",
        source: "wards",
        paint: { "line-color": WARD_LINE, "line-width": 0.9, "line-opacity": 1 },
      },
      {
        id: "boundary",
        type: "line",
        source: "boundary",
        paint: { "line-color": INK, "line-width": 2.4 },
      },
      {
        id: "schools-cluster",
        type: "circle",
        source: "schools",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": "#9eb6c7",
          "circle-radius": ["step", ["get", "point_count"], 12, 25, 16, 80, 20],
          "circle-stroke-color": SCHOOL,
          "circle-stroke-width": 1,
        },
      },
      {
        id: "clinics-cluster",
        type: "circle",
        source: "clinics",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": "#e4a3a3",
          "circle-radius": ["step", ["get", "point_count"], 12, 25, 16, 80, 20],
          "circle-stroke-color": CLINIC,
          "circle-stroke-width": 1,
        },
      },
      {
        id: "schools",
        type: "symbol",
        source: "schools",
        filter: ["!", ["has", "point_count"]],
        layout: {
          "icon-image": "school-mark",
          "icon-size": markSize,
          "icon-allow-overlap": true,
          "icon-ignore-placement": true,
        },
      },
      {
        id: "clinics",
        type: "symbol",
        source: "clinics",
        filter: ["!", ["has", "point_count"]],
        layout: {
          "icon-image": "clinic-mark",
          "icon-size": markSize,
          "icon-allow-overlap": true,
          "icon-ignore-placement": true,
        },
      },
      {
        id: "labels-places-pinned",
        type: "symbol",
        source: "places",
        minzoom: 9,
        filter: ["any", ["==", ["get", "always"], 1], ["==", ["get", "pinned"], 1]],
        layout: {
          "text-field": ["coalesce", ["get", "label"], ["get", "name"]],
          "text-font": ["Noto Sans Regular"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 9, 11, 12, 13, 15, 15],
          "text-padding": 3,
          "text-max-width": 8,
          "text-variable-anchor": ["center", "top", "bottom", "right", "left"],
          "text-radial-offset": 0.2,
          "symbol-sort-key": ["-", ["coalesce", ["get", "priority"], 0]],
          "text-optional": true,
        },
        paint: { "text-color": PLACE_INK, "text-halo-color": HALO, "text-halo-width": 1.4 },
      },
      {
        id: "labels-places",
        type: "symbol",
        source: "places",
        minzoom: 11,
        filter: ["all", ["!=", ["get", "always"], 1], ["!=", ["get", "pinned"], 1]],
        layout: {
          "text-field": ["coalesce", ["get", "label"], ["get", "name"]],
          "text-font": ["Noto Sans Regular"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 11, 11, 14, 13, 16, 14],
          "text-padding": 4,
          "text-max-width": 8,
          "text-variable-anchor": ["center", "top", "bottom", "right", "left"],
          "text-radial-offset": 0.15,
          "symbol-sort-key": ["-", ["coalesce", ["get", "priority"], ["get", "rank"], 0]],
          "text-optional": true,
        },
        paint: { "text-color": PLACE_INK, "text-halo-color": HALO, "text-halo-width": 1.25 },
      },
      {
        id: "labels-wards",
        type: "symbol",
        source: "wards",
        minzoom: 12.6,
        layout: {
          "text-field": ["coalesce", ["get", "label"], ["get", "name"]],
          "text-font": ["Noto Sans Regular"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 12.6, 10, 15, 12, 17, 13],
          "text-padding": 6,
          "text-max-width": 9,
          "symbol-sort-key": ["-", ["coalesce", ["get", "people"], 0]],
          "text-optional": true,
        },
        paint: { "text-color": "#554e4b", "text-halo-color": HALO, "text-halo-width": 1.2 },
      },
      {
        id: "labels-clinics",
        type: "symbol",
        source: "clinics",
        minzoom: 15.2,
        filter: ["!", ["has", "point_count"]],
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["Noto Sans Regular"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 15.2, 10, 17, 12],
          "text-offset": [0, 1.15],
          "text-optional": true,
          "text-padding": 2,
          "text-max-width": 10,
        },
        paint: { "text-color": CLINIC, "text-halo-color": HALO, "text-halo-width": 1.1 },
      },
      {
        id: "labels-schools",
        type: "symbol",
        source: "schools",
        minzoom: 15.2,
        filter: ["!", ["has", "point_count"]],
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["Noto Sans Regular"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 15.2, 10, 17, 12],
          "text-offset": [0, 1.15],
          "text-optional": true,
          "text-padding": 2,
          "text-max-width": 10,
        },
        paint: { "text-color": SCHOOL, "text-halo-color": HALO, "text-halo-width": 1.1 },
      },
    ];
    const under3d = new Set(["wards-fill", "hexes", "hexes-line"]);
    layers.forEach((layer) => {
      const beforeId = under3d.has(layer.id) ? before : undefined;
      if (beforeId && map.getLayer(beforeId)) map.addLayer(layer, beforeId);
      else map.addLayer(layer);
    });
    applyOverlays();
    applyTheme();
  };

  const edgePadding = () => {
    map.resize();
    const width = map.getContainer().clientWidth || 800;
    const panel = document.querySelector("calcite-shell-panel");
    const panelW = panel ? Math.round(panel.getBoundingClientRect().width) : 0;
    const left = width > panelW + 280 ? panelW + 16 : 48;
    return { top: 64, right: 48, bottom: 48, left };
  };

  const flyToCity = (slug, boundary) => {
    const padding = edgePadding();
    const feat = boundary?.features?.[0];
    const maxZoom = basemap === "color" ? 13.2 : 12.6;
    if (!feat) {
      const bbox = meta.cities[slug].bbox;
      map.fitBounds(
        [
          [bbox[0], bbox[1]],
          [bbox[2], bbox[3]],
        ],
        { padding, duration: 700, maxZoom, pitch: basemap === "color" ? 48 : 0, bearing: 0 }
      );
      return;
    }
    const b = new maplibregl.LngLatBounds();
    const walk = (coords) => {
      if (typeof coords[0] === "number") {
        b.extend(coords);
        return;
      }
      coords.forEach(walk);
    };
    walk(feat.geometry.coordinates);
    try {
      map.fitBounds(b, { padding, duration: 700, maxZoom, pitch: basemap === "color" ? 48 : 0, bearing: 0 });
    } catch (err) {
      map.fitBounds(b, { padding: 40, duration: 700, maxZoom });
    }
  };

  const fetchCity = async (slug) => {
    if (cityCache.has(slug)) return cityCache.get(slug);
    const base = `./data/cities/${slug}`;
    const files = ["hexes", "boundary", "wards", "clinics", "schools"];
    const bundle = {};
    for (const name of files) {
      bundle[name] = await loadJSON(`${base}/${name}.geojson`);
    }
    bundle.places = await loadJSON(`${base}/places.geojson`).catch(() => EMPTY);
    cityCache.set(slug, bundle);
    return bundle;
  };

  const paintCity = (slug, bundle) => {
    wardLookup = new Map((bundle.wards?.features || []).map((f) => [f.properties.name, f.properties]));
    const go = () => {
      try {
        addCityLayers(slug, bundle);
        map.resize();
        requestAnimationFrame(() => {
          flyToCity(slug, bundle.boundary);
          showLoader(false);
        });
      } catch (err) {
        showLoader(false);
        document.getElementById("city-blurb").textContent = String(err);
      }
    };
    if (map.isStyleLoaded()) go();
    else map.once("style.load", go);
  };

  const loadCity = async (slug) => {
    const gen = ++loadGen;
    current = slug;
    showLoader(true);
    renderScores(meta.cities[slug]);
    renderLegend(theme);
    try {
      const bundle = await fetchCity(slug);
      if (gen !== loadGen) return;
      paintCity(slug, bundle);
    } catch (err) {
      if (gen !== loadGen) return;
      showLoader(false);
      document.getElementById("city-blurb").textContent =
        `Map data missing for this city. From the repo root run python -m proximity.web_map. (${err})`;
    }
  };

  const restoreThematic = () => {
    addIcons(map);
    if (lastBundle) addCityLayers(current, lastBundle);
  };

  const isVectorStyle = () => Boolean(map.getSource("openmaptiles"));

  const applyRasterTiles = (key) => {
    const spec = rasterSpec(key);
    const src = map.getSource("basemap");
    if (!src || !src.setTiles) return false;
    src.setTiles(spec.tiles);
    if (spec.labels) {
      if (map.getSource("labels")?.setTiles) {
        map.getSource("labels").setTiles([spec.labels]);
      } else if (!map.getSource("labels")) {
        map.addSource("labels", { type: "raster", tiles: [spec.labels], tileSize: 256, maxzoom: spec.maxzoom });
        if (!map.getLayer("basemap-labels")) {
          map.addLayer({ id: "basemap-labels", type: "raster", source: "labels", paint: { "raster-opacity": 1, "raster-fade-duration": 0 } });
        }
      }
    } else if (map.getLayer("basemap-labels")) {
      map.removeLayer("basemap-labels");
      if (map.getSource("labels")) map.removeSource("labels");
    }
    return true;
  };

  const changeBasemap = (value) => {
    if (value === basemap && !(value === "gray" && isVectorStyle())) {
      if (value !== "color") applyRasterTiles(value);
      return;
    }
    const prev = basemap;
    basemap = value;
    const center = map.getCenter();
    const zoom = map.getZoom();
    const bearing = map.getBearing();

    if (value === "color") {
      map.setStyle(LIBERTY);
      map.once("style.load", () => {
        map.setCenter(center);
        map.setZoom(zoom);
        map.setPitch(48);
        map.setBearing(bearing);
        restoreThematic();
      });
      return;
    }

    if (prev === "color" || isVectorStyle()) {
      map.setStyle(rasterStyle(value));
      map.once("style.load", () => {
        map.setCenter(center);
        map.setZoom(zoom);
        map.setPitch(0);
        map.setBearing(0);
        restoreThematic();
      });
      return;
    }

    applyRasterTiles(value);
    map.setPitch(0);
  };

  map.on("load", () => {
    addIcons(map);
    loadCity("lagos");
    map.resize();
  });

  const hitLayers = [
    "clinics",
    "schools",
    "labels-places-pinned",
    "labels-places",
    "hexes",
    "labels-wards",
    "wards-fill",
  ];

  map.on("mousemove", (e) => {
    const hits = map.queryRenderedFeatures(e.point, { layers: hitLayers.filter((id) => map.getLayer(id)) });
    map.getCanvas().style.cursor = hits.length ? "pointer" : "";
    if (hovered !== null && map.getSource("hexes")) {
      map.setFeatureState({ source: "hexes", id: hovered }, { hover: false });
      hovered = null;
    }
    const hex = hits.find((f) => f.layer.id === "hexes");
    if (hex && hex.id !== undefined) {
      hovered = hex.id;
      map.setFeatureState({ source: "hexes", id: hovered }, { hover: true });
    }
  });

  map.on("click", (e) => {
    try {
      for (const clusterId of ["clinics-cluster", "schools-cluster"]) {
        if (!map.getLayer(clusterId)) continue;
        const clustered = map.queryRenderedFeatures(e.point, { layers: [clusterId] });
        if (clustered.length) {
          const src = map.getSource(clustered[0].source);
          src.getClusterExpansionZoom(clustered[0].properties.cluster_id, (err, zoom) => {
            if (err) return;
            map.easeTo({ center: clustered[0].geometry.coordinates, zoom });
          });
          return;
        }
      }
      const hits = map.queryRenderedFeatures(e.point, { layers: hitLayers.filter((id) => map.getLayer(id)) });
      if (!hits.length) {
        popup.remove();
        return;
      }
      const prefer = hitLayers.find((id) => hits.some((f) => f.layer.id === id));
      const f = hits.find((h) => h.layer.id === prefer) || hits[0];
      const props = { ...f.properties };
      if (f.layer.id === "hexes" && !props.ward) {
        const wf = hits.find((h) => h.layer.id === "wards-fill");
        if (wf?.properties?.name) props.ward = wf.properties.name;
      }
      popup
        .setLngLat(e.lngLat)
        .setHTML(popupHTML(f.layer.id, props, meta.cities[current], wardLookup))
        .addTo(map);
    } catch (err) {
      console.error(err);
      document.getElementById("city-blurb").textContent = String(err);
    }
  });

  const bindSelect = (id, fn) => {
    document.getElementById(id).addEventListener("calciteSelectChange", fn);
  };
  bindSelect("city-select", (e) => loadCity(e.target.value));
  bindSelect("theme-select", (e) => {
    theme = e.target.value;
    applyTheme();
  });
  document.getElementById("beyond-switch").addEventListener("calciteSwitchChange", applyTheme);
  ["lyr-hexes", "lyr-clinics", "lyr-schools", "lyr-wards", "lyr-places", "lyr-boundary"].forEach((id) => {
    document.getElementById(id).addEventListener("calciteCheckboxChange", applyOverlays);
  });

  const syncBasemapControls = (value) => {
    const toggle = document.getElementById("basemap-toggle");
    const select = document.getElementById("basemap-select");
    if (toggle) toggle.value = value;
    if (select) select.value = value;
  };
  document.getElementById("basemap-toggle").addEventListener("calciteSegmentedControlChange", (e) => {
    syncBasemapControls(e.target.value);
    changeBasemap(e.target.value);
  });
  bindSelect("basemap-select", (e) => {
    syncBasemapControls(e.target.value);
    changeBasemap(e.target.value);
  });

  document.getElementById("theme-toggle").addEventListener("click", () => {
    const dark = !isDark();
    document.documentElement.classList.toggle("calcite-mode-dark", dark);
    document.documentElement.classList.toggle("calcite-mode-light", !dark);
    const action = document.getElementById("theme-toggle");
    action.icon = dark ? "brightness" : "moon";
    action.text = dark ? "Light" : "Dark";
    if (basemap === "gray" && !isVectorStyle()) applyRasterTiles("gray");
  });
}

main().catch((err) => {
  document.body.insertAdjacentHTML(
    "beforeend",
    `<calcite-alert open kind="danger" label="Map failed"><div slot="title">The map could not start</div><div slot="message">${err}</div></calcite-alert>`
  );
});
