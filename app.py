"""
MONK-OS V2: CEO Terminal
Main entry point — page config, CSS injection, sidebar with currency/timezone, live clock.
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from db.database import init_db, get_setting, set_setting
from utils.helpers import inject_css, TIMEZONES, CURRENCY_SYMBOLS, get_now_str

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MONK-OS : CEO Terminal",
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
inject_css()

# ── Session state defaults ───────────────────────────────────────────────────
if "currency" not in st.session_state:
    st.session_state.currency = get_setting("preferred_currency", "EUR")
if "timezone" not in st.session_state:
    st.session_state.timezone = get_setting("preferred_timezone", "Europe/Brussels")

# ── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    # Branding
    st.markdown("""
    <div style="padding:1.2rem 0 1.5rem 0; text-align:center; border-bottom:1px solid #232836;">
        <div style="font-size:1.4rem; font-weight:800; color:#F0F4FF;
                    letter-spacing:-0.02em; font-family:'JetBrains Mono',monospace;">
            MONK-OS
        </div>
        <div style="font-size:0.58rem; color:#4A5568; letter-spacing:0.3em;
                    text-transform:uppercase; margin-top:0.3rem;">
            CEO Terminal · V2.0
        </div>
        <div style="margin-top:0.8rem;">
            <span style="background:#1E3A5F; color:#3B82F6; padding:0.2rem 0.7rem;
                         border-radius:20px; font-size:0.62rem; font-weight:600;
                         letter-spacing:0.05em;">● LIVE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Currency toggle ──────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:0.58rem; color:#4A5568; letter-spacing:0.2em;
                text-transform:uppercase; margin-bottom:0.5rem; font-weight:500;">
        Devise d'affichage
    </div>
    """, unsafe_allow_html=True)

    ccy_options = ["EUR", "USD", "AED"]
    ccy_labels  = ["€  EUR", "$  USD", "د.إ  AED"]
    ccy_idx     = ccy_options.index(st.session_state.currency) if st.session_state.currency in ccy_options else 0

    selected_ccy = st.radio(
        "currency_radio", ccy_labels,
        index=ccy_idx, label_visibility="collapsed"
    )
    new_ccy = ccy_options[ccy_labels.index(selected_ccy)]
    if new_ccy != st.session_state.currency:
        st.session_state.currency = new_ccy
        set_setting("preferred_currency", new_ccy)
        st.rerun()

    st.markdown("<div style='height:0.5rem; border-top:1px solid #232836; margin-top:0.5rem'></div>",
                unsafe_allow_html=True)

    # ── Timezone selector ────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:0.58rem; color:#4A5568; letter-spacing:0.2em;
                text-transform:uppercase; margin:0.5rem 0; font-weight:500;">
        Fuseau Horaire
    </div>
    """, unsafe_allow_html=True)

    tz_names    = list(TIMEZONES.keys())
    tz_values   = list(TIMEZONES.values())
    current_tz  = st.session_state.timezone
    tz_idx      = tz_values.index(current_tz) if current_tz in tz_values else 0

    selected_tz_name = st.selectbox("tz_select", tz_names,
                                    index=tz_idx, label_visibility="collapsed")
    new_tz = TIMEZONES[selected_tz_name]
    if new_tz != st.session_state.timezone:
        st.session_state.timezone = new_tz
        set_setting("preferred_timezone", new_tz)
        st.rerun()

# ── MAIN PAGE HEADER with live clock ────────────────────────────────────────
date_str, time_str = get_now_str(st.session_state.timezone)

# Top-right datetime display
col_title, col_clock = st.columns([3, 1])
with col_title:
    st.markdown("""
    <div style="padding-top:0.5rem;">
        <div style="font-size:0.65rem; color:#3B82F6; letter-spacing:0.4em;
                    text-transform:uppercase; margin-bottom:0.5rem; font-weight:600;">
            Système opérationnel
        </div>
        <div style="font-size:3rem; font-weight:800; color:#F0F4FF;
                    letter-spacing:-0.04em; line-height:1.0;
                    font-family:'JetBrains Mono',monospace;">
            MONK-OS
        </div>
        <div style="font-size:0.85rem; color:#8892AA; letter-spacing:0.3em;
                    text-transform:uppercase; margin-top:0.4rem;">
            CEO Terminal · V2.0
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_clock:
    tz_label = selected_tz_name.split(" ")[-1].upper()
    st.markdown(f"""
    <div class="datetime-widget" style="padding-top:0.8rem;">
        <div class="datetime-time">{time_str}</div>
        <div class="datetime-date">{date_str}</div>
        <div class="datetime-tz">{selected_tz_name}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin:1rem 0; width:60px; height:3px; background:#3B82F6; border-radius:2px;'></div>",
            unsafe_allow_html=True)

# ── Module grid ──────────────────────────────────────────────────────────────
ccy_sym = CURRENCY_SYMBOLS.get(st.session_state.currency, "€")

cols = st.columns(5)
modules = [
    ("Fortress_One", "🏰", "Fortress One",     "Dashboard Épargne",        "#3B82F6"),
    ("Equity_Engine", "📈", "Equity Engine",    "ETF Multi-Position V2",    "#10B981"),
    ("Freedom_Simulator", "🔮", "Freedom Sim",      "Projections 20 ans",       "#8B5CF6"),
    ("Sentinel", "🛡️", "Sentinel",         "Anti-Tilt & Discipline",  "#F59E0B"),
    ("CEO_Report", "📄", "CEO Report",       "PDF Monthly Report",       "#EC4899"),
]
for col, (url, icon, name, desc, color) in zip(cols, modules):
    with col:
        st.markdown(f"""
        <a href="{url}" target="_self" style="text-decoration:none;">
            <div class="monk-card" style="text-align:center; cursor:pointer; padding:1.5rem 0.8rem; height:100%;">
                <div style="font-size:1.8rem; margin-bottom:0.7rem;">{icon}</div>
                <div style="font-size:0.72rem; color:{color}; letter-spacing:0.06em;
                            text-transform:uppercase; font-weight:700;
                            font-family:'Inter',sans-serif;">{name}</div>
                <div style="font-size:0.67rem; color:#4A5568; margin-top:0.35rem;">{desc}</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

# Current currency pill
st.markdown(f"""
<div style="text-align:center; margin-top:1rem;">
    <span class="stat-pill" style="border-color:#3B82F6; color:#3B82F6;">
        Devise active : <strong style="margin-left:0.3rem; font-family:'JetBrains Mono',monospace;">
            {ccy_sym} {st.session_state.currency}
        </strong>
    </span>
</div>
""", unsafe_allow_html=True)
