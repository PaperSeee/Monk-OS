"""
Module 5 V2 — DATA INPUT
Month picker with upsert/delete, multi-investment fields, stacked bar chart
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from db.database import (init_db, upsert_finance_entry, get_finances,
                          get_finance_for_month, get_setting, set_setting,
                          delete_finance_entry)
from utils.helpers import inject_css, section_head, sub_label, plotly_theme, fmt, get_fx_rates

init_db()
inject_css()

import pandas as pd
import plotly.graph_objects as go

section_head("MODULE 05 — TERMINAL D'ENTRÉE DES DONNÉES")

ccy   = st.session_state.get("currency", "EUR")
rates = get_fx_rates() if ccy != "EUR" else {"EUR": 1.0}

# ── Month Selector ────────────────────────────────────────────────────────────
sub_label("Période — Sélectionner le mois")

today  = date.today()
months = []
cur    = date(2026, 4, 1)   # Start from April 2026 as requested
target = date(today.year, today.month, 1)
while cur <= target:
    months.append(cur.strftime("%B %Y"))
    m = cur.month + 1
    y = cur.year + (1 if m > 12 else 0)
    cur = date(y, m % 12 or 12, 1)
months.reverse()  # most recent first
if not months:
    months = [today.strftime("%B %Y")]

col_month, col_del, col_spacer = st.columns([1.5, 1, 2])
with col_month:
    selected_label = st.selectbox("Mois", months if months else [today.strftime("%B %Y")],
                                  index=0, label_visibility="collapsed")

selected_dt = datetime.strptime(selected_label, "%B %Y")
month_key   = selected_dt.strftime("%Y-%m")
existing    = get_finance_for_month(month_key)

with col_del:
    if existing:
        st.markdown("<div style='padding-top:0.4rem;'></div>", unsafe_allow_html=True)
        if st.button("🗑  Supprimer ce mois", type="secondary"):
            delete_finance_entry(month_key)
            st.success(f"✓ Entrée {selected_label} supprimée.")
            st.rerun()

# ── Finance Form ──────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="font-size:0.7rem; color:{'#3B82F6' if not existing else '#F59E0B'};
            font-family:'JetBrains Mono',monospace; font-weight:600;
            margin:0.3rem 0 1rem 0;">
    {"✏️  Modification" if existing else "➕  Nouvelle entrée"} — {selected_label}
</div>
""", unsafe_allow_html=True)

with st.form("finance_form_v2", clear_on_submit=False):
    col_inc, col_sp = st.columns([1.2, 2])
    with col_inc:
        income = st.number_input("💰 Revenu net (€)", min_value=0.0,
                                  value=float(existing["income"]) if existing else 1250.0,
                                  step=50.0)

    sub_label("Dépenses fixes")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        rent = st.number_input("🏠 Loyer / Charges", min_value=0.0,
                               value=float(existing["rent"]) if existing else 0.0, step=10.0)
    with c2:
        food = st.number_input("🍽️ Nourriture", min_value=0.0,
                               value=float(existing["food"]) if existing else 0.0, step=10.0)
    with c3:
        transport = st.number_input("🚇 Transport", min_value=0.0,
                                    value=float(existing["transport"]) if existing else 0.0, step=5.0)
    with c4:
        misc = st.number_input("📦 Divers", min_value=0.0,
                               value=float(existing["misc"]) if existing else 0.0, step=5.0)

    sub_label("Investissements du mois")
    ci1, ci2, ci3 = st.columns(3)
    with ci1:
        inv_etf = st.number_input("📈 ETF (€)", min_value=0.0,
                                   value=float(existing.get("investments_etf", 0)) if existing else 0.0,
                                   step=50.0)
    with ci2:
        inv_crypto = st.number_input("🔶 Crypto (€)", min_value=0.0,
                                      value=float(existing.get("investments_crypto", 0)) if existing else 0.0,
                                      step=10.0)
    with ci3:
        inv_other = st.number_input("🏦 Autres (€)", min_value=0.0,
                                     value=float(existing.get("investments_other", 0)) if existing else 0.0,
                                     step=10.0)

    note = st.text_input("Note", value=existing.get("note", "") if existing else "",
                          placeholder="Ex: Mois d'avril 2026 — premier mois Monk Mode")

    # Live preview
    total_expenses = rent + food + transport + misc
    total_invest   = inv_etf + inv_crypto + inv_other
    savings        = income - total_expenses - total_invest
    s_color        = "#10B981" if savings >= 0 else "#EF4444"
    s_rate         = (savings / income * 100) if income > 0 else 0

    st.markdown(f"""
    <div style="background:#1C2130; border-radius:8px; padding:1rem 1.4rem;
                border:1px solid #2D3447; margin-top:0.8rem;
                display:flex; gap:3rem; flex-wrap:wrap; align-items:center;">
        <span style="color:#8892AA; font-size:0.85rem;">
            Dépenses : <b style="color:#F0F4FF; font-family:'JetBrains Mono',monospace;">
            {fmt(total_expenses, ccy, rates)}</b>
        </span>
        <span style="color:#8892AA; font-size:0.85rem;">
            Invest. : <b style="color:#8B5CF6; font-family:'JetBrains Mono',monospace;">
            {fmt(total_invest, ccy, rates)}</b>
        </span>
        <span style="color:#8892AA; font-size:0.85rem;">
            Épargne nette : <b style="color:{s_color}; font-family:'JetBrains Mono',monospace;">
            {fmt(savings, ccy, rates)}</b>
        </span>
        <span style="color:#8892AA; font-size:0.85rem;">
            Taux : <b style="color:{s_color}; font-family:'JetBrains Mono',monospace;
            font-size:1.1rem;">{s_rate:.1f}%</b>
        </span>
    </div>
    """, unsafe_allow_html=True)

    submitted = st.form_submit_button(
        f"💾  {'Mettre à jour' if existing else 'Enregistrer'} — {selected_label}"
    )
    if submitted:
        try:
            actual = upsert_finance_entry(
                month_key, income, rent, food, transport, misc,
                inv_etf, inv_crypto, inv_other, note
            )
            if actual >= 0:
                st.success(f"✓ {selected_label} enregistré — Épargne nette : {fmt(actual, ccy, rates)}")
            else:
                st.error(f"⚠ Déficit de {fmt(abs(actual), ccy, rates)} ce mois !")
        except Exception as e:
            st.error(f"Erreur : {e}")

# ── Settings ─────────────────────────────────────────────────────────────────
st.divider()
with st.expander("⚙  Paramètres globaux", expanded=False):
    col_gs1, col_gs2 = st.columns(2)
    with col_gs1:
        new_budget = st.number_input("Revenu mensuel de référence (€)",
                                      value=float(get_setting("monthly_budget", "1250")), step=50.0)
    with col_gs2:
        new_goal = st.number_input("Objectif épargne Fortress (€)",
                                    value=float(get_setting("savings_goal", "2000")), step=100.0)
    if st.button("Sauvegarder paramètres"):
        set_setting("monthly_budget", new_budget)
        set_setting("savings_goal", new_goal)
        st.success("✓ Paramètres mis à jour.")

# ── Analytics ─────────────────────────────────────────────────────────────────
st.divider()
sub_label("Historique & Analytics")

finances = get_finances()
if finances:
    df = pd.DataFrame(finances)
    df["total_expense"] = df["rent"] + df["food"] + df["transport"] + df["misc"]
    for c in ["investments_etf", "investments_crypto", "investments_other"]:
        if c not in df.columns:
            df[c] = 0.0
    df["total_invest"] = df["investments_etf"] + df["investments_crypto"] + df["investments_other"]
    df_sorted = df.sort_values("month_key")

    # Summary metrics
    sm1, sm2, sm3, sm4 = st.columns(4)
    sm1.metric("Revenu moyen",        fmt(df["income"].mean(), ccy, rates))
    sm2.metric("Dépenses moyennes",   fmt(df["total_expense"].mean(), ccy, rates))
    sm3.metric("Épargne nette moy.",  fmt(df["savings"].mean(), ccy, rates))
    sm4.metric("Total épargné",       fmt(df["savings"].sum(), ccy, rates))

    st.markdown("<br>", unsafe_allow_html=True)

    # Stacked bar with savings scatter
    fig = go.Figure()
    for name, col, color in [
        ("Loyer",      "rent",         "#1E3A6E"),
        ("Nourriture", "food",         "#1A3355"),
        ("Transport",  "transport",    "#152840"),
        ("Divers",     "misc",         "#112030"),
        ("Invest.",    "total_invest", "#2D1B69"),
    ]:
        if col in df_sorted.columns:
            fig.add_trace(go.Bar(x=df_sorted["month_key"], y=df_sorted[col],
                                  name=name, marker_color=color))

    fig.add_trace(go.Scatter(
        x=df_sorted["month_key"], y=df_sorted["savings"],
        name="Épargne nette", mode="lines+markers+text",
        line=dict(color="#3B82F6", width=2.5),
        marker=dict(size=7, color="#3B82F6"),
        text=df_sorted["savings"].map(lambda x: f"{x:.0f}€"),
        textposition="top center",
        textfont=dict(size=10, color="#60A5FA"),
    ))
    fig.update_layout(
        **plotly_theme(), height=340, barmode="stack",
        margin=dict(t=10, b=50, l=50, r=10),
        yaxis_title=f"Montant ({ccy})",
        legend=dict(x=0.01, y=0.99, font=dict(size=10, family="Inter", color="#8892AA"),
                    bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Editable raw table — click row to jump back to month form
    st.markdown("<br>", unsafe_allow_html=True)
    sub_label("Entrées enregistrées — clic sur une ligne pour la modifier ci-dessus")

    disp = df_sorted[["month_key", "income", "total_expense", "total_invest", "savings"]].copy()
    disp.columns = ["Mois", "Revenu", "Dépenses", "Invest.", "Épargne Nette"]
    if ccy != "EUR":
        r = rates.get(ccy, 1.0)
        for col in ["Revenu", "Dépenses", "Invest.", "Épargne Nette"]:
            disp[col] = (disp[col] * r).map(lambda x: f"{x:,.0f}")
    st.dataframe(disp, use_container_width=True, hide_index=True)
else:
    st.markdown("""
    <div class="monk-card" style="text-align:center; padding:3rem;">
        <div style="font-size:2.5rem; margin-bottom:1rem;">📊</div>
        <div style="font-size:0.85rem; color:#4A5568; line-height:1.8;">
            Aucune donnée. Commence par avril 2026.
        </div>
    </div>
    """, unsafe_allow_html=True)
