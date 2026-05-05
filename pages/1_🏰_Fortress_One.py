"""
Module 1 V2 — FORTRESS ONE
Dashboard: Net Worth, Savings Goal, Monk Mode Countdown — currency-aware, clean layout
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))
from db.database import (
    init_db,
    get_setting,
    set_setting,
    get_latest_portfolio_v2,
    get_finances,
    get_lt_capital,
    set_lt_capital,
    get_fortress_savings_for_month,
    get_fortress_savings_history,
    upsert_fortress_saving,
    delete_fortress_saving,
)
from utils.helpers import inject_css, section_head, sub_label, fmt, get_fx_rates, get_now_str, TIMEZONES, render_long_term_sidebar_nav

st.set_page_config(
    page_title="MONK-OS : Fortress One",
    page_icon="assets/monk_favicon.svg",
    layout="wide",
)

init_db()
inject_css()
render_long_term_sidebar_nav("fortress")

ccy     = st.session_state.get("currency", "EUR")
tz_name = st.session_state.get("timezone", "Europe/Brussels")
rates   = get_fx_rates() if ccy != "EUR" else {"EUR": 1.0}

st.markdown(
    """
    <style>
    .fortress-kicker {
        font-size: 0.62rem;
        letter-spacing: 0.28em;
        text-transform: uppercase;
        color: #5DA8FF;
        font-weight: 700;
        margin: 0.1rem 0 0.55rem 0;
    }
    .fortress-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.15rem 0 1rem 0;
    }
    .fortress-strip-card {
        background: linear-gradient(145deg, rgba(29, 39, 61, 0.95), rgba(19, 26, 42, 0.95));
        border: 1px solid #2A3A59;
        border-radius: 12px;
        padding: 0.85rem 0.95rem;
        box-shadow: inset 0 1px 0 rgba(93,168,255,0.08), 0 8px 24px rgba(8, 12, 20, 0.32);
    }
    .fortress-strip-label {
        font-size: 0.58rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #7C8BA7;
        margin-bottom: 0.45rem;
    }
    .fortress-strip-value {
        font-size: 1rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #EEF5FF;
        font-family: 'JetBrains Mono', monospace;
    }
    .fortress-hero-card {
        background:
            radial-gradient(circle at 90% 8%, rgba(79, 144, 255, 0.22) 0%, rgba(79, 144, 255, 0.02) 44%, transparent 66%),
            linear-gradient(145deg, rgba(28, 35, 51, 0.95), rgba(17, 23, 36, 0.95));
        border-color: #2E436A !important;
        box-shadow: 0 12px 30px rgba(9, 15, 26, 0.32);
    }
    .fortress-status-card {
        background:
            radial-gradient(circle at 10% 8%, rgba(52, 211, 153, 0.16) 0%, rgba(52, 211, 153, 0.02) 42%, transparent 65%),
            linear-gradient(145deg, rgba(28, 35, 51, 0.96), rgba(17, 23, 36, 0.96));
        box-shadow: 0 10px 28px rgba(8, 12, 20, 0.34);
    }
    .fortress-section-note {
        margin-top: -0.3rem;
        margin-bottom: 0.65rem;
        color: #6E7D9B;
        font-size: 0.78rem;
        line-height: 1.45;
    }
    .fortress-glow-divider {
        width: 92px;
        height: 3px;
        border-radius: 3px;
        background: linear-gradient(90deg, rgba(93,168,255,0.0), rgba(93,168,255,0.95), rgba(93,168,255,0.0));
        margin: 0.55rem 0 0.95rem 0;
    }
    .fortress-focus {
        border: 1px solid #2A3A59;
        border-radius: 12px;
        background: linear-gradient(145deg, rgba(26, 33, 49, 0.92), rgba(17, 24, 38, 0.92));
        padding: 0.7rem 0.9rem;
        margin: 0.2rem 0 1rem 0;
    }
    .fortress-focus-title {
        font-size: 0.62rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #8FA3C6;
        font-weight: 600;
        margin-bottom: 0.35rem;
    }
    .fortress-focus-desc {
        font-size: 0.8rem;
        color: #A5B2CB;
        line-height: 1.45;
    }
    @media (max-width: 1080px) {
        .fortress-strip {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
    @media (max-width: 640px) {
        .fortress-strip {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Data ─────────────────────────────────────────────────────────────────────
current_savings = get_lt_capital()
savings_goal    = float(get_setting("savings_goal", "2000"))
monk_end_raw    = get_setting("monk_mode_end_date", "2026-04-09")
portfolio_rows  = get_latest_portfolio_v2()
portfolio_value = sum(r["shares"] * r["price"] for r in portfolio_rows)
net_worth       = current_savings + portfolio_value
goal_remaining  = max(savings_goal - current_savings, 0)
goal_ratio      = (current_savings / savings_goal * 100) if savings_goal > 0 else 0

# ── Header ────────────────────────────────────────────────────────────────────
col_head, col_clock = st.columns([3, 1])
with col_head:
    section_head("MODULE 01 — FORTRESS ONE")
    st.markdown('<div class="fortress-kicker">Fintech Wealth Command Center</div>', unsafe_allow_html=True)
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

st.markdown(
    f"""
    <div class="fortress-strip">
        <div class="fortress-strip-card">
            <div class="fortress-strip-label">Net Worth</div>
            <div class="fortress-strip-value">{fmt(net_worth, ccy, rates)}</div>
        </div>
        <div class="fortress-strip-card">
            <div class="fortress-strip-label">Objectif Fortress</div>
            <div class="fortress-strip-value">{fmt(savings_goal, ccy, rates)}</div>
        </div>
        <div class="fortress-strip-card">
            <div class="fortress-strip-label">Restant</div>
            <div class="fortress-strip-value">{fmt(goal_remaining, ccy, rates)}</div>
        </div>
        <div class="fortress-strip-card">
            <div class="fortress-strip-label">Progression</div>
            <div class="fortress-strip-value">{goal_ratio:.1f}%</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── NET WORTH HERO ────────────────────────────────────────────────────────────
col_nw, col_status = st.columns([2, 1.2])

with col_nw:
    st.markdown(f"""
    <div class="monk-card fortress-hero-card">
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
    <div class="monk-card fortress-status-card" style="text-align:center; border-color:{border_color};">
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
st.markdown('<div class="fortress-glow-divider"></div>', unsafe_allow_html=True)

# Ensure progress value is always between 0.0 and 1.0
try:
    raw_progress = (current_savings / savings_goal) if savings_goal and float(savings_goal) != 0 else 0.0
    progress_val = max(0.0, min(float(raw_progress), 1.0))
except Exception:
    progress_val = 0.0
st.progress(progress_val)

cpct, cact, crest = st.columns(3)
cpct.metric("Progression",       f"{progress_val*100:.1f}%")
cact.metric("Épargne actuelle",  fmt(current_savings, ccy, rates))
crest.metric("Restant",          fmt(max(savings_goal - current_savings, 0), ccy, rates))

st.divider()

# ── MONK MODE COUNTDOWN ───────────────────────────────────────────────────────
sub_label("Monk Mode — Compte à rebours")
st.markdown('<div class="fortress-section-note">Rythme d\'exécution et discipline temporelle de ton plan d\'accumulation.</div>', unsafe_allow_html=True)

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
    st.markdown('<div class="fortress-section-note">Vue consolidée de tes positions, pondérations et valorisation instantanée.</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="fortress-section-note">Lecture chronologique des flux mensuels pour piloter les arbitrages cash/investissement.</div>', unsafe_allow_html=True)
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

# ── Fortress Monthly Savings Input & History ────────────────────────────────
st.divider()
sub_label("Fortress One — Épargne mensuelle")
st.markdown(
    """
    <div class="fortress-focus">
        <div class="fortress-focus-title">Journal de capitalisation</div>
        <div class="fortress-focus-desc">
            Saisis ton effort d'épargne mensuel pour alimenter le capital LT automatiquement.
            Chaque modification met à jour le dashboard central en temps réel.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

month_col = st.columns([1.2, 1.2, 1])[0]
selected_month = month_col.date_input(
    "Mois concerné",
    value=date.today().replace(day=1),
    format="YYYY-MM-DD",
)
selected_month_key = selected_month.strftime("%Y-%m")
existing_month = get_fortress_savings_for_month(selected_month_key)

with st.form("fortress_monthly_savings_form", clear_on_submit=False):
    amount_col, note_col, action_col = st.columns([1.2, 1.8, 1])
    monthly_amount = amount_col.number_input(
        "Montant épargné ce mois (€)",
        min_value=0.0,
        value=float(existing_month["amount"]) if existing_month else 0.0,
        step=10.0,
    )
    monthly_note = note_col.text_input(
        "Note",
        value=existing_month["note"] if existing_month else "",
        placeholder="Ex: Avril 2026 — effort supplémentaire",
    )
    with action_col:
        st.markdown("<div style='height:1.7rem;'></div>", unsafe_allow_html=True)
        save_btn = st.form_submit_button(
        "💾 Enregistrer",
        use_container_width=True,
        )

if save_btn:
    new_capital = upsert_fortress_saving(selected_month_key, monthly_amount, monthly_note)
    st.success(
        f"✓ Épargne du mois {selected_month_key} enregistrée. Capital LT: {fmt(new_capital, ccy, rates)}"
    )
    st.rerun()

if existing_month:
    del_col1, del_col2 = st.columns([1.5, 3])
    with del_col1:
        if st.button("🗑 Supprimer ce mois", type="secondary", use_container_width=True):
            new_capital = delete_fortress_saving(selected_month_key)
            st.success(
                f"✓ Entrée {selected_month_key} supprimée. Capital LT: {fmt(new_capital, ccy, rates)}"
            )
            st.rerun()

history = get_fortress_savings_history()
if history:
    import pandas as pd

    h1, h2 = st.columns(2)
    total_saved = sum(float(row.get("amount", 0) or 0) for row in history)
    h1.metric("Total épargné (historique Fortress)", fmt(total_saved, ccy, rates))
    h2.metric("Nombre de mois saisis", str(len(history)))

    hdf = pd.DataFrame(history)
    hdf = hdf.sort_values("month_key", ascending=False)
    disp_hist = hdf[["month_key", "amount", "note"]].copy()
    # Keep raw numeric values for editor; format only for display when needed
    disp_hist.columns = ["Mois", "Épargne", "Note"]
    try:
        edited = st.data_editor(disp_hist, use_container_width=True, hide_index=True, num_rows="fixed", key="fortress_editor")
    except Exception:
        # Fallback to non-editable dataframe if st.data_editor not available
        st.dataframe(disp_hist, use_container_width=True, hide_index=True)
        edited = None

    if edited is not None:
        if st.button("💾 Appliquer modifications", key="fortress_apply_changes"):
            # Build lookup of original months
            orig_months = {row["month_key"]: row for row in history}
            edited_rows = edited.to_dict(orient="records")
            edited_months = set()

            def parse_amount(v):
                try:
                    # handle strings with commas or currency symbols
                    s = str(v)
                    for ch in ["€", ",", "\u202f", " "]:
                        s = s.replace(ch, "")
                    return float(s) if s not in ("", "None", "nan") else 0.0
                except Exception:
                    return 0.0

            for r in edited_rows:
                mk = r.get("Mois")
                if not mk:
                    continue
                amount = parse_amount(r.get("Épargne", 0))
                note = r.get("Note", "") or ""
                upsert_fortress_saving(mk, amount, note)
                edited_months.add(mk)

            # Delete months removed by the user
            for orig in orig_months:
                if orig not in edited_months:
                    delete_fortress_saving(orig)

            st.success("✓ Modifications appliquées.")
            st.rerun()
else:
    st.info("Aucune épargne mensuelle saisie dans Fortress One pour le moment.")

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
        set_lt_capital(manual_sav)
        st.success("✓ Paramètres sauvegardés.")
        st.rerun()
