"""
CT — Court Terme : APP Business & Tests (Le Laboratoire)
Standalone application for managing business experiments and sandbox tests.
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import (
    init_db,
    get_setting,
    set_setting,
    create_business_test,
    update_business_test_status,
    add_business_cash_burn,
    get_business_tests,
    get_lt_capital,
)
from utils.helpers import inject_css, TIMEZONES, CURRENCY_SYMBOLS, get_now_str, fmt, get_fx_rates

st.set_page_config(
    page_title="MONK-OS : CT — Business & Tests",
    page_icon="🔮",
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
        if st.button("📈 MT", use_container_width=True, key="nav_mt"):
            st.switch_page("pages/2_MT_Trading.py")
    with nav_col[2]:
        st.button("🔮 CT", use_container_width=True, key="nav_ct_disabled", disabled=True)

    if st.button("← Accueil", use_container_width=True, key="home"):
        st.switch_page("app.py")

    st.divider()

    st.markdown("""
    <div style="font-size:0.58rem; color:#4A5568; letter-spacing:0.3em;
                text-transform:uppercase; font-weight:500; margin-bottom:0.5rem;">
        Court Terme
    </div>
    """, unsafe_allow_html=True)

    st.caption("Expérimentation d'idées et tests de nouveaux business")



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
            Court Terme — Business
        </div>
        <div style="font-size:2.5rem; font-weight:800; color:#F0F4FF;
                    letter-spacing:-0.04em; font-family:'JetBrains Mono',monospace;">
            🔮 LABORATOIRE
        </div>
        <div style="font-size:0.85rem; color:#8892AA; margin-top:0.3rem;">
            Sandbox · Expérimentation
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
lt_capital = get_lt_capital()
tests = get_business_tests()

total_budget = sum(float(t.get("allocated_budget", 0) or 0) for t in tests)
total_burn = sum(float(t.get("cash_burn", 0) or 0) for t in tests)

# Top KPI
kpi_col = st.columns(4)
kpi_col[0].metric("💎 Capital LT", fmt(lt_capital, ccy, r))
kpi_col[1].metric("💰 Budget alloué", fmt(total_budget, ccy, r))
kpi_col[2].metric("🔥 Cash Burn", fmt(total_burn, ccy, r))
kpi_col[3].metric("📊 Nombre de tests", len(tests))

st.divider()

# Create New Test Form (Top)
st.markdown("### 🚀 Lancer un Nouveau Test")

form_col = st.columns([2, 1])

with form_col[0]:
    with st.form("ct_new_test", clear_on_submit=True):
        col_form1, col_form2 = st.columns([1, 1])

        with col_form1:
            test_name = st.text_input("📝 Nom de l'idée", placeholder="Ex: SaaS Notion template")
            test_status = st.selectbox("🎯 Statut initial", ["To Do", "Testing", "Scaling", "Failed"])

        with col_form2:
            test_budget = st.number_input(f"💵 Budget ({ccy_sym})", min_value=0.0, step=10.0, value=0.0)
            deduct_now = st.checkbox("Déduire du LT", value=False)

        test_desc = st.text_area("📄 Description", placeholder="Détail du test...", height=60)

        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            submit = st.form_submit_button("✓ Créer le test", use_container_width=True)
            if submit and test_name.strip():
                create_business_test(
                    name=test_name.strip(),
                    description=test_desc.strip(),
                    status=test_status,
                    allocated_budget=test_budget,
                    deduct_from_lt=deduct_now,
                )
                msg = f"✓ Test créé!" if not (deduct_now and test_budget > 0) \
                    else f"✓ Test créé. {fmt(test_budget, ccy, r)} déduits du LT."
                st.success(msg)
                st.rerun()
            elif submit:
                st.error("Veuillez entrer un nom")

with form_col[1]:
    st.info("""
    **Structure:**
    - To Do → Testing → Scaling → Failed
    - Chaque test peut être déplacé dans le Kanban
    """)

st.divider()

# Kanban Board
st.markdown("### 📊 KANBAN BOARD")

if not tests:
    st.info("✨ Aucun test pour l'instant. Créez-en un au-dessus!")
else:
    statuses = ["To Do", "Testing", "Scaling", "Failed"]
    columns_display = st.columns(4, gap="small")
    grouped = {s: [t for t in tests if t["status"] == s] for s in statuses}

    status_colors = {
        "To Do": "#8892AA",
        "Testing": "#3B82F6",
        "Scaling": "#10B981",
        "Failed": "#EF4444",
    }

    for col_idx, (status, column) in enumerate(zip(statuses, columns_display)):
        with column:
            items = grouped[status]
            color = status_colors.get(status, "#8892AA")

            # Header
            st.markdown(f"""
            <div style="background:#1E2330; border-top:3px solid {color}; padding:0.8rem; border-radius:8px; margin-bottom:0.8rem;">
                <div style="font-size:0.75rem; color:{color}; font-weight:700; letter-spacing:0.05em;
                            text-transform:uppercase; margin-bottom:0.3rem;">
                    {status}
                </div>
                <div style="font-size:0.9rem; color:#F0F4FF; font-weight:700;">
                    {len(items)}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Items
            if not items:
                st.caption("Aucun test")
            else:
                for item in items:
                    item_id = item["id"]
                    
                    st.markdown(f"""
                    <div class="monk-card" style="padding:0.9rem; margin-bottom:0.8rem; 
                                                  border-left:3px solid {color};">
                        <div style="font-size:0.8rem; color:{color}; font-weight:700;">
                            {item['name'][:25]}
                        </div>
                        <div style="font-size:0.65rem; color:#8892AA; margin-top:0.4rem;">
                            {item['description'][:60]}{'...' if len(item['description']) > 60 else ''}
                        </div>
                        <div style="font-size:0.7rem; color:#4A5568; margin-top:0.5rem; 
                                    padding-top:0.5rem; border-top:1px solid #232836;">
                            💰 {fmt(float(item['allocated_budget']), ccy, r)} · 🔥 {fmt(float(item['cash_burn']), ccy, r)}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    col_move, col_burn = st.columns([1, 1])

                    with col_move:
                        next_status = st.selectbox(
                            f"Déplacer #{item_id}",
                            statuses,
                            index=statuses.index(status),
                            key=f"move_{item_id}",
                            label_visibility="collapsed"
                        )
                        if next_status != status:
                            update_business_test_status(item_id, next_status)
                            st.success(f"✓ Déplacé vers {next_status}")
                            st.rerun()

                    with col_burn:
                        burn_amt = st.number_input(
                            f"Burn #{item_id}",
                            min_value=0.0,
                            step=10.0,
                            value=0.0,
                            key=f"burn_{item_id}",
                            label_visibility="collapsed"
                        )
                        if burn_amt > 0:
                            deduct_burn = st.checkbox(
                                f"Déduire du LT",
                                value=True,
                                key=f"cb_burn_{item_id}"
                            )
                            if st.button("✓ +Burn", key=f"btn_burn_{item_id}", use_container_width=True):
                                add_business_cash_burn(item_id, burn_amt, deduct_burn)
                                msg = f"✓ Cash burn ajouté!" if not deduct_burn \
                                    else f"✓ Cash burn ajouté. {fmt(burn_amt, ccy, r)} déduits du LT."
                                st.success(msg)
                                st.rerun()

                    st.divider()

st.markdown(f"""
<div style="text-align:center; margin-top:1.5rem;">
    <span class="stat-pill" style="border-color:#8B5CF6; color:#8B5CF6;">
        CT · <strong style="margin-left:0.3rem; font-family:'JetBrains Mono',monospace;">{ccy_sym} {ccy}</strong>
    </span>
</div>
""", unsafe_allow_html=True)
