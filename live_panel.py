"""
Live parts of the dashboard: alert cards, industry alert box, trend charts.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from live_data import CHOKEPOINTS, PORTS
from routes import signal_level
from ui_style import STATUS, alert_card, pill

ACTIONS = {
    "HIGH": [
        "Confirm feedstock and raw-material deliveries for the next 2 weeks",
        "Contact backup suppliers outside the Gulf Coast",
        "Delay non-urgent shipments through affected ports",
        "Warn customers about possible delays and price increases",
    ],
    "ELEVATED": [
        "Check inventory days-on-hand for critical inputs",
        "Watch the flagged signals daily",
        "Get quotes from a second supplier",
    ],
    "NORMAL": ["No action needed. Keep normal ordering."],
}
SIGNAL_LABELS = {"weather": "severe Gulf Coast weather", "wti": "WTI crude price move",
                 "gas": "natural gas price move", "refinery": "low Gulf Coast refinery use",
                 "port_arthur": "Port Arthur tanker drop", "houston": "Houston tanker drop",
                 "panama": "Panama Canal tanker drop"}
LINE = "#2A78D6"       # single-series trend line
LINE2 = "#EB6834"      # second series (Brent) where two share one axis
GUIDE = "#64748B"      # recessive grey for alert lines


def _when(ts):
    return f"data through {ts:%b %d}" if ts is not None else ""


# ------------------------------------------------------------------ alert cards
def alert_cards(sig: dict) -> None:
    c1, c2, c3, c4 = st.columns(4)
    w = sig["weather"]
    with c1:
        if w["flag"]:
            alert_card("HIGH", "Weather alert", "🌀", ", ".join(w["events"]),
                       f"{w['relevant']} supply-relevant severe alert(s) active in Gulf Coast "
                       "refinery and port counties.", "live")
        elif w["value"]:
            names = ", ".join(sorted(set(w["detail"]["event"].dropna())))[:90]
            alert_card("MONITOR", "Weather alert", "🌦", f"{w['value']} active alert(s), none supply-critical",
                       names, "live")
        else:
            alert_card("NORMAL", "Weather alert", "☀", "No active alerts",
                       "No National Weather Service alerts in Gulf Coast refinery and port counties.", "live")
    with c2:
        _traffic_card(sig, PORTS, "Port disruption", "⚓", "tanker calls")
    with c3:
        _traffic_card(sig, CHOKEPOINTS, "Chokepoint traffic", "⛴", "tanker transits")
    with c4:
        wti, gas, ref = sig["wti"], sig["gas"], sig["refinery"]
        if wti["value"] is None:
            alert_card("NODATA", "Energy prices", "$", "No price data", "EIA price data is not available.")
        else:
            lvl = "HIGH" if (wti["flag"] or gas["flag"] or ref["flag"]) else \
                  "MONITOR" if abs(wti["value"]) >= 5 else "NORMAL"
            body = (f"Henry Hub gas ${gas['last']:.2f} ({gas['value']:+.1f}%). " if gas["value"] is not None else "") + \
                   (f"Gulf Coast refinery use {ref['value']:.1f}%." if ref["value"] is not None else "")
            alert_card(lvl, "Energy prices", "$",
                       f"WTI ${wti['last']:.2f}/bbl, {wti['value']:+.1f}% (5-day vs 60-day)",
                       body, _when(wti["date"]))


def _traffic_card(sig, places, kind, icon, what):
    vals = [(k, v["label"], sig[k]["value"]) for k, v in places.items() if sig[k]["value"] is not None]
    if not vals:
        alert_card("NODATA", kind, icon, "No traffic data", "IMF PortWatch data is not available.")
        return
    k, label, v = min(vals, key=lambda t: t[2])
    others = ", ".join(f"{lab} {val:+.0f}%" for kk, lab, val in vals if kk != k)
    alert_card(signal_level(sig, k), kind, icon, f"{label} {what} {v:+.0f}%",
               f"7-day average vs the previous 90 days. {('Others: ' + others + '.') if others else ''}",
               _when(sig[k]["date"]))


# ------------------------------------------------------------------ industry alert
def industry_alert(industry: str, score: float, sig: dict, level: str) -> None:
    s = STATUS[level]
    flagged = [SIGNAL_LABELS[k] for k in SIGNAL_LABELS if sig.get(k, {}).get("flag")]
    reason = ", ".join(flagged) if flagged else "no live warning signals"
    fragile = "fragile" if score >= 0.35 else "sturdier"
    st.markdown(
        f"""<div style="border:1px solid {s['bd']};background:{s['bg']};border-left:6px solid {s['fg']};
        border-radius:12px;padding:14px 18px">
        <div style="font-size:13px;color:#64748B">Alert level for {industry}</div>
        <div style="font-size:30px;font-weight:800;color:{s['fg']}">{level}</div>
        <div style="font-size:13.5px;color:#334155">Live warnings: {reason}. Structural score
        {score:.2f} ({fragile} industry; HIGH needs 2+ warnings and a score of 0.35 or more).
        Checked {sig['checked_at']}.</div></div>""", unsafe_allow_html=True)
    st.markdown("**Recommended actions**")
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
        hovermode="x unified", xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(100,116,139,0.15)", zeroline=False))
    st.plotly_chart(fig, width="stretch")


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
    fig.update_layout(height=340, margin=dict(l=10, r=90, t=10, b=10), hovermode="x unified",
                      yaxis_title="$ per barrel", legend=dict(orientation="h", y=1.08, x=0),
                      xaxis=dict(showgrid=False), yaxis=dict(gridcolor="rgba(100,116,139,0.15)"))
    st.plotly_chart(fig, width="stretch")
