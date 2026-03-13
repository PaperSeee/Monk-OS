"""
MONK-OS V3: Life & Wealth OS — CENTRAL DASHBOARD
Home page: aggregates all KPI from LT / MT / CT with navigation buttons.
Each pillar (LT/MT/CT) is a full standalone app accessible via pages.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from db.database import (
    init_db,
    get_setting,
    set_setting,
    get_lt_capital,
    get_prop_challenges,
    get_business_tests,
    get_total_payouts,
    get_risk_investment_totals,
)
from utils.helpers import inject_css, TIMEZONES, CURRENCY_SYMBOLS, get_now_str, fmt, get_fx_rates

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MONK-OS : Life & Wealth OS — Dashboard Central",
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
            Life & Wealth OS · V3.0
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

# ── MAIN PAGE HEADER ────────────────────────────────────────────────────────
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
            Dashboard Central
        </div>
        <div style="font-size:3rem; font-weight:800; color:#F0F4FF;
                    letter-spacing:-0.04em; line-height:1.0;
                    font-family:'JetBrains Mono',monospace;">
            MONK-OS
        </div>
        <div style="font-size:0.85rem; color:#8892AA; letter-spacing:0.3em;
                    text-transform:uppercase; margin-top:0.4rem;">
            Life & Wealth OS — Synthèse
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_clock:
    st.markdown(f"""
    <div class="datetime-widget" style="padding-top:0.8rem;">
        <div class="datetime-time">{time_str}</div>
        <div class="datetime-date">{date_str}</div>
        <div class="datetime-tz">{selected_tz_name}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin:1rem 0; width:60px; height:3px; background:#3B82F6; border-radius:2px;'></div>",
            unsafe_allow_html=True)

# ── LOAD AGGREGATED DATA FROM ALL 3 PILLARS ───────────────────────────────
lt_capital = get_lt_capital()
challenges = get_prop_challenges()
tests = get_business_tests()
risk_totals = get_risk_investment_totals()

total_challenge_cost = sum(float(c.get("price", 0) or 0) for c in challenges)
total_payouts = sum(get_total_payouts(c['id']) for c in challenges)
total_allocated_budget = sum(float(t.get("allocated_budget", 0) or 0) for t in tests)
total_cash_burn = sum(float(t.get("cash_burn", 0) or 0) for t in tests)
funded_live = sum(
    float(c.get("account_size", 0) or 0)
    for c in challenges
    if c.get("status") in ["En cours", "Passé"]
)

inv_bourse = float(get_setting("lt_invest_bourse", "0"))
inv_crypto = float(get_setting("lt_invest_crypto", "0"))
inv_immo = float(get_setting("lt_invest_immo", "0"))
total_invest = inv_bourse + inv_crypto + inv_immo

# ── CENTRAL KPI GRID ────────────────────────────────────────────────────────
st.markdown("""
<div style="font-size:0.62rem; color:#4A5568; letter-spacing:0.2em;
            text-transform:uppercase; margin-bottom:1rem; font-weight:500;">
    ▸ KPI CONSOLIDÉS
</div>
""", unsafe_allow_html=True)

kpi_cols = st.columns(4)
kpi_cols[0].metric("💎 Capital Global (LT)", fmt(lt_capital, ccy, r))
kpi_cols[1].metric("🚀 Funded (MT)", fmt(funded_live, ccy, r))
kpi_cols[2].metric("📊 Investis (Risque)", fmt(risk_totals['total_invested'], ccy, r))
gain_loss_emoji = "🟢" if risk_totals['gain_loss'] >= 0 else "🔴"
kpi_cols[3].metric(f"{gain_loss_emoji} Gains/Pertes", fmt(risk_totals['gain_loss'], ccy, r))

st.divider()

# ── NAVIGATION CARDS BY PILLAR ───────────────────────────────────────────────
st.markdown("""
<div style="font-size:0.62rem; color:#4A5568; letter-spacing:0.2em;
            text-transform:uppercase; margin-bottom:1rem; font-weight:500;">
    ▸ ACCÉDER AUX APPLICATIONS
</div>
""", unsafe_allow_html=True)

nav_cols = st.columns(3)

# LT Card
with nav_cols[0]:
    st.markdown(f"""
    <div class="monk-card" style="text-align:center; padding:1.5rem 1rem; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
        <div>
            <div style="font-size:2rem; margin-bottom:0.8rem;">🏰</div>
            <div style="font-size:0.68rem; color:#8892AA; margin-bottom:1rem;">
                Épargne & Investissement
            </div>
            <div style="font-size:0.85rem; color:#F0F4FF; font-weight:700; font-family:'JetBrains Mono',monospace; margin-bottom:0.6rem;">
                {fmt(lt_capital, ccy, r)}
            </div>
            <hr style="border-color:#232836; margin:0.5rem 0;">
            <div style="font-size:0.65rem; color:#8892AA;">
                ETF: {fmt(total_invest, ccy, r)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Ouvrir", key="btn_lt", use_container_width=True):
        st.switch_page("pages/_1_LT_Epargne.py")

# MT Card
with nav_cols[1]:
    st.markdown(f"""
    <div class="monk-card" style="text-align:center; padding:1.5rem 1rem; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
        <div>
            <div style="font-size:2rem; margin-bottom:0.8rem;">📈</div>
            <div style="font-size:0.68rem; color:#8892AA; margin-bottom:1rem;">
                Trading & Prop Firms
            </div>
            <div style="font-size:0.85rem; color:#F0F4FF; font-weight:700; font-family:'JetBrains Mono',monospace; margin-bottom:0.6rem;">
                {fmt(funded_live, ccy, r)}
            </div>
            <hr style="border-color:#232836; margin:0.5rem 0;">
            <div style="font-size:0.65rem; color:#8892AA;">
                Payouts: {fmt(total_payouts, ccy, r)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Ouvrir", key="btn_mt", use_container_width=True):
        st.switch_page("pages/_2_MT_Trading.py")

# CT Card — Risk Investments
with nav_cols[2]:
    st.markdown(f"""
    <div class="monk-card" style="text-align:center; padding:1.5rem 1rem; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
        <div>
            <div style="font-size:2rem; margin-bottom:0.8rem;">💰</div>
            <div style="font-size:0.68rem; color:#8892AA; margin-bottom:1rem;">
                Crypto & Spéculation
            </div>
            <div style="font-size:0.85rem; color:#F0F4FF; font-weight:700; font-family:'JetBrains Mono',monospace; margin-bottom:0.6rem;">
                {fmt(risk_totals['gain_loss'], ccy, r)}
            </div>
            <hr style="border-color:#232836; margin:0.5rem 0;">
            <div style="font-size:0.65rem; color:#8892AA;">
                {risk_totals['gain_loss_pct']:+.2f}% Performance
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Ouvrir", key="btn_risk", use_container_width=True):
        st.switch_page("pages/_3_CT_Business.py")

st.divider()

# ── FLOW DIAGRAM ────────────────────────────────────────────────────────────
st.markdown("""
<div style="font-size:0.62rem; color:#4A5568; letter-spacing:0.2em;
            text-transform:uppercase; margin-bottom:1rem; font-weight:500;">
    ▸ INTERCONNEXION DES FLUX
</div>
""", unsafe_allow_html=True)

flow_text = f"""
**LT (Coffre-Fort) ← Source de Vérité**
- Capital global : {fmt(lt_capital, ccy, r)}
- Impacté par : Challenges achetés en MT, allocations budgétaires CT, payouts MT

**MT (Levier) → Impacte LT**
- Nouveaux challenges : déduisent du capital LT
- Payouts reçus : crédités au capital LT

**CT (Laboratoire) → Impacte LT**
- Budgets alloués : optionnellement déduits du capital LT
- Cash burn : tracké et visible dans la synthèse LT
"""

st.markdown(flow_text)

st.markdown(f"""
<div style="text-align:center; margin-top:1.5rem;">
    <span class="stat-pill" style="border-color:#3B82F6; color:#3B82F6;">
        Devise active : <strong style="margin-left:0.3rem; font-family:'JetBrains Mono',monospace;">{ccy_sym} {ccy}</strong>
    </span>
</div>
""", unsafe_allow_html=True)
