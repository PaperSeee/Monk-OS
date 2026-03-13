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
    create_business_test,
    get_business_tests,
    update_business_test_status,
    add_business_cash_burn,
    delete_business_test,
)
from utils.helpers import inject_css, TIMEZONES, CURRENCY_SYMBOLS, get_now_str, fmt, get_fx_rates, render_pillar_top_nav

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
render_pillar_top_nav("ct")

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
business_tests = get_business_tests()

total_allocated_budget = sum(float(t.get("allocated_budget", 0) or 0) for t in business_tests)
total_cash_burn = sum(float(t.get("cash_burn", 0) or 0) for t in business_tests)
active_business = sum(
    1 for t in business_tests if (t.get("status") or "").lower() not in ["terminé", "abandonne", "abandonné", "fail"]
)

# Top KPI metrics
kpi_top_1, kpi_top_2, kpi_top_3 = st.columns(3)
kpi_top_1.metric("Capital Investi", fmt(totals['total_invested'], ccy, r))
kpi_top_2.metric("Valeur Actuelle", fmt(totals['total_current'], ccy, r))
kpi_top_3.metric("Gain/Perte €", fmt(totals['gain_loss'], ccy, r))

kpi_bot_1, kpi_bot_2, kpi_bot_3 = st.columns(3)
kpi_bot_1.metric("Performance %", f"{totals['gain_loss_pct']:.2f}%")
kpi_bot_2.metric("Budget Business", fmt(total_allocated_budget, ccy, r))
kpi_bot_3.metric("Burn Business", fmt(total_cash_burn, ccy, r), delta=f"{active_business} actifs")

st.divider()

col_risk, col_business = st.columns(2)

with col_risk:
    st.markdown("### 💣 Investissement à risque")
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

    st.markdown("### 📊 Portefeuille risque")
    if not investments:
        st.caption("Aucun investissement pour l'instant.")
    else:
        for inv in investments:
            gain_color = "🟢" if inv['gain_loss'] >= 0 else "🔴"
            perf_color = "#10B981" if inv['gain_loss'] >= 0 else "#EF4444"

            st.markdown(f"""
            <div class="uniform-card">
                <div>
                    <div class="uniform-card-title">{inv['name']}</div>
                    <div class="uniform-card-value">{gain_color} {fmt(inv['gain_loss'], ccy, r)}</div>
                    <div style="font-size:0.7rem; color:#8892AA;">
                        {inv['asset_type']} · {inv['quantity']:.4f}
                    </div>
                </div>
                <div class="uniform-card-subtitle">
                    <div style="color:{perf_color}; font-weight:700; font-size:0.75rem;">
                        {inv['gain_loss_pct']:+.2f}%
                    </div>
                    <div style="font-size:0.65rem; margin-top:0.3rem;">
                        In: {fmt(inv['invested_amount'], ccy, r)} → Now: {fmt(inv['current_amount'], ccy, r)}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_price, col_delete = st.columns([3, 1])
            with col_price:
                new_price = st.number_input(
                    f"Prix {inv['name']}",
                    min_value=0.0,
                    step=0.01,
                    value=float(inv['current_price']),
                    key=f"price_{inv['id']}",
                    label_visibility="collapsed"
                )
                if new_price != float(inv['current_price']):
                    update_risk_investment_price(inv['id'], new_price)
                    st.rerun()

            with col_delete:
                if st.button("🗑️", key=f"del_inv_{inv['id']}", use_container_width=True):
                    delete_risk_investment(inv['id'])
                    st.warning("✓ Liquidé")
                    st.rerun()

            st.divider()

with col_business:
    st.markdown("### 🚀 Business lancés (non établis)")
    with st.form("add_business_form"):
        st.write("**Nouveau business test**")
        biz_name = st.text_input("Nom du business", placeholder="Ex: Shop Shopify niche fitness")
        biz_type = st.selectbox("Type", ["E-commerce", "SaaS", "Agence", "Contenu", "Autre"])
        biz_budget = st.number_input("Budget alloué", min_value=0.0, step=50.0, value=0.0)
        biz_desc = st.text_input("Description", placeholder="Offre, canal d'acquisition, cible...")
        deduct_lt = st.checkbox("Déduire du capital LT", value=False)

        if st.form_submit_button("✓ Ajouter business"):
            if biz_name:
                create_business_test(
                    name=f"{biz_type} — {biz_name}",
                    description=biz_desc,
                    status="Lancé",
                    allocated_budget=float(biz_budget),
                    deduct_from_lt=deduct_lt,
                )
                st.success(f"✓ {biz_name} ajouté!")
                st.rerun()
            else:
                st.error("Le nom du business est requis")

    if not business_tests:
        st.caption("Aucun business lancé pour l'instant.")
    else:
        st.markdown("### 📦 Business en cours")
        status_options = ["Idée", "Lancé", "Test", "En croissance", "Pausé", "Terminé", "Abandonné"]

        for test in business_tests:
            allocated = float(test.get("allocated_budget", 0) or 0)
            burn = float(test.get("cash_burn", 0) or 0)
            runway = allocated - burn
            status = test.get("status") or "Lancé"

            st.markdown(f"""
            <div class="uniform-card">
                <div>
                    <div class="uniform-card-title">{test.get('name', 'Business')}</div>
                    <div class="uniform-card-value">{fmt(allocated, ccy, r)}</div>
                    <div style="font-size:0.7rem; color:#8892AA;">Budget alloué</div>
                </div>
                <div class="uniform-card-subtitle">
                    <div style="font-size:0.75rem; color:#F0F4FF; font-weight:700;">Statut: {status}</div>
                    <div style="font-size:0.65rem; margin-top:0.25rem; color:#8892AA;">
                        Burn: {fmt(burn, ccy, r)} · Reste: {fmt(runway, ccy, r)}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            current_idx = status_options.index(status) if status in status_options else 1
            new_status = st.selectbox(
                f"Statut {test['id']}",
                options=status_options,
                index=current_idx,
                key=f"biz_status_{test['id']}",
                label_visibility="collapsed",
            )
            if new_status != status:
                update_business_test_status(int(test['id']), new_status)
                st.rerun()

            burn_col1, burn_col2, burn_col3 = st.columns([3, 1, 1])
            with burn_col1:
                burn_add = st.number_input(
                    f"Burn add {test['id']}",
                    min_value=0.0,
                    step=10.0,
                    value=0.0,
                    key=f"biz_burn_{test['id']}",
                    label_visibility="collapsed",
                )
            with burn_col2:
                if st.button("+ Burn", key=f"add_burn_{test['id']}", use_container_width=True):
                    if burn_add > 0:
                        add_business_cash_burn(int(test['id']), float(burn_add), deduct_from_lt=False)
                        st.success("Burn ajouté")
                        st.rerun()
            with burn_col3:
                if st.button("🗑️", key=f"del_biz_{test['id']}", use_container_width=True):
                    delete_business_test(int(test['id']))
                    st.warning("Business supprimé")
                    st.rerun()

            st.divider()

st.divider()

st.markdown(f"""
<div style="text-align:center; margin-top:1.5rem;">
    <span class="stat-pill" style="border-color:#8B5CF6; color:#8B5CF6;">
        Devise : <strong style="margin-left:0.3rem; font-family:'JetBrains Mono',monospace;">{ccy_sym} {ccy}</strong>
    </span>
</div>
""", unsafe_allow_html=True)
