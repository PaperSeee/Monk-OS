"""
Module 2 — EQUITY ENGINE V2
Dynamic multi-ETF tracking, smart rebalancing, lock system, dividend tracker
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import (
    init_db, get_latest_portfolio_v2, save_portfolio_v2, get_setting,
    save_monthly_investment, get_monthly_investments, get_monthly_investment_totals,
    get_total_invested_all_time, delete_monthly_investment,
    get_finances, get_fortress_savings_history, get_risk_investment_totals,
)
from utils.helpers import (
    inject_css, section_head, sub_label, plotly_theme,
    ETF_CATALOG, ETF_YIELD, fmt, get_fx_rates, render_long_term_sidebar_nav,
)

st.set_page_config(
    page_title="MONK-OS : Equity Engine",
    page_icon="📈",
    layout="wide",
)

init_db()
inject_css()
render_long_term_sidebar_nav("equity")

import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np

section_head("MODULE 02 — EQUITY ENGINE V2")

# ── Session state: currency & FX ─────────────────────────────────────────────
ccy     = st.session_state.get("currency", "EUR")
with st.spinner("Chargement des taux de change…") if ccy != "EUR" else st.empty():
    rates = get_fx_rates() if ccy != "EUR" else {"EUR": 1.0}

# ── Monthly investment amount (TOP) ───────────────────────────────────────────
col_amt, col_spacer = st.columns([1, 2])
with col_amt:
    invest_amount_eur = st.number_input(
        "💰 Montant mensuel à investir (€)", min_value=0.0, value=250.0, step=25.0,
        help="Ton DCA mensuel — le montant est réparti automatiquement selon tes % cibles"
    )

# ── Lock System ──────────────────────────────────────────────────────────────
current_savings = float(get_setting("current_savings", "0"))
savings_goal    = float(get_setting("savings_goal", "2000"))
is_locked       = current_savings < savings_goal

if is_locked:
    st.markdown(f"""
    <div class="lock-overlay" style="margin-bottom:1.5rem;">
        <div style="font-size:1.5rem; margin-bottom:0.5rem;">🔒</div>
        <div style="font-size:0.85rem; font-weight:700; color:#F59E0B;
                    font-family:'JetBrains Mono',monospace; letter-spacing:0.06em;">
            FORTRESS NON SÉCURISÉE
        </div>
        <div style="font-size:0.78rem; color:#8892AA; margin-top:0.4rem; line-height:1.6;">
            Focus sur ta Forteresse, CEO.<br>
            Épargne :
            <span style="color:#EF4444; font-family:'JetBrains Mono',monospace; font-weight:600;">
                {fmt(current_savings, ccy, rates)}
            </span>
            / objectif
            <span style="color:#F0F4FF; font-family:'JetBrains Mono',monospace; font-weight:600;">
                {fmt(savings_goal, ccy, rates)}
            </span>
        </div>
        <div style="font-size:0.7rem; color:#4A5568; margin-top:0.6rem;">
            Le calculateur de rééquilibrage sera débloqué une fois l'objectif atteint.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Price fetch (cached) ──────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_price(ticker: str) -> float | None:
    try:
        t    = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None

@st.cache_data(ttl=3600)
def fetch_history_multi(tickers: list) -> dict:
    data = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="3mo")
            if not hist.empty:
                data[t] = hist["Close"]
        except Exception:
            pass
    return data

# ── ETF Row State ─────────────────────────────────────────────────────────────
if "etf_rows" not in st.session_state:
    saved = get_latest_portfolio_v2()
    if saved:
        st.session_state.etf_rows = [
            {"ticker": r["ticker"], "shares": r["shares"], "target_pct": r["target_pct"]}
            for r in saved
        ]
    else:
        st.session_state.etf_rows = [
            {"ticker": "SXR8.DE", "shares": 0.0, "target_pct": 55.0},
            {"ticker": "IUSN.DE", "shares": 0.0, "target_pct": 20.0},
            {"ticker": "IS3N.DE", "shares": 0.0, "target_pct": 15.0},
            {"ticker": "MEUD.PA", "shares": 0.0, "target_pct": 10.0},
        ]

# ── ETF SELECTOR ─────────────────────────────────────────────────────────────
sub_label("Mon allocation — Portefeuille Multi-ETF")

all_tickers = list(ETF_CATALOG.keys())
ticker_labels = [f"{k} — {v}" for k, v in ETF_CATALOG.items()]

# Column headers
st.markdown("""
<div style="display:flex; gap:0; font-size:0.6rem; color:#4A5568;
            letter-spacing:0.1em; text-transform:uppercase; padding:0 0.2rem; margin-bottom:0.3rem;">
    <span style="flex:2.8;">Ticker / ETF</span>
    <span style="flex:1;">Cible %</span>
    <span style="flex:1.2;">Prix / part</span>
    <span style="flex:1.2;">À investir</span>
    <span style="flex:1.2;">Parts à acheter</span>
</div>
""", unsafe_allow_html=True)

rows_to_delete = []
prices_cache   = {}
palette = ["#3B82F6","#10B981","#8B5CF6","#F59E0B","#EF4444",
           "#06B6D4","#EC4899","#84CC16","#F97316","#A78BFA"]

for i, row in enumerate(st.session_state.etf_rows):
    with st.container():
        col_t, col_pct, col_price, col_buy, col_parts, col_del = st.columns([2.8, 1, 1.2, 1.2, 1.2, 0.4])

        with col_t:
            options_display = ticker_labels if row["ticker"] in all_tickers else [f"{row['ticker']} — Custom"] + ticker_labels
            chosen_label    = st.selectbox(
                f"ETF {i+1}",
                options=options_display,
                index=0 if row["ticker"] not in all_tickers else all_tickers.index(row["ticker"]),
                key=f"etf_select_{i}",
                label_visibility="collapsed",
            )
            new_ticker = chosen_label.split(" — ")[0].strip()
            if new_ticker != row["ticker"]:
                st.session_state.etf_rows[i]["ticker"] = new_ticker

        with col_pct:
            new_pct = st.number_input(
                "Cible %", min_value=0.0, max_value=100.0,
                value=float(row["target_pct"]), step=5.0, format="%.1f",
                key=f"pct_{i}", label_visibility="collapsed",
            )
            st.session_state.etf_rows[i]["target_pct"] = new_pct

        ticker   = st.session_state.etf_rows[i]["ticker"]
        price_eur = fetch_price(ticker) or 0.0
        prices_cache[ticker] = price_eur
        price_display = fmt(price_eur, ccy, rates) if price_eur else "N/A"

        buy_eur = invest_amount_eur * (new_pct / 100)
        buy_parts = buy_eur / price_eur if price_eur > 0 else 0

        with col_price:
            st.markdown(
                f'<div style="padding-top:0.9rem;font-size:0.85rem;font-weight:600;'
                f'color:#F0F4FF;font-family:JetBrains Mono,monospace;">{price_display}</div>',
                unsafe_allow_html=True,
            )

        with col_buy:
            st.markdown(
                f'<div style="padding-top:0.9rem;font-size:0.88rem;font-weight:700;'
                f'color:#3B82F6;font-family:JetBrains Mono,monospace;">{fmt(buy_eur, ccy, rates)}</div>',
                unsafe_allow_html=True,
            )

        with col_parts:
            # Editable current parts/shares held (reflects real holdings)
            current_shares = st.number_input(
                "Parts détenues", min_value=0.0, value=float(row.get("shares", 0.0)), step=0.0001, format="%.4f", key=f"shares_{i}", label_visibility="collapsed"
            )
            st.session_state.etf_rows[i]["shares"] = float(current_shares)
            # Show calculated parts to buy for this month
            st.markdown(
                f'<div style="padding-top:0.45rem;font-size:0.75rem;color:#10B981;font-family:JetBrains Mono,monospace;">Acheter: {buy_parts:.4f} parts</div>',
                unsafe_allow_html=True,
            )

        with col_del:
            st.markdown("<div style='padding-top:0.5rem;'></div>", unsafe_allow_html=True)
            if st.button("✕", key=f"del_{i}", help="Supprimer cette ligne"):
                rows_to_delete.append(i)

# Apply deletions
for idx in sorted(rows_to_delete, reverse=True):
    del st.session_state.etf_rows[idx]
if rows_to_delete:
    st.rerun()

# ── Buttons: Add ETF + Save ───────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
col_add, col_save, col_refresh, col_spacer2 = st.columns([1, 1, 1, 2])

with col_add:
    if st.button("➕  Ajouter un ETF"):
        st.session_state.etf_rows.append({"ticker": "IWDA.AS", "shares": 0.0, "target_pct": 0.0})
        st.rerun()

with col_save:
    if st.button("💾  Sauvegarder"):
        db_rows = [
            {"ticker": r["ticker"],
             "shares": r.get("shares", 0),
             "price": prices_cache.get(r["ticker"], 0),
             "target_pct": r["target_pct"]}
            for r in st.session_state.etf_rows
        ]
        save_portfolio_v2(db_rows)
        st.success("✓ Positions sauvegardées.")

with col_refresh:
    if st.button("↻  Refresh prix"):
        st.cache_data.clear()
        st.rerun()

# ── Allocation Validation ─────────────────────────────────────────────────────
total_target = sum(r["target_pct"] for r in st.session_state.etf_rows)
if abs(total_target - 100) > 0.1:
    st.warning(f"⚠ L'allocation cible totalise **{total_target:.1f}%** (doit être 100%). Ajuste tes %, CEO.")
else:
    st.markdown(
        f'<div style="font-size:0.72rem;color:#10B981;font-weight:500;margin-top:0.3rem;">'
        f'✓ Allocation validée : {total_target:.1f}%</div>',
        unsafe_allow_html=True,
    )

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  SYNTHÈSE DE L'ALLOCATION
# ══════════════════════════════════════════════════════════════════════════════
sub_label("Synthèse de l'allocation mensuelle")

total_eur = invest_amount_eur

if total_eur > 0:
    col_donut, col_summary = st.columns([1.3, 1])

    with col_donut:
        chart_labels, chart_values, chart_colors = [], [], []
        for idx, r in enumerate(st.session_state.etf_rows):
            alloc = total_eur * (r["target_pct"] / 100)
            if alloc > 0:
                chart_labels.append(r["ticker"])
                chart_values.append(alloc)
                chart_colors.append(palette[idx % len(palette)])

        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=chart_labels, values=chart_values,
            hole=0.60,
            marker=dict(colors=chart_colors, line=dict(color="#161A22", width=3)),
            textfont=dict(family="Inter", size=11, color="#F0F4FF"),
            texttemplate="%{label}<br><b>%{percent}</b>",
            textposition="outside",
            showlegend=True,
        ))
        fig.update_layout(
            **plotly_theme(),
            margin=dict(t=20, b=30, l=20, r=20), height=320,
            legend=dict(font=dict(family="Inter", size=10, color="#8892AA"),
                        bgcolor="rgba(0,0,0,0)",
                        x=0.5, y=-0.18, xanchor="center", orientation="h"),
            annotations=[dict(
                text=f"<b>{fmt(total_eur, ccy, rates)}</b><br><span style='font-size:10px;color:#4A5568'>/ mois</span>",
                x=0.5, y=0.5,
                font=dict(size=16, color="#F0F4FF", family="JetBrains Mono"),
                showarrow=False
            )],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_summary:
        st.markdown("<br>", unsafe_allow_html=True)
        rows_html = ""
        for r in st.session_state.etf_rows:
            tk = r["ticker"]
            pct = r["target_pct"]
            alloc = total_eur * (pct / 100)
            pr = prices_cache.get(tk, 0)
            pts = alloc / pr if pr > 0 else 0
            rows_html += (
                '<div class="info-row">'
                '<span class="info-key">'
                '<span style="color:#F0F4FF;">' + tk + '</span>'
                '<span style="color:#4A5568;font-size:0.65rem;margin-left:0.3rem;">(' + f'{pct:.0f}' + '%)</span>'
                '</span>'
                '<span style="font-size:0.78rem;font-family:JetBrains Mono,monospace;">'
                '<span style="color:#3B82F6;font-weight:700;">' + fmt(alloc, ccy, rates) + '</span>'
                '<span style="color:#4A5568;font-size:0.68rem;margin-left:0.3rem;"> · ' + f'{pts:.4f}' + ' parts</span>'
                '</span>'
                '</div>'
            )

        card_html = (
            '<div class="monk-card">'
            '<div class="monk-card-title">Répartition mensuelle</div>'
            + rows_html +
            '<div class="info-row" style="margin-top:0.5rem;border-top:1px solid #232836;padding-top:0.5rem;">'
            '<span class="info-key">Total mensuel</span>'
            '<span class="info-value" style="color:#10B981;">' + fmt(total_eur, ccy, rates) + '</span>'
            '</div></div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  ETF RECAP CARDS — Prix live & investissement
# ══════════════════════════════════════════════════════════════════════════════
sub_label("Récap par ETF — Prix live & investissement mensuel")

etf_cols = st.columns(len(st.session_state.etf_rows))
for idx, r in enumerate(st.session_state.etf_rows):
    tk = r["ticker"]
    pct = r["target_pct"]
    price = prices_cache.get(tk, 0)
    alloc = total_eur * (pct / 100)
    parts = alloc / price if price > 0 else 0
    name = ETF_CATALOG.get(tk, tk)
    color = palette[idx % len(palette)]

    with etf_cols[idx]:
        st.markdown(
            '<div style="background:#1A1F2E;border-radius:12px;padding:1rem;border-left:3px solid ' + color + ';">'
            '<div style="font-size:0.9rem;font-weight:700;color:#F0F4FF;font-family:JetBrains Mono,monospace;">' + tk + '</div>'
            '<div style="font-size:0.62rem;color:#4A5568;margin-top:0.15rem;line-height:1.4;">' + name + '</div>'
            '<div style="margin-top:0.8rem;">'
            '<div style="font-size:0.6rem;color:#4A5568;text-transform:uppercase;letter-spacing:0.1em;">Prix live</div>'
            '<div style="font-size:1.1rem;font-weight:700;color:#F0F4FF;font-family:JetBrains Mono,monospace;">' + fmt(price, ccy, rates) + '</div>'
            '</div>'
            '<div style="margin-top:0.6rem;">'
            '<div style="font-size:0.6rem;color:#4A5568;text-transform:uppercase;letter-spacing:0.1em;">Allocation (' + f'{pct:.0f}' + '%)</div>'
            '<div style="font-size:0.95rem;font-weight:700;color:' + color + ';font-family:JetBrains Mono,monospace;">' + fmt(alloc, ccy, rates) + '</div>'
            '<div style="font-size:0.72rem;color:#8892AA;font-family:JetBrains Mono,monospace;">' + f'{parts:.4f}' + ' parts</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  PERFORMANCE 3 MOIS
# ══════════════════════════════════════════════════════════════════════════════
active_tickers = list({r["ticker"] for r in st.session_state.etf_rows if prices_cache.get(r["ticker"])})
if active_tickers:
    sub_label("Performance 3 mois (base 100)")
    hist_data = fetch_history_multi(tuple(active_tickers))
    if hist_data:
        fig2 = go.Figure()
        for i, (ticker, series) in enumerate(hist_data.items()):
            norm = series / series.iloc[0] * 100
            fig2.add_trace(go.Scatter(
                x=series.index, y=norm, name=ticker,
                line=dict(color=palette[i % len(palette)], width=2),
                hovertemplate=f"<b>{ticker}</b><br>Base 100 : %{{y:.1f}}<extra></extra>",
            ))
        fig2.add_hline(y=100, line=dict(color="#232836", width=1, dash="dot"))
        fig2.update_layout(
            **plotly_theme(), height=300,
            margin=dict(t=10, b=40, l=40, r=10),
            yaxis_title="Base 100", hovermode="x unified",
            legend=dict(x=0.02, y=0.98, font=dict(size=10, family="Inter", color="#8892AA"),
                        bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  PROJECTION MULTI-SCÉNARIOS
# ══════════════════════════════════════════════════════════════════════════════
sub_label("Projection — Combien vaudra ton portefeuille ?")

col_years, _ = st.columns([1, 2])
with col_years:
    projection_years = st.slider("Horizon (années)", min_value=1, max_value=30, value=10, step=1)
    include_dca = st.checkbox("Inclure investissements mensuels (DCA)", value=False, help="Si activé, les montants mensuels saisis seront ajoutés au portefeuille chaque mois")

# monthly_invest only applied when DCA is enabled — otherwise projections start from current value only
monthly_invest = total_eur if include_dca else 0.0
scenarios = {
    "Pessimiste (4%/an)": 0.04,
    "Modéré (7%/an)": 0.07,
    "Optimiste (10%/an)": 0.10,
}
scenario_colors = {"Pessimiste (4%/an)": "#EF4444", "Modéré (7%/an)": "#F59E0B", "Optimiste (10%/an)": "#10B981"}

# Compute starting capital from current holdings
starting_value = 0.0
for r in st.session_state.etf_rows:
    tk = r.get("ticker")
    pr = prices_cache.get(tk, 0) or 0
    shares = float(r.get("shares", 0) or 0)
    starting_value += shares * pr

# Only render projection if there is a meaningful starting capital or monthly contributions
if starting_value > 0 or monthly_invest > 0:
    fig3 = go.Figure()
    final_values = {}
    months = projection_years * 12

    for sc_name, annual_rate in scenarios.items():
        monthly_rate = (1 + annual_rate) ** (1/12) - 1
        values = []
        cumul = starting_value
        for m in range(months + 1):
            if m > 0:
                cumul = (cumul + monthly_invest) * (1 + monthly_rate)
            values.append(cumul)

        years_axis = [m / 12 for m in range(months + 1)]
        final_values[sc_name] = values[-1]

        fig3.add_trace(go.Scatter(
            x=years_axis, y=values, name=sc_name,
            line=dict(color=scenario_colors[sc_name], width=2),
            hovertemplate="<b>" + sc_name + "</b><br>Année %{x:.1f}<br>Valeur: %{y:,.0f}€<extra></extra>",
        ))

    # Capital investi line (inclut starting capital)
    invested_vals = [starting_value + monthly_invest * m for m in range(months + 1)]
    fig3.add_trace(go.Scatter(
        x=[m / 12 for m in range(months + 1)], y=invested_vals,
        name="Capital investi",
        line=dict(color="#4A5568", width=1, dash="dash"),
        hovertemplate="<b>Capital investi</b><br>%{y:,.0f}€<extra></extra>",
    ))

    fig3.update_layout(
        **plotly_theme(), height=350,
        margin=dict(t=10, b=40, l=50, r=10),
        yaxis_title="Valeur (€)", xaxis_title="Années",
        hovermode="x unified",
        legend=dict(x=0.02, y=0.98, font=dict(size=10, family="Inter", color="#8892AA"),
                    bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig3, use_container_width=True)

    # Scenario summary cards
    total_invested_final = starting_value + monthly_invest * months
    sc_cols = st.columns(3)
    for idx_s, (sc_name, sc_val) in enumerate(final_values.items()):
        gain = sc_val - total_invested_final
        gain_pct = (gain / total_invested_final * 100) if total_invested_final > 0 else 0
        color = list(scenario_colors.values())[idx_s]
        with sc_cols[idx_s]:
            st.markdown(f"""
<div style="background:#1A1F2E;border-radius:12px;padding:1rem;text-align:center;border-top:3px solid {color};">
  <div style="font-size:0.65rem;color:#4A5568;text-transform:uppercase;letter-spacing:0.1em;">{sc_name}</div>
  <div style="font-size:1.3rem;font-weight:800;color:{color};font-family:JetBrains Mono,monospace;margin-top:0.4rem;">{fmt(sc_val, ccy, rates)}</div>
  <div style="font-size:0.72rem;color:#8892AA;margin-top:0.3rem;">+{fmt(gain, ccy, rates)} ({gain_pct:+.1f}%)</div>
  <div style="font-size:0.6rem;color:#4A5568;margin-top:0.3rem;">sur {fmt(total_invested_final, ccy, rates)} investi</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
sub_label("Scénarios probabilistes calibrés (historique Equity)")
st.markdown(
    """
    <div style="font-size:0.78rem;color:#6E7D9B;margin-top:-0.3rem;margin-bottom:0.7rem;line-height:1.5;">
        Modèle basé sur ton historique réel (finances + investissements + valorisation live),
        avec profils de risque et probabilité d'atteinte des scénarios.
    </div>
    """,
    unsafe_allow_html=True,
)

profile_col, scen_col, horizon_col = st.columns([1.1, 2.2, 1])
profile_name = profile_col.selectbox(
    "Profil",
    ["Conservateur", "Équilibré", "Agressif", "Personnalisé"],
    index=1,
    key="eq_scenario_profile",
)

profile_presets = {
    "Conservateur": {"rates": [3.0, 5.0, 7.0, 9.0], "vol_mult": 0.82},
    "Équilibré": {"rates": [5.0, 9.0, 11.0, 15.0], "vol_mult": 1.00},
    "Agressif": {"rates": [8.0, 11.0, 15.0, 20.0], "vol_mult": 1.25},
}

if profile_name == "Personnalisé":
    scenario_raw = scen_col.text_input(
        "Scénarios annuels (%)",
        value="5, 9, 11, 15",
        help="Exemple: 5, 9, 11, 15",
        key="eq_scenario_custom",
    )
    profile_vol_mult = 1.0
else:
    preset_rates = profile_presets[profile_name]["rates"]
    scenario_raw = ", ".join(str(v).rstrip("0").rstrip(".") for v in preset_rates)
    scen_col.text_input(
        "Scénarios annuels (%)",
        value=scenario_raw,
        disabled=True,
        key="eq_scenario_preset",
    )
    profile_vol_mult = profile_presets[profile_name]["vol_mult"]

horizon_months = int(horizon_col.number_input("Horizon (mois)", min_value=6, max_value=240, value=36, step=6, key="eq_horizon_m"))

parsed = []
for chunk in scenario_raw.split(","):
    val = chunk.strip().replace("%", "")
    if not val:
        continue
    try:
        parsed.append(float(val))
    except Exception:
        pass
if len(parsed) < 2:
    parsed = [5.0, 9.0, 11.0, 15.0]

scenario_rates = sorted(set(max(-99.0, min(250.0, v)) for v in parsed))
scenario_dec = [v / 100.0 for v in scenario_rates]

finances = get_finances()
fort_hist = get_fortress_savings_history()
inv_hist = get_monthly_investment_totals()

fin_df = pd.DataFrame(finances) if finances else pd.DataFrame(columns=["month_key", "savings"])
fort_df = pd.DataFrame(fort_hist) if fort_hist else pd.DataFrame(columns=["month_key", "amount"])
inv_df = pd.DataFrame(inv_hist) if inv_hist else pd.DataFrame(columns=["month_key", "total"])

month_pool = set()
if not fin_df.empty and "month_key" in fin_df.columns:
    month_pool.update(fin_df["month_key"].dropna().tolist())
if not fort_df.empty and "month_key" in fort_df.columns:
    month_pool.update(fort_df["month_key"].dropna().tolist())
if not inv_df.empty and "month_key" in inv_df.columns:
    month_pool.update(inv_df["month_key"].dropna().tolist())

timeline = []
for mk in sorted(month_pool):
    cash = 0.0
    if not fin_df.empty:
        m = fin_df[fin_df["month_key"] == mk]
        if not m.empty and "savings" in m.columns:
            cash = float(m.iloc[0]["savings"] or 0)
    if cash == 0.0 and not fort_df.empty:
        m = fort_df[fort_df["month_key"] == mk]
        if not m.empty and "amount" in m.columns:
            cash = float(m.iloc[0]["amount"] or 0)

    invest = 0.0
    if not inv_df.empty:
        m = inv_df[inv_df["month_key"] == mk]
        if not m.empty and "total" in m.columns:
            invest = float(m.iloc[0]["total"] or 0)

    timeline.append({"month_key": mk, "flow": cash + invest})

flow_df = pd.DataFrame(timeline)
monthly_flow_avg = float(flow_df["flow"].mean()) if not flow_df.empty else 0.0

risk_totals = get_risk_investment_totals()
invested_total = float(get_total_invested_all_time()) + float(risk_totals.get("total_invested", 0) or 0)

portfolio_live_now = 0.0
for row in st.session_state.etf_rows:
    tk = row["ticker"]
    sh = float(row.get("shares", 0) or 0)
    pr = float(prices_cache.get(tk, 0) or 0)
    portfolio_live_now += sh * pr

current_invest_value = portfolio_live_now + float(risk_totals.get("total_current", 0) or 0)
obs_months = max(len(inv_df), 6)

if invested_total > 0 and current_invest_value > 0:
    hist_annual = (current_invest_value / invested_total) ** (12 / obs_months) - 1
else:
    hist_annual = 0.06

if not flow_df.empty and len(flow_df) >= 3:
    abs_mean = max(float(np.mean(np.abs(flow_df["flow"].values))), 1.0)
    flow_cv = float(np.std(flow_df["flow"].values) / abs_mean)
else:
    flow_cv = 0.55

sigma_annual = min(max((0.09 + flow_cv * 0.18) * profile_vol_mult, 0.07), 0.55)

weights = []
for sr in scenario_dec:
    z = (sr - hist_annual) / sigma_annual if sigma_annual > 0 else 0.0
    weights.append(float(np.exp(-0.5 * z * z)))
weights_sum = sum(weights) if weights else 1.0
scenario_probs = [w / weights_sum for w in weights]

base_wealth = float(current_savings) + float(portfolio_live_now) + float(risk_totals.get("total_current", 0) or 0)
mu_month = hist_annual / 12.0
sigma_month = sigma_annual / np.sqrt(12.0)
rng = np.random.default_rng(42)
sim_count = 1500
rand = rng.normal(mu_month, sigma_month, size=(sim_count, horizon_months))
terminal_values = np.full(sim_count, base_wealth, dtype=float)
for m in range(horizon_months):
    terminal_values = terminal_values * (1.0 + rand[:, m]) + monthly_flow_avg

def deterministic_target(rate_annual: float, months: int, start: float, monthly_flow: float) -> float:
    rm = (1 + rate_annual) ** (1 / 12) - 1
    if abs(rm) < 1e-10:
        return start + monthly_flow * months
    return start * ((1 + rm) ** months) + monthly_flow * ((((1 + rm) ** months) - 1) / rm)

target_values = [deterministic_target(sr, horizon_months, base_wealth, monthly_flow_avg) for sr in scenario_dec]
reach_probs = [float(np.mean(terminal_values >= tgt)) for tgt in target_values]

scenario_table = pd.DataFrame(
    {
        "Scénario": [f"{s:.1f}%" for s in scenario_rates],
        "Probabilité historique": [f"{p * 100:.1f}%" for p in scenario_probs],
        "Probabilité d'atteinte": [f"{p * 100:.1f}%" for p in reach_probs],
        "Cible à horizon": [fmt(v, ccy, rates) for v in target_values],
    }
)
st.dataframe(scenario_table, use_container_width=True, hide_index=True)

fig_prob = go.Figure()
fig_prob.add_trace(
    go.Bar(
        x=[f"{s:.1f}%" for s in scenario_rates],
        y=[p * 100 for p in scenario_probs],
        name="Probabilité historique",
        marker_color="#3B82F6",
        opacity=0.9,
    )
)
fig_prob.add_trace(
    go.Scatter(
        x=[f"{s:.1f}%" for s in scenario_rates],
        y=[p * 100 for p in reach_probs],
        name="Probabilité d'atteinte",
        mode="lines+markers",
        line=dict(color="#22D484", width=3),
        marker=dict(size=7),
    )
)
fig_prob.update_layout(
    **plotly_theme(),
    height=330,
    margin=dict(t=20, b=40, l=40, r=10),
    hovermode="x unified",
    yaxis_title="Probabilité (%)",
    xaxis_title="Scénarios annuels",
)
st.plotly_chart(fig_prob, use_container_width=True)

st.markdown(
    f"""
    <div style="font-size:0.74rem;color:#7C8DAA;margin-top:-0.3rem;margin-bottom:0.7rem;">
        Profil actif : <strong>{profile_name}</strong> ·
        Signal historique implicite : <strong>{hist_annual*100:.2f}%/an</strong> ·
        Volatilité estimée : <strong>{sigma_annual*100:.2f}%/an</strong> ·
        Flux mensuel moyen : <strong>{fmt(monthly_flow_avg, ccy, rates)}</strong>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  DIVIDEND TRACKER
# ══════════════════════════════════════════════════════════════════════════════
sub_label("Dividend Tracker — Rendement théorique (positions ACC réinvesties)")

if total_eur > 0:
    div_rows = ""
    total_annual_div = 0.0
    for r in st.session_state.etf_rows:
        tk = r["ticker"]
        val = total_eur * (r["target_pct"] / 100)
        yld_pct = ETF_YIELD.get(tk, 1.5)
        yld = yld_pct / 100
        annual_val = val * 12
        annual_div = annual_val * yld
        monthly_div = annual_div / 12
        total_annual_div += annual_div
        div_rows += (
            '<div class="info-row">'
            '<span class="info-key">'
            '<span style="color:#F0F4FF;font-family:JetBrains Mono,monospace;">' + tk + '</span>'
            '<span style="color:#4A5568;font-size:0.7rem;margin-left:0.3rem;">(' + f'{yld_pct:.1f}' + '% yield)</span>'
            '</span>'
            '<span class="info-value">'
            + fmt(annual_div, ccy, rates) + '/an'
            '<span style="color:#4A5568;font-size:0.72rem;"> · ' + fmt(monthly_div, ccy, rates) + '/mois</span>'
            '</span>'
            '</div>'
        )

    base_info = fmt(total_eur, ccy, rates) + "/mois × 12 = " + fmt(total_eur * 12, ccy, rates) + "/an investi"

    div_card = (
        '<div class="monk-card">'
        '<div class="monk-card-title">Dividendes théoriques (réinvestis automatiquement)</div>'
        '<div style="font-size:0.62rem;color:#4A5568;margin-bottom:0.6rem;">Basé sur ' + base_info + '</div>'
        + div_rows +
        '<div class="info-row" style="border-top:1px solid #2D3447;padding-top:0.5rem;margin-top:0.3rem;">'
        '<span class="info-key">Total annuel estimé</span>'
        '<span class="info-value" style="color:#10B981;font-size:1rem;">' + fmt(total_annual_div, ccy, rates) + '/an</span>'
        '</div>'
        '<div style="font-size:0.68rem;color:#4A5568;margin-top:0.8rem;line-height:1.6;">'
        'ⓘ Ces ETFs sont ACC (accumulants) — les dividendes sont réinvestis automatiquement, '
        'non versés. Ces chiffres représentent la croissance implicite incluse dans le prix.'
        '</div>'
        '</div>'
    )
    st.markdown(div_card, unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  JOURNAL D'INVESTISSEMENT MENSUEL
# ══════════════════════════════════════════════════════════════════════════════
sub_label("Journal d'investissement — Log tes achats mensuels")

from datetime import date as _date, datetime as _dt

# Month selector
now = _date.today()
month_options = []
for offset in range(12):
    m = now.month - offset
    y = now.year
    while m <= 0:
        m += 12
        y -= 1
    month_options.append(f"{y}-{m:02d}")

col_month, col_action, _ = st.columns([1, 1, 2])
with col_month:
    selected_month = st.selectbox("Mois", month_options, index=0, key="inv_month")

# Show current allocation for this month
st.markdown(
    '<div style="font-size:0.72rem;color:#8892AA;margin-bottom:0.5rem;">'
    'Les montants sont pré-remplis selon ton allocation cible et ton montant mensuel (' + fmt(invest_amount_eur, ccy, rates) + ').'
    ' Ajuste si besoin puis clique Enregistrer.</div>',
    unsafe_allow_html=True,
)

# Pre-fill amounts based on allocation
existing = get_monthly_investments(selected_month)
existing_map = {inv["ticker"]: inv["amount_eur"] for inv in existing}

inv_amounts = {}
for i, r in enumerate(st.session_state.etf_rows):
    tk = r["ticker"]
    default_val = existing_map.get(tk, invest_amount_eur * (r["target_pct"] / 100))
    cols = st.columns([2, 1.5, 1])
    with cols[0]:
        name = ETF_CATALOG.get(tk, tk)
        st.markdown(
            '<div style="padding-top:0.7rem;font-size:0.82rem;color:#F0F4FF;font-family:JetBrains Mono,monospace;">'
            + tk + '<span style="color:#4A5568;font-size:0.65rem;margin-left:0.4rem;">(' + name[:30] + ')</span></div>',
            unsafe_allow_html=True,
        )
    with cols[1]:
        inv_amounts[tk] = st.number_input(
            f"Montant {tk}", min_value=0.0, value=float(default_val),
            step=10.0, format="%.2f", key=f"inv_amt_{i}",
            label_visibility="collapsed",
        )
    with cols[2]:
        pr = prices_cache.get(tk, 0)
        pts = inv_amounts[tk] / pr if pr > 0 else 0
        st.markdown(
            '<div style="padding-top:0.7rem;font-size:0.78rem;color:#10B981;font-family:JetBrains Mono,monospace;">'
            + f'{pts:.4f}' + ' parts</div>',
            unsafe_allow_html=True,
        )

total_month = sum(inv_amounts.values())
st.markdown(
    '<div style="font-size:0.82rem;color:#F0F4FF;margin-top:0.3rem;">'
    'Total ce mois : <span style="color:#3B82F6;font-weight:700;font-family:JetBrains Mono,monospace;">'
    + fmt(total_month, ccy, rates) + '</span></div>',
    unsafe_allow_html=True,
)

with col_action:
    st.markdown("<div style='padding-top:1.6rem;'></div>", unsafe_allow_html=True)
    if st.button("✅ Enregistrer ce mois", key="save_inv"):
        investments = []
        for tk, amt in inv_amounts.items():
            if amt > 0:
                pr = prices_cache.get(tk, 0)
                pts = amt / pr if pr > 0 else 0
                investments.append({"ticker": tk, "amount_eur": amt, "buy_price": pr, "parts": pts})
        save_monthly_investment(selected_month, investments)
        st.success(f"✓ Investissement de {selected_month} enregistré !")
        st.rerun()

# History
st.markdown("<br>", unsafe_allow_html=True)
all_totals = get_monthly_investment_totals()
if all_totals:
    total_all_time = get_total_invested_all_time()
    history_rows = ""
    for mt in all_totals:
        mk = mt["month_key"]
        details = get_monthly_investments(mk)
        detail_str = " · ".join([d["ticker"] + " " + fmt(d["amount_eur"], ccy, rates) for d in details])
        history_rows += (
            '<div class="info-row">'
            '<span class="info-key" style="color:#F0F4FF;font-family:JetBrains Mono,monospace;">'
            + mk + '</span>'
            '<span class="info-value">'
            '<span style="color:#3B82F6;font-weight:700;">' + fmt(mt["total"], ccy, rates) + '</span>'
            '<span style="color:#4A5568;font-size:0.65rem;margin-left:0.4rem;">' + detail_str + '</span>'
            '</span></div>'
        )

    hist_card = (
        '<div class="monk-card">'
        '<div class="monk-card-title">Historique des investissements</div>'
        + history_rows +
        '<div class="info-row" style="border-top:1px solid #2D3447;padding-top:0.5rem;margin-top:0.3rem;">'
        '<span class="info-key">Total investi (all-time)</span>'
        '<span class="info-value" style="color:#10B981;font-size:1rem;font-weight:700;">'
        + fmt(total_all_time, ccy, rates) + '</span></div></div>'
    )
    st.markdown(hist_card, unsafe_allow_html=True)

    # Delete option
    col_del_month, col_del_btn, _ = st.columns([1, 1, 2])
    with col_del_month:
        del_month = st.selectbox("Supprimer un mois", [m["month_key"] for m in all_totals], key="del_inv_month")
    with col_del_btn:
        st.markdown("<div style='padding-top:0.5rem;'></div>", unsafe_allow_html=True)
        if st.button("🗑 Supprimer", key="del_inv_btn"):
            delete_monthly_investment(del_month)
            st.success(f"✓ Investissement {del_month} supprimé.")
            st.rerun()
