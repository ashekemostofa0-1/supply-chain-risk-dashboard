"""
Live parts of the dashboard: product strip, alert cards, tanker traffic card,
industry alert box and trend charts.
"""

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from live_data import CHOKEPOINTS, PORTS

PLACE_LABELS = {k: v["label"] for k, v in {**CHOKEPOINTS, **PORTS}.items()}
from products import BENCHMARKS
from routes import signal_level
from ui_style import STATUS, alert_card, pill

ACTIONS = {
    "HIGH": ["Confirm feedstock and raw-material deliveries for the next 2 weeks",
             "Contact backup suppliers outside the Gulf Coast",
             "Delay non-urgent shipments through affected ports",
             "Warn customers about possible delays and price increases"],
    "ELEVATED": ["Check inventory days-on-hand for critical inputs",
                 "Watch the flagged signals daily",
                 "Get quotes from a second supplier"],
    "NORMAL": ["No action needed. Keep normal ordering."],
}
SIGNAL_LABELS = {"weather": "severe Gulf Coast weather", "wti": "WTI crude price move",
                 "gas": "natural gas price move", "refinery": "low Gulf Coast refinery use",
                 "port_arthur": "Port Arthur tanker drop", "houston": "Houston tanker drop",
                 "panama": "Panama Canal tanker drop"}
LINE = "#1D5BD8"
LINE2 = "#EB6834"
GUIDE = "#64748B"


def ago(ts) -> str:
    """'2 days ago' style label for a data date."""
    if ts is None:
        return ""
    today = pd.Timestamp.now(tz="America/Chicago").tz_localize(None).normalize()
    d = (today - pd.Timestamp(ts).normalize()).days
    return "today" if d <= 0 else "1 day ago" if d == 1 else f"{d} days ago"


def week_change(df):
    """Latest value and % change vs about one week earlier (5 trading days / 7 days)."""
    if df is None or len(df) < 8:
        return None, None
    df = df.sort_values("date")
    last = float(df["value"].iloc[-1])
    past = df[df["date"] <= df["date"].iloc[-1] - pd.Timedelta(days=7)]
    if past.empty:
        return last, None
    prev = float(past["value"].iloc[-1])
    return last, (last - prev) / prev * 100 if prev else None


# ------------------------------------------------------------------ product strip
def product_strip(p: dict, sig: dict, lanes: list) -> None:
    label, unit = BENCHMARKS[p["benchmark"]]
    last, chg = week_change(sig["series"].get(p["benchmark"]))
    if last is None:
        price_html = '<div class="big">no data</div>'
    else:
        color = "#16A34A" if (chg or 0) >= 0 else "#DC2626"
        arrow = "↑" if (chg or 0) >= 0 else "↓"
        price_html = (f'<div class="big">USD {last:,.2f} <small>{unit}</small></div>'
                      + (f'<div class="chg" style="color:{color}">{arrow} {chg:+.1f}% '
                         f'<span style="color:#64748B;font-weight:400">(vs. last week)</span></div>'
                         if chg is not None else ""))
    lanes_html = "<br>".join(html.escape(l) for l in lanes[:3]) or "No lanes for this filter"
    st.markdown(
        f"""<div class="prod" id="filters-summary">
        <div class="main"><div class="pic">{p['emoji']}</div>
          <div><div class="pname">{html.escape(p['name'])}</div>
          <div class="pcode">HS Code: <b>{html.escape(p['hs'])}</b></div>
          <div class="pdesc">{html.escape(p['desc'])}</div></div></div>
        <div style="flex:1.1"><div class="lab">{label}</div>{price_html}</div>
        <div style="flex:0.9"><div class="lab">Typical Import Duty</div>
          <div class="lanes">Varies by country</div>
          <a href="https://hts.usitc.gov/" target="_blank">View U.S. tariff schedule</a></div>
        <div style="flex:1.2"><div class="lab">Key Trade Lanes</div><div class="lanes">{lanes_html}</div></div>
        <div style="flex:0.8;display:flex;align-items:center;justify-content:center">
          <a href="#alerts" class="watch">☆ Watch Product</a></div>
        </div>""", unsafe_allow_html=True)


# ------------------------------------------------------------------ alert cards
def alert_cards(sig: dict) -> None:
    cards = [_weather_card(sig), _traffic_card(sig, PORTS, "port", "Port Disruption", "⚓", "calls"),
             _traffic_card(sig, CHOKEPOINTS, "choke", "Chokepoint Risk", "⚠️", "transits"),
             _price_card(sig)]
    cols = st.columns(4)
    for c, h in zip(cols, cards):
        c.markdown(h, unsafe_allow_html=True)


def _weather_card(sig):
    w = sig["weather"]
    if w["flag"]:
        return alert_card("disaster", "HIGH", "Natural Disaster Alert", "🌀", ", ".join(w["events"]),
                          f"{w['relevant']} supply-relevant severe alert(s) in Gulf Coast refinery and port "
                          "counties. Plants and terminals may slow or shut.", "live")
    if w["value"]:
        names = ", ".join(sorted(set(w["detail"]["event"].dropna())))[:80]
        return alert_card("disaster", "MONITOR", "Natural Disaster Alert", "🌦", f"{w['value']} minor weather alert(s)",
                          f"{names}. Not expected to disrupt supply.", "live")
    return alert_card("disaster", "NORMAL", "Natural Disaster Alert", "☀", "No active alerts",
                      "No National Weather Service alerts in Gulf Coast refinery and port counties.", "live")


def _traffic_card(sig, places, ctype, kind, emoji, what):
    vals = [(k, v["label"], sig[k]["value"]) for k, v in places.items() if sig.get(k, {}).get("value") is not None]
    if not vals:
        return alert_card(ctype, "NODATA", kind, emoji, "No traffic data", "IMF PortWatch data is not available.")
    k, label, v = min(vals, key=lambda t: t[2])
    lvl = signal_level(sig, k)
    head = f"{'Fewer' if v < 0 else 'More'} tankers at {label}" if abs(v) >= 10 else f"{label} traffic normal"
    body = (f"Tanker {what} {v:+.0f}% (7-day avg vs previous 90 days). "
            + ("Expect longer waits and possible re-routing." if lvl == "HIGH" else
               "Watch for further drops." if lvl == "MONITOR" else "No disruption signal."))
    return alert_card(ctype, lvl, kind, emoji, head, body, ago(sig[k]["date"]), "#shipping")


def _price_card(sig):
    wti, gas, ref = sig["wti"], sig["gas"], sig["refinery"]
    if wti["value"] is None:
        return alert_card("price", "NODATA", "Energy Price Update", "📈", "No price data", "EIA price data is not available.")
    lvl = "HIGH" if (wti["flag"] or gas["flag"] or ref["flag"]) else "MONITOR" if abs(wti["value"]) >= 5 else "NORMAL"
    direction = "rising" if wti["value"] > 0 else "falling"
    head = f"Crude prices {direction}" if abs(wti["value"]) >= 5 else "Energy prices steady"
    body = (f"WTI ${wti['last']:.2f}/bbl, {wti['value']:+.1f}% (5-day vs 60-day). "
            + (f"Henry Hub ${gas['last']:.2f} ({gas['value']:+.1f}%). " if gas["value"] is not None else "")
            + (f"Refinery use {ref['value']:.1f}%." if ref["value"] is not None else ""))
    return alert_card("price", lvl, "Energy Price Update", "📊", head, body, ago(wti["date"]), "#prices")


# ------------------------------------------------------------------ tanker traffic card
TRAFFIC_TABS = {"Hormuz": "hormuz", "Suez": "suez", "Panama": "panama", "Houston": "houston"}


def _seg(label, options, default, key):
    if hasattr(st, "segmented_control"):
        return st.segmented_control(label, options, default=default, key=key,
                                    label_visibility="collapsed") or default
    return st.radio(label, options, index=options.index(default), horizontal=True, key=key,
                    label_visibility="collapsed")


def traffic_panel(sig: dict) -> None:
    tabs = list(TRAFFIC_TABS)
    flagged = [t for t in tabs if sig.get(TRAFFIC_TABS[t], {}).get("flag")]
    tab = _seg("Location", tabs, flagged[0] if flagged else tabs[0], "traffic_tab")
    k = TRAFFIC_TABS[tab]
    df = sig["series"].get(k)
    if df is None or df.empty:
        st.caption("No traffic data for this location right now.")
        return
    last = float(df["value"].iloc[-1])
    v = sig[k]["value"] or 0
    color, arrow = ("#DC2626", "↓") if v < 0 else ("#16A34A", "↑")
    st.markdown(f'<div class="bignum" style="margin:4px 0 2px">{last:,.1f} <small>tankers / day</small> '
                f'<span style="font-size:15px;color:{color};font-weight:700;margin-left:6px">{arrow} {v:+.0f}%</span> '
                f'<span style="font-size:12.5px;color:#64748B">(vs. 90-day avg)</span></div>',
                unsafe_allow_html=True)
    rng = {"1M": 31, "3M": 92, "6M": 183, "1Y": 366}
    pick = st.session_state.get("traffic_range") or "1M"
    d = df[df["date"] >= df["date"].max() - pd.Timedelta(days=rng[pick])]
    fig = go.Figure(go.Scatter(x=d["date"], y=d["value"], mode="lines", line=dict(color=LINE, width=2),
                               hovertemplate="%{x|%b %d}<br><b>%{y:.1f}</b> tankers/day<extra></extra>"))
    fig.update_layout(height=200, margin=dict(l=0, r=4, t=6, b=0), showlegend=False, hovermode="x unified",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(showgrid=False, tickformat="%b %d", nticks=6),
                      yaxis=dict(gridcolor="rgba(100,116,139,0.15)", zeroline=False, rangemode="tozero"))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    _, mid, _ = st.columns([0.6, 3, 0.6])
    with mid:
        _seg("Range", list(rng), "1M", "traffic_range")
    st.caption(f"{PLACE_LABELS[k]} · IMF PortWatch, data through {sig[k]['date']:%b %d}. "
               "Live stand-in for freight pressure (tanker rates are paid data).")


# ------------------------------------------------------------------ industry alert
def industry_alert(industry: str, score: float, sig: dict, level: str) -> None:
    s = STATUS[level]
    flagged = [SIGNAL_LABELS[k] for k in SIGNAL_LABELS if sig.get(k, {}).get("flag")]
    reason = ", ".join(flagged) if flagged else "no live warning signals"
    fragile = "fragile" if score >= 0.35 else "sturdier"
    word = {"HIGH": "HIGH", "ELEVATED": "ELEVATED", "NORMAL": "NORMAL"}[level]
    st.markdown(
        f"""<div style="border:1px solid {s['bd']};background:{s['bg']};border-left:6px solid {s['fg']};
        border-radius:12px;padding:14px 18px">
        <div style="font-size:13px;color:#64748B">Alert level for {html.escape(industry)}</div>
        <div style="font-size:28px;font-weight:800;color:{s['fg']}">{word}</div>
        <div style="font-size:13.5px;color:#334155"><b>What changed:</b> {reason}.<br>
        <b>Why it matters:</b> structural score {score:.2f} ({fragile} industry). HIGH needs 2+ warnings
        and a score of 0.35 or more.<br>Checked {html.escape(sig['checked_at'])}.</div></div>""",
        unsafe_allow_html=True)
    st.markdown("**Actions to consider**")
    for a in ACTIONS[level]:
        st.markdown(f"- {a}")


# ------------------------------------------------------------------ charts
def trend_chart(df, title, unit, fmt, alert=None, alert_text="", height=230):
    if df is None or df.empty:
        st.caption(f"{title}: no data right now")
        return
    last = df.iloc[-1]
    fig = go.Figure(go.Scatter(
        x=df["date"], y=df["value"], mode="lines", line=dict(color=LINE, width=2),
        hovertemplate=f"%{{x|%b %d, %Y}}<br><b>%{{y:{fmt}}}</b> {unit}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[last["date"]], y=[last["value"]], mode="markers",
                             marker=dict(color=LINE, size=8), hoverinfo="skip"))
    if alert is not None:
        fig.add_hline(y=alert, line_dash="dot", line_color=GUIDE, line_width=1,
                      annotation_text=alert_text, annotation_position="bottom left",
                      annotation_font_color=GUIDE)
    fig.update_layout(
        title=dict(text=f"{title}  <span style='font-size:12px;color:{GUIDE}'>latest "
                        f"{last['date']:%b %d}: {last['value']:{fmt}} {unit}</span>", font=dict(size=14)),
        height=height, margin=dict(l=10, r=10, t=40, b=10), showlegend=False,
        hovermode="x unified", xaxis=dict(showgrid=False), paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="rgba(100,116,139,0.15)", zeroline=False))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def crude_chart(series: dict, days: int) -> None:
    """WTI and Brent on one axis (same unit), with direct end labels."""
    fig = go.Figure()
    for key, name, color in [("wti", "WTI", LINE), ("brent", "Brent", LINE2)]:
        df = series.get(key)
        if df is None or df.empty:
            continue
        df = df[df["date"] >= df["date"].max() - pd.Timedelta(days=days)]
        fig.add_trace(go.Scatter(x=df["date"], y=df["value"], mode="lines", name=name,
                                 line=dict(color=color, width=2),
                                 hovertemplate=f"{name} <b>$%{{y:.2f}}</b>/bbl<extra></extra>"))
        fig.add_annotation(x=df["date"].iloc[-1], y=df["value"].iloc[-1], text=f"{name} ${df['value'].iloc[-1]:.2f}",
                           showarrow=False, xanchor="left", xshift=6, font=dict(color="#334155", size=12))
    fig.update_layout(height=320, margin=dict(l=10, r=90, t=10, b=10), hovermode="x unified",
                      yaxis_title="$ per barrel", legend=dict(orientation="h", y=1.08, x=0),
                      paper_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(showgrid=False), yaxis=dict(gridcolor="rgba(100,116,139,0.15)"))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
