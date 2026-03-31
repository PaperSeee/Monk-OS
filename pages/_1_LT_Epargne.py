"""
LT — Long Terme : Épargne & Investissement
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import (
    init_db,
    get_setting,
    set_setting,
    get_latest_finance,
    get_lt_capital,
    get_latest_portfolio_total_value,
    get_risk_crypto_current_value,
)
from utils.helpers import inject_css, fmt, get_fx_rates, CURRENCY_SYMBOLS, get_now_str, render_pillar_top_nav, render_modules_quick_menu

st.set_page_config(
    page_title="MONK-OS : LT — Épargne & Investissement",
    page_icon="🏰",
    layout="wide",
)

init_db()
inject_css()

if "currency" not in st.session_state:
    st.session_state.currency = get_setting("preferred_currency", "EUR")
if "timezone" not in st.session_state:
    st.session_state.timezone = get_setting("preferred_timezone", "Europe/Brussels")

ccy = st.session_state.currency
rates = get_fx_rates() if ccy != "EUR" else {"EUR": 1.0}
ccy_sym = CURRENCY_SYMBOLS.get(ccy, "€")

latest_finance = get_latest_finance()
cash_capital = get_lt_capital()
inv_etf = get_latest_portfolio_total_value()
inv_crypto = get_risk_crypto_current_value()
inv_other = float(latest_finance.get("investments_other", 0) or 0) if latest_finance else 0.0
capital = cash_capital + inv_etf + inv_crypto + inv_other

with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0; text-align:center; border-bottom:1px solid #232836;">
        <div style="font-size:1rem; font-weight:800; color:#F0F4FF;
                    letter-spacing:-0.02em; font-family:'JetBrains Mono',monospace;">
            MONK-OS v3
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    if st.button("← Retour Dashboard", use_container_width=True):
        st.switch_page("app.py")
    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
    render_modules_quick_menu("lt")

date_str, time_str = get_now_str(st.session_state.timezone)

render_pillar_top_nav("lt")

head_col, clock_col = st.columns([3, 1])
with head_col:
    st.markdown("""
    <div style="padding-top:0.3rem;">
        <div style="font-size:0.65rem; color:#3B82F6; letter-spacing:0.35em;
                    text-transform:uppercase; margin-bottom:0.45rem; font-weight:600;">
            Long Terme
        </div>
        <div style="font-size:2.2rem; font-weight:800; color:#F0F4FF;
                    letter-spacing:-0.03em; font-family:'JetBrains Mono',monospace;">
            🏰 LT Épargne & Investissement
        </div>
    </div>
    """, unsafe_allow_html=True)

with clock_col:
    st.markdown(f"""
    <div class="datetime-widget" style="padding-top:0.6rem;">
        <div class="datetime-time">{time_str}</div>
        <div class="datetime-date">{date_str}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin:1rem 0; width:60px; height:3px; background:#3B82F6; border-radius:2px;'></div>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("💎 Capital LT", fmt(capital, ccy, rates))
c2.metric("📈 ETF", fmt(inv_etf, ccy, rates))
c3.metric("🔐 Crypto", fmt(inv_crypto, ccy, rates))
c4.metric("🏠 Autres", fmt(inv_other, ccy, rates))

st.info("Cette page LT agrège les données live : cash LT, ETF (Equity Engine), crypto (CT Risque) et autres investissements.")

st.markdown(f"""
<div style="text-align:center; margin-top:1.2rem;">
    <span class="stat-pill" style="border-color:#3B82F6; color:#3B82F6;">
        Devise active : <strong style="margin-left:0.3rem; font-family:'JetBrains Mono',monospace;">{ccy_sym} {ccy}</strong>
    </span>
</div>
""", unsafe_allow_html=True)
