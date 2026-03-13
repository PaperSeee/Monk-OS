"""
CT — Investissements à Risque : APP Crypto & Spéculation (Le Casino)
Standalone application for managing risky investments with live gains/losses.
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import (
    init_db,
    get_setting,
    set_setting,
    create_risk_investment,
    update_risk_investment_price,
    delete_risk_investment,
    get_risk_investments,
    get_risk_investment_totals,
)
from utils.helpers import inject_css, TIMEZONES, CURRENCY_SYMBOLS, get_now_str, fmt, get_fx_rates

st.set_page_config(
    page_title="MONK-OS : CT — Investissements à Risque",
    page_icon="💰",
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

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📈 MT", use_container_width=True, key="nav_mt"):
            st.switch_page("pages/_2_MT_Trading.py")
    with col2:
        st.button("💰 Investissements", use_container_width=True, key="nav_risk_disabled", disabled=True)

    if st.button("← Accueil", use_container_width=True, key="home"):
        st.switch_page("app.py")

    st.divider()

    st.markdown("""
    <div style="font-size:0.58rem; color:#4A5568; letter-spacing:0.3em;
                text-transform:uppercase; font-weight:500; margin-bottom:0.5rem;">
        Investissements à Risque
    </div>
    """, unsafe_allow_html=True)

    st.caption("Crypto · Spéculation · Gains & Pertes")

# ── HEADER ──────────────────────────────────────────────────────────────────
date_str, time_str = get_now_str(st.session_state.timezone)
r = get_fx_rates() if st.session_state.currency != "EUR" else {"EUR": 1.0}
ccy = st.session_state.currency
ccy_sym = CURRENCY_SYMBOLS.get(ccy, "€")

col_title, col_clock = st.columns([3, 1])
with col_title:
    st.markdown("""
    <div style="padding-top:0.5rem;">
        <div style="font-size:0.65rem; color:#8B5CF6; letter-spacing:0.4em;
                    text-transform:uppercase; margin-bottom:0.5rem; font-weight:600;">
            Court Terme — Investissements
        </div>
        <div style="font-size:2.5rem; font-weight:800; color:#F0F4FF;
                    letter-spacing:-0.04em; font-family:'JetBrains Mono',monospace;">
            💰 CASINO
        </div>
        <div style="font-size:0.85rem; color:#8892AA; margin-top:0.3rem;">
            Crypto & Spéculation · Gains/Pertes
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

st.markdown("<div style='margin:1rem 0; width:60px; height:3px; background:#8B5CF6; border-radius:2px;'></div>",
            unsafe_allow_html=True)

# ── MAIN CONTENT ────────────────────────────────────────────────────────────
investments = get_risk_investments()
totals = get_risk_investment_totals()

# Top KPI metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Capital Investi", fmt(totals['total_invested'], ccy, r))
col2.metric("Valeur Actuelle", fmt(totals['total_current'], ccy, r))

gain_loss_color = "green" if totals['gain_loss'] >= 0 else "red"
col3.metric("Gain/Perte €", fmt(totals['gain_loss'], ccy, r))
col4.metric("Performance %", f"{totals['gain_loss_pct']:.2f}%")

st.divider()

# Add new investment form
st.markdown("### ➕ Ajouter un investissement à risque")
col_form1, col_form2 = st.columns(2)

with col_form1:
    with st.form("add_investment_form"):
        st.write("**Nouvel investissement**")
        inv_name = st.text_input("Nom de l'actif", placeholder="Bitcoin, Ethereum, Tesla, etc.")
        asset_type = st.selectbox("Type d'actif", ["Crypto", "Action Spec", "ETF Risqué", "Commodité", "Autre"])
        quantity = st.number_input("Quantité", min_value=0.0, step=0.01, value=0.0)
        entry_price = st.number_input("Prix d'entrée", min_value=0.0, step=0.01, value=0.0)
        note = st.text_input("Note (optionnel)", placeholder="Raison de l'investissement")
        
        if st.form_submit_button("✓ Ajouter investissement"):
            if inv_name and quantity > 0 and entry_price > 0:
                create_risk_investment(inv_name, asset_type, quantity, entry_price, note)
                st.success(f"✓ {inv_name} ajouté!")
                st.rerun()
            else:
                st.error("Tous les champs sont requis (quantité > 0)")

with col_form2:
    st.info("""
    **Comment ça marche:**
    - Entrez l'actif que vous possédez
    - Mettez à jour le prix actuel ci-dessous
    - Suivez vos gains/pertes en temps réel
    - Supprimez quand vous liquidez
    """)

st.divider()

# Investment portfolio
if not investments:
    st.caption("Aucun investissement pour l'instant.")
else:
    st.markdown("### 📊 Votre portefeuille")
    
    for inv in investments:
        col_inv1, col_inv2, col_inv3 = st.columns([2.5, 2, 0.5])
        
        with col_inv1:
            # Update current price
            new_price = st.number_input(
                f"Prix actuel: {inv['name']} ({inv['asset_type']})",
                min_value=0.0,
                step=0.01,
                value=float(inv['current_price']),
                key=f"price_{inv['id']}",
                label_visibility="collapsed"
            )
            if new_price != float(inv['current_price']):
                update_risk_investment_price(inv['id'], new_price)
                st.rerun()
        
        with col_inv2:
            # Display gains/losses
            gain_color = "🟢" if inv['gain_loss'] >= 0 else "🔴"
            st.markdown(f"""
            <div class="monk-card" style="padding:0.8rem;">
                <div style="font-size:0.75rem; color:#8B5CF6; font-weight:700;">
                    {inv['name']} · {inv['quantity']:.4f}
                </div>
                <div style="font-size:0.9rem; color:#F0F4FF; margin-top:0.3rem;">
                    {gain_color} {fmt(inv['gain_loss'], ccy, r)}
                </div>
                <div style="font-size:0.65rem; color:#8892AA; margin-top:0.2rem;">
                    In: {fmt(inv['invested_amount'], ccy, r)} → Now: {fmt(inv['current_amount'], ccy, r)}
                </div>
                <div style="font-size:0.65rem; color:#10B981; margin-top:0.1rem;">
                    {inv['gain_loss_pct']:+.2f}%
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_inv3:
            if st.button("🗑️", key=f"del_inv_{inv['id']}", use_container_width=True):
                delete_risk_investment(inv['id'])
                st.warning(f"✓ {inv['name']} liquidé")
                st.rerun()

st.divider()

st.markdown(f"""
<div style="text-align:center; margin-top:1.5rem;">
    <span class="stat-pill" style="border-color:#8B5CF6; color:#8B5CF6;">
        Devise : <strong style="margin-left:0.3rem; font-family:'JetBrains Mono',monospace;">{ccy_sym} {ccy}</strong>
    </span>
</div>
""", unsafe_allow_html=True)
