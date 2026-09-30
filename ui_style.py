"""
Visual style for the Supply Chain Risk Dashboard: a light trade-intelligence layout
(left icon rail, top navigation bar, filter bar, white cards).

    from ui_style import apply_style, left_rail, top_bar, card_title, pill, alert_card, STATUS
"""

import html

import streamlit as st

# Status colors are reserved for state; each ships with an icon + label.
STATUS = {
    "HIGH":     {"fg": "#DC2626", "bg": "#FEF2F2", "tint": "#FDECEC", "bd": "#FECACA", "icon": "▲", "label": "High"},
    "ELEVATED": {"fg": "#EA580C", "bg": "#FFF7ED", "tint": "#FFF1E6", "bd": "#FED7AA", "icon": "●", "label": "Medium"},
    "MONITOR":  {"fg": "#CA8A04", "bg": "#FEFCE8", "tint": "#FFF8DB", "bd": "#FDE68A", "icon": "◆", "label": "Monitor"},
    "NORMAL":   {"fg": "#16A34A", "bg": "#F0FDF4", "tint": "#EAF8EF", "bd": "#BBF7D0", "icon": "✓", "label": "Low"},
    "NODATA":   {"fg": "#64748B", "bg": "#F8FAFC", "tint": "#F1F5F9", "bd": "#E2E8F0", "icon": "–", "label": "No data"},
}
BLUE = "#1D5BD8"
# Card types keep one color each (like the reference design); status is shown as a tag.
CARD_TYPES = {
    "disaster": {"fg": "#DC2626", "bg": "#FDF2F2", "ico": "#FDE2E2", "bd": "#F9D9D9"},
    "port":     {"fg": "#EA580C", "bg": "#FFF7F0", "ico": "#FFE4CC", "bd": "#FCE3CF"},
    "choke":    {"fg": "#D97706", "bg": "#FFFBEF", "ico": "#FFEDB8", "bd": "#F8EACB"},
    "price":    {"fg": "#1D5BD8", "bg": "#F2F6FF", "ico": "#DCE7FD", "bd": "#DDE6FA"},
}
INK, INK2, MUTED, LINE = "#0F172A", "#334155", "#64748B", "#E3E8F0"

_SVG = {  # simple outline icons (24px, stroke = currentColor)
    "home": '<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    "box": '<path d="M21 8l-9-5-9 5 9 5 9-5z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/>',
    "map": '<path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2z"/><path d="M9 4v14M15 6v14"/>',
    "bell": '<path d="M6 16V11a6 6 0 1 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    "calc": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 12h2M12 12h2M16 12h0M8 16h2M12 16h2M16 16h0"/>',
    "doc": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
}


def icon(name, size=22, color="currentColor"):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{_SVG[name]}</svg>')


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, select, textarea, label {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important; }
[data-testid="stAppViewContainer"] { background: #F3F6FB; }
header[data-testid="stHeader"] { display: none; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }
.block-container { padding: 14px 22px 40px 104px !important; max-width: 1560px; }
[data-testid="stVerticalBlock"] { gap: 0.7rem; }
html { scroll-behavior: smooth; }

/* Left icon rail */
.rail { position: fixed; top: 0; left: 0; bottom: 0; width: 82px; background: #0E1E3A; z-index: 1000;
        display: flex; flex-direction: column; align-items: center; padding-top: 74px; gap: 6px; }
.rail a { width: 68px; padding: 10px 0 8px; border-radius: 10px; color: #C7D2E5 !important;
          text-decoration: none !important; display: flex; flex-direction: column; align-items: center;
          gap: 5px; font-size: 12px; font-weight: 500; position: relative; }
.rail a:hover { background: #17305A; color: #fff !important; }
.rail a.on { background: #1D5BD8; color: #fff !important; }
.rail .badge { position: absolute; top: 5px; right: 15px; background: #DC2626; color: #fff;
               font-size: 10px; font-weight: 700; border-radius: 999px; padding: 1px 5px; }

/* Top bar */
.topbar { display: flex; align-items: center; gap: 28px; background: #fff; border: 1px solid #E3E8F0;
          border-radius: 12px; padding: 10px 18px; flex-wrap: wrap; }
.topbar .brand { display: flex; align-items: center; gap: 10px; }
.topbar .bname { font-size: 19px; font-weight: 800; color: #0F172A; line-height: 1.1; }
.topbar .bsub { font-size: 12.5px; color: #475569; }
.topbar nav { display: flex; gap: 6px; flex-wrap: wrap; margin-left: 40px; }
.topbar nav a { color: #1E293B !important; text-decoration: none !important; font-size: 14px;
                font-weight: 500; padding: 8px 14px; border-bottom: 2px solid transparent; }
.topbar nav a.on { color: #1D5BD8 !important; border-bottom-color: #1D5BD8; font-weight: 600; }
.topbar .right { margin-left: auto; display: flex; align-items: center; gap: 16px; }
.topbar .bell { position: relative; color: #334155; }
.topbar .bell .badge { position: absolute; top: -6px; right: -7px; background: #DC2626; color: #fff;
                       font-size: 10px; font-weight: 700; border-radius: 999px; padding: 1px 5px; }
.topbar .avatar { width: 34px; height: 34px; border-radius: 999px; background: #E2E8F0; color: #334155;
                  display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; }
.topbar .meta { font-size: 11.5px; color: #64748B; text-align: right; line-height: 1.4; }

/* Widgets: compact, filter-bar look */
[data-testid="stWidgetLabel"] p { font-size: 13px !important; font-weight: 600 !important; color: #0F172A !important; }
/* Clear, bordered inputs and dropdowns (like the reference filter bar) */
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="base-input"] {
  background: #FFFFFF !important; border: 1px solid #C9D3E0 !important; border-radius: 8px !important;
  min-height: 42px; box-shadow: none !important; }
[data-baseweb="select"] > div:hover, [data-baseweb="input"]:hover { border-color: #94A3B8 !important; }
[data-baseweb="select"] > div:focus-within, [data-baseweb="input"]:focus-within {
  border-color: #1D5BD8 !important; box-shadow: 0 0 0 3px rgba(29,91,216,0.15) !important; }
[data-baseweb="input"] > div, [data-baseweb="base-input"] > div { background: transparent !important; border: none !important; }
[data-baseweb="select"] div, [data-baseweb="input"] input { font-size: 14px !important; color: #0F172A !important; }
[data-baseweb="input"] input::placeholder { color: #64748B !important; opacity: 1; }
[data-baseweb="select"] svg { color: #334155 !important; }
/* magnifier icon inside every text search box */
[data-testid="stTextInput"] input {
  padding-left: 36px !important;
  background: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%2364748B' stroke-width='2' stroke-linecap='round'><circle cx='11' cy='11' r='7'/><path d='M20 20l-3.5-3.5'/></svg>") no-repeat 11px center !important; }
/* dropdown list: readable rows, blue highlight */
[data-baseweb="popover"] li { font-size: 14px !important; padding-top: 9px !important; padding-bottom: 9px !important; }
[data-baseweb="popover"] li[aria-selected="true"] { background: #EAF1FF !important; color: #1D5BD8 !important; }
[data-testid="stForm"] { background: #fff; border: 1px solid #E3E8F0 !important; border-radius: 12px; padding: 14px 16px 8px; }
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"], .stButton button[kind="primary"] {
  background: #1D5BD8 !important; border-color: #1D5BD8 !important; border-radius: 8px !important;
  height: 42px; font-weight: 600 !important; }
[data-testid="stFormSubmitButton"] button[kind="secondaryFormSubmit"] {
  border: none !important; background: transparent !important; color: #1D5BD8 !important; font-weight: 600 !important; height: 42px; }

/* White cards */
[data-testid="stVerticalBlockBorderWrapper"] { background: #fff; border-radius: 12px !important;
  border-color: #E3E8F0 !important; }
.ctitle { font-size: 17px; font-weight: 700; color: #0F172A; margin: 2px 0 4px; }
.csub { font-size: 12.5px; color: #64748B; margin: -2px 0 6px; }
.sect { font-size: 22px; font-weight: 800; color: #0F172A; margin: 18px 0 2px; scroll-margin-top: 12px; }
.anchor { position: relative; top: -10px; }

/* Product summary strip */
.prod { display: flex; background: #fff; border: 1px solid #E3E8F0; border-radius: 12px; overflow: hidden; flex-wrap: wrap; }
.prod > div { padding: 14px 20px; border-right: 1px solid #E3E8F0; min-width: 0; }
.prod > div:last-child { border-right: none; }
.prod .main { display: flex; gap: 16px; align-items: center; flex: 2.2; }
.prod .pic { width: 74px; height: 74px; border-radius: 10px; background: #0F172A; display: flex;
             align-items: center; justify-content: center; font-size: 34px; flex-shrink: 0; }
.prod .pname { font-size: 22px; font-weight: 700; color: #0F172A; }
.prod .pcode { font-size: 15px; color: #334155; }
.prod .pdesc { font-size: 12.5px; color: #64748B; }
.prod .lab { font-size: 12px; color: #334155; margin-bottom: 4px; }
.prod .big { font-size: 24px; font-weight: 800; color: #0F172A; }
.prod .big small { font-size: 13px; font-weight: 500; color: #475569; }
.prod .chg { font-size: 13px; font-weight: 600; }
.prod .lanes { font-size: 13px; color: #1E293B; line-height: 1.55; }
.prod a { color: #1D5BD8 !important; font-size: 12.5px; text-decoration: none; }
.watch { display: inline-flex; gap: 6px; align-items: center; border: 1.5px solid #1D5BD8; color: #1D5BD8;
         border-radius: 8px; padding: 8px 14px; font-weight: 600; font-size: 13.5px; white-space: nowrap; }

/* Alert cards */
.acard { border-radius: 12px; padding: 16px 18px 12px; height: 176px; display: flex; gap: 14px;
         border: 1px solid transparent; margin-bottom: 6px; box-sizing: border-box; overflow: hidden; }
.acard .ico { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center;
              justify-content: center; font-size: 22px; flex-shrink: 0; }
.acard .txt { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.acard .row1 { display: flex; align-items: baseline; gap: 8px; }
.acard .kind { font-size: 14.5px; font-weight: 700; }
.acard .when { margin-left: auto; font-size: 11.5px; color: #64748B; white-space: nowrap; }
.acard .head { font-size: 16px; font-weight: 700; color: #0F172A; line-height: 1.3; }
.acard .body { font-size: 13px; color: #334155; line-height: 1.45; display: -webkit-box;
               -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.acard .head { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.acard .more { margin-top: auto; display: flex; align-items: center; justify-content: space-between; }
.acard .tag { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 6px; }
.acard .more a { color: #1D5BD8 !important; font-size: 13px; font-weight: 600; text-decoration: none; }

/* Segmented buttons (tabs on the traffic and price cards) */
[data-testid="stButtonGroup"] { gap: 0 !important; }
button[data-testid="stBaseButton-segmented_control"], button[data-testid="stBaseButton-segmented_controlActive"] {
  border-radius: 6px !important; min-height: 34px; padding: 4px 16px !important; font-size: 13px !important; }
button[data-testid="stBaseButton-segmented_controlActive"] {
  background: #1D5BD8 !important; color: #fff !important; border-color: #1D5BD8 !important; }
button[data-testid="stBaseButton-segmented_controlActive"] p { color: #fff !important; }

/* Pills and tables */
.pill { display: inline-block; font-size: 12.5px; font-weight: 600; padding: 3px 10px; border-radius: 6px; white-space: nowrap; }
table.rt { width: 100%; border-collapse: collapse; font-size: 13px; }
table.rt th { background: #F8FAFC; color: #334155; font-weight: 600; text-align: left; padding: 9px 10px;
              border-bottom: 1px solid #E3E8F0; }
table.rt td { padding: 10px; border-bottom: 1px solid #EEF2F7; color: #1E293B; vertical-align: middle; }
table.rt td.num, table.rt th.num { text-align: right; font-variant-numeric: tabular-nums; }
.tbl-wrap { overflow-x: auto; border: 1px solid #E3E8F0; border-radius: 10px; }
.bignum { font-size: 26px; font-weight: 800; color: #0F172A; }
.bignum small { font-size: 14px; font-weight: 500; color: #475569; }
.takeaways { background: #F2F6FE; border: 1px solid #DCE6FB; border-radius: 12px; padding: 14px 16px; }
.takeaways h4 { margin: 0 0 8px; font-size: 15.5px; font-weight: 700; color: #0F172A; }
.takeaways li { font-size: 13px; color: #1E293B; margin-bottom: 8px; line-height: 1.45; }
@media (max-width: 900px) { .block-container { padding-left: 14px !important; } .rail { display: none; }
  .topbar nav { margin-left: 0; } }
</style>
"""


def apply_style() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def left_rail(n_alerts: int) -> None:
    items = [("#overview", "home", "Home", True), ("#filters", "box", "Products", False),
             ("#shipping", "map", "Map", False), ("#alerts", "bell", "Alerts", False),
             ("#simulator", "calc", "Simulator", False), ("#reports", "doc", "Reports", False)]
    links = "".join(
        f'<a href="{h}" class="{"on" if on else ""}">{icon(i)}<span>{t}</span>'
        f'{f"<span class=badge>{n_alerts}</span>" if i == "bell" and n_alerts else ""}</a>'
        for h, i, t, on in items)
    st.markdown(f'<div class="rail">{links}</div>', unsafe_allow_html=True)


def top_bar(n_alerts: int, checked_at: str, initials: str = "AM") -> None:
    nav = [("#overview", "Overview", True), ("#prices", "Trade &amp; Prices", False),
           ("#shipping", "Shipping &amp; Routes", False), ("#alerts", "Risk &amp; Alerts", False),
           ("#simulator", "Procurement Simulator", False)]
    links = "".join(f'<a href="{h}" class="{"on" if on else ""}">{t}</a>' for h, t, on in nav)
    badge = f'<span class="badge">{n_alerts}</span>' if n_alerts else ""
    st.markdown(
        f"""<div class="topbar" id="overview">
        <div class="brand">{icon("globe", 36, BLUE)}<div><div class="bname">Supply Chain Risk Pro</div>
        <div class="bsub">Gulf Coast Oil, Gas &amp; Chemical Supply Intelligence</div></div></div>
        <nav>{links}</nav>
        <div class="right"><div class="meta">Live data checked<br>{html.escape(checked_at)}</div>
        <a href="#alerts" class="bell">{icon("bell", 22)}{badge}</a>
        <div class="avatar">{html.escape(initials)}</div></div></div>""", unsafe_allow_html=True)


def pill(level: str, text: str = None) -> str:
    s = STATUS.get(level, STATUS["NODATA"])
    return (f'<span class="pill" style="color:{s["fg"]};background:{s["tint"]}">'
            f'{html.escape(text or s["label"])}</span>')


def card_title(title: str, sub: str = "") -> None:
    st.markdown(f'<div class="ctitle">{title}</div>' + (f'<div class="csub">{sub}</div>' if sub else ""),
                unsafe_allow_html=True)


def section(anchor: str, title: str, sub: str = "") -> None:
    st.markdown(f'<div class="sect" id="{anchor}">{title}</div>'
                + (f'<div class="csub">{sub}</div>' if sub else ""), unsafe_allow_html=True)


def alert_card(ctype: str, level: str, kind: str, emoji: str, head: str, body: str, when: str = "",
               link: str = "#alerts") -> str:
    t = CARD_TYPES[ctype]
    st_ = STATUS.get(level, STATUS["NODATA"])
    tag = {"HIGH": "High risk", "ELEVATED": "Medium risk", "MONITOR": "Monitor", "NORMAL": "Normal",
           "NODATA": "No data"}[level]
    return (f'<div class="acard" style="background:{t["bg"]};border-color:{t["bd"]}">'
            f'<div class="ico" style="background:{t["ico"]}">{emoji}</div>'
            f'<div class="txt"><div class="row1"><span class="kind" style="color:{t["fg"]}">{html.escape(kind)}</span>'
            f'<span class="when">{html.escape(when)}</span></div>'
            f'<div class="head" title="{html.escape(head)}">{html.escape(head)}</div>'
            f'<div class="body">{html.escape(body)}</div>'
            f'<div class="more"><span class="tag" style="color:{st_["fg"]};background:{st_["tint"]}">{tag}</span>'
            f'<a href="{link}">See details →</a></div></div></div>')
