"""
"Right now" panel: live signals + alert level + recommended actions.

Usage in app.py (after you know the selected industry and its risk score):
    from live_panel import render_live_panel
    render_live_panel(industry_name, risk_score)
"""

import plotly.graph_objects as go
import streamlit as st
from live_data import live_signals, alert_level

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
COLORS = {"HIGH": "#EF4444", "ELEVATED": "#F59E0B", "NORMAL": "#22C55E"}


def _fmt(v, unit="%"):
    return "no data" if v is None else f"{v:+.1f}{unit}"


def _panel(industry_name: str, structural_score: float):
    with st.spinner("Checking live sources..."):
        sig = live_signals()
    level, flags = alert_level(structural_score, sig)

    st.subheader("Right now: live early warning")
    st.markdown(
        f"""<div style="border-left:6px solid {COLORS[level]};padding:12px 16px;
        border-radius:10px;background:rgba(17,27,46,0.7);margin-bottom:12px">
        <div style="font-size:13px;color:#94A3B8">Alert level for {industry_name}</div>
        <div style="font-size:30px;font-weight:800;color:{COLORS[level]}">{level}</div>
        <div style="font-size:13px;color:#CBD5E1">{flags} live warning signal(s) +
        structural risk score {structural_score:.2f}. Checked {sig['checked_at']}.</div></div>""",
        unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gulf Coast weather alerts", sig["weather"]["value"],
              "warning active" if sig["weather"]["flag"] else "none severe", delta_color="off")
    c2.metric("WTI crude, 5-day vs 60-day", _fmt(sig["wti"]["value"]),
              "flag" if sig["wti"]["flag"] else "normal", delta_color="off")
    c3.metric("Henry Hub gas, 5-day vs 60-day", _fmt(sig["gas"]["value"]),
              "flag" if sig["gas"]["flag"] else "normal", delta_color="off")
    c4.metric("Gulf Coast refinery use", _fmt(sig["refinery"]["value"], "%").lstrip("+"),
              "flag" if sig["refinery"]["flag"] else "normal", delta_color="off")

    c5, c6, c7 = st.columns(3)
    c5.metric("Port Arthur tanker calls, 7d vs 90d", _fmt(sig["port_arthur"]["value"]),
              "flag" if sig["port_arthur"]["flag"] else "normal", delta_color="off")
    c6.metric("Houston tanker calls, 7d vs 90d", _fmt(sig["houston"]["value"]),
              "flag" if sig["houston"]["flag"] else "normal", delta_color="off")
    c7.metric("Panama Canal tanker transits, 7d vs 90d", _fmt(sig["panama"]["value"]),
              "flag" if sig["panama"]["flag"] else "normal", delta_color="off")

    _trends(sig["series"])

    st.markdown("**Recommended actions**")
    for a in ACTIONS[level]:
        st.markdown(f"- {a}")

    if not sig["weather"]["detail"].empty:
        with st.expander("Active weather alerts (National Weather Service)"):
            st.dataframe(sig["weather"]["detail"], width="stretch", hide_index=True)

    st.caption("Sources: National Weather Service (real time), EIA (daily prices, weekly "
               "refinery use), IMF PortWatch (daily port calls, 2 to 4 days behind). Thresholds are simple "
               "rules tested on past events; they are not forecasts.")


LINE = "#38bdf8"      # one hue for every trend chart (single series each)
GUIDE = "#94a3b8"     # recessive grey for alert lines


def _trend_chart(df, title, unit, fmt, alert=None, alert_text=""):
    if df.empty:
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
        height=230, margin=dict(l=10, r=10, t=40, b=10), showlegend=False,
        hovermode="x unified", xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(148,163,184,0.15)", zeroline=False))
    st.plotly_chart(fig, width="stretch")


def _trends(series):
    st.markdown("**Last 12 months, up to the latest available day**")
    a, b = st.columns(2)
    with a:
        _trend_chart(series["wti"], "WTI crude", "$/bbl", ".2f")
    with b:
        _trend_chart(series["gas"], "Henry Hub natural gas", "$/MMBtu", ".2f")
    c, d = st.columns(2)
    with c:
        _trend_chart(series["refinery"], "Gulf Coast refinery use", "%", ".1f",
                     alert=85, alert_text="alert below 85%")
    with d:
        _trend_chart(series["port_arthur"], "Port Arthur tanker calls, 7-day average",
                     "calls/day", ".1f")
    st.caption("Structural scores use annual data (latest year 2024, the newest the Census "
               "has published). The live signals and these charts run up to the latest day "
               "each source has released.")


def render_live_panel(industry_name: str, structural_score: float):
    """Draw the panel and re-run it every 10 minutes while the page is open."""
    if hasattr(st, "fragment"):                       # Streamlit 1.37+
        st.fragment(run_every="10m")(_panel)(industry_name, structural_score)
    else:
        _panel(industry_name, structural_score)
