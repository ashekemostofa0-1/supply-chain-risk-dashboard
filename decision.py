"""
Decision engine: Supply Chain Risk Index (0-100), what changed, outlook, actions,
order-now-vs-later scenarios, route alternatives and supplier comparison.

Every number comes from the live signals (NWS, GDACS, EIA, IMF PortWatch, BLS, Freightos)
or from the user's own inputs. Rules are simple and written out so they can be explained
in the demo and tested in the backtest. Nothing here is a price forecast.
"""

import datetime as dt
import html
import math

import numpy as np
import pandas as pd
import streamlit as st

from lanes import DESTS, ORIGINS, as_map_routes, freight_estimate, route_options
from live_data import CHOKEPOINTS, SUPPLY_WEATHER
from risk_map import relevant_disasters
from ui_style import STATUS, card_title, pill

WEIGHTS = {"weather": 0.20, "port": 0.15, "route": 0.20, "freight": 0.15, "price": 0.15, "structure": 0.15}
NAMES = {"weather": "Weather & disasters", "port": "Destination port", "route": "Route / chokepoints",
         "freight": "Freight cost trend", "price": "Commodity price", "structure": "Industry structure"}
BENCH_NAME = {"brent": "Brent crude", "wti": "WTI crude", "gas": "Henry Hub gas"}


def level_of(score):
    score = round(score)          # match the rounded number shown on screen
    return "HIGH" if score >= 70 else "ELEVATED" if score >= 45 else "NORMAL"


LEVEL_WORD = {"HIGH": "HIGH", "ELEVATED": "MEDIUM", "NORMAL": "LOW"}


# ------------------------------------------------------------------ small helpers
def _pct(df, as_of, recent, base, col="value"):
    """Recent average vs the base-period average before it, using data up to as_of."""
    if df is None or df.empty:
        return None
    d = df[df["date"] <= as_of].sort_values("date")
    s = d[col].astype(float)
    if len(s) < recent + base:
        return None
    now, before = s.tail(recent).mean(), s.iloc[-(recent + base):-recent].mean()
    return None if before == 0 else (now - before) / before * 100


def _last(df):
    return None if df is None or df.empty else float(df.sort_values("date")["value"].iloc[-1])


def _yoy(bls, mode, as_of):
    if bls is None or bls.empty:
        return None
    d = bls[(bls["mode"] == mode) & (bls["date"] <= as_of)].set_index("date")["value"]
    if len(d) < 13:
        return None
    prev = d.get(d.index[-1] - pd.DateOffset(years=1))
    return None if prev is None else (d.iloc[-1] / prev - 1) * 100


def traffic_score(v):
    return None if v is None else (5.0 if v >= 0 else min(100.0, 5 + (-v) * 1.9))


def price_score(ch):
    return None if ch is None else min(100.0, abs(ch) * 4)


def freight_score(yoy):
    return None if yoy is None else float(np.clip(15 + yoy * 2.2, 0, 100))


def _daily_sigma(prices, days=250):
    if prices is None or len(prices) < 30:
        return None
    s = prices.sort_values("date")["value"].astype(float).tail(days + 1)
    r = np.log(s).diff().dropna()
    return float(r.std())


# ------------------------------------------------------------------ risk index
def risk_components(sig, product, origin, dest, option, structural, as_of=None):
    """Component scores 0-100 for one route option, using data up to `as_of` (default: latest)."""
    now = pd.Timestamp.now(tz="America/Chicago").tz_localize(None)
    as_of = as_of or now
    raw = sig.get("traffic_raw", {})
    parts, notes = {}, {}

    # weather: NWS (Gulf destination) + GDACS near this route
    w = 5.0
    det = sig["weather"]["detail"]
    if det is not None and not det.empty:
        d = det.copy()
        d["eff"] = pd.to_datetime(d.get("effective"), errors="coerce", utc=True).dt.tz_convert(None) \
            if "effective" in d else pd.NaT
        d = d[d["eff"].isna() | (d["eff"] <= as_of)] if as_of < now else d
        ev = [str(e).lower() for e in d["event"].tolist()]
        rel = pd.Series([any(x in e for x in SUPPLY_WEATHER) for e in ev], index=d.index, dtype=bool)
        sev = pd.Series([str(v) in ("Severe", "Extreme") for v in d["severity"].tolist()], index=d.index, dtype=bool)
        if len(d) and (rel & sev).any():
            w = 85.0
            notes["weather"] = ", ".join(sorted(set(d.loc[rel & sev, "event"])))[:60] + f" near {dest.split(',')[0]}"
        elif len(d):
            w = 25.0
            notes["weather"] = f"{len(d)} minor Gulf Coast weather alert(s)"
    near = relevant_disasters(sig.get("disasters", []), as_map_routes(origin, dest, [option]))
    near = [e for e in near if not e.get("from") or pd.Timestamp(e["from"]) <= as_of]
    for e in near:
        s = {"Red": 90.0, "Orange": 70.0}.get(e["alert"], 50.0)
        if s > w:
            w = s
            notes["weather"] = f"{e['kind']} {e['name']} ({e['country'] or 'at sea'}), {e['km']:,} km from route"
    parts["weather"] = w
    notes.setdefault("weather", "no supply-relevant alerts")

    # destination port traffic
    key = DESTS[dest]["signal"]
    keys = [key] if key else ["houston", "port_arthur"]
    vals = [_pct(raw.get(k), as_of, 7, 90) for k in keys]
    vals = [v for v in vals if v is not None]
    v = min(vals) if vals else None
    parts["port"] = traffic_score(v)
    notes["port"] = (f"tanker calls {v:+.0f}% vs 90-day avg" + ("" if key else " (nearest Gulf ports)")
                     if v is not None else "no port data")

    # route / chokepoints
    chokes = [k for k in option["signals"] if k in CHOKEPOINTS]
    if chokes:
        cv = {k: _pct(raw.get(k), as_of, 7, 90) for k in chokes}
        cv = {k: x for k, x in cv.items() if x is not None}
        if cv:
            worst = min(cv, key=cv.get)
            parts["route"] = traffic_score(cv[worst])
            notes["route"] = f"{CHOKEPOINTS[worst]['label']} tankers {cv[worst]:+.0f}%"
        else:
            parts["route"], notes["route"] = None, "no chokepoint data"
    else:
        parts["route"], notes["route"] = 10.0, "no major chokepoint on this route"

    # freight cost trend (BLS): truck for overland, sea otherwise
    fmode = "truck" if option["mode"] in ("Truck",) else "rail" if option["mode"] == "Rail" else "sea"
    y = _yoy(sig.get("freight", {}).get("bls"), fmode, as_of)
    parts["freight"] = freight_score(y)
    notes["freight"] = f"U.S. {fmode} freight prices {y:+.1f}% vs last year (BLS)" if y is not None else "no data"

    # commodity price move (product benchmark)
    b = product["benchmark"]
    ch = _pct(sig["prices_full"].get(b), as_of, 5, 60)
    parts["price"] = price_score(ch)
    notes["price"] = f"{BENCH_NAME[b]} {ch:+.1f}% (5-day vs 60-day)" if ch is not None else "no data"

    parts["structure"] = structural * 100
    notes["structure"] = f"structural score {structural:.2f} ({'fragile' if structural >= 0.35 else 'sturdier'})"
    return parts, notes


def combine(parts):
    used = {k: v for k, v in parts.items() if v is not None}
    wsum = sum(WEIGHTS[k] for k in used)
    return sum(WEIGHTS[k] * v for k, v in used.items()) / wsum if wsum else 0.0


# ------------------------------------------------------------------ route evaluation
def evaluate_routes(sig, product, origin, dest, structural, qty_units, payload, fallback_per_box,
                    freight_quote, w_cost=0.4, w_time=0.3, w_risk=0.3):
    """Cost, time and risk for every route option, plus a balanced score (lower = better)."""
    options = route_options(origin, dest)
    boxes = max(1, math.ceil(qty_units / payload)) if product["freight"] == "container" else 0
    est = freight_estimate(origin, dest, boxes) if product["freight"] == "container" else None
    rows = []
    for o in options:
        parts, notes = risk_components(sig, product, origin, dest, o, structural)
        route_risk = combine({k: parts[k] for k in ("weather", "port", "route")})
        if product["freight"] == "container":
            if est:
                lo, hi = est["min"], est["max"]
                src = "Freightos"
            else:
                lo = hi = fallback_per_box * boxes
                src = "fallback"
            lo, hi = lo * o["cost_factor"] + o["add_on"] * boxes, hi * o["cost_factor"] + o["add_on"] * boxes
        else:
            lo = hi = freight_quote * qty_units * o["cost_factor"]
            src = "your quote"
        rows.append({"key": o["key"], "name": o["name"], "mode": o["mode"], "days": o["days"],
                     "f_lo": lo, "f_hi": hi, "f_src": src, "risk": route_risk, "parts": parts, "notes": notes,
                     "option": o, "est": est if o["key"] == "A" else None})
    df = pd.DataFrame(rows)

    def norm(s):
        return (s - s.min()) / (s.max() - s.min()) if s.max() > s.min() else s * 0

    mid = (df["f_lo"] + df["f_hi"]) / 2
    days = df["days"].apply(lambda d: sum(d) / 2)
    tot = w_cost + w_time + w_risk or 1
    df["balanced"] = (w_cost * norm(mid) + w_time * norm(days) + w_risk * norm(df["risk"])) / tot * 100
    df["best"] = df["balanced"] == df["balanced"].min()
    return df, boxes


# ------------------------------------------------------------------ what changed / outlook / actions
ACTION_BY_DRIVER = {
    "weather": "Confirm supplier and terminal status at the destination and move deliveries ahead of the "
               "storm window.",
    "port": "Ask your forwarder about berth and truck delays at the destination port; consider another Gulf port.",
    "route": "Compare the alternative routes below and ask the carrier about reroute surcharges and extra days.",
    "freight": "Book freight earlier or lock a contract rate; transport costs are rising.",
    "price": "Consider buying part of the volume now or hedging; the commodity price is moving fast.",
    "structure": "Keep extra safety stock; this industry is structurally exposed to supply shocks.",
}


def what_changed(sig, product, origin, dest, option, structural, days):
    now = pd.Timestamp.now(tz="America/Chicago").tz_localize(None)
    cur, cur_n = risk_components(sig, product, origin, dest, option, structural)
    prev, _ = risk_components(sig, product, origin, dest, option, structural, as_of=now - pd.Timedelta(days=days))
    s_now, s_prev = combine(cur), combine(prev)
    deltas = {k: WEIGHTS[k] * ((cur[k] or 0) - (prev[k] or 0)) for k in cur if cur[k] is not None}
    return {"now": s_now, "prev": s_prev, "parts": cur, "prev_parts": prev, "notes": cur_n, "deltas": deltas}


def drivers(parts, deltas, n=2):
    """Main drivers: biggest recent increases, otherwise biggest weighted contributions."""
    up = [k for k, d in sorted(deltas.items(), key=lambda t: -t[1]) if d > 0.5][:n]
    if up:
        return up, True
    top = sorted((k for k in parts if parts[k] is not None), key=lambda k: -WEIGHTS[k] * parts[k])[:n]
    return top, False


def outlook(sig, product):
    b = product["benchmark"]
    p = sig["prices_full"].get(b)
    last, sigma = _last(p), _daily_sigma(p)
    out = {}
    if last and sigma:
        for d in (7, 30):
            s = sigma * math.sqrt(d * 252 / 365)
            out[d] = (last * math.exp(-s), last * math.exp(s))
    return last, out


# ------------------------------------------------------------------ rendering: decision center
def _bar(v, color):
    v = 0 if v is None else v
    return (f'<div style="height:8px;background:#EEF2F7;border-radius:99px;overflow:hidden">'
            f'<div style="width:{v:.0f}%;height:100%;background:{color};border-radius:99px"></div></div>')


def render_score_card(res):
    s, lvl = res["now"], level_of(res["now"])
    st_ = STATUS[lvl]
    delta = s - res["prev"]
    arrow = "↑" if delta > 0.5 else "↓" if delta < -0.5 else "→"
    rows = ""
    for k in WEIGHTS:
        v = res["parts"].get(k)
        c = STATUS[level_of(v)]["fg"] if v is not None else "#94A3B8"
        rows += (f'<div style="display:grid;grid-template-columns:140px 1fr 34px;gap:8px;align-items:center;'
                 f'margin:5px 0;font-size:12.5px;color:#334155"><span>{NAMES[k]}</span>{_bar(v, c)}'
                 f'<b style="text-align:right;color:#0F172A">{"–" if v is None else f"{v:.0f}"}</b></div>')
    st.markdown(
        f"""<div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap">
        <span style="font-size:46px;font-weight:800;color:{st_['fg']};line-height:1">{s:.0f}</span>
        <span style="font-size:15px;color:#64748B">/ 100</span>
        <span class="pill" style="color:{st_['fg']};background:{st_['tint']};font-size:13px">{LEVEL_WORD[lvl]}</span>
        <span style="font-size:13px;color:#334155">{arrow} from {res['prev']:.0f}</span></div>
        <div style="margin-top:10px">{rows}</div>""", unsafe_allow_html=True)


def render_changes(res, days):
    ds, cur, prev, notes = res["deltas"], res["parts"], res["prev_parts"], res["notes"]
    items = ""
    for k in sorted(ds, key=lambda k: -abs(ds[k])):
        d = (cur[k] or 0) - (prev[k] or 0)
        icon, col = ("▲", "#DC2626") if d > 2 else ("▼", "#16A34A") if d < -2 else ("•", "#64748B")
        word = "risk up" if d > 2 else "risk down" if d < -2 else "stable"
        items += (f'<div style="display:flex;gap:8px;margin:5px 0;font-size:13px">'
                  f'<span style="color:{col};width:14px">{icon}</span><div><b>{NAMES[k]}</b> '
                  f'<span style="color:{col}">{word}</span><br><span style="color:#64748B">'
                  f'{html.escape(notes[k])}</span></div></div>')
    top, rising = drivers(cur, ds)
    main = " and ".join(NAMES[k].lower() for k in top)
    lvl_prev, lvl_now = LEVEL_WORD[level_of(res["prev"])], LEVEL_WORD[level_of(res["now"])]
    sentence = (f"Risk moved from <b>{res['prev']:.0f} → {res['now']:.0f}</b> ({lvl_prev} → {lvl_now}). "
                + (f"Main driver: {main}." if rising else f"No big change; the score is held up mainly by {main}."))
    st.markdown(f'<div style="font-size:13.5px;margin-bottom:6px">{sentence}</div>{items}', unsafe_allow_html=True)
    st.caption(f"Compared with the data available {days} day{'s' if days > 1 else ''} ago. Port and chokepoint "
               "data run 2 to 4 days behind; BLS freight is monthly.")


def render_outlook_actions(sig, product, res, origin, dest):
    last, rng = outlook(sig, product)
    b = BENCH_NAME[product["benchmark"]]
    lines = []
    if rng:
        u = "/MMBtu" if product["benchmark"] == "gas" else "/bbl"
        lines.append(f"<b>{b}</b> now ${last:,.2f}{u}. Usual range in 7 days ${rng[7][0]:,.2f}–{rng[7][1]:,.2f}, "
                     f"in 30 days ${rng[30][0]:,.2f}–{rng[30][1]:,.2f} (±1σ of past moves).")
    yoy = res["parts"].get("freight")
    fm = (sig.get("freight") or {}).get("modes", {}).get("sea", {})
    if fm.get("yoy") is not None:
        lines.append(f"<b>Freight</b> trend {fm['yoy']:+.1f}% a year means about "
                     f"{((1 + fm['yoy'] / 100) ** (1 / 12) - 1) * 100:+.1f}% per month if it continues.")
    det = sig["weather"]["detail"]
    if sig["weather"]["flag"] and det is not None and "expires" in det:
        exp = pd.to_datetime(det["expires"], errors="coerce", utc=True).max()
        if pd.notna(exp):
            lines.append(f"<b>Weather</b>: current Gulf Coast alerts run until about "
                         f"{exp.tz_convert('America/Chicago'):%b %d, %I %p}.")
    lvl = level_of(res["now"])
    top, _ = drivers(res["parts"], res["deltas"])
    lines.append(f"<b>Next 7 days</b>: risk likely stays <b>{LEVEL_WORD[lvl]}</b> while "
                 + " and ".join(NAMES[k].lower() for k in top) + " remain the main pressures.")
    st.markdown("<div style='font-size:13px;line-height:1.5'>" + "<br>".join(lines) + "</div>",
                unsafe_allow_html=True)
    st.markdown("**What procurement should consider**")
    acts = [ACTION_BY_DRIVER[k] for k in top]
    if lvl == "NORMAL":
        acts = ["No urgent action. Keep normal ordering and watch this page for changes."] + acts[:1]
    for a in acts:
        st.markdown(f"- {a}")


# ------------------------------------------------------------------ rendering: order now vs later
def _m(x):
    return f"${x / 1e6:,.2f}M" if abs(x) >= 1e6 else f"${x / 1e3:,.0f}K"


def render_order_simulator(sig, product, origin, dest, routes_df, boxes, score, qty, unit_price, tariff_pct,
                           allow_pct, grow_freight, route_key, sens):
    r = routes_df[routes_df["key"] == route_key].iloc[0]
    sigma = _daily_sigma(sig["prices_full"].get(product["benchmark"])) or 0.0
    fm = (sig.get("freight") or {}).get("modes", {})
    fmode = "truck" if r["mode"] == "Truck" else "rail" if r["mode"] == "Rail" else "sea"
    yoy = fm.get(fmode, {}).get("yoy")
    g = (1 + yoy / 100) ** (1 / 12) - 1 if (grow_freight and yoy is not None) else 0.0
    rows = []
    for m, label in [(0, "Now"), (1, "+30 days"), (2, "+60 days"), (3, "+90 days")]:
        s = sens * sigma * math.sqrt(m * 21)
        mat_lo, mat_hi = qty * unit_price * math.exp(-s), qty * unit_price * math.exp(s)
        f_lo, f_hi = r["f_lo"] * (1 + g) ** m, r["f_hi"] * (1 + g) ** m
        tar_lo, tar_hi = mat_lo * tariff_pct / 100, mat_hi * tariff_pct / 100
        a = allow_pct / 100 * score / 100 * (1 + m / 3)
        al_lo, al_hi = (mat_lo + f_lo) * a, (mat_hi + f_hi) * a
        rows.append({"Scenario": label, "Order date": (dt.date.today() + dt.timedelta(days=30 * m)).strftime("%b %d"),
                     "lo": mat_lo + f_lo + tar_lo + al_lo, "hi": mat_hi + f_hi + tar_hi + al_hi,
                     "mat": (mat_lo, mat_hi), "fr": (f_lo, f_hi), "tar": (tar_lo, tar_hi), "al": (al_lo, al_hi)})

    def cell(p):
        return _m(p[0]) if abs(p[1] - p[0]) < 500 else f"{_m(p[0])}–{_m(p[1])}"

    body = "".join(
        f"<tr><td><b>{x['Scenario']}</b><br><span style='color:#64748B;font-size:12px'>{x['Order date']}</span></td>"
        f"<td class=num>{cell(x['mat'])}</td><td class=num>{cell(x['fr'])}</td><td class=num>{cell(x['tar'])}</td>"
        f"<td class=num>{cell(x['al'])}</td><td class=num><b>{cell((x['lo'], x['hi']))}</b></td></tr>" for x in rows)
    st.markdown('<div class="tbl-wrap"><table class="rt"><tr><th>Scenario</th><th class=num>Material</th>'
                '<th class=num>Freight</th><th class=num>Tariff / fees</th><th class=num>Risk allowance</th>'
                f'<th class=num>Estimated landed cost</th></tr>{body}</table></div>', unsafe_allow_html=True)

    mids = [(x["lo"] + x["hi"]) / 2 for x in rows]
    best = int(np.argmin(mids))
    other = 1 if best == 0 else 0
    diff = mids[other] - mids[best]
    half = np.mean([(x["hi"] - x["lo"]) / 2 for x in (rows[best], rows[other])]) or 1
    conf = "High" if diff / half > 1 else "Moderate" if diff / half > 0.4 else "Low"
    factors = []
    if g > 0:
        factors.append(f"rising {fmode} freight (+{g * 100:.1f}% per month, BLS trend)")
    if score >= 45:
        factors.append(f"elevated supply risk ({score:.0f}/100) adds to the risk allowance the longer you wait")
    factors.append("price uncertainty widens with time")
    st.markdown(
        f"""<div class="takeaways" style="margin-top:10px"><h4>💡 Recommendation logic</h4>
        <div style="font-size:13.5px;line-height:1.6">Lower-cost scenario: <b>{rows[best]['Scenario']}</b>
        (midpoint {_m(mids[best])}).<br>Estimated difference vs {rows[other]['Scenario'].lower()}: <b>{_m(diff)}</b>.<br>
        Main factors: {'; '.join(factors)}.<br>Confidence: <b>{conf}</b>
        (how clearly the difference stands out from the price ranges).</div></div>""", unsafe_allow_html=True)
    st.caption("Material ranges use the past year's volatility of "
               f"{BENCH_NAME[product['benchmark']]} × your price sensitivity; they show about 2 in 3 likely "
               "outcomes, not a forecast. Risk allowance = (material + freight) × allowance % × risk score/100, "
               "growing with the wait. Freight: " + ("Freightos estimate" if r["f_src"] == "Freightos" else
                                                      "your quote or fallback") + f", {r['name']}.")


# ------------------------------------------------------------------ rendering: routes and suppliers
def render_route_table(routes_df, product):
    unit = "shipment"
    rows = ""
    for x in routes_df.itertuples():
        lvl = level_of(x.risk)
        f = _m(x.f_lo) if abs(x.f_hi - x.f_lo) < 500 else f"{_m(x.f_lo)}–{_m(x.f_hi)}"
        star = " ⭐ Best balance" if x.best else ""
        rows += (f"<tr><td><b>Route {x.key}</b>{star}<br><span style='color:#64748B;font-size:12px'>"
                 f"{html.escape(x.name)} · {x.mode}</span></td><td class=num>{x.days[0]}–{x.days[1]} days</td>"
                 f"<td class=num>{f}<br><span style='color:#64748B;font-size:11px'>{x.f_src}</span></td>"
                 f"<td>{pill(lvl, f'{LEVEL_WORD[lvl].title()} {x.risk:.0f}')}</td>"
                 f"<td class=num>{x.balanced:.0f}</td></tr>")
    st.markdown('<div class="tbl-wrap"><table class="rt"><tr><th>Route</th><th class=num>Transit</th>'
                f'<th class=num>Freight ({unit})</th><th>Route risk</th><th class=num>Balance score<br>'
                f'<span style="font-weight:400;font-size:11px">lower = better</span></th></tr>{rows}</table></div>',
                unsafe_allow_html=True)


def supplier_table(sig, product, dest, structural, qty, payload, fallback_per_box, freight_quote, prices,
                   tariff_pct, allow_pct):
    rows = []
    for c in product["origins"]:
        df, _ = evaluate_routes(sig, product, c, dest, structural, qty, payload, fallback_per_box, freight_quote)
        b = df.loc[df["balanced"].idxmin()]
        parts, _ = risk_components(sig, product, c, dest, b["option"], structural)
        risk = combine(parts)
        price = prices.get(c, product["price"] or 0)
        mat = price * qty
        fr = (b["f_lo"] + b["f_hi"]) / 2
        landed = mat * (1 + tariff_pct / 100) + fr + (mat + fr) * allow_pct / 100 * risk / 100
        rows.append({"Supplier country": c, "Port": ORIGINS[c]["port"], "Best route": b["name"],
                     "Lead time (days)": f"{b['days'][0]}–{b['days'][1]}", "_days": sum(b["days"]) / 2,
                     "Price per unit": price, "Freight": fr, "Landed cost": landed,
                     "Risk": risk, "src": b["f_src"]})
    df = pd.DataFrame(rows)

    def norm(s):
        return (s - s.min()) / (s.max() - s.min()) if s.max() > s.min() else s * 0

    df["Overall"] = (0.4 * norm(df["Landed cost"]) + 0.3 * norm(df["_days"]) + 0.3 * norm(df["Risk"])) * 100
    return df.sort_values("Overall")


def render_suppliers(df, product):
    rows = ""
    best = df["Overall"].min()
    for _, x in df.iterrows():
        lvl = level_of(x["Risk"])
        rows += (f"<tr><td><b>{x['Supplier country']}</b>{' ⭐ Best overall' if x['Overall'] == best else ''}<br>"
                 f"<span style='color:#64748B;font-size:12px'>{html.escape(x['Port'])}</span></td>"
                 f"<td class=num>${x['Price per unit']:,.0f}/{product['unit']}</td><td class=num>{_m(x['Freight'])}</td>"
                 f"<td class=num>{x['Lead time (days)']}</td>"
                 f"<td>{pill(lvl, LEVEL_WORD[lvl].title() + ' ' + format(x['Risk'], '.0f'))}</td>"
                 f"<td class=num><b>{_m(x['Landed cost'])}</b></td><td class=num>{x['Overall']:.0f}</td></tr>")
    st.markdown('<div class="tbl-wrap"><table class="rt"><tr><th>Supplier country</th><th class=num>Price</th>'
                '<th class=num>Freight</th><th class=num>Lead time</th><th>Risk</th>'
                '<th class=num>Est. landed cost</th><th class=num>Overall<br><span style="font-weight:400;'
                f'font-size:11px">lower = better</span></th></tr>{rows}</table></div>', unsafe_allow_html=True)
