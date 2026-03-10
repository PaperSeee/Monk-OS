"""
Module 2 — EQUITY ENGINE V2
Dynamic multi-ETF tracking, smart rebalancing, lock system, dividend tracker
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import init_db, get_latest_portfolio_v2, save_portfolio_v2, get_setting
from utils.helpers import (
    inject_css, section_head, sub_label, plotly_theme,
    ETF_CATALOG, ETF_YIELD, fmt, get_fx_rates,
)

init_db()
inject_css()

import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

section_head("MODULE 02 — EQUITY ENGINE V2")

# ── Session state: currency & FX ─────────────────────────────────────────────
ccy     = st.session_state.get("currency", "EUR")
with st.spinner("Chargement des taux de change…") if ccy != "EUR" else st.empty():
    rates = get_fx_rates() if ccy != "EUR" else {"EUR": 1.0}

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
    # Load from DB or default
    saved = get_latest_portfolio_v2()
    if saved:
        st.session_state.etf_rows = [
            {"ticker": r["ticker"], "shares": r["shares"], "target_pct": r["target_pct"]}
            for r in saved
        ]
    else:
        st.session_state.etf_rows = [
            {"ticker": "VWCE.DE", "shares": 0.0, "target_pct": 80.0},
            {"ticker": "SXRV.DE", "shares": 0.0, "target_pct": 20.0},
        ]

# ── ETF SELECTOR ─────────────────────────────────────────────────────────────
sub_label("Mes positions — Portefeuille Multi-ETF")

all_tickers = list(ETF_CATALOG.keys())
ticker_labels = [f"{k} — {v}" for k, v in ETF_CATALOG.items()]

rows_to_delete = []
prices_cache   = {}

for i, row in enumerate(st.session_state.etf_rows):
    with st.container():
        col_t, col_s, col_pct, col_price, col_val, col_del = st.columns([2.5, 1.4, 1.2, 1.5, 1.5, 0.4])

        with col_t:
            # Find index in catalog or allow custom
            if row["ticker"] in all_tickers:
                t_idx = all_tickers.index(row["ticker"])
            else:
                t_idx = 0
                all_tickers_ext     = [row["ticker"]] + all_tickers
                ticker_labels_ext   = [f"{row['ticker']} — Custom"] + ticker_labels
            options_display = ticker_labels if row["ticker"] in all_tickers else [f"{row['ticker']} — Custom"] + ticker_labels
            chosen_label    = st.selectbox(
                f"ETF {i+1}",
                options=options_display,
                index=0 if row["ticker"] not in all_tickers else all_tickers.index(row["ticker"]),
                key=f"etf_select_{i}",
                label_visibility="collapsed",
            )
            # Parse ticker from label
            new_ticker = chosen_label.split(" — ")[0].strip()
            if new_ticker != row["ticker"]:
                st.session_state.etf_rows[i]["ticker"] = new_ticker

        with col_s:
            new_shares = st.number_input(
                "Parts", min_value=0.0, value=float(row["shares"]),
                step=0.5, format="%.2f",
                key=f"shares_{i}", label_visibility="collapsed",
            )
            st.session_state.etf_rows[i]["shares"] = new_shares

        with col_pct:
            new_pct = st.number_input(
                "Cible %", min_value=0.0, max_value=100.0,
                value=float(row["target_pct"]), step=5.0, format="%.1f",
                key=f"pct_{i}", label_visibility="collapsed",
            )
            st.session_state.etf_rows[i]["target_pct"] = new_pct

        # Fetch price
        ticker   = st.session_state.etf_rows[i]["ticker"]
        price_eur = fetch_price(ticker) or 0.0
        prices_cache[ticker] = price_eur
        price_display = fmt(price_eur, ccy, rates) if price_eur else "N/A"
        val_eur   = new_shares * price_eur
        val_display = fmt(val_eur, ccy, rates)

        with col_price:
            st.markdown(f"""
            <div style="padding-top:0.9rem; font-size:0.85rem; font-weight:600;
                        color:#F0F4FF; font-family:'JetBrains Mono',monospace;">
                {price_display}
            </div>
            <div style="font-size:0.6rem; color:#4A5568;">Prix / part</div>
            """, unsafe_allow_html=True)

        with col_val:
            st.markdown(f"""
            <div style="padding-top:0.9rem; font-size:0.85rem; font-weight:700;
                        color:#3B82F6; font-family:'JetBrains Mono',monospace;">
                {val_display}
            </div>
            <div style="font-size:0.6rem; color:#4A5568;">Valeur totale</div>
            """, unsafe_allow_html=True)

        with col_del:
            st.markdown("<div style='padding-top:0.5rem;'></div>", unsafe_allow_html=True)
            if st.button("✕", key=f"del_{i}", help="Supprimer cette ligne"):
                rows_to_delete.append(i)

# Apply deletions
for idx in sorted(rows_to_delete, reverse=True):
    del st.session_state.etf_rows[idx]
if rows_to_delete:
    st.rerun()

# Column headers hint
st.markdown("""
<div style="display:flex; gap:0; font-size:0.6rem; color:#4A5568;
            letter-spacing:0.1em; text-transform:uppercase; margin-top:-0.3rem; padding:0 0.2rem;">
    <span style="flex:2.5;">Ticker / ETF</span>
    <span style="flex:1.4;">Parts détenues</span>
    <span style="flex:1.2;">Cible %</span>
    <span style="flex:1.5;">Prix live</span>
    <span style="flex:1.5;">Valeur</span>
</div>
""", unsafe_allow_html=True)

# ── Buttons: Add ETF + Save ───────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
col_add, col_save, col_refresh, col_spacer = st.columns([1, 1, 1, 2])

with col_add:
    if st.button("➕  Ajouter un ETF"):
        st.session_state.etf_rows.append({"ticker": "IWDA.AS", "shares": 0.0, "target_pct": 0.0})
        st.rerun()

with col_save:
    if st.button("💾  Sauvegarder"):
        db_rows = [
            {"ticker": r["ticker"],
             "shares": r["shares"],
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
    st.markdown(f"""
    <div style="font-size:0.72rem; color:#10B981; font-weight:500; margin-top:0.3rem;">
        ✓ Allocation validée : {total_target:.1f}%
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Portfolio Summary ─────────────────────────────────────────────────────────
sub_label("Synthèse du portefeuille")

total_eur = sum(
    r["shares"] * prices_cache.get(r["ticker"], 0)
    for r in st.session_state.etf_rows
)

if total_eur > 0:
    col_donut, col_summary = st.columns([1.3, 1])

    with col_donut:
        labels, values, colors_list, devs = [], [], [], []
        palette = ["#3B82F6","#10B981","#8B5CF6","#F59E0B","#EF4444",
                   "#06B6D4","#EC4899","#84CC16","#F97316","#A78BFA"]

        for idx, r in enumerate(st.session_state.etf_rows):
            v = r["shares"] * prices_cache.get(r["ticker"], 0)
            if v > 0:
                labels.append(r["ticker"])
                values.append(v)
                colors_list.append(palette[idx % len(palette)])
                actual_pct = v / total_eur * 100
                devs.append(actual_pct - r["target_pct"])

        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=labels, values=values,
            hole=0.60,
            marker=dict(colors=colors_list, line=dict(color="#161A22", width=3)),
            textfont=dict(family="Inter", size=11, color="#F0F4FF"),
            texttemplate="%{label}<br><b>%{percent}</b>",
            textposition="outside",
            showlegend=True,
        ))
        theme = plotly_theme()
        fig.update_layout(
            **theme,
            margin=dict(t=20, b=30, l=20, r=20), height=320,
            legend=dict(font=dict(family="Inter", size=10, color="#8892AA"),
                        bgcolor="rgba(0,0,0,0)",
                        x=0.5, y=-0.18, xanchor="center", orientation="h"),
            annotations=[dict(
                text=f"<b>{fmt(total_eur, ccy, rates)}</b>",
                x=0.5, y=0.5,
                font=dict(size=16, color="#F0F4FF", family="JetBrains Mono"),
                showarrow=False
            )],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_summary:
        st.markdown("<br>", unsafe_allow_html=True)
        rows_html = ""
        for idx, r in enumerate(st.session_state.etf_rows):
            val = r["shares"] * prices_cache.get(r["ticker"], 0)
            actual_pct = val / total_eur * 100 if total_eur > 0 else 0
            dev = actual_pct - r["target_pct"]
            dev_color = "#10B981" if abs(dev) < 2 else "#F59E0B" if abs(dev) < 5 else "#EF4444"
            rows_html += f"""
            <div class="info-row">
                <span class="info-key">{r["ticker"]}</span>
                <span style="font-size:0.78rem; font-family:'JetBrains Mono',monospace;">
                    <span style="color:#F0F4FF;">{actual_pct:.1f}%</span>
                    <span style="color:{dev_color}; margin-left:0.4rem; font-size:0.72rem;">
                        ({'+' if dev >= 0 else ''}{dev:.1f}% vs {r['target_pct']:.0f}%)
                    </span>
                </span>
            </div>"""

        st.markdown(f"""
        <div class="monk-card">
            <div class="monk-card-title">Répartition actuelle vs cible</div>
            {rows_html}
            <div class="info-row" style="margin-top:0.5rem; border-top:1px solid #232836; padding-top:0.5rem;">
                <span class="info-key">Total portefeuille</span>
                <span class="info-value" style="color:#3B82F6;">{fmt(total_eur, ccy, rates)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ── Performance Chart ─────────────────────────────────────────────────────────
active_tickers = list({r["ticker"] for r in st.session_state.etf_rows if prices_cache.get(r["ticker"])})
if active_tickers:
    sub_label("Performance 3 mois (base 100)")
    hist_data = fetch_history_multi(tuple(active_tickers))
    if hist_data:
        palette = ["#3B82F6","#10B981","#8B5CF6","#F59E0B","#EF4444",
                   "#06B6D4","#EC4899","#84CC16"]
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

# ── Smart Rebalancing Calculator ──────────────────────────────────────────────
sub_label("Calculateur de rééquilibrage intelligent")

col_inv, col_notes = st.columns([1, 2])
with col_inv:
    invest_amount_eur = st.number_input(
        "Montant à investir (€)", min_value=0.0, value=750.0, step=50.0
    )

if is_locked:
    st.markdown("""
    <div class="lock-overlay">
        <div style="font-size:1.2rem; margin-bottom:0.4rem;">🔒</div>
        <div style="color:#F59E0B; font-family:'JetBrains Mono',monospace; font-weight:700;
                    font-size:0.8rem; letter-spacing:0.08em;">
            INVESTISSEMENT VERROUILLÉ
        </div>
        <div style="color:#8892AA; font-size:0.75rem; margin-top:0.4rem;">
            Atteins d'abord l'objectif Fortress de 2 000 €.
        </div>
    </div>
    """, unsafe_allow_html=True)
elif st.button("🧮  Calculer mes achats", type="primary"):
    if total_eur == 0 and invest_amount_eur == 0:
        st.warning("Entre ton montant à investir et tes positions actuelles.")
    else:
        total_after = total_eur + invest_amount_eur
        orders = []
        for r in st.session_state.etf_rows:
            ticker    = r["ticker"]
            price_eur = prices_cache.get(ticker, 0)
            if price_eur == 0:
                continue
            current_val = r["shares"] * price_eur
            target_val  = total_after * (r["target_pct"] / 100)
            buy_eur     = max(target_val - current_val, 0)
            orders.append({
                "ticker": ticker,
                "buy_eur": buy_eur,
                "price": price_eur,
                "target_pct": r["target_pct"]
            })

        # Normalize to invest_amount
        total_buy = sum(o["buy_eur"] for o in orders)
        if total_buy > invest_amount_eur and total_buy > 0:
            ratio = invest_amount_eur / total_buy
            for o in orders:
                o["buy_eur"] *= ratio

        rows_html = ""
        for o in orders:
            parts = o["buy_eur"] / o["price"] if o["price"] > 0 else 0
            rows_html += f"""
            <div class="info-row">
                <span class="info-key">
                    <span style="color:#F0F4FF; font-family:'JetBrains Mono',monospace; font-weight:700;">
                        {o['ticker']}
                    </span>
                    <span style="color:#4A5568; font-size:0.72rem; margin-left:0.4rem;">
                        (cible {o['target_pct']:.0f}%)
                    </span>
                </span>
                <span class="info-value" style="color:#3B82F6;">
                    {parts:.3f} parts ≈ {fmt(o['buy_eur'], ccy, rates)}
                </span>
            </div>"""

        total_deployed = sum(o["buy_eur"] for o in orders)
        st.markdown(f"""
        <div class="rebal-result">
            <div style="font-size:0.62rem; color:#3B82F6; letter-spacing:0.2em;
                        text-transform:uppercase; margin-bottom:1rem; font-weight:600;">
                ✓ Ordres d'achat recommandés
            </div>
            {rows_html}
            <div class="info-row" style="border-top:1px solid #232836; padding-top:0.5rem; margin-top:0.3rem;">
                <span class="info-key">Total déployé</span>
                <span class="info-value">
                    {fmt(total_deployed, ccy, rates)} / {fmt(invest_amount_eur, ccy, rates)}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ── Dividend Tracker ──────────────────────────────────────────────────────────
sub_label("Dividend Tracker — Rendement théorique (positions ACC réinvesties)")

if total_eur > 0:
    div_rows = ""
    total_annual_div = 0.0
    for r in st.session_state.etf_rows:
        ticker    = r["ticker"]
        val       = r["shares"] * prices_cache.get(ticker, 0)
        yld       = ETF_YIELD.get(ticker, 1.5) / 100
        annual_div = val * yld
        monthly_div = annual_div / 12
        total_annual_div += annual_div
        div_rows += f"""
        <div class="info-row">
            <span class="info-key">
                <span style="color:#F0F4FF; font-family:'JetBrains Mono',monospace;">{ticker}</span>
                <span style="color:#4A5568; font-size:0.7rem; margin-left:0.3rem;">
                    ({ETF_YIELD.get(ticker, 1.5):.1f}% yield estimé)
                </span>
            </span>
            <span class="info-value">
                {fmt(annual_div, ccy, rates)}/an
                <span style="color:#4A5568; font-size:0.72rem;"> · {fmt(monthly_div, ccy, rates)}/mois</span>
            </span>
        </div>"""

    st.markdown(f"""
    <div class="monk-card">
        <div class="monk-card-title">Dividendes théoriques (réinvestis automatiquement)</div>
        {div_rows}
        <div class="info-row" style="border-top:1px solid #2D3447; padding-top:0.5rem; margin-top:0.3rem;">
            <span class="info-key">Total annuel estimé</span>
            <span class="info-value" style="color:#10B981; font-size:1rem;">
                {fmt(total_annual_div, ccy, rates)}/an
            </span>
        </div>
        <div style="font-size:0.68rem; color:#4A5568; margin-top:0.8rem; line-height:1.6;">
            ⓘ Ces ETFs sont ACC (accumulants) — les dividendes sont réinvestis automatiquement,
            non versés. Ces chiffres représentent la croissance implicite incluse dans le prix.
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="monk-card" style="text-align:center; padding:2rem;">
        <div style="color:#4A5568; font-size:0.82rem;">
            Entre tes positions pour voir le dividend tracker.
        </div>
    </div>
    """, unsafe_allow_html=True)
