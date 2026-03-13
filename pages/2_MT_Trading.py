"""
MT — Mid Terme : APP Trading & Prop Firms (Le Levier)
Standalone application for managing prop firm challenges and trading.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import (
    init_db,
    get_setting,
    set_setting,
    create_prop_challenge,
    add_prop_payout,
    delete_prop_payout,
    update_prop_challenge_status,
    set_challenge_funded,
    delete_prop_challenge,
    get_prop_challenges,
    get_prop_challenges_by_status,
    get_lt_capital,
    get_prop_payouts,
    get_total_payouts,
)
from utils.helpers import inject_css, TIMEZONES, CURRENCY_SYMBOLS, get_now_str, fmt, get_fx_rates

st.set_page_config(
    page_title="MONK-OS : MT — Trading & Prop Firms",
    page_icon="📈",
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
        if st.button("🏰 LT", use_container_width=True, key="nav_lt"):
            st.switch_page("pages/1_LT_Epargne.py")
    with nav_col[1]:
        st.button("📈 MT", use_container_width=True, key="nav_mt_disabled", disabled=True)
    with nav_col[2]:
        if st.button("🔮 CT", use_container_width=True, key="nav_ct"):
            st.switch_page("pages/3_CT_Business.py")

    if st.button("← Accueil", use_container_width=True, key="home"):
        st.switch_page("app.py")

    st.divider()

    # Devise
    st.markdown("""
    <div style="font-size:0.58rem; color:#4A5568; letter-spacing:0.3em;
                text-transform:uppercase; font-weight:500; margin-bottom:0.5rem;">
        Devise MT
    </div>
    """, unsafe_allow_html=True)

    st.info("📌 MT est en **USD**\n\nLes montants ne sont pas convertis.")



# ── HEADER ──────────────────────────────────────────────────────────────────
date_str, time_str = get_now_str(st.session_state.timezone)
r = {"USD": 1.0}  # MT is always in USD
ccy = "USD"
ccy_sym = "$"

col_title, col_clock = st.columns([3, 1])
with col_title:
    st.markdown("""
    <div style="padding-top:0.5rem;">
        <div style="font-size:0.65rem; color:#10B981; letter-spacing:0.4em;
                    text-transform:uppercase; margin-bottom:0.5rem; font-weight:600;">
            Mid Terme — Trading
        </div>
        <div style="font-size:2.5rem; font-weight:800; color:#F0F4FF;
                    letter-spacing:-0.04em; font-family:'JetBrains Mono',monospace;">
            📈 PROP FIRMS
        </div>
        <div style="font-size:0.85rem; color:#8892AA; margin-top:0.3rem;">
            Le Levier · Challenges & Payouts
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

st.markdown("<div style='margin:1rem 0; width:60px; height:3px; background:#10B981; border-radius:2px;'></div>",
            unsafe_allow_html=True)

# ── MAIN CONTENT ────────────────────────────────────────────────────────────
lt_capital = get_lt_capital()
all_challenges = get_prop_challenges()
challenges_active = [c for c in all_challenges if c.get("status") != "Échoué"]
challenges_failed = [c for c in all_challenges if c.get("status") == "Échoué"]

funded_challenges = [c for c in challenges_active if c.get("is_funded") == 1]
bought_challenges = [c for c in challenges_active if c.get("is_funded") != 1]

total_payouts = sum(get_total_payouts(c['id']) for c in all_challenges)

# Top metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Capital LT", fmt(lt_capital, "EUR", {"EUR": 1.0}))
col2.metric("🎖️ Challenges Funded", f"${sum(float(c.get('account_size', 0) or 0) for c in funded_challenges):,.0f}")
col3.metric("💼 Challenges Achetés", len(bought_challenges))
col4.metric("💰 Payouts reçus", f"${total_payouts:,.2f}")

st.divider()

# Sections: Bought + Funded + Failed
tab_bought, tab_funded, tab_failed = st.tabs(["Challenges Achetés", "Challenges Funded", "Challenges Échoués"])

with tab_bought:
    st.markdown("### 🛒 Acheter un Challenge Prop Firm")

    col_form, col_info = st.columns([1, 1])

    with col_form:
        with st.form("buy_challenge_form"):
            account_size = st.number_input("Taille du compte ($)", min_value=0.0, step=1000.0, value=10000.0)
            challenge_price = st.number_input("Prix du challenge ($)", min_value=0.0, step=10.0, value=100.0)
            buy = st.form_submit_button("✓ Acheter cet challenge")
            if buy:
                create_prop_challenge(account_size=account_size, price=challenge_price)
                st.success(f"✓ Challenge créé. ${challenge_price:,.2f} déduits du capital LT.")
                st.rerun()

    with col_info:
        st.info("""
        **Note:** Un challenge **acheté** n'est pas encore **Funded**.
        Vous devez le valider comme "Funded" après réussite du Step.
        """)

    st.markdown("#### Vos Challenges Achetés")

    if not bought_challenges:
        st.caption("Aucun challenge acheté pour l'instant.")
    else:
        for ch in bought_challenges:
            col_a, col_b, col_c = st.columns([2, 1.2, 1.5])

            with col_a:
                st.markdown(f"""
                <div class="monk-card" style="padding:0.8rem;">
                    <div style="font-size:0.75rem; color:#10B981; font-weight:700;">
                        Challenge #{ch['id']}
                    </div>
                    <div style="font-size:0.9rem; color:#F0F4FF; font-weight:700; margin-top:0.3rem;">
                        ${ch['account_size']:,.0f}
                    </div>
                    <div style="font-size:0.65rem; color:#8892AA; margin-top:0.2rem;">
                        Acheté le {ch['created_at'][:10]} · Coût: ${ch['price']:,.2f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_b:
                status = ch.get("status", "En cours")
                status_color = "#3B82F6" if status == "En cours" else "#F59E0B"
                st.markdown(f"""
                <div style="font-size:0.65rem; color:{status_color}; font-weight:700; margin-top:0.8rem;">
                    {status}
                </div>
                """, unsafe_allow_html=True)

            with col_c:
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    if st.button("🎖️ Funded", key=f"funded_{ch['id']}", use_container_width=True):
                        set_challenge_funded(ch['id'], True)
                        st.success(f"✓ Challenge #{ch['id']} est maintenant Funded!")
                        st.rerun()

                with col_c2:
                    if st.button("🗑️ Supprimer", key=f"del_{ch['id']}", use_container_width=True):
                        refund = delete_prop_challenge(ch['id'])
                        st.warning(f"✓ Challenge #{ch['id']} supprimé. ${refund:,.2f} refundés au LT.")
                        st.rerun()

with tab_funded:
    st.markdown("### 🎖️ Challenges Funded")

    if not funded_challenges:
        st.info("Aucun challenge Funded pour l'instant.")
    else:
        for ch in funded_challenges:
            total_payout = get_total_payouts(ch['id'])
            payouts_history = get_prop_payouts(ch['id'])
            
            with st.expander(f"📌 Challenge #{ch['id']} · ${ch['account_size']:,.0f} · Payouts: ${total_payout:,.2f}", expanded=True):
                col_d1, col_d2 = st.columns([1.5, 1])

                with col_d1:
                    st.markdown(f"""
                    **Statut:** {ch.get('status', 'En cours')}
                    **Compte:** ${ch['account_size']:,.0f}
                    **Prix Acheté:** ${ch['price']:,.2f}
                    **Payouts Totaux:** ${total_payout:,.2f}
                    """)

                with col_d2:
                    st.markdown("**Gérer les Payouts**")
                    payout_amount = st.number_input(f"Ajouter payout pour Challenge #{ch['id']}", 
                                                   min_value=0.0, step=10.0, value=0.0,
                                                   key=f"payout_{ch['id']}")
                    payout_note = st.text_input(f"Note (optionnel)", key=f"note_{ch['id']}", placeholder="Ex: Step 1 complete")
                    if st.button(f"✓ Ajouter Payout", key=f"add_payout_{ch['id']}", use_container_width=True):
                        if payout_amount > 0:
                            add_prop_payout(ch['id'], payout_amount, payout_note)
                            st.success(f"✓ ${payout_amount:,.2f} ajouté au capital LT!")
                            st.rerun()
                        else:
                            st.warning("Veuillez entrer un montant > 0")

                # Payout history
                if payouts_history:
                    st.divider()
                    st.markdown("**Historique des Payouts**")
                    for payout in payouts_history:
                        col_ph1, col_ph2, col_ph3 = st.columns([2, 1, 0.8])
                        with col_ph1:
                            note_display = f" · {payout['note']}" if payout['note'] else ""
                            st.caption(f"${payout['amount']:,.2f}{note_display}")
                        with col_ph2:
                            st.caption(payout['created_at'][:10])
                        with col_ph3:
                            if st.button("🗑️", key=f"del_payout_{payout['id']}", use_container_width=True):
                                delete_prop_payout(ch['id'], payout['id'], payout['amount'])
                                st.warning(f"✓ Payout supprimé. ${payout['amount']:,.2f} refundé au LT.")
                                st.rerun()

with tab_failed:
    st.markdown("### ❌ Challenges Échoués")

    if not challenges_failed:
        st.caption("Aucun challenge échoué.")
    else:
        for ch in challenges_failed:
            st.markdown(f"""
            <div class="monk-card" style="padding:0.8rem; border-left:3px solid #EF4444;">
                <div style="font-size:0.75rem; color:#EF4444; font-weight:700;">Challenge #{ch['id']}</div>
                <div style="font-size:0.9rem; color:#F0F4FF; margin-top:0.3rem;">
                    ${ch['account_size']:,.0f} · Coût: ${ch['price']:,.2f}
                </div>
                <div style="font-size:0.65rem; color:#8892AA; margin-top:0.2rem;">
                    Acheté le {ch['created_at'][:10]} · Statut: {ch.get("status", "Échoué")}
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown(f"""
<div style="text-align:center; margin-top:1.5rem;">
    <span class="stat-pill" style="border-color:#10B981; color:#10B981;">
        MT · <strong style="margin-left:0.3rem; font-family:'JetBrains Mono',monospace;">USD</strong>
    </span>
</div>
""", unsafe_allow_html=True)
