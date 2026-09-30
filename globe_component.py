"""
Rotating 3D globe for the Supply Chain Risk Dashboard.

Shows the United States highlighted, with animated oil, gas and chemical
corridors: tanker routes (ship) and crude/chemical rail routes (train).

Routes are ILLUSTRATIVE major corridors, drawn from well-known flows
(Gulf Coast exports, Bakken crude-by-rail, Alaska crude by tanker, etc.).
They are not scaled to volume. Say this in the demo and the report.

Usage in app.py:
    from globe_component import render_globe
    render_globe(height=480)
"""

import json
import streamlit.components.v1 as components

# Each route: name, mode ("ship" or "rail"), list of [lat, lng] waypoints.
ROUTES = [
    # ---------------- Ship (tanker / LNG carrier) ----------------
    {"name": "Gulf Coast exports to Europe (Rotterdam)", "mode": "ship", "points": [
        [29.87, -93.93], [27.5, -90.0], [24.6, -83.5], [24.3, -81.0], [26.5, -79.3],
        [32.0, -75.0], [38.0, -60.0], [43.0, -40.0], [47.0, -20.0], [49.5, -6.0],
        [51.0, 1.5], [51.95, 4.10]]},
    {"name": "Gulf Coast exports to Asia (via Panama Canal)", "mode": "ship", "points": [
        [29.73, -95.00], [27.0, -93.0], [22.0, -88.0], [21.5, -86.3], [17.0, -82.0],
        [12.0, -80.5], [9.35, -79.90], [8.90, -79.50], [7.0, -82.0], [12.0, -100.0],
        [20.0, -130.0], [28.0, -160.0], [33.0, 170.0], [34.2, 145.0], [35.30, 139.80]]},
    {"name": "Gulf Coast exports to South America (Brazil)", "mode": "ship", "points": [
        [27.80, -97.40], [25.0, -94.0], [22.0, -88.0], [21.3, -86.0], [18.0, -76.0],
        [13.0, -62.0], [5.0, -45.0], [-2.0, -36.0], [-10.0, -34.0], [-20.0, -39.0],
        [-23.95, -46.30]]},
    {"name": "Middle East crude imports (via Suez)", "mode": "ship", "points": [
        [26.64, 50.16], [26.5, 56.5], [22.0, 62.0], [13.0, 51.0], [12.6, 43.4],
        [20.0, 38.5], [27.5, 34.0], [30.0, 32.5], [33.5, 28.0], [36.5, 15.0],
        [36.0, -5.6], [35.0, -20.0], [30.0, -45.0], [26.0, -70.0], [24.3, -81.0],
        [24.8, -84.5], [27.5, -90.0], [29.87, -93.93]]},
    {"name": "Alaska crude to the West Coast (Valdez)", "mode": "ship", "points": [
        [61.10, -146.35], [59.5, -146.0], [56.0, -140.0], [47.0, -127.0],
        [40.0, -125.0], [37.80, -122.60]]},

    # ---------------- Rail (crude oil / chemicals) ----------------
    {"name": "Bakken crude by rail to East Coast refineries", "mode": "rail", "points": [
        [48.15, -103.60], [46.9, -96.8], [45.0, -93.3], [41.9, -87.6],
        [41.5, -81.7], [40.4, -80.0], [39.95, -75.20]]},
    {"name": "Bakken crude by rail to the Gulf Coast", "mode": "rail", "points": [
        [48.15, -103.60], [44.4, -100.3], [41.3, -96.0], [39.1, -94.6],
        [35.5, -97.5], [32.8, -96.8], [30.08, -94.10]]},
    {"name": "Bakken crude by rail to Pacific Northwest", "mode": "rail", "points": [
        [48.15, -103.60], [47.5, -111.3], [47.66, -117.40], [47.6, -122.3],
        [48.50, -122.60]]},
    {"name": "Permian Basin to Houston", "mode": "rail", "points": [
        [32.00, -102.10], [31.5, -99.0], [30.3, -97.7], [29.76, -95.37]]},
    {"name": "Gulf Coast chemicals and plastics to the Midwest", "mode": "rail", "points": [
        [29.76, -95.37], [32.5, -93.7], [35.15, -90.05], [38.6, -90.2], [41.9, -87.6]]},
]

GEO_LABELS = [
    {"name": "NORTH AMERICA", "lat": 56.0, "lng": -106.0, "kind": "continent"},
    {"name": "SOUTH AMERICA", "lat": -12.0, "lng": -58.0, "kind": "continent"},
    {"name": "EUROPE", "lat": 53.0, "lng": 20.0, "kind": "continent"},
    {"name": "AFRICA", "lat": 6.0, "lng": 20.0, "kind": "continent"},
    {"name": "ASIA", "lat": 48.0, "lng": 90.0, "kind": "continent"},
    {"name": "AUSTRALIA", "lat": -25.0, "lng": 134.0, "kind": "continent"},
    {"name": "North Atlantic Ocean", "lat": 33.0, "lng": -45.0, "kind": "ocean"},
    {"name": "South Atlantic Ocean", "lat": -28.0, "lng": -15.0, "kind": "ocean"},
    {"name": "North Pacific Ocean", "lat": 30.0, "lng": -145.0, "kind": "ocean"},
    {"name": "South Pacific Ocean", "lat": -28.0, "lng": -125.0, "kind": "ocean"},
    {"name": "Indian Ocean", "lat": -20.0, "lng": 78.0, "kind": "ocean"},
    {"name": "Arctic Ocean", "lat": 82.0, "lng": -30.0, "kind": "ocean"},
]

HUBS = [
    {"name": "Port Arthur / Beaumont", "lat": 29.95, "lng": -93.95, "pulse": True},
    {"name": "Houston", "lat": 29.76, "lng": -95.37, "pulse": True},
    {"name": "Corpus Christi", "lat": 27.80, "lng": -97.40, "pulse": False},
    {"name": "Bakken (Williston)", "lat": 48.15, "lng": -103.60, "pulse": False},
    {"name": "Chicago", "lat": 41.88, "lng": -87.63, "pulse": False},
    {"name": "Philadelphia", "lat": 39.95, "lng": -75.20, "pulse": False},
    {"name": "Valdez", "lat": 61.10, "lng": -146.35, "pulse": False},
    {"name": "Rotterdam", "lat": 51.95, "lng": 4.10, "pulse": False},
    {"name": "Tokyo Bay", "lat": 35.30, "lng": 139.80, "pulse": False},
    {"name": "Santos", "lat": -23.95, "lng": -46.30, "pulse": False},
    {"name": "Ras Tanura", "lat": 26.64, "lng": 50.16, "pulse": False},
]

_TEMPLATE = r"""
<div id="gwrap">
  <div id="globe"></div>
  <div class="overlay top">
    <div class="title">__TITLE__</div>
    <div class="legend">
      <span><i class="sw ship"></i>Tanker / LNG ship</span>
      <span><i class="sw rail"></i>Rail (crude &amp; chemicals)</span>
      <span><i class="sw road"></i>Truck (road)</span>
      <span><i class="sw usa"></i>United States</span>
      <span style="color:#94a3b8">Hover a country to see its name</span>
    </div>
  </div>
  <div class="overlay bottom">
    <button id="btnRotate" class="on">Rotate</button>
    <button id="btnUSA">Focus USA</button>
    <span class="note">Illustrative major corridors, not scaled to volume</span>
  </div>
  <div id="gerr" class="overlay err" style="display:none">Globe could not load (no internet or CDN blocked).</div>
</div>

<style>
  html, body { margin:0; padding:0; background:transparent; overflow:hidden;
               font-family: Inter, "Segoe UI", system-ui, sans-serif; }
  #gwrap { position:relative; width:100%; height:__H__px; border-radius:18px; overflow:hidden;
           background: #000005;
           border:1px solid rgba(148,163,184,0.18); }
  #globe { position:absolute; inset:0; }
  .overlay { position:absolute; left:16px; right:16px; color:#e5e7eb; pointer-events:none; z-index:5; }
  .overlay.top { top:14px; }
  .overlay.bottom { bottom:12px; display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  .overlay.err { top:45%; text-align:center; color:#fca5a5; }
  .title { font-weight:700; font-size:15px; letter-spacing:.2px; }
  .legend { margin-top:6px; display:flex; gap:14px; flex-wrap:wrap; font-size:12px; color:#cbd5e1; }
  .legend span { display:inline-flex; align-items:center; gap:6px; }
  .sw { display:inline-block; width:18px; height:4px; border-radius:2px; }
  .sw.ship { background:#22d3ee; box-shadow:0 0 8px #22d3ee; }
  .sw.rail { background:#fbbf24; box-shadow:0 0 8px #fbbf24; }
  .sw.road { background:#c084fc; box-shadow:0 0 8px #c084fc; }
  .sw.usa  { background:rgba(59,130,246,0.45); border:1.5px solid #fde68a; height:10px; width:14px; }
  button { pointer-events:auto; cursor:pointer; font:600 12px Inter, system-ui, sans-serif;
           color:#e5e7eb; background:rgba(17,27,46,0.85); border:1px solid rgba(148,163,184,0.35);
           border-radius:999px; padding:5px 12px; }
  button.on { border-color:#f59e0b; color:#fbbf24; }
  .note { font-size:11px; color:#94a3b8; margin-left:auto; }
</style>

<script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/globe.gl@2/dist/globe.gl.min.js"></script>
<script>
(function () {
  const ROUTES = __ROUTES__;
  const HUBS = __HUBS__;
  const GEO = __GEO__;
  const LABELS = HUBS.map(h => ({ ...h, kind: "hub" })).concat(GEO);
  const H = __H__;
  const USA_IDS = new Set(["840", "630"]);  // United States, Puerto Rico
  const COLORS = { ship: "#22d3ee", sea: "#22d3ee", rail: "#fbbf24", road: "#c084fc" };
  const BASE = { ship: "rgba(34,211,238,0.22)", sea: "rgba(34,211,238,0.22)", rail: "rgba(251,191,36,0.25)",
                 road: "rgba(192,132,252,0.25)" };
  const FOCUS = __FOCUS__;

  if (typeof Globe === "undefined") {
    document.getElementById("gerr").style.display = "block";
    return;
  }

  const el = document.getElementById("globe");
  const wrap = document.getElementById("gwrap");

  // Two layers per route: a faint base line plus a bright moving dash.
  const paths = [];
  ROUTES.forEach(r => {
    paths.push({ ...r, layer: "base" });
    paths.push({ ...r, layer: "flow" });
  });

  // Works with both the newer class API and the older factory API of globe.gl
  let globe = new Globe(el);
  if (typeof globe === "function") { globe = globe(el); }

  globe
    .width(wrap.clientWidth)
    .height(H)
    .backgroundColor("#000005")
    .backgroundImageUrl("https://unpkg.com/three-globe/example/img/night-sky.png")
    .showGraticules(false)
    .showAtmosphere(true)
    .atmosphereColor("#7dd3fc")
    .atmosphereAltitude(0.12)

    .pathsData(paths)
    .pathPoints("points")
    .pathPointLat(p => p[0])
    .pathPointLng(p => p[1])
    .pathPointAlt(0.016)
    .pathResolution(3)
    .pathColor(r => r.layer === "base" ? BASE[r.mode] : COLORS[r.mode])
    .pathStroke(r => r.layer === "base" ? (FOCUS ? 1.0 : 0.5) : (r.mode === "sea" || r.mode === "ship" ? 1.3 : 1.6))
    .pathDashLength(r => r.layer === "base" ? 1 : (r.mode === "rail" ? 0.06 : r.mode === "road" ? 0.08 : 0.04))
    .pathDashGap(r => r.layer === "base" ? 0 : (r.mode === "rail" ? 0.05 : r.mode === "road" ? 0.04 : 0.08))
    .pathDashInitialGap(() => Math.random())
    .pathDashAnimateTime(r => r.layer === "base" ? 0 : (r.mode === "rail" ? 7000 : r.mode === "road" ? 5000 : 14000))
    .pathLabel(r => r.layer === "flow" ? `<b>${r.name}</b><br/>${({ship:"Ship",sea:"Ship",rail:"Rail",road:"Truck"})[r.mode]}` : "")

    .labelsData(LABELS)
    .labelLat("lat").labelLng("lng").labelText("name")
    .labelAltitude(d => d.kind === "hub" ? 0.018 : 0.012)
    .labelSize(d => d.kind === "continent" ? 1.9 : d.kind === "ocean" ? 1.3 : 0.7)
    .labelIncludeDot(d => d.kind === "hub")
    .labelDotRadius(0.35)
    .labelColor(d => d.kind === "continent" ? "rgba(255,255,255,0.92)"
                   : d.kind === "ocean" ? "rgba(203,225,245,0.80)"
                   : "rgba(253,230,138,0.95)")
    .labelResolution(3)

    .ringsData(HUBS.filter(h => h.pulse))
    .ringLat("lat").ringLng("lng")
    .ringAltitude(0.018)
    .ringColor(() => t => `rgba(245,158,11,${1 - t})`)
    .ringMaxRadius(3.2)
    .ringPropagationSpeed(1.6)
    .ringRepeatPeriod(1100);

  // Real Earth look: satellite image + relief bump map
  globe
    .globeImageUrl("https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg")
    .bumpImageUrl("https://unpkg.com/three-globe/example/img/earth-topology.png");

  // Countries: USA highlighted, everything else dim
  fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json")
    .then(r => r.json())
    .then(world => {
      const feats = topojson.feature(world, world.objects.countries).features
        .filter(f => f.id !== "010");  // drop Antarctica
      globe
        .polygonsData(feats)
        .polygonAltitude(f => USA_IDS.has(f.id) ? 0.008 : 0.004)
        .polygonCapColor(f => USA_IDS.has(f.id) ? "rgba(59,130,246,0.15)" : "rgba(0,0,0,0)")
        .polygonSideColor(() => "rgba(0,0,0,0)")
        .polygonStrokeColor(f => USA_IDS.has(f.id) ? "#fde68a" : "rgba(255,255,255,0.70)")
        .polygonLabel(f => `<b>${f.properties && f.properties.name ? f.properties.name : ""}</b>`);
    })
    .catch(() => {});

  // Start looking at the USA, then rotate slowly
  const ctr = globe.controls();
  if (FOCUS) {
    globe.pointOfView({ lat: FOCUS.lat, lng: FOCUS.lng, altitude: FOCUS.alt }, 0);
    ctr.autoRotate = false;
    document.getElementById("btnRotate").classList.remove("on");
  } else {
    globe.pointOfView({ lat: 34, lng: -96, altitude: 2.1 }, 0);
    ctr.autoRotate = true;
  }
  ctr.autoRotateSpeed = 0.55;
  ctr.enableZoom = false;

  const bR = document.getElementById("btnRotate");
  const bU = document.getElementById("btnUSA");
  bR.onclick = () => {
    ctr.autoRotate = !ctr.autoRotate;
    bR.classList.toggle("on", ctr.autoRotate);
  };
  bU.onclick = () => {
    ctr.autoRotate = false;
    bR.classList.remove("on");
    globe.pointOfView({ lat: 38, lng: -97, altitude: 1.35 }, 1400);
  };

  window.addEventListener("resize", () => globe.width(wrap.clientWidth));
})();
</script>
"""


def globe_html(height: int = 480, paths=None, hubs=None, focus=None,
               title: str = "How U.S. oil, gas &amp; chemicals move") -> str:
    """Return the globe as an HTML string. paths: [{name, mode, points:[[lat,lng],...]}]."""
    return (_TEMPLATE
            .replace("__ROUTES__", json.dumps(paths if paths is not None else ROUTES))
            .replace("__HUBS__", json.dumps(hubs if hubs is not None else HUBS))
            .replace("__GEO__", json.dumps(GEO_LABELS))
            .replace("__FOCUS__", json.dumps(focus))
            .replace("__TITLE__", title)
            .replace("__H__", str(int(height))))


def render_globe(height: int = 480, paths=None, hubs=None, focus=None, title=None) -> None:
    """Draw the rotating globe inside the Streamlit page (optionally a filtered set of paths)."""
    kw = {"title": title} if title else {}
    components.html(globe_html(height, paths, hubs, focus, **kw), height=height + 4, scrolling=False)
