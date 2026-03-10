"""
Module 1 V2 — FORTRESS ONE
Dashboard: Net Worth, Savings Goal, Monk Mode Countdown — currency-aware, clean layout
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))
from db.database import init_db, get_setting, set_setting, get_latest_portfolio_v2, get_finances
from utils.helpers import inject_css, section_head, sub_label, fmt, get_fx_rates, get_now_str, TIMEZONES

init_db()
inject_css()

ccy     = st.session_state.get("currency", "EUR")
tz_name = st.session_state.get("timezone", "Europe/Brussels")
rates   = get_fx_rates() if ccy != "EUR" else {"EUR": 1.0}

# ── Data ─────────────────────────────────────────────────────────────────────
current_savings = float(get_setting("current_savings", "0"))
savings_goal    = float(get_setting("savings_goal", "2000"))
monk_end_raw    = get_setting("monk_mode_end_date", "2026-04-09")
portfolio_rows  = get_latest_portfolio_v2()
portfolio_value = sum(r["shares"] * r["price"] for r in portfolio_rows)
net_worth       = current_savings + portfolio_value

# ── Header ────────────────────────────────────────────────────────────────────
col_head, col_clock = st.columns([3, 1])
with col_head:
    section_head("MODULE 01 — FORTRESS ONE")
with col_clock:
    date_str, time_str = get_now_str(tz_name)
    tz_label = [k for k, v in TIMEZONES.items() if v == tz_name]
    tz_label = tz_label[0] if tz_label else tz_name
    st.markdown(f"""
    <div class="datetime-widget">
        <div class="datetime-time">{time_str}</div>
        <div class="datetime-date">{date_str}</div>
        <div class="datetime-tz">{tz_label}</div>
    </div>
    """, unsafe_allow_html=True)

# ── NET WORTH HERO ────────────────────────────────────────────────────────────
col_nw, col_status = st.columns([2, 1.2])

with col_nw:
    st.markdown(f"""
    <div class="monk-card">
        <div class="net-worth-label">▸ PATRIMOINE NET</div>
        <div class="net-worth-hero">{fmt(net_worth, ccy, rates)}</div>
        <div class="net-worth-sub">
            <span style="color:#8892AA;">Cash :</span>
            <span style="font-weight:700; font-family:'JetBrains Mono',monospace; color:#10B981;">
                {fmt(current_savings, ccy, rates)}
            </span>
            &nbsp;·&nbsp;
            <span style="color:#8892AA;">ETF :</span>
            <span style="font-weight:700; font-family:'JetBrains Mono',monospace; color:#3B82F6;">
                {fmt(portfolio_value, ccy, rates)}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_status:
    is_secure = current_savings >= savings_goal
    deficit   = savings_goal - current_savings
    badge_cls = "badge-secure" if is_secure else "badge-vulnerable"
    badge_txt = "✓ SÉCURISÉ"  if is_secure else "⚠ VULNÉRABLE"
    status_color = "#10B981" if is_secure else "#EF4444"
    border_color = "#10B981" if is_secure else "#EF4444"

    detail = (
        f"Objectif atteint !<br>"
        f"<span style=\"font-family:'JetBrains Mono',monospace; font-size:0.82rem;\">"
        f"{fmt(current_savings, ccy, rates)} / {fmt(savings_goal, ccy, rates)}</span>"
    ) if is_secure else (
        f"Déficit : <span style=\"font-family:'JetBrains Mono',monospace;\">{fmt(deficit, ccy, rates)}</span><br>"
        f"<span style=\"font-family:'JetBrains Mono',monospace; font-size:0.78rem;\">"
        f"{fmt(current_savings, ccy, rates)} / {fmt(savings_goal, ccy, rates)}</span>"
    )

    st.markdown(f"""
    <div class="monk-card" style="text-align:center; border-color:{border_color};">
        <div style="font-size:0.58rem; color:#4A5568; letter-spacing:0.2em;
                    text-transform:uppercase; margin-bottom:0.8rem; font-weight:500;">
            Statut Fortress
        </div>
        <div class="{badge_cls}">{badge_txt}</div>
        <div style="font-size:0.72rem; color:{status_color}; margin-top:1rem;
                    font-weight:500; line-height:1.8;">
            {detail}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── SAVINGS PROGRESS ─────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
sub_label(f"Progression objectif épargne — {fmt(savings_goal, ccy, rates)}")

progress_val = min(current_savings / savings_goal, 1.0) if savings_goal > 0 else 0
st.progress(progress_val)

cpct, cact, crest = st.columns(3)
cpct.metric("Progression",       f"{progress_val*100:.1f}%")
cact.metric("Épargne actuelle",  fmt(current_savings, ccy, rates))
crest.metric("Restant",          fmt(max(savings_goal - current_savings, 0), ccy, rates))

st.divider()

# ── MONK MODE COUNTDOWN ───────────────────────────────────────────────────────
sub_label("Monk Mode — Compte à rebours")

try:
    monk_end    = date.fromisoformat(monk_end_raw)
    today       = date.today()
    delta_days  = (monk_end - today).days
    is_active   = delta_days >= 0
    display_days = max(delta_days, 0)
    display_hours = display_days * 24
    monk_status  = "ACTIF" if is_active else "TERMINÉ"
except Exception:
    display_days, display_hours = 0, 0
    is_active, monk_status = False, "TERMINÉ"

# Colors for active vs ended
day_color  = "#3B82F6" if is_active else "#4A5568"
stat_color = "#10B981" if is_active else "#EF4444"
badge_stat = "badge-neutral" if is_active else "badge-vulnerable"

c1, c2, c3, c4 = st.columns(4)

c1.markdown(f"""
<div class="countdown-block">
    <div class="countdown-number" style="color:{day_color};">{display_days}</div>
    <div class="countdown-label">JOURS</div>
</div>
""", unsafe_allow_html=True)

c2.markdown(f"""
<div class="countdown-block">
    <div class="countdown-number" style="color:#8892AA; font-size:1.6rem;">{display_hours}</div>
    <div class="countdown-label">HEURES</div>
</div>
""", unsafe_allow_html=True)

c3.markdown(f"""
<div class="countdown-block">
    <div class="countdown-number" style="color:#8892AA; font-size:1.2rem;">
        {monk_end_raw}
    </div>
    <div class="countdown-label" style="margin-top:0.6rem;">DATE DE FIN</div>
</div>
""", unsafe_allow_html=True)

c4.markdown(f"""
<div class="countdown-block">
    <div style="margin-top:0.4rem;">
        <span class="{badge_stat}">{monk_status}</span>
    </div>
    <div class="countdown-label" style="margin-top:0.6rem;">STATUT</div>
</div>
""", unsafe_allow_html=True)

# ── ETF Positions ─────────────────────────────────────────────────────────────
if portfolio_rows and any(r["shares"] > 0 for r in portfolio_rows):
    st.divider()
    sub_label("Détail du portefeuille ETF")
    rows_html = ""
    for r in portfolio_rows:
        if r["shares"] > 0:
            val = r["shares"] * r["price"]
            pct = val / portfolio_value * 100 if portfolio_value > 0 else 0
            rows_html += f"""
            <div class="info-row">
                <span class="info-key" style="font-family:'JetBrains Mono',monospace; color:#F0F4FF;">{r['ticker']}</span>
                <span style="font-size:0.78rem; color:#8892AA;">
                    {r['shares']:.2f} parts ×
                    <span style="font-family:'JetBrains Mono',monospace;">{fmt(r['price'], ccy, rates)}</span>
                </span>
                <span style="font-family:'JetBrains Mono',monospace; font-weight:700; color:#3B82F6;">
                    {fmt(val, ccy, rates)} <span style="color:#4A5568; font-size:0.72rem;">({pct:.1f}%)</span>
                </span>
            </div>"""
    if rows_html:
        st.markdown(f"""
        <div class="monk-card"><div class="monk-card-title">Positions actives</div>{rows_html}</div>
        """, unsafe_allow_html=True)

# ── Finances History ──────────────────────────────────────────────────────────
finances = get_finances()
if finances:
    import pandas as pd
    st.divider()
    sub_label("Historique financier")
    df = pd.DataFrame(finances).sort_values("month_key")
    show_cols = ["month_key","income","rent","food","transport","misc","savings"]
    show_cols = [c for c in show_cols if c in df.columns]
    disp = df[show_cols].copy()
    if ccy != "EUR":
        r = rates.get(ccy, 1.0)
        for col in ["income","rent","food","transport","misc","savings"]:
            if col in disp.columns:
                disp[col] = (disp[col] * r).map(lambda x: f"{x:,.0f}")
    disp.columns = ["Mois","Revenu","Loyer","Nourriture","Transport","Divers","Épargne Nette"][:len(disp.columns)]
    st.dataframe(disp, use_container_width=True, hide_index=True)

# ── Settings ─────────────────────────────────────────────────────────────────
st.divider()
with st.expander("⚙  Paramètres Fortress", expanded=False):
    cs1, cs2 = st.columns(2)
    with cs1:
        new_goal = st.number_input("Objectif épargne (€)", min_value=0.0,
                                    value=savings_goal, step=100.0)
    with cs2:
        try:
            current_end = date.fromisoformat(monk_end_raw)
        except Exception:
            current_end = date(2026, 4, 9)
        new_end = st.date_input("Date fin Monk Mode", value=current_end)
    manual_sav = st.number_input("Épargne actuelle (€) — Override manuel",
                                  min_value=0.0, value=current_savings, step=50.0)
    if st.button("💾  Sauvegarder"):
        set_setting("savings_goal", new_goal)
        set_setting("monk_mode_end_date", new_end.isoformat())
        set_setting("current_savings", manual_sav)
        st.success("✓ Paramètres sauvegardés.")
        st.rerun()
