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

const VIEW_KEYS = ["city", "color", "theme", "bm", "within", "beyond", "max", "off", "lat", "lng", "z"];

function foldText(s) {
  return String(s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[–—]/g, "-")
    .replace(/\s+/g, " ")
    .trim();
}

function walkCoords(coords, fn) {
  if (typeof coords[0] === "number") {
    fn(coords);
    return;
  }
  coords.forEach((c) => walkCoords(c, fn));
}

function featureBounds(feat) {
  if (!feat?.geometry) return null;
  const b = new maplibregl.LngLatBounds();
  walkCoords(feat.geometry.coordinates, (c) => b.extend(c));
  return b.isEmpty() ? null : b;
}

function featureCenter(feat) {
  if (feat?.geometry?.type === "Point") return feat.geometry.coordinates.slice();
  const b = featureBounds(feat);
  if (!b) return null;
  const c = b.getCenter();
  return [c.lng, c.lat];
}

function pointInRing(point, ring) {
  const [x, y] = point;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / ((yj - yi) || 1e-12) + xi) inside = !inside;
  }
  return inside;
}

function pointInFeature(point, feat) {
  const g = feat?.geometry;
  if (!g) return false;
  if (g.type === "Polygon") return pointInRing(point, g.coordinates[0]);
  if (g.type === "MultiPolygon") return g.coordinates.some((poly) => pointInRing(point, poly[0]));
  return false;
}

function hexCentroid(feat) {
  const ring = feat?.geometry?.coordinates?.[0];
  if (!ring?.length) return null;
  const n = Math.max(1, ring.length - 1);
  let x = 0;
  let y = 0;
  for (let i = 0; i < n; i += 1) {
    x += ring[i][0];
    y += ring[i][1];
  }
  return [x / n, y / n];
}

function matchScore(query, name) {
  const q = foldText(query);
  const n = foldText(name);
  if (!q || !n) return null;
  if (n === q) return 0;
  if (n.startsWith(q)) return 1;
  if (n.split(/[\s-/]+/).some((part) => part.startsWith(q))) return 2;
  if (n.includes(q)) return 3;
  return null;
}

function readView() {
  const q = new URLSearchParams(location.search);
  const city = q.get("city");
  const theme = q.get("color") || q.get("theme");
  const bm = q.get("bm");
  const lat = parseFloat(q.get("lat"));
  const lng = parseFloat(q.get("lng"));
  const z = parseFloat(q.get("z"));
  const max = parseFloat(q.get("max"));
  return {
    city,
    theme,
    basemap: bm,
    within: q.get("within") === "1",
    beyond: q.get("beyond") === "1",
    cutoff: Number.isFinite(max) ? max : null,
    hideCutoff: Number.isFinite(max),
    off: q.get("off") === "1",
    camera: Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lng, zoom: Number.isFinite(z) ? z : 12.4 } : null,
  };
}

function peopleUnderCutoff(hexes, field, cutoff) {
  let inBar = 0;
  let all = 0;
  (hexes?.features || []).forEach((feat) => {
    const people = Number(feat.properties?.people) || 0;
    all += people;
    const minutes = feat.properties?.[field];
    if (minutes != null && Number(minutes) <= cutoff) inBar += people;
  });
  if (!all) return null;
  return (100 * inBar) / all;
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

function hatchImage() {
  const size = 16;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  ctx.strokeStyle = "rgba(16,16,16,0.78)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(-2, 8);
  ctx.lineTo(8, -2);
  ctx.moveTo(0, 16);
  ctx.lineTo(16, 0);
  ctx.moveTo(8, 18);
  ctx.lineTo(18, 8);
  ctx.stroke();
  ctx.strokeStyle = "rgba(255,255,255,0.62)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(-1, 11);
  ctx.lineTo(11, -1);
  ctx.moveTo(3, 18);
  ctx.lineTo(18, 3);
  ctx.stroke();
  return ctx.getImageData(0, 0, size, size);
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
  try {
    if (map.hasImage("clinic-mark")) map.removeImage("clinic-mark");
    if (map.hasImage("school-mark")) map.removeImage("school-mark");
    if (map.hasImage("name-shield")) map.removeImage("name-shield");
    if (map.hasImage("off-hatch")) map.removeImage("off-hatch");
    map.addImage("clinic-mark", clinic);
    map.addImage("school-mark", school);
    map.addImage("off-hatch", hatchImage());
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
  let pickedWard = null;
  let wardLookup = new Map();
  let lastBundle = null;
  let searchItems = [];
  let holdCamera = false;
  let bootColor = false;
  let locateAfter = null;
  let urlTimer = 0;
  const initial = readView();
  if (initial.city && meta.cities[initial.city]) current = initial.city;
  if (initial.theme && ["walk", "clinic", "school", "people"].includes(initial.theme)) theme = initial.theme;
  if (initial.basemap && ["gray", "streets", "color", "imagery"].includes(initial.basemap)) basemap = initial.basemap;
  holdCamera = Boolean(initial.camera);
  bootColor = initial.basemap === "color";

  const map = new maplibregl.Map({
    container: "map",
    style: rasterStyle(basemap === "color" ? "gray" : basemap),
    center: initial.camera ? [initial.camera.lng, initial.camera.lat] : [8.1, 9.2],
    zoom: initial.camera ? initial.camera.zoom : 5.6,
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
    focusAfterOpen: false,
    maxWidth: "min(320px, calc(100vw - 24px))",
    offset: 12,
    className: "access-popup",
  });

  const popupInsets = () => {
    const mapRect = map.getContainer().getBoundingClientRect();
    const nav = document.querySelector("calcite-navigation");
    const panel = document.getElementById("layers-panel");
    const fab = document.getElementById("layers-fab");
    const top = Math.max(8, (nav?.getBoundingClientRect().bottom || 0) - mapRect.top + 8);
    let left = 8;
    if (!isMobile() && panel && !panel.collapsed) {
      const pr = panel.getBoundingClientRect();
      if (pr.width > 8) left = Math.max(left, pr.right - mapRect.left + 8);
    }
    const bottom = isMobile() && fab && !fab.hidden ? 56 : 12;
    return { top, right: 12, bottom, left };
  };

  const popupLayout = (lngLat) => {
    const point = map.project(lngLat);
    const w = map.getContainer().clientWidth;
    const h = map.getContainer().clientHeight;
    const pad = popupInsets();
    const above = Math.max(0, point.y - pad.top);
    const below = Math.max(0, h - point.y - pad.bottom);
    const fromLeft = Math.max(0, point.x - pad.left);
    const fromRight = Math.max(0, w - point.x - pad.right);
    const preferAbove = above >= below;
    let anchor = preferAbove ? "bottom" : "top";
    if (fromLeft < 140 && fromRight >= fromLeft) anchor = `${anchor}-left`;
    else if (fromRight < 140) anchor = `${anchor}-right`;
    const available = h - pad.top - pad.bottom - 16;
    const room = (preferAbove ? above : below) - 18;
    const shiftLeft = Math.max(0, pad.left - point.x);
    const shiftRight = Math.max(0, point.x - (w - pad.right));
    const tip = 12;
    const offsets = {
      top: [0, tip],
      bottom: [0, -tip],
      "top-left": [tip + shiftLeft, tip],
      "bottom-left": [tip + shiftLeft, -tip],
      "top-right": [-(tip + shiftRight), tip],
      "bottom-right": [-(tip + shiftRight), -tip],
    };
    return {
      anchor,
      maxHeight: Math.max(80, Math.min(room, available)),
      offset: offsets[anchor] || [0, tip],
    };
  };

  let popupFitRaf = 0;
  let lastFitKey = "";
  const fitPopup = ({ resetScroll = false } = {}) => {
    if (!popup.isOpen()) return;
    const lngLat = popup.getLngLat();
    if (!lngLat) return;
    const layout = popupLayout(lngLat);
    const key = `${layout.anchor}:${Math.floor(layout.maxHeight)}:${layout.offset.join(",")}`;
    const el = popup.getElement()?.querySelector(".maplibregl-popup-content");
    if (el) {
      el.style.maxHeight = `${Math.floor(layout.maxHeight)}px`;
      el.style.overflowY = "auto";
      if (resetScroll) el.scrollTop = 0;
    }
    if (resetScroll || key !== lastFitKey || popup.options.anchor !== layout.anchor) {
      lastFitKey = key;
      popup.options.anchor = layout.anchor;
      popup.setOffset(layout.offset);
    }
  };

  const schedulePopupFit = () => {
    if (!popup.isOpen()) return;
    if (popupFitRaf) cancelAnimationFrame(popupFitRaf);
    popupFitRaf = requestAnimationFrame(() => {
      popupFitRaf = 0;
      fitPopup();
    });
  };

  map.on("move", schedulePopupFit);
  map.on("resize", schedulePopupFit);
  window.visualViewport?.addEventListener("resize", schedulePopupFit);
  document.getElementById("layers-panel")?.addEventListener("calciteShellPanelToggle", schedulePopupFit);

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
    "hexes-off-line",
    "hexes-off",
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

  const cutoffValue = () => Number(document.getElementById("minute-slider")?.value) || 15;

  const hexAccessFilter = () => {
    const within = document.getElementById("within-switch")?.checked;
    const beyond = document.getElementById("beyond-switch")?.checked;
    const hide = document.getElementById("cutoff-switch")?.checked;
    const field = fieldFor(theme);
    if (within) {
      return theme === "clinic" || theme === "school" ? ["<=", ["get", field], 15] : ["==", ["get", "within_15"], 1];
    }
    if (beyond) {
      return theme === "clinic" || theme === "school" ? [">", ["get", field], 15] : ["!=", ["get", "within_15"], 1];
    }
    if (hide) return ["<=", ["get", field], cutoffValue()];
    return null;
  };

  const offFilter = () => {
    const access = hexAccessFilter();
    const off = [">", ["to-number", ["coalesce", ["get", "off_street"], 0]], 0];
    return access ? ["all", off, access] : off;
  };

  const flash = (kind, title, message) => {
    const alert = document.getElementById("map-alert");
    const titleEl = document.getElementById("map-alert-title");
    const msgEl = document.getElementById("map-alert-msg");
    if (!alert || !titleEl || !msgEl) return;
    alert.kind = kind || "brand";
    titleEl.textContent = title || "";
    msgEl.textContent = message || "";
    alert.open = true;
  };

  const writeView = () => {
    const q = new URLSearchParams(location.search);
    VIEW_KEYS.forEach((key) => q.delete(key));
    q.set("city", current);
    if (theme !== "walk") q.set("color", theme);
    if (basemap !== "gray") q.set("bm", basemap);
    const within = document.getElementById("within-switch")?.checked;
    const beyond = document.getElementById("beyond-switch")?.checked;
    const hide = document.getElementById("cutoff-switch")?.checked;
    if (within) q.set("within", "1");
    else if (beyond) q.set("beyond", "1");
    else if (hide) q.set("max", String(cutoffValue()));
    if (document.getElementById("lyr-off")?.checked) q.set("off", "1");
    try {
      const center = map.getCenter();
      q.set("lat", center.lat.toFixed(5));
      q.set("lng", center.lng.toFixed(5));
      q.set("z", map.getZoom().toFixed(2));
    } catch (err) {
      /* map not ready */
    }
    const next = `${location.pathname}?${q.toString()}${location.hash}`;
    if (`${location.pathname}${location.search}${location.hash}` !== next) history.replaceState(null, "", next);
  };

  const scheduleWriteView = () => {
    if (urlTimer) clearTimeout(urlTimer);
    urlTimer = setTimeout(writeView, 350);
  };

  const updateLiveShare = () => {
    const cutoff = cutoffValue();
    const readout = document.getElementById("minute-readout");
    const live = document.getElementById("live-share");
    if (readout) readout.textContent = `${cutoff} min`;
    if (!live) return;
    const city = meta.cities[current];
    const share = peopleUnderCutoff(lastBundle?.hexes, fieldFor(theme), cutoff);
    const what = theme === "clinic" ? "a clinic" : theme === "school" ? "a school" : "clinics and schools";
    const shareText = share == null ? "n/a" : `${share.toFixed(1)}%`;
    const f15 = city?.f15 != null ? `${Number(city.f15).toFixed(1)}%` : "n/a";
    live.textContent = `${shareText} of people on this map have a walk to ${what} of ${cutoff} min or less. The city F15 stays ${f15} at 15 minutes.`;
  };

  const applyTheme = () => {
    if (!map.getLayer("hexes")) return;
    const paint = hexPaint(theme, meta.cities[current].people_breaks);
    map.setPaintProperty("hexes", "fill-color", paint["fill-color"]);
    const filter = hexAccessFilter();
    map.setFilter("hexes", filter);
    map.setFilter("hexes-line", filter);
    if (map.getLayer("hexes-off")) map.setFilter("hexes-off", offFilter());
    if (map.getLayer("hexes-off-line")) map.setFilter("hexes-off-line", offFilter());
    renderLegend(theme);
    updateLiveShare();
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
    const offOn = document.getElementById("lyr-off")?.checked;
    setVisibility(map, "hexes-off", offOn);
    setVisibility(map, "hexes-off-line", offOn);
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
    setText("labels-clinics", wardText, 1.5);
    setText("labels-schools", wardText, 1.5);
    if (map.getLayer("boundary")) map.setPaintProperty("boundary", "line-color", boundary);
    if (map.getLayer("wards")) map.setPaintProperty("wards", "line-color", wardLine);
    if (map.getLayer("hexes-off-line")) {
      map.setPaintProperty("hexes-off-line", "line-color", dark ? "#f4f4f4" : "#121212");
    }
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
        paint: {
          "fill-color": "#0079c1",
          "fill-opacity": ["case", ["boolean", ["feature-state", "picked"], false], 0.16, 0],
        },
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
        id: "hexes-off",
        type: "fill",
        source: "hexes",
        layout: { visibility: "none" },
        paint: { "fill-pattern": "off-hatch", "fill-opacity": 0.7 },
      },
      {
        id: "hexes-off-line",
        type: "line",
        source: "hexes",
        layout: { visibility: "none" },
        paint: {
          "line-color": "#121212",
          "line-width": 1.15,
          "line-dasharray": [1.6, 1.2],
          "line-opacity": 0.9,
        },
      },
      {
        id: "wards",
        type: "line",
        source: "wards",
        paint: {
          "line-color": WARD_LINE,
          "line-width": ["case", ["boolean", ["feature-state", "picked"], false], 2.2, 0.9],
          "line-opacity": 1,
        },
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
          "text-field": ["get", "name"],
          "text-font": ["Noto Sans Regular"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 14.8, 10, 17, 13],
          "text-offset": [0, 1.15],
          "text-optional": true,
          "text-padding": 6,
          "text-max-width": 9,
        },
        paint: { "text-color": "#554e4b", "text-halo-color": HALO, "text-halo-width": 1.2 },
      },
      {
        id: "labels-schools",
        type: "symbol",
        source: "schools",
        minzoom: 14.8,
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["Noto Sans Regular"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 14.8, 10, 17, 13],
          "text-offset": [0, 1.15],
          "text-optional": true,
          "text-padding": 6,
          "text-max-width": 9,
        },
        paint: { "text-color": "#554e4b", "text-halo-color": HALO, "text-halo-width": 1.2 },
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

  const showPopup = (kind, feature, lngLat) => {
    const props = { ...(feature.properties || {}) };
    lastFitKey = "";
    popup.setLngLat(lngLat).setHTML(popupHTML(kind, props, meta.cities[current], wardLookup)).addTo(map);
    fitPopup({ resetScroll: true });
    requestAnimationFrame(() => fitPopup({ resetScroll: true }));
  };

  const markWard = (feature) => {
    if (pickedWard != null && map.getSource("wards")) {
      try {
        map.setFeatureState({ source: "wards", id: pickedWard }, { picked: false });
      } catch (err) {
        /* source rebuilt */
      }
    }
    pickedWard = feature?.id;
    if (pickedWard != null && map.getSource("wards")) {
      try {
        map.setFeatureState({ source: "wards", id: pickedWard }, { picked: true });
      } catch (err) {
        pickedWard = null;
      }
    }
    document.querySelectorAll(".ward-row").forEach((el) => {
      if (el.dataset.name === feature?.properties?.name) el.setAttribute("aria-current", "true");
      else el.removeAttribute("aria-current");
    });
  };

  const fitFeature = (feat, maxZoom = 14.2) => {
    const bounds = featureBounds(feat);
    const padding = edgePadding();
    if (bounds) {
      try {
        map.fitBounds(bounds, { padding, duration: 500, maxZoom, pitch: map.getPitch(), bearing: 0 });
        return;
      } catch (err) {
        /* fall through */
      }
    }
    const center = featureCenter(feat);
    if (center) map.easeTo({ center, zoom: Math.min(14.2, Math.max(map.getZoom(), 13.2)), duration: 500 });
  };

  const afterMove = (fn) => {
    let done = false;
    const run = () => {
      if (done) return;
      done = true;
      fn();
    };
    map.once("moveend", run);
    setTimeout(run, 650);
  };

  const maybeClosePanel = () => {
    if (isMobile()) setPanelOpen(false);
  };

  const hideSearch = () => {
    const box = document.getElementById("search-results");
    if (box) {
      box.hidden = true;
      box.innerHTML = "";
    }
  };

  const buildSearchIndex = (bundle) => {
    const items = [];
    (bundle.wards?.features || []).forEach((feat) => {
      const name = nonempty(feat.properties.label) || nonempty(feat.properties.name);
      if (!name) return;
      items.push({ kind: "ward", name, sub: nonempty(feat.properties.lga) || "Ward", feature: feat });
    });
    const lgas = new Map();
    (bundle.wards?.features || []).forEach((feat) => {
      const lga = nonempty(feat.properties.lga);
      if (!lga) return;
      if (!lgas.has(lga)) lgas.set(lga, []);
      lgas.get(lga).push(feat);
    });
    lgas.forEach((features, name) => {
      items.push({ kind: "lga", name, sub: "Local government", features });
    });
    (bundle.places?.features || []).forEach((feat) => {
      const name = nonempty(feat.properties.label) || nonempty(feat.properties.name);
      if (!name) return;
      items.push({ kind: "place", name, sub: nonempty(feat.properties.place) || "Place", feature: feat });
    });
    searchItems = items;
  };

  const openSearchHit = (item) => {
    hideSearch();
    const input = document.getElementById("place-search");
    if (input) input.value = item.name;
    if (item.kind === "lga") {
      const bounds = new maplibregl.LngLatBounds();
      item.features.forEach((feat) => {
        const b = featureBounds(feat);
        if (b) bounds.extend(b);
      });
      if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: edgePadding(), duration: 500, maxZoom: 13.4, pitch: map.getPitch() });
      maybeClosePanel();
      return;
    }
    const feat = item.feature;
    const center = featureCenter(feat);
    if (!center) return;
    if (item.kind === "ward") {
      fitFeature(feat, 14.4);
      afterMove(() => showPopup("wards-fill", feat, center));
      markWard(feat);
    } else {
      map.easeTo({ center, zoom: Math.max(map.getZoom(), 13.6), duration: 480 });
      afterMove(() => showPopup("labels-places", feat, center));
    }
    maybeClosePanel();
  };

  const renderSearch = (query) => {
    const box = document.getElementById("search-results");
    if (!box) return;
    const q = foldText(query);
    if (q.length < 2) {
      hideSearch();
      return;
    }
    const hits = searchItems
      .map((item) => {
        const score = matchScore(q, item.name);
        if (score == null) return null;
        const kindRank = item.kind === "ward" ? 0 : item.kind === "lga" ? 1 : 2;
        return { item, score: score * 10 + kindRank };
      })
      .filter(Boolean)
      .sort((a, b) => a.score - b.score || a.item.name.localeCompare(b.item.name))
      .slice(0, 8);
    if (!hits.length) {
      box.hidden = false;
      box.innerHTML = `<button type="button" class="search-hit" disabled>No match in ${meta.cities[current]?.name || "this city"}</button>`;
      return;
    }
    box.hidden = false;
    box.innerHTML = hits
      .map(
        ({ item }, i) =>
          `<button type="button" class="search-hit" role="option" data-i="${i}" ${i === 0 ? 'aria-selected="true"' : ""}><span class="hit-kind">${item.sub}</span>${item.name}</button>`
      )
      .join("");
    box.querySelectorAll(".search-hit").forEach((btn, i) => {
      btn.addEventListener("click", () => openSearchHit(hits[i].item));
    });
  };

  const renderWardList = () => {
    const box = document.getElementById("ward-list");
    if (!box) return;
    const sort = document.getElementById("ward-sort")?.value || "f15";
    const rows = (lastBundle?.wards?.features || []).slice();
    rows.sort((a, b) => {
      const pa = a.properties || {};
      const pb = b.properties || {};
      if (sort === "walk") return (Number(pb.walk) || 0) - (Number(pa.walk) || 0);
      if (sort === "people") return (Number(pb.people) || 0) - (Number(pa.people) || 0);
      return (Number(pa.f15) || 0) - (Number(pb.f15) || 0);
    });
    box.innerHTML = rows
      .map((feat) => {
        const p = feat.properties || {};
        const name = nonempty(p.label) || nonempty(p.name) || "Ward";
        return `<button type="button" class="ward-row" role="listitem" data-name="${String(p.name || "").replace(/"/g, "&quot;")}"><span><span class="ward-name">${name}</span><span class="ward-lga">${nonempty(p.lga) || ""}</span></span><span class="ward-stat">${pct(p.f15)}<span class="ward-walk">${minutes(p.walk)}</span></span></button>`;
      })
      .join("");
    box.querySelectorAll(".ward-row").forEach((btn, i) => {
      btn.addEventListener("click", () => {
        const feat = rows[i];
        const center = featureCenter(feat);
        fitFeature(feat, 14.4);
        markWard(feat);
        if (center) afterMove(() => showPopup("wards-fill", feat, center));
        maybeClosePanel();
      });
    });
  };

  const cityForPoint = (lng, lat) => {
    for (const slug of meta.order || Object.keys(meta.cities)) {
      const bbox = meta.cities[slug]?.bbox;
      if (!bbox) continue;
      if (lng >= bbox[0] && lat >= bbox[1] && lng <= bbox[2] && lat <= bbox[3]) return slug;
    }
    return null;
  };

  const snapToLngLat = (lng, lat) => {
    const hexes = lastBundle?.hexes?.features || [];
    const point = [lng, lat];
    let hit = hexes.find((feat) => pointInFeature(point, feat));
    if (!hit) {
      let best = Infinity;
      hexes.forEach((feat) => {
        const c = hexCentroid(feat);
        if (!c) return;
        const d = (c[0] - lng) ** 2 + (c[1] - lat) ** 2;
        if (d < best) {
          best = d;
          hit = feat;
        }
      });
      if (!hit || best > 0.0004) {
        flash("warning", "No neighbourhood here", "There is no tile under that point. Try a nearby street inside the city outline.");
        return;
      }
    }
    const center = hexCentroid(hit) || point;
    map.easeTo({ center, zoom: Math.max(map.getZoom(), 14), duration: 500 });
    afterMove(() => {
      showPopup("hexes", hit, center);
      if (hit.properties?.off_street) {
        flash("warning", "Off mapped streets", "This neighbourhood sits more than 250 m from the walking network, so the minutes can mean a missing street as well as a missing clinic.");
      }
    });
  };

  const locateMe = () => {
    const btn = document.getElementById("locate-btn");
    if (!navigator.geolocation) {
      flash("danger", "Location is not available", "This browser cannot read a GPS position.");
      return;
    }
    if (btn) btn.loading = true;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        if (btn) btn.loading = false;
        const lng = pos.coords.longitude;
        const lat = pos.coords.latitude;
        const slug = cityForPoint(lng, lat);
        if (!slug) {
          flash("warning", "Outside the mapped cities", "You are outside Lagos, Ibadan, Kano, Port Harcourt and Abuja as drawn here. Search a ward instead.");
          return;
        }
        if (slug !== current) {
          locateAfter = { lng, lat };
          document.getElementById("city-select").value = slug;
          loadCity(slug);
          maybeClosePanel();
          return;
        }
        snapToLngLat(lng, lat);
        maybeClosePanel();
      },
      (err) => {
        if (btn) btn.loading = false;
        const denied = err?.code === 1;
        flash(
          "danger",
          denied ? "Location blocked" : "Could not find you",
          denied ? "Allow location for this page, then try again." : "The GPS reading timed out. Try once more, or search a ward."
        );
      },
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 30000 }
    );
  };

  const copyView = async () => {
    writeView();
    const url = location.href;
    try {
      await navigator.clipboard.writeText(url);
      flash("success", "Link copied", "Anyone with the link opens this city, colour, filter and map position.");
    } catch (err) {
      window.prompt("Copy this link", url);
    }
  };

  const paintCity = (slug, bundle) => {
    const seq = ++paintSeq;
    wardLookup = new Map((bundle.wards?.features || []).map((f) => [f.properties.name, f.properties]));
    const city = { ...meta.cities[slug] };
    city.clinics = bundle.clinics?.features?.length ?? city.clinics;
    city.schools = bundle.schools?.features?.length ?? city.schools;
    renderScores(city);
    buildSearchIndex(bundle);
    lastBundle = bundle;
    renderWardList();
    updateLiveShare();
    pickedWard = null;
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
      if (locateAfter) {
        const target = locateAfter;
        locateAfter = null;
        snapToLngLat(target.lng, target.lat);
      } else if (holdCamera) {
        holdCamera = false;
        map.jumpTo({
          center: [initial.camera.lng, initial.camera.lat],
          zoom: initial.camera.zoom,
          pitch: basemap === "color" ? basemapPitch() : map.getPitch(),
        });
      } else {
        flyToCity(slug, bundle.boundary);
      }
      showLoader(false);
      prefetchOthers();
      scheduleWriteView();
      if (bootColor) {
        bootColor = false;
        map.once("idle", () => changeBasemap("color"));
      }
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
    const citySelect = document.getElementById("city-select");
    if (citySelect && citySelect.value !== slug) citySelect.value = slug;
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
      scheduleWriteView();
      return;
    }
    const swapRaster = isRasterBasemap(prev) && isRasterBasemap(value) && prev !== value && !isVectorStyle();
    basemap = value;

    if (value === "color") {
      map.setStyle(LIBERTY, { diff: false });
      afterStyle(() => {
        map.jumpTo({ ...camera, pitch: basemapPitch() });
        restoreThematic();
        scheduleWriteView();
      });
      return;
    }

    if (prev === "color" || isVectorStyle() || swapRaster || !map.getSource("basemap")?.setTiles) {
      map.setStyle(rasterStyle(value), { diff: false });
      afterStyle(() => {
        map.jumpTo({ ...camera, pitch: 0 });
        restoreThematic();
        scheduleWriteView();
      });
      return;
    }

    applyRasterTiles(value);
    map.setPitch(0);
    scheduleWriteView();
  };

  map.on("styleimagemissing", (e) => {
    if (e.id === "clinic-mark" || e.id === "school-mark" || e.id === "off-hatch") addIcons(map);
  });

  const applyInitialControls = () => {
    const citySelect = document.getElementById("city-select");
    const themeSelect = document.getElementById("theme-select");
    if (citySelect) citySelect.value = current;
    if (themeSelect) themeSelect.value = theme;
    const slider = document.getElementById("minute-slider");
    if (slider && initial.cutoff != null) slider.value = Math.max(5, Math.min(60, initial.cutoff));
    if (initial.within) {
      const el = document.getElementById("within-switch");
      if (el) el.checked = true;
    }
    if (initial.beyond) {
      const el = document.getElementById("beyond-switch");
      if (el) el.checked = true;
    }
    if (initial.hideCutoff) {
      const el = document.getElementById("cutoff-switch");
      if (el) el.checked = true;
    }
    if (initial.off) {
      const el = document.getElementById("lyr-off");
      if (el) el.checked = true;
    }
    const toggle = document.getElementById("basemap-toggle");
    const select = document.getElementById("basemap-select");
    if (toggle) toggle.value = basemap === "color" ? "color" : basemap;
    if (select) select.value = basemap === "color" ? "color" : basemap;
  };
  applyInitialControls();

  let started = false;
  const start = () => {
    if (started) return;
    started = true;
    map.resize();
    addIcons(map);
    loadCity(current);
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
      showPopup(kind, { ...f, properties: props }, e.lngLat);
      if (kind === "wards" || kind === "wards-fill" || kind === "labels-wards") markWard(f);
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
    scheduleWriteView();
  });
  bindSelect("ward-sort", () => renderWardList());
  const bindAccessSwitch = (id, otherId) => {
    document.getElementById(id)?.addEventListener("calciteSwitchChange", (e) => {
      if (e.target.checked) {
        const other = document.getElementById(otherId);
        if (other) other.checked = false;
        const cutoff = document.getElementById("cutoff-switch");
        if (cutoff) cutoff.checked = false;
      }
      applyTheme();
      scheduleWriteView();
    });
  };
  bindAccessSwitch("within-switch", "beyond-switch");
  bindAccessSwitch("beyond-switch", "within-switch");
  document.getElementById("cutoff-switch")?.addEventListener("calciteSwitchChange", (e) => {
    if (e.target.checked) {
      ["within-switch", "beyond-switch"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.checked = false;
      });
    }
    applyTheme();
    scheduleWriteView();
  });
  const slider = document.getElementById("minute-slider");
  slider?.addEventListener("calciteSliderInput", updateLiveShare);
  slider?.addEventListener("calciteSliderChange", () => {
    updateLiveShare();
    if (document.getElementById("cutoff-switch")?.checked) applyTheme();
    scheduleWriteView();
  });
  ["lyr-hexes", "lyr-clinics", "lyr-schools", "lyr-wards", "lyr-places", "lyr-boundary", "lyr-off"].forEach((id) => {
    document.getElementById(id)?.addEventListener("calciteCheckboxChange", () => {
      applyOverlays();
      scheduleWriteView();
    });
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
  document.getElementById("locate-btn")?.addEventListener("click", locateMe);
  document.getElementById("share-btn")?.addEventListener("click", copyView);
  const searchInput = document.getElementById("place-search");
  searchInput?.addEventListener("calciteInputInput", (e) => renderSearch(e.target.value));
  searchInput?.addEventListener("calciteInputChange", (e) => renderSearch(e.target.value));
  document.getElementById("search-go")?.addEventListener("click", () => {
    const first = document.querySelector("#search-results .search-hit:not([disabled])");
    if (first) first.click();
    else renderSearch(searchInput?.value);
  });
  searchInput?.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hideSearch();
    if (e.key === "Enter") {
      e.preventDefault();
      const first = document.querySelector("#search-results .search-hit:not([disabled])");
      first?.click();
    }
  });
  document.addEventListener("click", (e) => {
    const path = e.composedPath ? e.composedPath() : [];
    if (path.some((node) => node?.id === "place-search" || node?.id === "search-results" || node?.id === "search-go")) return;
    hideSearch();
  });
  map.on("moveend", scheduleWriteView);
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
