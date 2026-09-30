"""
Supplier-country lanes to U.S. Gulf Coast ports, and the Freightos freight estimate.

Each origin has one or more route options (A, B, C...). For every option:
  days        typical transit range (planning estimate, no port delays)
  signals     live signals that sit on the route (chokepoints, Gulf weather, destination port)
  cost_factor freight relative to the direct all-water option (scenario estimate, not a quote)
  add_on      extra cost per 40ft container for inland legs (editable estimate, e.g. rail)
  points      waypoints for the map
Only the direct ocean option is priced by Freightos. Other options scale that price, and are
labeled as estimated scenarios in the app.
"""

import math

import requests
import streamlit as st

ORIGINS = {
    "China":               {"port": "Shanghai", "q": "Shanghai, China", "lat": 31.23, "lng": 121.47,
                            "region": "Northeast Asia", "group": "asia"},
    "South Korea":         {"port": "Busan", "q": "Busan, South Korea", "lat": 35.10, "lng": 129.04,
                            "region": "Northeast Asia", "group": "asia"},
    "Vietnam":             {"port": "Cai Mep", "q": "Ho Chi Minh City, Vietnam", "lat": 10.50, "lng": 107.02,
                            "region": "Northeast Asia", "group": "asia"},
    "India":               {"port": "Nhava Sheva", "q": "Nhava Sheva, India", "lat": 18.95, "lng": 72.95,
                            "region": "Middle East", "group": "india"},
    "Saudi Arabia":        {"port": "Ras Tanura / Jubail", "q": "Jubail, Saudi Arabia", "lat": 26.64, "lng": 50.16,
                            "region": "Middle East", "group": "gulf"},
    "Netherlands":         {"port": "Rotterdam", "q": "Rotterdam, Netherlands", "lat": 51.95, "lng": 4.10,
                            "region": "Europe", "group": "europe"},
    "Brazil":              {"port": "Santos", "q": "Santos, Brazil", "lat": -23.95, "lng": -46.30,
                            "region": "South America", "group": "brazil"},
    "Nigeria":             {"port": "Bonny / Lagos", "q": "Lagos, Nigeria", "lat": 4.40, "lng": 7.15,
                            "region": "Europe", "group": "wafrica"},
    "Trinidad and Tobago": {"port": "Point Lisas", "q": "Point Lisas, Trinidad and Tobago", "lat": 10.40,
                            "lng": -61.50, "region": "South America", "group": "carib"},
    "Mexico":              {"port": "Monterrey (overland)", "q": "Monterrey, Mexico", "lat": 25.68, "lng": -100.31,
                            "region": "US Gulf Coast", "group": "mexico"},
}

DESTS = {
    "Houston, TX":        {"q": "Houston, TX, USA", "signal": "houston", "lat": 29.73, "lng": -95.00},
    "Port Arthur / Beaumont, TX": {"q": "Beaumont, TX, USA", "signal": "port_arthur", "lat": 29.87, "lng": -93.93},
    "Corpus Christi, TX": {"q": "Corpus Christi, TX, USA", "signal": None, "lat": 27.80, "lng": -97.40},
    "New Orleans, LA":    {"q": "New Orleans, LA, USA", "signal": None, "lat": 29.95, "lng": -90.07},
}

# ------------------------------------------------------------------ waypoints
_GULF_IN = [[24.3, -81.0], [24.8, -84.5], [27.0, -90.0]]
_PANAMA_E = [[9.35, -79.9], [12.0, -80.5], [17.0, -82.0], [21.5, -86.3], [24.0, -89.0]]
_PAC = {"China": [[31.2, 121.5], [30.0, 130.0], [30.0, 160.0], [25.0, -170.0], [18.0, -130.0], [10.0, -95.0],
                  [7.0, -82.0], [8.9, -79.5]],
        "South Korea": [[35.1, 129.0], [34.0, 145.0], [32.0, 170.0], [25.0, -165.0], [17.0, -128.0],
                        [10.0, -95.0], [7.0, -82.0], [8.9, -79.5]],
        "Vietnam": [[10.5, 107.0], [15.0, 118.0], [20.0, 135.0], [20.0, 170.0], [15.0, -150.0], [10.0, -110.0],
                    [7.0, -82.0], [8.9, -79.5]]}
_TO_LA = {"China": [[31.2, 121.5], [33.0, 135.0], [38.0, 160.0], [38.0, -165.0], [35.0, -135.0], [33.75, -118.2]],
          "South Korea": [[35.1, 129.0], [37.0, 145.0], [40.0, 170.0], [39.0, -160.0], [35.0, -135.0], [33.75, -118.2]],
          "Vietnam": [[10.5, 107.0], [20.0, 122.0], [30.0, 140.0], [36.0, 170.0], [36.0, -150.0], [33.75, -118.2]]}
_RAIL_LA_HOU = [[33.75, -118.2], [34.0, -114.5], [32.2, -110.9], [31.8, -106.4], [29.4, -98.5]]
_SE_ASIA_W = {"China": [[31.2, 121.5], [22.0, 118.0], [10.0, 110.0], [1.3, 104.0]],
              "South Korea": [[35.1, 129.0], [25.0, 124.0], [12.0, 112.0], [1.3, 104.0]],
              "Vietnam": [[10.5, 107.0], [5.0, 105.0], [1.3, 104.0]]}
_MALACCA_TO_INDIA = [[2.5, 101.5], [5.8, 95.0], [6.0, 80.0], [12.0, 60.0]]
_SUEZ_TO_GULF = [[12.6, 43.4], [20.0, 38.5], [27.5, 34.0], [30.0, 32.5], [33.5, 28.0], [36.5, 15.0], [36.0, -5.6],
                 [35.0, -20.0], [30.0, -45.0], [26.0, -70.0]] + _GULF_IN
_CAPE_TO_GULF = [[-25.0, 40.0], [-34.8, 20.0], [-30.0, 8.0], [-15.0, -8.0], [3.0, -25.0], [15.0, -50.0],
                 [22.0, -70.0]] + _GULF_IN


def _opt(key, name, days, signals, cost_factor, points, add_on=0, mode="Ocean"):
    return {"key": key, "name": name, "days": days, "signals": signals, "cost_factor": cost_factor,
            "add_on": add_on, "points": points, "mode": mode}


def route_options(origin: str, dest: str):
    """Route alternatives from a supplier country to a U.S. Gulf port."""
    o, d = ORIGINS[origin], DESTS[dest]
    end = [[d["lat"], d["lng"]]]
    dsig = [d["signal"]] if d["signal"] else []
    gulf = ["weather"] + dsig
    g = o["group"]
    if g == "asia":
        base = {"China": (30, 35), "South Korea": (28, 33), "Vietnam": (33, 38)}[origin]
        la = {"China": (14, 18), "South Korea": (12, 16), "Vietnam": (18, 22)}[origin]
        return [
            _opt("A", f"{o['port']} → Panama Canal → {dest.split(',')[0]}", base, ["panama"] + gulf, 1.0,
                 _PAC[origin] + _PANAMA_E + end),
            _opt("B", f"{o['port']} → Los Angeles → rail → {dest.split(',')[0]}",
                 (la[0] + 7, la[1] + 11), [], 0.75, _TO_LA[origin] + _RAIL_LA_HOU + end, add_on=2500,
                 mode="Ocean + rail"),
            _opt("C", f"{o['port']} → Malacca → Suez → {dest.split(',')[0]}", (base[0] + 8, base[1] + 9),
                 ["malacca", "bab", "suez"] + gulf, 1.15, _SE_ASIA_W[origin] + _MALACCA_TO_INDIA + _SUEZ_TO_GULF + end),
            _opt("D", f"{o['port']} → Malacca → Cape of Good Hope → {dest.split(',')[0]}",
                 (base[0] + 15, base[1] + 17), ["malacca", "good_hope"] + gulf, 1.3,
                 _SE_ASIA_W[origin] + _MALACCA_TO_INDIA[:3] + [[-10.0, 60.0]] + _CAPE_TO_GULF + end),
        ]
    if g in ("gulf", "india"):
        start = [[o["lat"], o["lng"]]] + ([[26.5, 56.5], [22.0, 62.0]] if g == "gulf" else [[15.0, 62.0]])
        pre = ["hormuz"] if g == "gulf" else []
        via_suez = (30, 35) if g == "gulf" else (25, 30)
        return [
            _opt("A", f"{o['port']} → Suez Canal → {dest.split(',')[0]}", via_suez, pre + ["bab", "suez"] + gulf, 1.0,
                 start + [[13.0, 51.0]] + _SUEZ_TO_GULF + end),
            _opt("B", f"{o['port']} → Cape of Good Hope → {dest.split(',')[0]}",
                 (via_suez[0] + 10, via_suez[1] + 10), pre + ["good_hope"] + gulf, 1.25,
                 start + [[5.0, 58.0], [-10.0, 50.0]] + _CAPE_TO_GULF + end),
        ]
    if g == "europe":
        return [_opt("A", f"Rotterdam → Atlantic → {dest.split(',')[0]}", (15, 18), gulf, 1.0,
                     [[51.95, 4.1], [49.5, -6.0], [47.0, -20.0], [43.0, -40.0], [38.0, -60.0], [32.0, -75.0],
                      [26.5, -79.3]] + _GULF_IN + end)]
    if g == "brazil":
        return [_opt("A", f"Santos → Caribbean → {dest.split(',')[0]}", (16, 19), gulf, 1.0,
                     [[-23.95, -46.3], [-20.0, -39.0], [-10.0, -34.0], [-2.0, -36.0], [5.0, -45.0],
                      [13.0, -62.0], [18.0, -76.0], [21.3, -86.0], [25.0, -90.0]] + end)]
    if g == "wafrica":
        return [_opt("A", f"{o['port']} → Atlantic → {dest.split(',')[0]}", (18, 22), gulf, 1.0,
                     [[4.4, 7.15], [2.0, -5.0], [5.0, -25.0], [12.0, -50.0], [18.0, -68.0], [22.0, -80.0]]
                     + _GULF_IN + end)]
    if g == "carib":
        return [_opt("A", f"Point Lisas → Caribbean → {dest.split(',')[0]}", (5, 7), gulf, 1.0,
                     [[10.4, -61.5], [14.0, -70.0], [18.5, -80.0], [21.5, -86.3], [25.0, -90.0]] + end)]
    if g == "mexico":
        return [
            _opt("A", f"Monterrey → truck → {dest.split(',')[0]}", (1, 2), gulf, 1.0,
                 [[25.68, -100.31], [27.5, -99.5], [28.8, -97.5]] + end, mode="Truck"),
            _opt("B", f"Monterrey → rail → {dest.split(',')[0]}", (2, 4), gulf, 0.8,
                 [[25.68, -100.31], [27.5, -99.5], [29.4, -98.5]] + end, mode="Rail"),
        ]
    raise KeyError(origin)


def as_map_routes(origin, dest, options):
    """Convert route options into the route dicts used by the risk map and route table."""
    return [{"name": f"Route {o['key']}: {o['name']}", "origin": ORIGINS[origin]["region"], "dest": "US Gulf Coast",
             "signals": o["signals"], "typical": f"{o['days'][0]}–{o['days'][1]} days", "points": o["points"]}
            for o in options]


def great_circle_km(a_lat, a_lng, b_lat, b_lng):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dl = math.radians(b_lng - a_lng)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


# ------------------------------------------------------------------ Freightos (public estimate, no key)
FREIGHTOS_URL = "https://ship.freightos.com/api/shippingCalculator"
FREIGHTOS_ERRORS = {}


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def _freightos(origin_q, dest_q, loadtype, quantity):
    r = requests.get(FREIGHTOS_URL, params={"loadtype": loadtype, "quantity": quantity, "origin": origin_q,
                                            "destination": dest_q, "estimate": "true", "format": "json"},
                     headers={"User-Agent": "Mozilla/5.0 (student project)"}, timeout=12)
    r.raise_for_status()
    est = (r.json().get("response") or {}).get("estimatedFreightRates") or {}
    modes = est.get("mode")
    modes = modes if isinstance(modes, list) else [modes] if modes else []
    out = []
    for m in modes:
        try:
            out.append({"mode": m.get("mode"),
                        "min": float(m["price"]["min"]["moneyAmount"]["amount"]),
                        "max": float(m["price"]["max"]["moneyAmount"]["amount"]),
                        "t_min": float(m["transitTimes"]["min"]), "t_max": float(m["transitTimes"]["max"])})
        except (KeyError, TypeError, ValueError):
            continue
    return out            # [] = Freightos had no carrier quotes; cached so the app does not ask again


def freight_estimate(origin: str, dest: str, containers: int = 1, loadtype: str = "container40"):
    """Freightos price range for the whole shipment (FCL preferred). None if unavailable."""
    try:
        res = _freightos(ORIGINS[origin]["q"], DESTS[dest]["q"], loadtype, int(max(containers, 1)))
    except Exception as e:
        FREIGHTOS_ERRORS[f"{origin}→{dest}"] = repr(e)[:200]
        return None
    if not res:
        FREIGHTOS_ERRORS[f"{origin}→{dest}"] = "Freightos returned no carrier quotes for this lane"
        return None
    fcl = [m for m in res if (m["mode"] or "").upper() in ("FCL", "OCEAN")] or \
          [m for m in res if (m["mode"] or "").upper() in ("FTL", "LTL")] or res
    return min(fcl, key=lambda m: m["min"])
