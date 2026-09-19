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
const ASSET = "19";
const ESRI_CREDIT = "Tiles © Esri · GRID3 clinics and schools";

const EMPTY = { type: "FeatureCollection", features: [] };

const bust = (url) => `${url}${url.includes("?") ? "&" : "?"}v=${ASSET}`;

const RASTER = {
  gray: {
    light: {
      tiles: [bust("https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}")],
      labels: bust("https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}"),
    },
    dark: {
      tiles: [bust("https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}")],
      labels: bust("https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}"),
    },
    maxzoom: 16,
    attribution: ESRI_CREDIT,
  },
  imagery: {
    tiles: [bust("https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}")],
    labels: bust("https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"),
    maxzoom: 19,
    attribution: ESRI_CREDIT,
  },
  streets: {
    tiles: [bust("https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}")],
    maxzoom: 19,
    attribution: ESRI_CREDIT,
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
  if (key === "streets") return RASTER.streets;
  return RASTER.imagery;
}

function rasterPaint(key) {
  const darkStreets = isDark() && key === "streets";
  return {
    "raster-opacity": 1,
    "raster-fade-duration": 0,
    "raster-brightness-min": darkStreets ? 0.06 : 0,
    "raster-brightness-max": darkStreets ? 0.76 : 1,
    "raster-saturation": darkStreets ? -0.15 : 0,
  };
}

function isRasterBasemap(key) {
  return key === "gray" || key === "streets" || key === "imagery";
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
  const paint = rasterPaint(key);
  const layers = [
    { id: "bg", type: "background", paint: { "background-color": isDark() ? "#1a1a1a" : "#e5e5e5" } },
    { id: "basemap", type: "raster", source: "basemap", paint },
  ];
  const sources = {
    basemap: { type: "raster", tiles: spec.tiles, tileSize: 256, maxzoom: spec.maxzoom, attribution: spec.attribution },
  };
  if (spec.labels) {
    sources.labels = { type: "raster", tiles: [spec.labels], tileSize: 256, maxzoom: spec.maxzoom };
    layers.push({ id: "basemap-labels", type: "raster", source: "labels", paint });
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

function rasterIcon(draw, size = 40) {
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
  if (!map.getStyle()) return;
  const clinic = rasterIcon((ctx, size) => {
    const r = 7;
    ctx.fillStyle = CLINIC;
    ctx.strokeStyle = "rgba(255,255,255,0.95)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(2, 2, size - 4, size - 4, r);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#fff";
    const arm = 5;
    const bar = 16;
    ctx.fillRect((size - arm) / 2, (size - bar) / 2, arm, bar);
    ctx.fillRect((size - bar) / 2, (size - arm) / 2, bar, arm);
  });
  const school = rasterIcon((ctx, size) => {
    ctx.fillStyle = SCHOOL;
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 2 - 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.95)";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = "#fff";
    ctx.beginPath();
    ctx.moveTo(size / 2, 8);
    ctx.lineTo(size * 0.78, 17);
    ctx.lineTo(size * 0.22, 17);
    ctx.closePath();
    ctx.fill();
    ctx.fillRect(size * 0.32, 17, size * 0.36, 12);
    ctx.fillRect(size / 2 - 2.2, 21, 4.4, 8);
    ctx.fillRect(size / 2 - 1, 6, 2, 4);
  });
  const shield = rasterIcon((ctx, size) => {
    ctx.fillStyle = "#ffffff";
    ctx.strokeStyle = "rgba(28,25,22,0.28)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.roundRect(2, 2, size - 4, size - 4, 8);
    ctx.fill();
    ctx.stroke();
  }, 64);
  try {
    ["clinic-mark", "school-mark", "name-shield"].forEach((id) => {
      if (map.hasImage(id)) map.removeImage(id);
    });
    map.addImage("clinic-mark", clinic);
    map.addImage("school-mark", school);
    map.addImage("name-shield", shield, {
      content: [12, 12, 52, 52],
      stretchX: [[12, 52]],
      stretchY: [[12, 52]],
      pixelRatio: 1,
    });
  } catch (err) {
    console.warn(err);
  }
}

function row(label, value) {
  return `<dt>${label}</dt><dd>${value}</dd>`;
}

function giniText(v) {
  if (v == null || Number.isNaN(Number(v))) return "n/a";
  return Number(v).toFixed(2);
}

function nstarLine(city) {
  if (city?.nstar == null) return "";
  const stock = city.nstar_vs_stock != null && city.nstar_vs_stock > 1
    ? ` That is more than the ${fmt(city.clinics)} clinics on this map.`
    : ` This map already shows ${fmt(city.clinics)} clinics.`;
  return `N* is ${fmt(city.nstar)} well-placed clinics to cover 90% of people.${stock}`;
}

function cityContext(city) {
  if (!city) return "";
  const parts = [];
  if (city.gini != null) {
    parts.push(`City Gini is ${giniText(city.gini)}. Zero would mean everyone walks the same; one would mean a long far tail.`);
  }
  const nstar = nstarLine(city);
  if (nstar) parts.push(nstar);
  return parts.length ? `<div class="popup-compare">${parts.join(" ")}</div>` : "";
}

function wardBlock(props, city, { heading = true, cityStats = true } = {}) {
  if (!props) return "";
  const name = props.label || props.name || "Ward";
  const lga = nonempty(props.lga);
  const rank =
    props.rank != null && props.of != null
      ? `${fmt(props.rank)} of ${fmt(props.of)} wards by share within 15 minutes`
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
        ${props.gini != null ? row("How uneven walks are here (Gini)", giniText(props.gini)) : ""}
        ${cityStats && city?.gini != null ? row("How uneven walks are in the city (Gini)", giniText(city.gini)) : ""}
        ${cityStats && city?.nstar != null ? row("Well-placed clinics for 90% (N*)", `${fmt(city.nstar)} for the city`) : ""}
        ${rank ? row("Standing in this city", rank) : ""}
      </dl>
      ${cityStats ? cityContext(city) : ""}
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
          ${city?.gini != null ? row("How uneven walks are in the city (Gini)", giniText(city.gini)) : ""}
          ${city?.nstar != null ? row("Well-placed clinics for 90% (N*)", `${fmt(city.nstar)} for the city`) : ""}
        </dl>
        ${cityContext(city)}
      </div>
      ${ward ? wardBlock(ward, city, { cityStats: false }) : wardName ? `<div class="popup-head ward">${wardName}</div><div class="popup-body">No ward score attached to this tile.</div>` : ""}`;
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
        ${cityContext(city)}
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
        ${cityContext(city)}
      </div>`;
  }
  if (kind === "labels-places" || kind === "labels-places-pinned") {
    return `<div class="popup-head">${props.label || props.name}</div>
      <div class="popup-body">${nonempty(props.place) ? props.place : "Named place"}${cityContext(city)}</div>`;
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
    [city.gini != null ? giniText(city.gini) : "n/a", "How uneven the walks are (Gini)"],
    [city.nstar != null ? fmt(city.nstar) : "n/a", "Well-placed clinics for 90% (N*)"],
  ];
  document.getElementById("score-grid").innerHTML = cards
    .map(([value, label]) => `<div class="score"><div class="score-value">${value}</div><div class="score-label">${label}</div></div>`)
    .join("");
  document.getElementById("city-blurb").textContent = city.blurb;
  const clinicsEl = document.getElementById("count-clinics");
  const schoolsEl = document.getElementById("count-schools");
  if (clinicsEl) clinicsEl.textContent = city.clinics != null ? `(${fmt(city.clinics)})` : "";
  if (schoolsEl) schoolsEl.textContent = city.schools != null ? `(${fmt(city.schools)})` : "";
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
  const url = bust(path);
  for (let i = 0; i < tries; i += 1) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) throw new Error(`${path} ${res.status}`);
      return await res.json();
    } catch (err) {
      last = err;
      await new Promise((resolve) => setTimeout(resolve, 250 * (i + 1)));
    }
  }
  throw last;
}

const MOBILE_MQ = "(max-width: 860px)";
function isMobile() {
  return window.matchMedia(MOBILE_MQ).matches;
}

async function main() {
  const meta = await loadJSON("./data/metrics.json");
  document.title = meta.title;
  const cityData = new Map();
  const cityWait = new Map();
  let loadGen = 0;
  let paintSeq = 0;
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
    attributionControl: false,
    maxPitch: 60,
    pitch: 0,
    cooperativeGestures: false,
    fadeDuration: 0,
    refreshExpiredTiles: true,
    dragRotate: !isMobile(),
    touchPitch: !isMobile(),
    transformRequest: (url, resourceType) => {
      if (resourceType === "Tile" && /arcgisonline\.com/.test(url) && !/[?&]v=/.test(url)) {
        return { url: bust(url) };
      }
      return { url };
    },
  });
  window.__map = map;
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: !isMobile(), showCompass: !isMobile() }), "bottom-right");
  map.addControl(new maplibregl.ScaleControl({ unit: "metric", maxWidth: isMobile() ? 72 : 100 }), "bottom-left");
  map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
  if (isMobile() && map.touchZoomRotate) map.touchZoomRotate.disableRotation();

  const popup = new maplibregl.Popup({
    closeButton: true,
    maxWidth: "min(320px, calc(100vw - 20px))",
    offset: 12,
  });

  const cityLayerIds = [
    "labels-clinics",
    "labels-schools",
    "labels-wards",
    "labels-places",
    "labels-places-pinned",
    "clinics",
    "schools",
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

  const hexAccessFilter = () => {
    const within = document.getElementById("within-switch")?.checked;
    const beyond = document.getElementById("beyond-switch")?.checked;
    if (within) return ["==", ["get", "within_15"], 1];
    if (beyond) return ["!=", ["get", "within_15"], 1];
    return null;
  };

  const applyTheme = () => {
    if (!map.getLayer("hexes")) return;
    const paint = hexPaint(theme, meta.cities[current].people_breaks);
    map.setPaintProperty("hexes", "fill-color", paint["fill-color"]);
    const filter = hexAccessFilter();
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
    setVisibility(map, "labels-clinics", clinicsOn);
    const schoolsOn = document.getElementById("lyr-schools").checked;
    setVisibility(map, "schools", schoolsOn);
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

  const applyMapChrome = () => {
    const dark = isDark();
    const place = dark ? "#f3eee8" : PLACE_INK;
    const halo = dark ? "#111111" : HALO;
    const wardText = dark ? "#e6e1db" : "#554e4b";
    const boundary = dark ? "#f0f0f0" : INK;
    const wardLine = dark ? "rgba(230,230,230,0.55)" : WARD_LINE;
    const setText = (id, color, buffer = 1.4, haloColor = halo) => {
      if (!map.getLayer(id)) return;
      map.setPaintProperty(id, "text-color", color);
      map.setPaintProperty(id, "text-halo-color", haloColor);
      map.setPaintProperty(id, "text-halo-width", buffer);
      map.setPaintProperty(id, "text-halo-blur", buffer > 2 ? 0.45 : 0.2);
    };
    setText("labels-places", place, 1.6);
    setText("labels-places-pinned", place, 1.6);
    setText("labels-wards", wardText, 1.5);
    setText("labels-clinics", "#1c1916", 0.2, "#ffffff");
    setText("labels-schools", "#1c1916", 0.2, "#ffffff");
    if (map.getLayer("boundary")) map.setPaintProperty("boundary", "line-color", boundary);
    if (map.getLayer("wards")) map.setPaintProperty("wards", "line-color", wardLine);
  };

  const addCityLayers = (slug, bundle) => {
    lastBundle = bundle;
    removeCityLayers();
    addIcons(map);
    const sparse = slug === "abuja";
    const add = (id, data, extra = {}) => {
      map.addSource(id, { type: "geojson", data: data || EMPTY, ...extra });
    };
    add("hexes", bundle.hexes, { generateId: true });
    add("wards", bundle.wards, { generateId: true });
    add("boundary", bundle.boundary);
    add("places", bundle.places);
    add("clinics", bundle.clinics);
    add("schools", bundle.schools);

    const markSize = sparse
      ? ["interpolate", ["linear"], ["zoom"], 12, 0.14, 14, 0.28, 16, 0.44]
      : ["interpolate", ["linear"], ["zoom"], 12.8, 0.14, 14, 0.24, 16, 0.38];
    const markMinZoom = sparse ? 12 : 12.8;
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
        id: "schools",
        type: "symbol",
        source: "schools",
        minzoom: markMinZoom,
        layout: {
          "icon-image": "school-mark",
          "icon-size": markSize,
          "icon-allow-overlap": true,
          "icon-ignore-placement": true,
          "icon-padding": 0,
          "icon-anchor": "center",
        },
      },
      {
        id: "clinics",
        type: "symbol",
        source: "clinics",
        minzoom: markMinZoom,
        layout: {
          "icon-image": "clinic-mark",
          "icon-size": markSize,
          "icon-allow-overlap": true,
          "icon-ignore-placement": true,
          "icon-padding": 0,
          "icon-anchor": "center",
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
        minzoom: 14.8,
        layout: {
          "icon-image": "name-shield",
          "icon-text-fit": "both",
          "icon-text-fit-padding": [5, 7, 5, 7],
          "icon-allow-overlap": false,
          "icon-ignore-placement": false,
          "icon-anchor": "top",
          "text-anchor": "top",
          "text-offset": [0, 1.2],
          "text-field": ["get", "name"],
          "text-font": ["Noto Sans Bold"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 14.8, 11.5, 17, 13.5],
          "text-optional": true,
          "text-padding": 8,
          "text-max-width": 11,
        },
        paint: { "text-color": "#1c1916", "text-halo-color": "#ffffff", "text-halo-width": 0.2 },
      },
      {
        id: "labels-schools",
        type: "symbol",
        source: "schools",
        minzoom: 14.8,
        layout: {
          "icon-image": "name-shield",
          "icon-text-fit": "both",
          "icon-text-fit-padding": [5, 7, 5, 7],
          "icon-allow-overlap": false,
          "icon-ignore-placement": false,
          "icon-anchor": "top",
          "text-anchor": "top",
          "text-offset": [0, 1.2],
          "text-field": ["get", "name"],
          "text-font": ["Noto Sans Bold"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 14.8, 11.5, 17, 13.5],
          "text-optional": true,
          "text-padding": 8,
          "text-max-width": 11,
        },
        paint: { "text-color": "#1c1916", "text-halo-color": "#ffffff", "text-halo-width": 0.2 },
      },
    ];
    layers.forEach((layer) => map.addLayer(layer));
    applyOverlays();
    applyTheme();
    applyMapChrome();
  };

  const updateCityData = (slug, bundle) => {
    lastBundle = bundle;
    map.getSource("hexes").setData(bundle.hexes || EMPTY);
    map.getSource("wards").setData(bundle.wards || EMPTY);
    map.getSource("boundary").setData(bundle.boundary || EMPTY);
    map.getSource("places").setData(bundle.places || EMPTY);
    map.getSource("clinics").setData(bundle.clinics || EMPTY);
    map.getSource("schools").setData(bundle.schools || EMPTY);
    applyOverlays();
    applyTheme();
  };

  const basemapPitch = () => {
    if (basemap !== "color") return 0;
    return isMobile() ? 28 : 48;
  };

  const edgePadding = () => {
    map.resize();
    if (isMobile()) {
      const open = !document.getElementById("layers-panel").collapsed;
      return { top: 56, right: 18, bottom: open ? 72 : 56, left: 18 };
    }
    const width = map.getContainer().clientWidth || 800;
    const panel = document.getElementById("layers-panel");
    const panelW = panel && !panel.collapsed ? Math.round(panel.getBoundingClientRect().width) : 0;
    const left = width > panelW + 280 ? panelW + 16 : 48;
    return { top: 64, right: 48, bottom: 48, left };
  };

  const flyToCity = (slug, boundary) => {
    const padding = edgePadding();
    const feat = boundary?.features?.[0];
    const maxZoom = basemap === "color" ? (isMobile() ? 13.0 : 13.2) : isMobile() ? 12.8 : 12.6;
    const minZoom = isMobile() ? 11.6 : 10.8;
    const pitch = basemapPitch();
    const camera = { padding, duration: 420, maxZoom, pitch, bearing: 0 };
    const clamp = () => {
      if (map.getZoom() < minZoom) map.easeTo({ zoom: minZoom, duration: 180 });
    };
    if (!feat) {
      const bbox = meta.cities[slug].bbox;
      map.fitBounds(
        [
          [bbox[0], bbox[1]],
          [bbox[2], bbox[3]],
        ],
        camera
      );
      map.once("moveend", clamp);
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
      map.fitBounds(b, camera);
    } catch (err) {
      map.fitBounds(b, { padding: 24, duration: 700, maxZoom, pitch });
    }
    map.once("moveend", clamp);
  };

  const fetchCity = (slug) => {
    if (cityData.has(slug)) return Promise.resolve(cityData.get(slug));
    if (cityWait.has(slug)) return cityWait.get(slug);
    const base = `./data/cities/${slug}`;
    const names = ["hexes", "boundary", "wards", "clinics", "schools", "places"];
    const bundle = {};
    let cursor = 0;
    const worker = async () => {
      while (cursor < names.length) {
        const name = names[cursor];
        cursor += 1;
        bundle[name] =
          name === "places"
            ? await loadJSON(`${base}/${name}.geojson`).catch(() => EMPTY)
            : await loadJSON(`${base}/${name}.geojson`);
      }
    };
    const pending = Promise.all([worker(), worker(), worker()])
      .then(() => {
        cityData.set(slug, bundle);
        cityWait.delete(slug);
        return bundle;
      })
      .catch((err) => {
        cityWait.delete(slug);
        throw err;
      });
    cityWait.set(slug, pending);
    return pending;
  };

  let warmed = false;
  const prefetchOthers = () => {
    if (warmed) return;
    warmed = true;
    const rest = (meta.order || Object.keys(meta.cities)).filter((slug) => slug !== current);
    rest.reduce((chain, slug) => chain.then(() => fetchCity(slug).catch(() => null)), Promise.resolve());
  };

  const paintCity = (slug, bundle) => {
    const seq = ++paintSeq;
    wardLookup = new Map((bundle.wards?.features || []).map((f) => [f.properties.name, f.properties]));
    const city = { ...meta.cities[slug] };
    city.clinics = bundle.clinics?.features?.length ?? city.clinics;
    city.schools = bundle.schools?.features?.length ?? city.schools;
    renderScores(city);
    let painted = false;
    const go = () => {
      if (painted || seq !== paintSeq) return;
      try {
        if (!map.getStyle()) return;
        if (map.getSource("hexes")) updateCityData(slug, bundle);
        else addCityLayers(slug, bundle);
      } catch (err) {
        return;
      }
      painted = true;
      map.resize();
      flyToCity(slug, bundle.boundary);
      showLoader(false);
      prefetchOthers();
    };
    go();
    if (!painted) {
      map.once("style.load", go);
      setTimeout(go, 250);
    }
  };

  const loadCity = async (slug) => {
    const gen = ++loadGen;
    current = slug;
    renderScores(meta.cities[slug]);
    renderLegend(theme);
    const firstPaint = !lastBundle;
    if (firstPaint) showLoader(true);
    else if (!cityData.has(slug)) {
      document.getElementById("side-panel").description = "Loading…";
    }
    try {
      const bundle = await fetchCity(slug);
      if (gen !== loadGen) return;
      paintCity(slug, bundle);
    } catch (err) {
      if (gen !== loadGen) return;
      showLoader(false);
      document.getElementById("city-blurb").textContent =
        `Could not load ${meta.cities[slug]?.name || slug} from the server. Refresh the page.`;
    }
  };

  const firstCityLayer = () => ["wards-fill", "hexes", "hexes-line", "wards"].find((id) => map.getLayer(id));

  const afterStyle = (fn) => {
    let done = false;
    const run = () => {
      if (done) return;
      done = true;
      fn();
    };
    if (map.isStyleLoaded()) {
      run();
      return;
    }
    map.once("style.load", run);
    const poll = setInterval(() => {
      if (map.isStyleLoaded()) {
        clearInterval(poll);
        run();
      }
    }, 120);
    setTimeout(() => {
      clearInterval(poll);
      run();
    }, 2200);
  };

  const restoreThematic = () => {
    addIcons(map);
    if (lastBundle) addCityLayers(current, lastBundle);
  };

  const isVectorStyle = () => Boolean(map.getSource("openmaptiles"));

  const applyRasterPaint = (key = basemap) => {
    const paint = rasterPaint(key);
    ["basemap", "basemap-labels"].forEach((id) => {
      if (!map.getLayer(id)) return;
      Object.entries(paint).forEach(([prop, value]) => map.setPaintProperty(id, prop, value));
    });
  };

  const applyRasterTiles = (key) => {
    const spec = rasterSpec(key);
    const src = map.getSource("basemap");
    if (!src || !src.setTiles) return false;
    src.setTiles(spec.tiles);
    const under = firstCityLayer();
    if (spec.labels) {
      if (map.getSource("labels")?.setTiles) {
        map.getSource("labels").setTiles([spec.labels]);
      } else if (!map.getSource("labels")) {
        map.addSource("labels", { type: "raster", tiles: [spec.labels], tileSize: 256, maxzoom: spec.maxzoom });
      }
      if (!map.getLayer("basemap-labels")) {
        const layer = { id: "basemap-labels", type: "raster", source: "labels", paint: rasterPaint(key) };
        if (under && map.getLayer(under)) map.addLayer(layer, under);
        else map.addLayer(layer);
      } else if (under) {
        try {
          map.moveLayer("basemap-labels", under);
        } catch (err) {
          /* already below */
        }
      }
    } else if (map.getLayer("basemap-labels")) {
      map.removeLayer("basemap-labels");
      if (map.getSource("labels")) map.removeSource("labels");
    }
    applyRasterPaint(key);
    return true;
  };

  const changeBasemap = (value) => {
    const camera = {
      center: map.getCenter(),
      zoom: map.getZoom(),
      bearing: map.getBearing(),
    };
    const prev = basemap;
    const same = value === basemap && !(isRasterBasemap(value) && isVectorStyle());
    if (same && value !== "color") {
      applyRasterTiles(value);
      return;
    }
    const swapRaster = isRasterBasemap(prev) && isRasterBasemap(value) && prev !== value && !isVectorStyle();
    basemap = value;

    if (value === "color") {
      map.setStyle(LIBERTY, { diff: false });
      afterStyle(() => {
        map.jumpTo({ ...camera, pitch: basemapPitch() });
        restoreThematic();
      });
      return;
    }

    if (prev === "color" || isVectorStyle() || swapRaster || !map.getSource("basemap")?.setTiles) {
      map.setStyle(rasterStyle(value), { diff: false });
      afterStyle(() => {
        map.jumpTo({ ...camera, pitch: 0 });
        restoreThematic();
      });
      return;
    }

    applyRasterTiles(value);
    map.setPitch(0);
  };

  map.on("styleimagemissing", (e) => {
    if (e.id === "clinic-mark" || e.id === "school-mark" || e.id === "name-shield") addIcons(map);
  });

  let started = false;
  const start = () => {
    if (started) return;
    started = true;
    map.resize();
    addIcons(map);
    loadCity("lagos");
  };
  map.on("load", start);
  map.on("style.load", () => map.resize());
  if (window.ResizeObserver) new ResizeObserver(() => map.resize()).observe(document.getElementById("map"));
  setTimeout(start, 400);

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
      const hits = map.queryRenderedFeatures(e.point, { layers: hitLayers.filter((id) => map.getLayer(id)) });
      if (!hits.length) {
        popup.remove();
        return;
      }
      const prefer = hitLayers.find((id) => hits.some((f) => f.layer.id === id));
      const f = hits.find((h) => h.layer.id === prefer) || hits[0];
      const kind = f.layer.id.replace(/-dot$/, "");
      const props = { ...f.properties };
      if (kind === "hexes" && !props.ward) {
        const wf = hits.find((h) => h.layer.id === "wards-fill");
        if (wf?.properties?.name) props.ward = wf.properties.name;
      }
      popup
        .setLngLat(e.lngLat)
        .setHTML(popupHTML(kind, props, meta.cities[current], wardLookup))
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
  const bindAccessSwitch = (id, otherId) => {
    document.getElementById(id)?.addEventListener("calciteSwitchChange", (e) => {
      if (e.target.checked) {
        const other = document.getElementById(otherId);
        if (other) other.checked = false;
      }
      applyTheme();
    });
  };
  bindAccessSwitch("within-switch", "beyond-switch");
  bindAccessSwitch("beyond-switch", "within-switch");
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

  const setAppearance = (dark) => {
    document.documentElement.classList.toggle("calcite-mode-dark", dark);
    document.documentElement.classList.toggle("calcite-mode-light", !dark);
    const action = document.getElementById("theme-toggle");
    if (action) {
      action.icon = dark ? "brightness" : "moon";
      action.text = dark ? "Light" : "Dark";
    }
    const darkSwitch = document.getElementById("dark-switch");
    if (darkSwitch) darkSwitch.checked = dark;
    const themeMeta = document.querySelector("meta[name='theme-color']");
    if (themeMeta) themeMeta.setAttribute("content", dark ? "#1a1a1a" : "#0079c1");
    if (isRasterBasemap(basemap) && basemap !== "imagery" && !isVectorStyle()) applyRasterTiles(basemap);
    else applyRasterPaint();
    applyMapChrome();
  };

  const setPanelOpen = (open) => {
    const shellPanel = document.getElementById("layers-panel");
    const panel = document.getElementById("side-panel");
    const menu = document.getElementById("menu-toggle");
    const fab = document.getElementById("layers-fab");
    shellPanel.collapsed = !open;
    if (open) panel.closed = false;
    if (menu) menu.icon = open ? "x" : "hamburger";
    if (fab) fab.hidden = open;
    requestAnimationFrame(() => map.resize());
  };

  const applyMobileChrome = ({ crossing = false } = {}) => {
    const mobile = isMobile();
    const shellPanel = document.getElementById("layers-panel");
    const panel = document.getElementById("side-panel");
    const logo = document.getElementById("nav-logo");
    shellPanel.slot = "panel-start";
    shellPanel.displayMode = mobile ? "overlay" : "dock";
    shellPanel.resizable = true;
    panel.closable = mobile;
    if (logo) {
      logo.heading = mobile ? "15 min on foot" : "Fifteen minutes on foot";
      logo.description = mobile ? "Clinics and schools" : "Walking to clinics and schools";
    }
    if (crossing) setPanelOpen(!mobile);
    map.resize();
  };

  document.getElementById("theme-toggle").addEventListener("click", () => setAppearance(!isDark()));
  document.getElementById("dark-switch").addEventListener("calciteSwitchChange", (e) => setAppearance(e.target.checked));
  document.getElementById("menu-toggle").addEventListener("click", () => {
    setPanelOpen(document.getElementById("layers-panel").collapsed);
  });
  document.getElementById("layers-fab")?.addEventListener("click", () => {
    setPanelOpen(document.getElementById("layers-panel").collapsed);
  });
  document.getElementById("side-panel").addEventListener("calcitePanelClose", () => setPanelOpen(false));

  const panelEl = document.getElementById("layers-panel");
  if (window.ResizeObserver) new ResizeObserver(() => map.resize()).observe(panelEl);

  let lastMobile = isMobile();
  applyMobileChrome({ crossing: true });
  const mq = window.matchMedia(MOBILE_MQ);
  const onBreakpoint = () => {
    const mobile = mq.matches;
    applyMobileChrome({ crossing: mobile !== lastMobile });
    lastMobile = mobile;
  };
  if (mq.addEventListener) mq.addEventListener("change", onBreakpoint);
  else mq.addListener(onBreakpoint);
  window.addEventListener("orientationchange", () => setTimeout(() => map.resize(), 300));
  window.visualViewport?.addEventListener("resize", () => map.resize());
  setAppearance(true);
}

main().catch((err) => {
  document.body.insertAdjacentHTML(
    "beforeend",
    `<calcite-alert open kind="danger" label="Map failed"><div slot="title">The map could not start</div><div slot="message">${err}</div></calcite-alert>`
  );
});
