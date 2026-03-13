"""
LT — Long Terme : APP Épargne & Investissement (Le Coffre-Fort)
Standalone application for managing long-term savings and investments.
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import (
    init_db,
    get_setting,
    set_setting,
    get_lt_capital,
    set_lt_capital,
    get_prop_challenges,
    get_business_tests,
    get_total_payouts,
)
from utils.helpers import inject_css, TIMEZONES, CURRENCY_SYMBOLS, get_now_str, fmt, get_fx_rates

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

# ── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0; text-align:center; border-bottom:1px solid #232836;">
        <div style="font-size:1rem; font-weight:800; color:#F0F4FF;
                    letter-spacing:-0.02em; font-family:'JetBrains Mono',monospace;">
            MONK-OS v3
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    # Navigation Par Pilier
    st.markdown("""
    <div style="font-size:0.58rem; color:#4A5568; letter-spacing:0.3em;
                text-transform:uppercase; font-weight:500; margin-bottom:0.8rem;">
        Navigation
    </div>
    """, unsafe_allow_html=True)

    nav_col = st.columns(3)
    with nav_col[0]:
        st.button("🏰 LT", use_container_width=True, key="nav_lt_disabled", disabled=True)
    with nav_col[1]:
        if st.button("📈 MT", use_container_width=True, key="nav_mt"):
            st.switch_page("pages/2_MT_Trading.py")
    with nav_col[2]:
        if st.button("🔮 CT", use_container_width=True, key="nav_ct"):
            st.switch_page("pages/3_CT_Business.py")

    if st.button("← Accueil", use_container_width=True, key="home"):
        st.switch_page("app.py")

    st.divider()

    st.markdown("""
    <div style="font-size:0.58rem; color:#4A5568; letter-spacing:0.3em;
                text-transform:uppercase; font-weight:500; margin-bottom:0.5rem;">
        Long Terme
    </div>
    """, unsafe_allow_html=True)

    st.caption("Épargne & Investissements · Source de Vérité")

# ── HEADER ──────────────────────────────────────────────────────────────────
date_str, time_str = get_now_str(st.session_state.timezone)
r = get_fx_rates() if st.session_state.currency != "EUR" else {"EUR": 1.0}
ccy = st.session_state.currency
ccy_sym = CURRENCY_SYMBOLS.get(ccy, "€")

col_title, col_clock = st.columns([3, 1])
with col_title:
    st.markdown("""
    <div style="padding-top:0.5rem;">
        <div style="font-size:0.65rem; color:#3B82F6; letter-spacing:0.4em;
                    text-transform:uppercase; margin-bottom:0.5rem; font-weight:600;">
            Long Terme
        </div>
        <div style="font-size:2.5rem; font-weight:800; color:#F0F4FF;
                    letter-spacing:-0.04em; font-family:'JetBrains Mono',monospace;">
            🏰 ÉPARGNE
        </div>
        <div style="font-size:0.85rem; color:#8892AA; margin-top:0.3rem;">
            Coffre-Fort · Source de Vérité
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_clock:
    st.markdown(f"""
    <div class="datetime-widget" style="padding-top:0.8rem;">
        <div class="datetime-time">{time_str}</div>
        <div class="datetime-date">{date_str}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin:1rem 0; width:60px; height:3px; background:#3B82F6; border-radius:2px;'></div>",
            unsafe_allow_html=True)

# ── MAIN CONTENT ────────────────────────────────────────────────────────────
lt_capital = get_lt_capital()
challenges = get_prop_challenges()
tests = get_business_tests()

total_challenge_cost = sum(float(c.get("price", 0) or 0) for c in challenges)
total_payouts = sum(get_total_payouts(c['id']) for c in challenges)
total_cash_burn = sum(float(t.get("cash_burn", 0) or 0) for t in tests)

# Capital display
st.markdown(f"""
<div class="monk-card">
    <div class="net-worth-label">▸ CAPITAL GLOBAL</div>
    <div class="net-worth-hero">{fmt(lt_capital, ccy, r)}</div>
    <div style="font-size:0.72rem; color:#8892AA; margin-top:0.5rem;">
        <strong>Source de Vérité.</strong> Impacté par: Challenges MT achetés (-), Payouts MT reçus (+), Allocations budgétaires CT (-).
    </div>
</div>
""", unsafe_allow_html=True)

# Update capital
with st.expander("✏️ Mettre à jour le capital LT", expanded=False):
    col1, col2 = st.columns([1, 1])
    with col1:
        new_capital = st.number_input(
            "Nouveau capital global",
            min_value=0.0,
            value=float(lt_capital),
            step=100.0,
            key="lt_capital_input"
        )
    with col2:
        st.write("")
        if st.button("Sauvegarder capital", key="btn_save_capital"):
            set_lt_capital(new_capital)
            st.success(f"Capital mis à jour à {fmt(new_capital, ccy, r)}")
            st.rerun()

st.divider()

# Investments tracking
st.markdown("### Suivi Investissements")
col1, col2 = st.columns([1, 1])

with col1:
    inv_bourse = float(get_setting("lt_invest_bourse", "0"))
    inv_crypto = float(get_setting("lt_invest_crypto", "0"))
    inv_immo = float(get_setting("lt_invest_immo", "0"))

    with st.form("lt_invest_form"):
        st.write("**Ajouter une allocation d'investissement**")
        bourse = st.number_input("Bourse (€)", min_value=0.0, value=inv_bourse, step=100.0)
        crypto = st.number_input("Crypto (€)", min_value=0.0, value=inv_crypto, step=100.0)
        immo = st.number_input("Immobilier (€)", min_value=0.0, value=inv_immo, step=100.0)
        if st.form_submit_button("Enregistrer investissements"):
            set_setting("lt_invest_bourse", bourse)
            set_setting("lt_invest_crypto", crypto)
            set_setting("lt_invest_immo", immo)
            st.success("Investissements LT enregistrés.")
            st.rerun()

with col2:
    total_invest = inv_bourse + inv_crypto + inv_immo
    st.metric("Total investi LT", fmt(total_invest, ccy, r))
    if total_invest > 0:
        share_bourse = (inv_bourse / total_invest) * 100
        share_crypto = (inv_crypto / total_invest) * 100
        share_immo = (inv_immo / total_invest) * 100
        st.caption(
            f"Répartition: Bourse {share_bourse:.1f}% · Crypto {share_crypto:.1f}% · Immobilier {share_immo:.1f}%"
        )

st.divider()

# Impact tracking from other pillars
st.markdown("### Impacts depuis les autres piliers")

m1, m2, m3 = st.columns(3)
m1.metric("Charges MT (Challenges achetés)", fmt(total_challenge_cost, ccy, r))
m2.metric("Payouts MT crédités", fmt(total_payouts, ccy, r))
m3.metric("Cash Burn CT total", fmt(total_cash_burn, ccy, r))

st.markdown(f"""
<div style="text-align:center; margin-top:1.5rem;">
    <span class="stat-pill" style="border-color:#3B82F6; color:#3B82F6;">
        Devise : <strong style="margin-left:0.3rem; font-family:'JetBrains Mono',monospace;">{ccy_sym} {ccy}</strong>
    </span>
</div>
""", unsafe_allow_html=True)
