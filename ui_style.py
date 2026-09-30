"""
Visual style for the Supply Chain Risk Dashboard (light "control room" look).

    from ui_style import apply_style, brand_bar, alert_card, pill, section
"""

import html

import streamlit as st

# Status colors are reserved for state (never reused for data series)
STATUS = {
    "HIGH":     {"fg": "#B91C1C", "bg": "#FEF2F2", "bd": "#FECACA", "icon": "▲", "label": "High"},
    "ELEVATED": {"fg": "#C2410C", "bg": "#FFF7ED", "bd": "#FED7AA", "icon": "●", "label": "Elevated"},
    "MONITOR":  {"fg": "#A16207", "bg": "#FEFCE8", "bd": "#FDE68A", "icon": "◆", "label": "Monitor"},
    "NORMAL":   {"fg": "#15803D", "bg": "#F0FDF4", "bd": "#BBF7D0", "icon": "✓", "label": "Normal"},
    "NODATA":   {"fg": "#475569", "bg": "#F8FAFC", "bd": "#E2E8F0", "icon": "–", "label": "No data"},
}

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, select, textarea {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
}
[data-testid="stAppViewContainer"] { background: #F4F6FA; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.2rem; max-width: 1440px; }

/* Sidebar: dark navy rail like a product app */
[data-testid="stSidebar"] { background: #0F1B33; }
[data-testid="stSidebar"] * { color: #E2E8F0; }
[data-testid="stSidebar"] [data-baseweb="select"] * { color: #0F172A; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #FFFFFF; }

/* Tabs as a top navigation bar */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 4px;
}
.stTabs [data-baseweb="tab"] { height: 40px; padding: 0 16px; border-radius: 8px; font-weight: 600; }
.stTabs [aria-selected="true"] { background: #EFF4FF; color: #1D4ED8 !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

/* Cards */
[data-testid="stVerticalBlockBorderWrapper"] { background: #FFFFFF; border-radius: 14px; }
[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 12px 14px;
}
[data-testid="stMetricLabel"] { color: #64748B !important; font-weight: 600; }
[data-testid="stMetricValue"] { color: #0F172A !important; font-weight: 700; font-size: 26px !important; }
h2, h3 { font-weight: 700 !important; letter-spacing: -0.2px; color: #0F172A; }

/* Brand bar */
.brand { display:flex; align-items:center; gap:14px; flex-wrap:wrap;
         background:#FFFFFF; border:1px solid #E2E8F0; border-radius:14px; padding:14px 18px; }
.brand .logo { width:40px; height:40px; border-radius:10px; background:#1D4ED8; color:#fff;
               display:flex; align-items:center; justify-content:center; font-weight:800; font-size:18px; }
.brand .name { font-weight:800; font-size:20px; color:#0F172A; line-height:1.1; }
.brand .sub  { font-size:13px; color:#64748B; }
.brand .right { margin-left:auto; display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
.brand .meta { font-size:12.5px; color:#64748B; }

/* Pills */
.pill { display:inline-flex; align-items:center; gap:6px; font-size:12.5px; font-weight:700;
        padding:4px 10px; border-radius:999px; border:1px solid; white-space:nowrap; }

/* Alert cards */
.acard { border:1px solid; border-radius:14px; padding:14px 16px; height:100%;
         display:flex; flex-direction:column; gap:6px; min-height:170px; }
.acard .top { display:flex; align-items:center; gap:10px; }
.acard .ico { width:34px; height:34px; border-radius:9px; display:flex; align-items:center;
              justify-content:center; font-size:17px; color:#fff; flex-shrink:0; }
.acard .kind { font-size:13px; font-weight:700; }
.acard .when { margin-left:auto; font-size:11.5px; color:#64748B; white-space:nowrap; }
.acard .head { font-size:16px; font-weight:700; color:#0F172A; line-height:1.3; }
.acard .body { font-size:13px; color:#334155; line-height:1.45; }
.section-sub { font-size:13px; color:#64748B; margin-top:-8px; margin-bottom:6px; }
</style>
"""


def apply_style() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def pill(level: str, text: str = None) -> str:
    s = STATUS.get(level, STATUS["NODATA"])
    return (f'<span class="pill" style="color:{s["fg"]};background:{s["bg"]};border-color:{s["bd"]}">'
            f'{s["icon"]} {html.escape(text or s["label"])}</span>')


def brand_bar(title: str, subtitle: str, right_html: str = "") -> None:
    st.markdown(
        f"""<div class="brand"><div class="logo">SC</div>
        <div><div class="name">{html.escape(title)}</div><div class="sub">{html.escape(subtitle)}</div></div>
        <div class="right">{right_html}</div></div>""", unsafe_allow_html=True)


def alert_card(level: str, kind: str, icon: str, head: str, body: str, when: str = "") -> None:
    s = STATUS.get(level, STATUS["NODATA"])
    st.markdown(
        f"""<div class="acard" style="background:{s['bg']};border-color:{s['bd']}">
        <div class="top"><div class="ico" style="background:{s['fg']}">{icon}</div>
        <div class="kind" style="color:{s['fg']}">{html.escape(kind)}</div>
        <div class="when">{html.escape(when)}</div></div>
        <div class="head">{html.escape(head)}</div>
        <div class="body">{html.escape(body)}</div>
        <div>{pill(level)}</div></div>""", unsafe_allow_html=True)


def section(title: str, sub: str = "") -> None:
    st.subheader(title)
    if sub:
        st.markdown(f'<div class="section-sub">{html.escape(sub)}</div>', unsafe_allow_html=True)
