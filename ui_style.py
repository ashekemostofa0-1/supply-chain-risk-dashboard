"""
Visual styling for the Supply Chain Risk Dashboard.

Usage in app.py (right after st.set_page_config):
    from ui_style import apply_style, hero
    apply_style()
    hero("Supply Chain Risk Dashboard", "subtitle text", ["badge 1", "badge 2"])
"""

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stMarkdown, .stText, .stMetric, button, input, select {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
}

/* Page background: soft glow behind the content */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(1200px 600px at 85% -10%, rgba(59,130,246,0.14), transparent 60%),
        radial-gradient(900px 500px at -10% 10%, rgba(245,158,11,0.08), transparent 60%),
        #0B1220;
}
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.2rem; max-width: 1400px; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F1A30 0%, #0B1220 100%);
    border-right: 1px solid rgba(148,163,184,0.15);
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #FBBF24;
}

/* Section headings */
h2, h3 {
    font-weight: 700 !important;
    letter-spacing: -0.2px;
    padding-bottom: .35rem;
    border-bottom: 1px solid rgba(148,163,184,0.15);
}

/* KPI cards (st.metric) */
[data-testid="stMetric"] {
    background: linear-gradient(160deg, rgba(30,41,66,0.85), rgba(17,27,46,0.85));
    border: 1px solid rgba(148,163,184,0.18);
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
}
[data-testid="stMetricLabel"] { color: #94A3B8 !important; font-weight: 600; }
[data-testid="stMetricValue"] { color: #F8FAFC !important; font-weight: 800; }

/* Charts sit on cards too */
[data-testid="stPlotlyChart"] {
    background: rgba(17,27,46,0.6);
    border: 1px solid rgba(148,163,184,0.15);
    border-radius: 16px;
    padding: 8px;
}

/* Hero header */
.hero-kicker {
    display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: 1.4px;
    text-transform: uppercase; color: #FBBF24;
    background: rgba(245,158,11,0.12); border: 1px solid rgba(245,158,11,0.35);
    padding: 4px 10px; border-radius: 999px; margin-bottom: 14px;
}
.hero-title {
    font-size: 46px; line-height: 1.05; font-weight: 800; letter-spacing: -1px; margin: 0 0 12px 0;
    background: linear-gradient(90deg, #F8FAFC 0%, #93C5FD 55%, #FBBF24 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero-sub { font-size: 16px; color: #CBD5E1; line-height: 1.55; max-width: 620px; }
.hero-badges { margin-top: 16px; display: flex; flex-wrap: wrap; gap: 8px; }
.hero-badge {
    font-size: 12.5px; font-weight: 600; color: #E2E8F0;
    background: rgba(30,41,66,0.9); border: 1px solid rgba(148,163,184,0.25);
    padding: 5px 11px; border-radius: 999px;
}
@media (max-width: 800px) { .hero-title { font-size: 34px; } }
</style>
"""


def apply_style() -> None:
    """Inject the custom CSS. Call once, near the top of app.py."""
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, badges=None, kicker: str = "Engineering Management Project") -> None:
    """Large header block with a gradient title and small info badges."""
    badges = badges or []
    badge_html = "".join(f'<span class="hero-badge">{b}</span>' for b in badges)
    st.markdown(
        f"""
        <div style="padding-top:18px">
          <div class="hero-kicker">{kicker}</div>
          <div class="hero-title">{title}</div>
          <div class="hero-sub">{subtitle}</div>
          <div class="hero-badges">{badge_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
