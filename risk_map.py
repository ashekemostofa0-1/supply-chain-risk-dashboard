"""
Global Risk Map (D3, drawn in the browser): pale-blue land, curved colored routes with
arrows, blue anchor pins at ports, warning badges at chokepoints, disaster symbols
(typhoon, earthquake, flood, volcano, wildfire, drought, U.S. weather) and white
callout cards, with + / - zoom buttons.

    from risk_map import render_risk_map
    render_risk_map(sig, routes, routes_df, height=440)
"""

import datetime as dt
import json
import math

import streamlit.components.v1 as components

from live_data import CHOKEPOINTS, PORTS
from routes import signal_level

COLORS = {"HIGH": "#FF3B47", "ELEVATED": "#FF8A1F", "MONITOR": "#FFC928", "NORMAL": "#2EE06F",
          "NODATA": "#9AA9BC"}
# Endpoints drawn as blue anchor pins (no status of their own)
END_PORTS = [
    {"label": "Rotterdam", "lat": 51.95, "lng": 4.10}, {"label": "Tokyo Bay", "lat": 35.3, "lng": 139.8},
    {"label": "Santos", "lat": -23.95, "lng": -46.3}, {"label": "Ras Tanura", "lat": 26.64, "lng": 50.16},
    {"label": "Corpus Christi", "lat": 27.8, "lng": -97.4},
]
# Rough transit penalty when a canal route must divert around Africa (from the route table: 30-35 vs 40-45 days)
REROUTE = {"suez": "+~10 days if rerouted via Cape", "bab": "+~10 days if rerouted via Cape",
           "panama": "+~7–10 days if rerouted", "hormuz": "No alternative sea route"}
WORD = {"HIGH": "Higher risk", "ELEVATED": "Elevated risk", "MONITOR": "Monitor"}


NEAR_KM = 600          # a disaster counts only if it is this close to a shown route or port
RECENT_DAYS = 3        # ...and still active in the last few days


def _km(a_lat, a_lon, b_lat, b_lon):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


def _route_points(routes, step_deg=2.0):
    """Route waypoints filled in every ~2 degrees, plus port locations."""
    pts = []
    for r in routes:
        w = r["points"]
        for (a, b), (c, d) in zip(w, w[1:]):
            if abs(d - b) > 180:          # skip the date-line jump
                continue
            n = max(1, int(max(abs(c - a), abs(d - b)) / step_deg))
            pts += [(a + (c - a) * i / n, b + (d - b) * i / n) for i in range(n + 1)]
    pts += [(v["lat"], v["lng"]) for v in PORTS.values()] + [(p["lat"], p["lng"]) for p in END_PORTS]
    return pts


def relevant_disasters(events, routes):
    """Keep only recent, serious disasters that sit near a shipping route or port."""
    pts = _route_points(routes)
    cutoff = (dt.date.today() - dt.timedelta(days=RECENT_DAYS)).isoformat()
    keep = []
    for e in events:
        if e.get("to") and e["to"] < cutoff:               # finished more than a few days ago
            continue
        serious = e["alert"] in ("Orange", "Red") or e["type"] == "TC"
        if not serious or (e["type"] == "DR" and e["alert"] != "Red"):
            continue
        d = min(_km(e["lat"], e["lon"], a, b) for a, b in pts)
        if d <= NEAR_KM:
            keep.append({**e, "km": round(d)})
    rank = {"Red": 0, "Orange": 1, "Green": 2}
    return sorted(keep, key=lambda e: (rank.get(e["alert"], 3), e["km"]))[:6]


def _payload(sig, routes, routes_df):
    places = {**CHOKEPOINTS, **PORTS}
    used = {k for r in routes for k in r["signals"]}
    sites = []
    for k in [k for k in places if k in used]:
        v = places[k]
        lvl = signal_level(sig, k)
        val = sig.get(k, {}).get("value")
        sites.append({"key": k, "label": v["label"], "lat": v["lat"], "lng": v["lng"], "level": lvl,
                      "port": k in PORTS,
                      "line2": WORD.get(lvl, "Normal traffic"),
                      "line3": (f"{val:+.0f}% tankers" if val is not None else "no data")
                               + (f" · {REROUTE[k]}" if lvl == "HIGH" and k in REROUTE else "")})
    # Route points colored by the nearest signal on that route (so one route can change color)
    lv = {s["key"]: s["level"] for s in sites}
    lv["weather"] = "HIGH" if sig["weather"]["flag"] else "NORMAL"
    geo = {**{k: (v["lat"], v["lng"]) for k, v in places.items()}, "weather": (29.5, -94.5)}
    rts = []
    for r in routes:
        pts = []
        for lat, lng in r["points"]:
            best, bd = "NORMAL", 1e9
            for k in r["signals"]:
                if k not in geo:
                    continue
                d = ((lat - geo[k][0]) ** 2 + (lng - geo[k][1]) ** 2) ** 0.5
                if d < bd:
                    best, bd = lv.get(k, "NORMAL"), d
            pts.append([lat, lng, best if bd < 22 else "NORMAL"])
        rts.append({"name": r["name"], "points": pts})
    # Hazards: U.S. Gulf weather (NWS) + worldwide GDACS events
    hz = []
    w = sig["weather"]
    if w["flag"]:
        hz.append({"type": "WX", "lat": 29.2, "lng": -92.5, "level": "HIGH", "title": ", ".join(w["events"])[:40],
                   "line2": "U.S. Gulf Coast · NWS", "line3": "Plants & terminals may slow"})
    for e in relevant_disasters(sig.get("disasters", []), routes):
        level = {"Red": "HIGH", "Orange": "ELEVATED"}.get(e["alert"], "MONITOR")
        hz.append({"type": e["type"], "lat": e["lat"], "lng": e["lon"], "level": level,
                   "title": f"{e['kind']} {e['name']}".strip()[:38],
                   "line2": (((e["country"] or e["kind"])[:24]) + f" · {e['km']:,} km from route"),
                   "line3": (e["severity"] or f"{e['alert']} alert")[:44]})
    return {"routes": rts, "sites": sites, "ends": END_PORTS, "hazards": hz, "colors": COLORS,
            "focus": False, "note": ""}


_HTML = r"""
<div id="wrap">
  <div class="hdr"><div class="t">Global Risk Map</div><div class="note" id="note"></div>
    <div class="lg">
      <span><i style="background:#FF3B47;color:#FF3B47"></i>High Risk</span><span><i style="background:#FF8A1F;color:#FF8A1F"></i>Medium Risk</span>
      <span><i style="background:#FFC928;color:#FFC928"></i>Monitor</span><span><i style="background:#2EE06F;color:#2EE06F"></i>Normal</span>
    </div></div>
  <div id="map"><svg id="svg"></svg><div id="cards"></div>
    <div class="zoom"><button id="zin">+</button><button id="zout">−</button></div>
    <div class="sym" id="sym"></div>
    <div id="err" style="display:none">Map could not load (no internet or CDN blocked).</div></div>
</div>
<style>
 html,body{margin:0;background:transparent;font-family:Inter,"Segoe UI",system-ui,sans-serif;overflow:hidden}
 #wrap{background:radial-gradient(ellipse at 50% 30%,#0E2447 0%,#07101F 70%);border:1px solid #1E2B45;border-radius:12px;padding:12px 14px 10px;box-sizing:border-box;height:__H__px}
 .hdr{display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:6px}
 .t{font-size:17px;font-weight:700;color:#F8FAFC}
 .note{font-size:11.5px;color:#93C5FD;background:rgba(29,91,216,.25);border:1px solid rgba(147,197,253,.35);
       border-radius:999px;padding:2px 10px}
 .note:empty{display:none}
 .lg{margin-left:auto;display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:#CBD5E1}
 .lg span{display:inline-flex;align-items:center;gap:6px} .lg i{width:11px;height:11px;border-radius:99px;display:inline-block;box-shadow:0 0 6px currentColor}
 #map{position:relative;height:calc(100% - 34px);border-radius:10px;overflow:hidden;background:#000814;
       box-shadow:inset 0 0 40px rgba(0,0,0,.6)}
 #svg{width:100%;height:100%;display:block;cursor:grab}
 #cards{position:absolute;inset:0;pointer-events:none}
 .card{position:absolute;max-width:160px !important;background:rgba(9,20,42,.86);backdrop-filter:blur(4px);border:1px solid rgba(148,163,184,.35);
       border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,.45);
       padding:4px 8px 4px 6px;display:flex;gap:6px;align-items:flex-start;font-size:10.5px;color:#CBD5E1;
       line-height:1.35;max-width:190px;pointer-events:auto}
 .card b{color:#FFFFFF;font-size:11px;display:block}
 .card .l3{font-weight:600}
 .zoom{position:absolute;right:10px;bottom:34px;display:flex;flex-direction:column;border-radius:8px;overflow:hidden;
       box-shadow:0 2px 10px rgba(0,0,0,.5);border:1px solid rgba(148,163,184,.35)}
 .zoom button{width:32px;height:32px;border:none;background:rgba(9,20,42,.9);font-size:18px;color:#F8FAFC;cursor:pointer;
       border-bottom:1px solid rgba(148,163,184,.25)}
 .zoom button:hover{background:#17305A}
 .sym{position:absolute;left:8px;bottom:6px;display:flex;gap:10px;flex-wrap:wrap;font-size:11px;color:#E2E8F0;
      background:rgba(9,20,42,.8);border:1px solid rgba(148,163,184,.3);border-radius:6px;padding:3px 8px}
 .sym span{display:inline-flex;align-items:center;gap:4px}
 #err{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#B91C1C;font-size:13px}
</style>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>
<script>
(function(){
const D = __DATA__, C = D.colors;
if (typeof d3 === "undefined") { document.getElementById("err").style.display="flex"; return; }
const box = document.getElementById("map"), svg = d3.select("#svg"), cards = d3.select("#cards");
const W = box.clientWidth, H = box.clientHeight, CENTER = 0;
svg.attr("viewBox", `0 0 ${W} ${H}`);
const RAD = Math.PI/180, SC = W/(2*Math.PI);
const SPAN = Math.min(150, H/W*360), MID = Math.max(-58+SPAN/2, Math.min(80-SPAN/2, 12));
const proj = d3.geoEquirectangular().scale(SC).translate([W/2, H/2 + SC*MID*RAD]);
const g = svg.append("g"), gImg = g.append("g"), gLand = g.append("g"), gRoute = g.append("g"), gMark = g.append("g");
const path = d3.geoPath(proj);
let k = 1;

// ---------- satellite Earth image (NASA Blue Marble, equirectangular) ----------
const tl = proj([-180, 90]), br = proj([180, -90]);
gImg.append("image").attr("href", "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg")
  .attr("x", tl[0]).attr("y", tl[1]).attr("width", br[0]-tl[0]).attr("height", br[1]-tl[1])
  .attr("preserveAspectRatio", "none");
gImg.append("rect").attr("x", tl[0]).attr("y", tl[1]).attr("width", br[0]-tl[0]).attr("height", br[1]-tl[1])
  .attr("fill", "#04112B").attr("opacity", 0.18);          // slight dark tint so routes stand out

// ---------- symbols ----------
const ICON = {
  TC: (c)=>`<svg viewBox="0 0 24 24" width="100%" height="100%"><circle cx="12" cy="12" r="11" fill="#fff" stroke="${c}" stroke-width="1.5"/><path d="M12 5a7 7 0 0 1 7 7M12 19a7 7 0 0 1-7-7M5.5 8a7 7 0 0 1 9-2.5M18.5 16a7 7 0 0 1-9 2.5" stroke="${c}" stroke-width="2.4" fill="none" stroke-linecap="round"/><circle cx="12" cy="12" r="2.4" fill="${c}"/></svg>`,
  EQ: (c)=>`<svg viewBox="0 0 24 24" width="100%" height="100%"><circle cx="12" cy="12" r="11" fill="${c}"/><path d="M3 13h4l2-5 3 9 2-6 2 2h5" stroke="#fff" stroke-width="2" fill="none" stroke-linejoin="round"/></svg>`,
  FL: (c)=>`<svg viewBox="0 0 24 24" width="100%" height="100%"><circle cx="12" cy="12" r="11" fill="${c}"/><path d="M4 10c2-2 4 2 6 0s4 2 6 0 4 2 4 2M4 15c2-2 4 2 6 0s4 2 6 0 4 2 4 2" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round"/></svg>`,
  VO: (c)=>`<svg viewBox="0 0 24 24" width="100%" height="100%"><circle cx="12" cy="12" r="11" fill="${c}"/><path d="M5 18l4-8h6l4 8z" fill="#fff"/><path d="M11 8c-1-2 0-3 1-4M13 8c1-1 2-1 2-3" stroke="#fff" stroke-width="1.6" fill="none"/></svg>`,
  WF: (c)=>`<svg viewBox="0 0 24 24" width="100%" height="100%"><circle cx="12" cy="12" r="11" fill="${c}"/><path d="M12 5c1 3 5 5 5 9a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3-1-3 0-6 1-8z" fill="#fff"/></svg>`,
  DR: (c)=>`<svg viewBox="0 0 24 24" width="100%" height="100%"><circle cx="12" cy="12" r="11" fill="${c}"/><circle cx="12" cy="12" r="3.5" fill="#fff"/><path d="M12 4v2.5M12 17.5V20M4 12h2.5M17.5 12H20M6.3 6.3l1.8 1.8M15.9 15.9l1.8 1.8M6.3 17.7l1.8-1.8M15.9 8.1l1.8-1.8" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/></svg>`,
  WX: (c)=>`<svg viewBox="0 0 24 24" width="100%" height="100%"><circle cx="12" cy="12" r="11" fill="${c}"/><path d="M7 14a3.5 3.5 0 0 1 .5-7 4.5 4.5 0 0 1 8.5 1.5A3 3 0 0 1 16 14z" fill="#fff"/><path d="M9 16l-1 3M12.5 16l-1 3M16 16l-1 3" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/></svg>`,
  HIGH: (c)=>`<svg viewBox="0 0 24 24" width="100%" height="100%"><path d="M12 2l10.5 19h-21z" fill="${c}" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/><path d="M12 9v5.5" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/><circle cx="12" cy="17.6" r="1.4" fill="#fff"/></svg>`,
  ELEVATED: (c)=>`<svg viewBox="0 0 24 24" width="100%" height="100%"><circle cx="12" cy="12" r="11" fill="${c}"/><path d="M12 6.5v7" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/><circle cx="12" cy="17" r="1.4" fill="#fff"/></svg>`,
  MONITOR: (c)=>`<svg viewBox="0 0 24 24" width="100%" height="100%"><path d="M12 2l10.5 19h-21z" fill="${c}" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/><path d="M12 9v5.5" stroke="#0F172A" stroke-width="2.2" stroke-linecap="round"/><circle cx="12" cy="17.6" r="1.3" fill="#0F172A"/></svg>`,
  PORT: ()=>`<svg viewBox="0 0 24 24" width="100%" height="100%"><circle cx="12" cy="12" r="11" fill="#1D5BD8" stroke="#fff" stroke-width="1.5"/><path d="M12 7v10M9 9h6M7.5 13a4.5 4.5 0 0 0 9 0" stroke="#fff" stroke-width="1.8" fill="none" stroke-linecap="round"/><circle cx="12" cy="6.3" r="1.3" fill="none" stroke="#fff" stroke-width="1.4"/></svg>`,
};
const SYM = [["TC","Typhoon / cyclone"],["EQ","Earthquake"],["FL","Flood"],["VO","Volcano"],["WF","Wildfire"],
             ["DR","Drought"],["WX","U.S. weather alert"],["PORT","Port"]];
const present = new Set(D.hazards.map(h=>h.type).concat(["PORT"]));
document.getElementById("sym").innerHTML = SYM.filter(([t])=>present.has(t)).map(([t,n])=>
  `<span><span style="width:14px;height:14px;display:inline-block">${ICON[t](t==="TC"?"#F87171":"#94A3B8")}</span>${n}</span>`).join("")
  + (D.hazards.length ? "" : `<span style="color:#4ADE80;font-weight:600">✓ No active disasters near shipping routes</span>`);

// ---------- helpers ----------
function norm(lon){ let x = lon; while (x < CENTER-180) x += 360; while (x >= CENTER+180) x -= 360; return x; }
function splitDateline(pts){           // pts [lat, lng, level]; returns pieces that never jump across the map
  const out = []; let cur = [];
  for (let i=0;i<pts.length;i++){
    const p = [pts[i][0], norm(pts[i][1]), pts[i][2]];
    if (cur.length){
      const q = cur[cur.length-1];
      if (Math.abs(p[1]-q[1]) > 180){
        const edgeQ = q[1] > CENTER ? CENTER+179.9 : CENTER-179.9, edgeP = edgeQ > CENTER ? CENTER-179.9 : CENTER+179.9;
        const span = (edgeQ-q[1]) + (p[1]-edgeP), f = span ? (edgeQ-q[1])/span : 0.5, lat = q[0]+(p[0]-q[0])*f;
        cur.push([lat, edgeQ, q[2]]); out.push(cur); cur = [[lat, edgeP, p[2]]];
      }
    }
    cur.push(p);
  }
  if (cur.length) out.push(cur);
  return out;
}
const line = d3.line().curve(d3.curveCatmullRom.alpha(0.5));
const XY = (lat,lng)=>proj([lng,lat]);
const rank = {NODATA:0, NORMAL:1, MONITOR:2, ELEVATED:3, HIGH:4};

// arrow markers, one per color
const defs = svg.append("defs");
const glow = defs.append("filter").attr("id","glow").attr("x","-50%").attr("y","-50%").attr("width","200%").attr("height","200%");
glow.append("feGaussianBlur").attr("stdDeviation", 1.4).attr("result","b");
const mg = glow.append("feMerge"); mg.append("feMergeNode").attr("in","b"); mg.append("feMergeNode").attr("in","SourceGraphic");
Object.entries(C).forEach(([lvl,c])=>defs.append("marker").attr("id","a"+lvl).attr("viewBox","0 0 10 10")
  .attr("refX",5).attr("refY",5).attr("markerWidth",4).attr("markerHeight",4).attr("orient","auto-start-reverse")
  .append("path").attr("d","M0,0L10,5L0,10z").attr("fill",c));

function drawRoutes(){
  gRoute.selectAll("*").remove();
  D.routes.forEach(r=>{
    splitDateline(r.points).forEach(piece=>{
      if (piece.length < 2) return;
      const xy = piece.map(p=>XY(p[0],p[1]));
      // draw segment by segment so the color follows the nearest live signal
      for (let i=0;i<xy.length-1;i++){
        const lvl = rank[piece[i][2]] >= rank[piece[i+1][2]] ? piece[i][2] : piece[i+1][2];
        const seg = [xy[Math.max(i-1,0)], xy[i], xy[i+1], xy[Math.min(i+2,xy.length-1)]];
        const d = d3.line().curve(d3.curveCatmullRom.alpha(0.5))(seg);
        gRoute.append("path").attr("d", d).attr("fill","none").attr("stroke","#020817")
          .attr("stroke-width", 3.4/Math.sqrt(k)).attr("stroke-linecap","round").attr("opacity",0.55);
        const p = gRoute.append("path").attr("d", d).attr("fill","none").attr("stroke", C[lvl])
          .attr("stroke-width", 1.7/Math.sqrt(k)).attr("stroke-linecap","round").attr("filter","url(#glow)");
        if (i % 3 === 1) p.attr("marker-mid", null).attr("marker-end", "url(#a"+lvl+")");
        p.append("title").text(r.name);
      }
    });
  });
}

function placeMarkers(){
  gMark.selectAll("*").remove();
  const s = 1/Math.sqrt(k);
  const add = (lat,lng,size,html,tip)=>{
    const [x,y] = XY(lat,lng);
    const fo = gMark.append("foreignObject").attr("x", x-size*s/2).attr("y", y-size*s/2)
      .attr("width", size*s).attr("height", size*s).style("overflow","visible");
    fo.append("xhtml:div").style("width","100%").style("height","100%").html(html).attr("title", tip);
  };
  D.ends.forEach(p=>add(p.lat,p.lng,12,ICON.PORT(),p.label));
  D.sites.forEach(p=>{
    if (p.port){ add(p.lat,p.lng,13,ICON.PORT(),`${p.label}: ${p.line2}, ${p.line3}`); return; }
    if (p.level==="NORMAL"||p.level==="NODATA"){
      const [x,y]=XY(p.lat,p.lng);
      gMark.append("circle").attr("cx",x).attr("cy",y).attr("r",3.5*s).attr("fill",C[p.level])
        .attr("stroke","#fff").attr("stroke-width",1.2*s).attr("filter","url(#glow)").append("title").text(`${p.label}: ${p.line3}`);
    } else add(p.lat,p.lng,16,ICON[p.level](C[p.level]),`${p.label}: ${p.line2}, ${p.line3}`);
  });
  D.hazards.forEach(h=>add(h.lat,h.lng, h.type==="TC"?18:14, ICON[h.type](C[h.level]), `${h.title}: ${h.line3}`));
}

const leaders = svg.append("g");
function placeCards(){
  cards.selectAll("*").remove(); leaders.selectAll("*").remove();
  const t = d3.zoomTransform(svg.node());
  const items = [];
  D.sites.filter(p=>!p.port && rank[p.level]>=2).forEach(p=>items.push({...p, title:p.label, badge:p.level}));
  D.hazards.filter(h=>rank[h.level]>=3 || h.type==="WX" || h.type==="TC")
    .sort((a,b)=>rank[b.level]-rank[a.level]).slice(0,4)
    .forEach(h=>items.push({lat:h.lat,lng:h.lng,title:h.title,line2:h.line2,line3:h.line3,badge:h.type,level:h.level}));
  const placed = [];
  items.sort((a,b)=>rank[b.level]-rank[a.level]).slice(0,3).forEach(it=>{
    const [x0,y0] = XY(it.lat,it.lng), x = t.applyX(x0), y = t.applyY(y0);
    if (x < -20 || x > W+20 || y < -20 || y > H+20) return;
    const el = cards.append("div").attr("class","card").html(
      `<div style="width:14px;height:14px;flex-shrink:0;margin-top:1px">${(ICON[it.badge]||ICON.HIGH)(C[it.level])}</div>
       <div><b>${it.title}</b>${it.line2}<div class="l3" style="color:${C[it.level]}">${it.line3}</div></div>`);
    const w = el.node().offsetWidth, h = el.node().offsetHeight;
    const tries = [[14,-h-14],[14,12],[-w-14,-h-14],[-w-14,12],[-w/2,-h-22],[-w/2,18]];
    let best = null;
    for (const [dx,dy] of tries){
      const r = {x:x+dx, y:y+dy, w, h};
      const inside = r.x>=2 && r.y>=2 && r.x+w<=W-44 && r.y+h<=H-26;
      const clash = placed.some(q=>!(r.x+r.w<q.x||q.x+q.w<r.x||r.y+r.h<q.y||q.y+q.h<r.y));
      if (inside && !clash){ best = r; break; }
      if (!best && inside) best = {...r, weak:true};
    }
    if (!best || best.weak && placed.some(q=>!(best.x+w<q.x||q.x+q.w<best.x||best.y+h<q.y||q.y+q.h<best.y))){
      el.remove(); return;
    }
    el.style("left", best.x+"px").style("top", best.y+"px");
    const cx = Math.max(best.x, Math.min(x, best.x+w)), cy = Math.max(best.y, Math.min(y, best.y+h));
    leaders.append("line").attr("x1",x).attr("y1",y).attr("x2",cx).attr("y2",cy)
      .attr("stroke","rgba(255,255,255,0.6)").attr("stroke-width",1).attr("stroke-dasharray","2,2");
    placed.push(best);
  });
}

const zoom = d3.zoom().scaleExtent([1,6]).translateExtent([[0,0],[W,H]]).on("zoom", (ev)=>{
  g.attr("transform", ev.transform);
  if (Math.abs(ev.transform.k - k) > 0.05){ k = ev.transform.k; drawRoutes(); placeMarkers(); }
  placeCards();
});
svg.call(zoom).on("wheel.zoom", null);
document.getElementById("zin").onclick = ()=>svg.transition().duration(300).call(zoom.scaleBy, 1.5);
document.getElementById("zout").onclick = ()=>svg.transition().duration(300).call(zoom.scaleBy, 1/1.5);

fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json").then(r=>r.json()).then(w=>{
  const land = topojson.feature(w, w.objects.countries).features.filter(f=>f.id!=="010");
  gLand.selectAll("path").data(land).join("path").attr("d", path).attr("fill","none")
    .attr("stroke", f=>f.id==="840"?"#FDE68A":"rgba(255,255,255,0.55)")
    .attr("stroke-width", f=>f.id==="840"?1.1:0.5);
}).catch(()=>{});
drawRoutes(); placeMarkers(); placeCards();
document.getElementById("note").textContent = D.note || "";
// zoom to the selected origin-destination routes
if (D.focus && D.routes.length){
  const xy = [];
  D.routes.forEach(r=>splitDateline(r.points).forEach(pc=>pc.forEach(p=>xy.push(XY(p[0],p[1])))));
  const xs = xy.map(p=>p[0]), ys = xy.map(p=>p[1]);
  const x0=Math.min(...xs), x1=Math.max(...xs), y0=Math.min(...ys), y1=Math.max(...ys);
  const kk = Math.max(1, Math.min(4, 0.85*Math.min(W/Math.max(x1-x0,1), H/Math.max(y1-y0,1))));
  const tx = W/2 - kk*(x0+x1)/2, ty = H/2 - kk*(y0+y1)/2;
  svg.call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(kk));
}
})();
</script>
"""


def render_risk_map(sig, routes, routes_df, height: int = 440, focus: bool = False, note: str = "") -> None:
    data = _payload(sig, routes, routes_df)
    data["focus"], data["note"] = focus, note
    html = _HTML.replace("__DATA__", json.dumps(data)).replace("__H__", str(height - 4))
    components.html(html, height=height, scrolling=False)
