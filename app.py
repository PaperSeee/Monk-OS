"""
MONK-OS V3: Life & Wealth OS — CENTRAL DASHBOARD
Home page: aggregates all KPI from LT / MT / CT with navigation buttons.
Each pillar (LT/MT/CT) is a full standalone app accessible via pages.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from db.database import (
    init_db,
    get_setting,
    set_setting,
    get_finances,
    get_lt_capital,
    get_live_portfolio_value,
    get_total_invested_all_time,
    get_risk_crypto_current_value,
    get_prop_challenges,
    get_business_tests,
    get_total_payouts,
    get_risk_investment_totals,
    get_monthly_investment_totals,
    get_fortress_savings_history,
)
from utils.helpers import inject_css, TIMEZONES, CURRENCY_SYMBOLS, get_now_str, fmt, get_fx_rates, render_pillar_top_nav, plotly_theme

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MONK-OS : Life & Wealth OS — Dashboard Central",
    page_icon="assets/monk_favicon.svg",
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
    # Branding — APP LOGO
    if st.button("", key="logo_home", use_container_width=True, help="Retour au dashboard"):
        st.rerun()

    st.markdown('<div style="padding:0.4rem 0 0.2rem 0; border-bottom:1px solid #232836;">', unsafe_allow_html=True)
    st.image("assets/monk_logo.svg", use_container_width=True)
    st.markdown("""
    <div style="text-align:center; padding-bottom:0.45rem;">
        <div style="font-size:0.56rem; color:#5DA8FF; letter-spacing:0.28em;
                    text-transform:uppercase; margin-top:0.3rem; font-weight:700;">
            Life & Wealth OS
        </div>
        <div style="margin-top:0.52rem;">
            <span style="background:#1E3A5F; color:#6BC8FF; padding:0.2rem 0.72rem;
                         border-radius:20px; font-size:0.62rem; font-weight:600;
                         letter-spacing:0.06em;">● LIVE CORE</span>
        </div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

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
render_pillar_top_nav("app")

date_str, time_str = get_now_str(st.session_state.timezone)
r = get_fx_rates() if st.session_state.currency != "EUR" else {"EUR": 1.0}
ccy = st.session_state.currency
ccy_sym = CURRENCY_SYMBOLS.get(ccy, "€")

st.markdown(
    """
    <style>
    .central-kicker {
        font-size: 0.62rem;
        color: #5EA9FF;
        letter-spacing: 0.32em;
        text-transform: uppercase;
        font-weight: 700;
        margin-bottom: 0.55rem;
    }
    .wealth-hero {
        background:
            radial-gradient(circle at 88% 12%, rgba(79, 144, 255, 0.22) 0%, rgba(79, 144, 255, 0.03) 46%, transparent 70%),
            linear-gradient(145deg, rgba(27, 35, 52, 0.96), rgba(16, 22, 35, 0.96));
        border: 1px solid #2E436A;
        border-radius: 14px;
        padding: 1.2rem 1.35rem;
        margin: 0.25rem 0 1rem 0;
        box-shadow: 0 12px 30px rgba(8, 12, 20, 0.35);
    }
    .wealth-hero-title {
        font-size: 0.62rem;
        color: #8CA2C8;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }
    .wealth-hero-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.35rem;
        color: #EFF5FF;
        font-weight: 800;
        letter-spacing: -0.03em;
        line-height: 1.05;
    }
    .wealth-hero-sub {
        margin-top: 0.65rem;
        color: #90A0BE;
        font-size: 0.8rem;
        line-height: 1.5;
    }
    .wealth-ribbon {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.1rem 0 1rem 0;
    }
    .wealth-ribbon-card {
        background: linear-gradient(145deg, rgba(28, 36, 53, 0.95), rgba(18, 25, 39, 0.95));
        border: 1px solid #2A3A59;
        border-radius: 12px;
        padding: 0.8rem 0.9rem;
    }
    .wealth-ribbon-label {
        font-size: 0.56rem;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        color: #7C8DAE;
        margin-bottom: 0.4rem;
    }
    .wealth-ribbon-value {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 800;
        font-size: 0.98rem;
        letter-spacing: -0.02em;
        color: #EEF4FF;
    }
    .central-section-note {
        margin-top: -0.2rem;
        margin-bottom: 0.7rem;
        font-size: 0.78rem;
        color: #6D7F9E;
    }
    .app-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.32rem;
        background: rgba(79, 144, 255, 0.1);
        border: 1px solid #3B82F6;
        border-radius: 999px;
        padding: 0.2rem 0.68rem;
        font-size: 0.66rem;
        color: #74B4FF;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    @media (max-width: 1080px) {
        .wealth-ribbon { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 640px) {
        .wealth-ribbon { grid-template-columns: 1fr; }
        .wealth-hero-value { font-size: 1.8rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

col_title, col_clock = st.columns([3, 1])
with col_title:
    st.markdown("""
    <div style="padding-top:0.5rem;">
    <div class="central-kicker">Fintech Control Surface</div>
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
lt_cash_capital = get_lt_capital()
etf_live_value = get_live_portfolio_value()
etf_invested = get_total_invested_all_time()
etf_gain = etf_live_value - etf_invested
live_crypto_value = get_risk_crypto_current_value()
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

inv_bourse = etf_live_value
inv_crypto = live_crypto_value
inv_immo = float(get_setting("lt_invest_immo", "0"))
total_invest = inv_bourse + inv_crypto + inv_immo
lt_capital = lt_cash_capital + total_invest

# Consolidated wealth: cash + ETF + all risk assets + real estate
patrimoine_total = lt_cash_capital + etf_live_value + float(risk_totals.get("total_current", 0) or 0) + inv_immo
ct_net_budget = total_allocated_budget - total_cash_burn

# ── CENTRAL KPI GRID ────────────────────────────────────────────────────────
st.markdown("""
<div style="font-size:0.62rem; color:#4A5568; letter-spacing:0.2em;
            text-transform:uppercase; margin-bottom:1rem; font-weight:500;">
    ▸ KPI CONSOLIDÉS
</div>
""", unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="wealth-hero">
        <div class="wealth-hero-title">Patrimoine total consolidé</div>
        <div class="wealth-hero-value">{fmt(patrimoine_total, ccy, r)}</div>
        <div class="wealth-hero-sub">
            Base de calcul globale MONK-OS : cash LT + ETF live + actifs risque (CT) + immobilier.
            <span class="app-pill">Live</span>
        </div>
    </div>
    <div class="wealth-ribbon">
        <div class="wealth-ribbon-card">
            <div class="wealth-ribbon-label">Cash LT</div>
            <div class="wealth-ribbon-value">{fmt(lt_cash_capital, ccy, r)}</div>
        </div>
        <div class="wealth-ribbon-card">
            <div class="wealth-ribbon-label">ETF Live</div>
            <div class="wealth-ribbon-value">{fmt(etf_live_value, ccy, r)}</div>
        </div>
        <div class="wealth-ribbon-card">
            <div class="wealth-ribbon-label">Actifs Risque</div>
            <div class="wealth-ribbon-value">{fmt(float(risk_totals.get('total_current', 0) or 0), ccy, r)}</div>
        </div>
        <div class="wealth-ribbon-card">
            <div class="wealth-ribbon-label">Immobilier</div>
            <div class="wealth-ribbon-value">{fmt(inv_immo, ccy, r)}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

kpi_cols = st.columns(6)
kpi_cols[0].metric("🏦 Patrimoine total", fmt(patrimoine_total, ccy, r))
kpi_cols[1].metric("💎 Épargne (Cash)", fmt(lt_cash_capital, ccy, r))
kpi_cols[2].metric("📈 ETF (Live)", fmt(etf_live_value, ccy, r))
etf_delta = f"{'+' if etf_gain >= 0 else ''}{fmt(etf_gain, ccy, r)}"
kpi_cols[3].metric("📊 P&L ETF", etf_delta)
kpi_cols[4].metric("🚀 Funded (MT)", fmt(funded_live, ccy, r))
risk_emoji = "🟢" if risk_totals['gain_loss'] >= 0 else "🔴"
kpi_cols[5].metric(f"{risk_emoji} Risque P&L", fmt(risk_totals['gain_loss'], ccy, r))

st.divider()

# ── WEALTH EVOLUTION ─────────────────────────────────────────────────────────
st.markdown("""
<div style="font-size:0.62rem; color:#4A5568; letter-spacing:0.2em;
            text-transform:uppercase; margin-bottom:1rem; font-weight:500;">
    ▸ ÉVOLUTION DU PATRIMOINE
</div>
""", unsafe_allow_html=True)
st.markdown('<div class="central-section-note">Trajectoire mensuelle consolidée avec variations et intensité des fluctuations.</div>', unsafe_allow_html=True)

finances_hist = get_finances()
invest_hist = get_monthly_investment_totals()
fortress_hist = get_fortress_savings_history()

timeline_data = {}

for row in finances_hist:
    month = row.get("month_key")
    if not month:
        continue
    item = timeline_data.setdefault(month, {"cash_flow": 0.0, "invest": 0.0})
    item["cash_flow"] = float(row.get("savings", 0) or 0)

for row in invest_hist:
    month = row.get("month_key")
    if not month:
        continue
    item = timeline_data.setdefault(month, {"cash_flow": 0.0, "invest": 0.0})
    item["invest"] = float(row.get("total", 0) or 0)

for row in fortress_hist:
    month = row.get("month_key")
    if not month:
        continue
    # Use Fortress monthly savings only when no finance row exists for that month.
    if month not in timeline_data or timeline_data[month].get("cash_flow", 0.0) == 0.0:
        item = timeline_data.setdefault(month, {"cash_flow": 0.0, "invest": 0.0})
        item["cash_flow"] = float(row.get("amount", 0) or 0)

if timeline_data:
    evo = pd.DataFrame(
        [{"month_key": m, **vals} for m, vals in timeline_data.items()]
    ).sort_values("month_key")

    evo["monthly_contribution"] = evo["cash_flow"] + evo["invest"]
    evo["contributions_cum"] = evo["monthly_contribution"].cumsum()

    final_contrib = float(evo["contributions_cum"].iloc[-1]) if not evo.empty else 0.0
    scale = (patrimoine_total / final_contrib) if final_contrib > 0 else 1.0
    evo["patrimoine_estime"] = evo["contributions_cum"] * scale

    if final_contrib <= 0:
        evo["patrimoine_estime"] = 0.0
        evo.loc[evo.index[-1], "patrimoine_estime"] = patrimoine_total

    evo["fluctuation"] = evo["patrimoine_estime"].diff().fillna(evo["patrimoine_estime"])
    evo["fluctuation_color"] = evo["fluctuation"].apply(lambda x: "#22D484" if x >= 0 else "#FF5C5C")

    evo_display = evo.copy()
    if ccy != "EUR":
        rate = r.get(ccy, 1.0)
        for col in ["patrimoine_estime", "contributions_cum", "fluctuation"]:
            evo_display[col] = evo_display[col] * rate

    fig_evo = go.Figure()
    fig_evo.add_trace(go.Bar(
        x=evo_display["month_key"],
        y=evo_display["fluctuation"],
        name="Fluctuation mensuelle",
        marker_color=evo["fluctuation_color"],
        opacity=0.35,
    ))
    fig_evo.add_trace(go.Scatter(
        x=evo_display["month_key"],
        y=evo_display["patrimoine_estime"],
        mode="lines+markers",
        name="Patrimoine (évolution)",
        line=dict(color="#5EA9FF", width=3),
        marker=dict(size=6, color="#5EA9FF"),
        fill="tozeroy",
        fillcolor="rgba(94,169,255,0.10)",
    ))
    fig_evo.add_trace(go.Scatter(
        x=evo_display["month_key"],
        y=evo_display["contributions_cum"],
        mode="lines",
        name="Contributions cumulées",
        line=dict(color="#A78BFA", width=2, dash="dash"),
    ))
    fig_evo.update_layout(
        **plotly_theme(),
        height=390,
        margin=dict(t=10, b=45, l=50, r=10),
        hovermode="x unified",
        yaxis_title=f"Montant ({ccy})",
        xaxis_title="Mois",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.0),
        barmode="relative",
    )
    st.plotly_chart(fig_evo, use_container_width=True)

    fm1, fm2, fm3 = st.columns(3)
    fm1.metric("Variation moyenne / mois", fmt(float(evo["fluctuation"].mean()), ccy, r))
    fm2.metric("Meilleure variation", fmt(float(evo["fluctuation"].max()), ccy, r))
    fm3.metric("Pire variation", fmt(float(evo["fluctuation"].min()), ccy, r))
else:
    st.markdown("""
    <div class="monk-card" style="text-align:center; padding:2rem;">
        <div style="font-size:2rem; margin-bottom:0.6rem;">📉</div>
        <div style="font-size:0.82rem; color:#7F8EAB;">
            Pas assez d'historique pour tracer l'évolution du patrimoine.
            Commence par saisir des données mensuelles dans Fortress/Data Input.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── NAVIGATION CARDS BY PILLAR ───────────────────────────────────────────────
st.markdown("""
<div style="font-size:0.62rem; color:#4A5568; letter-spacing:0.2em;
            text-transform:uppercase; margin-bottom:1rem; font-weight:500;">
    ▸ ACCÉDER AUX APPLICATIONS
</div>
""", unsafe_allow_html=True)
st.markdown('<div class="central-section-note">Navigation rapide entre les piliers pour intervenir directement sur les drivers du patrimoine total.</div>', unsafe_allow_html=True)

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
                Cash: {fmt(lt_cash_capital, ccy, r)} · ETF: {fmt(etf_live_value, ccy, r)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Ouvrir", key="btn_lt", use_container_width=True):
        st.switch_page("pages/2_📈_Equity_Engine.py")

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
- Coût cumulé challenges : {fmt(total_challenge_cost, ccy, r)}

**CT (Laboratoire) → Impacte LT**
- Budgets alloués : optionnellement déduits du capital LT
- Cash burn : tracké et visible dans la synthèse LT
- Budget net CT : {fmt(ct_net_budget, ccy, r)}
"""

st.markdown(flow_text)

st.markdown(f"""
<div style="text-align:center; margin-top:1.5rem;">
    <span class="stat-pill" style="border-color:#3B82F6; color:#3B82F6;">
        Devise active : <strong style="margin-left:0.3rem; font-family:'JetBrains Mono',monospace;">{ccy_sym} {ccy}</strong>
    </span>
</div>
""", unsafe_allow_html=True)
