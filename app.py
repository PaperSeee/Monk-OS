"""
MONK-OS — Patrimoine (version minimaliste)
Une seule page : vue du patrimoine · encodage · évolution · projection.
Réutilise la base SQLite existante (aucune donnée perdue).
"""

import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
from datetime import date

from db.database import (
    init_db, get_setting, set_setting,
    get_lt_capital, set_lt_capital,
    get_portfolio_holdings, get_latest_portfolio_v2, save_portfolio_v2,
    get_crypto_wallet, save_crypto_wallet,
    record_wealth_snapshot, get_wealth_history,
)

st.set_page_config(page_title="MONK-OS — Patrimoine", page_icon="assets/monk_favicon.svg",
                   layout="wide", initial_sidebar_state="collapsed")
init_db()

css_path = Path(__file__).parent / "assets" / "minimal.css"
st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

SYM = "€"

# Couleurs par coin (répartition crypto)
COIN_COLORS = {
    "BTC": "#f7931a", "ETH": "#8a92b2", "USDT": "#26a17b", "USDC": "#2775ca",
    "SOL": "#9945ff", "BNB": "#f3ba2f", "XRP": "#23292f", "ADA": "#0033ad",
    "DOGE": "#c2a633", "AVAX": "#e84142", "MATIC": "#8247e5", "DOT": "#e6007a",
}
# Symbole yfinance par coin (vs EUR)
def yf_symbol(coin: str) -> str:
    c = coin.upper()
    if c in ("USDT", "USDC", "DAI", "BUSD"):
        return None  # stablecoin ≈ 1 USD, converti plus bas
    return f"{c}-EUR"


def fmt(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ") + " " + SYM


# ── Prix live (ETF + crypto), cache 15 min ──────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def live_prices(symbols: tuple) -> dict:
    out = {}
    try:
        import yfinance as yf
        for s in symbols:
            if not s:
                continue
            try:
                h = yf.Ticker(s).history(period="2d")
                if not h.empty:
                    out[s] = float(h["Close"].iloc[-1])
            except Exception:
                pass
    except ImportError:
        pass
    return out


@st.cache_data(ttl=900, show_spinner=False)
def usd_eur() -> float:
    try:
        import yfinance as yf
        h = yf.Ticker("EURUSD=X").history(period="2d")
        if not h.empty:
            return 1 / float(h["Close"].iloc[-1])
    except Exception:
        pass
    return 0.92  # fallback


# ── Données patrimoine ───────────────────────────────────────────────────────
epargne = get_lt_capital()

# Bourse ETF
holdings = get_portfolio_holdings()
etf_prices = live_prices(tuple(holdings.keys())) if holdings else {}
bourse_live = 0.0
bourse_invested = 0.0
for tk, d in holdings.items():
    bourse_invested += d["invested"]
    px = etf_prices.get(tk)
    bourse_live += d["parts"] * px if px else d["invested"]

# Crypto
wallet = get_crypto_wallet()
crypto_syms = tuple(yf_symbol(w["coin"]) for w in wallet)
crypto_prices = live_prices(crypto_syms) if wallet else {}
fx = usd_eur()
crypto_lines = []
crypto_total = 0.0
for w in wallet:
    coin, qty = w["coin"], w["qty"]
    sym = yf_symbol(coin)
    if sym is None:  # stablecoin en USD → EUR
        val = qty * fx
    else:
        px = crypto_prices.get(sym, 0)
        val = qty * px
    crypto_total += val
    crypto_lines.append({"coin": coin, "qty": qty, "val": val})

patrimoine = epargne + bourse_live + crypto_total
plus_value = bourse_live - bourse_invested

# Snapshot mensuel automatique (1 point / mois, mis à jour à chaque visite)
if patrimoine > 0:
    record_wealth_snapshot(patrimoine, epargne, bourse_live, crypto_total)

# ── HERO ─────────────────────────────────────────────────────────────────────
history = get_wealth_history()
delta_txt = ""
if len(history) >= 2:
    prev = history[-2]["total"]
    if prev > 0:
        d = patrimoine - prev
        pct = d / prev * 100
        cls = "up" if d >= 0 else "down"
        sgn = "+" if d >= 0 else ""
        delta_txt = f'<span class="{cls}">{sgn}{fmt(d)} ({sgn}{pct:.1f} %)</span> depuis le mois dernier'
if not delta_txt:
    pv_cls = "up" if plus_value >= 0 else "down"
    delta_txt = f'Plus-value bourse : <span class="{pv_cls}">{"+" if plus_value>=0 else ""}{fmt(plus_value)}</span>'

st.markdown(f"""
<div class="hero">
  <div class="eyebrow">Patrimoine total</div>
  <div class="total">{fmt(patrimoine)}</div>
  <div class="delta">{delta_txt}</div>
</div>
""", unsafe_allow_html=True)

# ── RÉPARTITION (3 classes) ──────────────────────────────────────────────────
def pct(x):
    return (x / patrimoine * 100) if patrimoine else 0

st.markdown(f"""
<div class="alloc alloc-3">
  <div class="acard">
    <div class="lab"><span class="dot" style="background:#6ba7ff"></span>Épargne</div>
    <div class="v">{fmt(epargne)}</div><div class="pct">{pct(epargne):.0f} %</div>
  </div>
  <div class="acard">
    <div class="lab"><span class="dot" style="background:#3ecf8e"></span>Bourse · ETF</div>
    <div class="v">{fmt(bourse_live)}</div><div class="pct">{pct(bourse_live):.0f} %</div>
  </div>
  <div class="acard">
    <div class="lab"><span class="dot" style="background:#f7931a"></span>Crypto</div>
    <div class="v">{fmt(crypto_total)}</div><div class="pct">{pct(crypto_total):.0f} %</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Répartition crypto détaillée (donut) ─────────────────────────────────────
if crypto_lines:
    labels = [c["coin"] for c in crypto_lines]
    vals = [c["val"] for c in crypto_lines]
    colors = [COIN_COLORS.get(c["coin"], "#6ba7ff") for c in crypto_lines]
    donut = go.Figure(go.Pie(
        labels=labels, values=vals, hole=0.62, marker=dict(colors=colors, line=dict(color="#0c0d10", width=2)),
        textinfo="label+percent", textfont=dict(color="#f2f4f8", size=12),
        hovertemplate="%{label}<br>%{value:,.0f} €<extra></extra>",
    ))
    donut.update_layout(
        height=250, margin=dict(l=0, r=0, t=6, b=0), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(text=f"<b>{fmt(crypto_total)}</b>", x=0.5, y=0.5,
                          font=dict(color="#f2f4f8", size=17), showarrow=False)],
    )
    st.markdown('<div class="sec-label">Répartition crypto</div>', unsafe_allow_html=True)
    st.plotly_chart(donut, use_container_width=True, config={"displayModeBar": False})

# ── ÉVOLUTION DU PATRIMOINE ──────────────────────────────────────────────────
if len(history) >= 2:
    st.markdown('<div class="sec-label">Évolution du patrimoine</div>', unsafe_allow_html=True)
    xs = [h["month_key"] for h in history]
    fig_h = go.Figure()
    fig_h.add_trace(go.Scatter(
        x=xs, y=[h["total"] for h in history], name="Total", mode="lines+markers",
        line=dict(color="#6ba7ff", width=2.5),
        fill="tozeroy", fillcolor="rgba(107,167,255,0.08)",
        marker=dict(size=5),
    ))
    fig_h.update_layout(
        height=260, margin=dict(l=0, r=0, t=6, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#9aa2b1", size=12), showlegend=False,
        xaxis=dict(gridcolor="#1c1f26", zeroline=False),
        yaxis=dict(gridcolor="#1c1f26", zeroline=False, tickformat=",.0f", ticksuffix=" €"),
        hovermode="x unified",
    )
    st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})

# ── ENCODAGE ─────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-label">Encoder</div>', unsafe_allow_html=True)

with st.expander("💰  Épargne (cash)"):
    new_ep = st.number_input("Total comptes épargne / courant", value=float(epargne),
                             min_value=0.0, step=100.0, key="ep")
    if st.button("Enregistrer l'épargne", key="save_ep"):
        set_lt_capital(new_ep)
        st.success("Épargne mise à jour.")
        st.rerun()

with st.expander("📈  Portefeuille bourse (ETF)"):
    st.caption("Parts détenues par ligne. Prix récupérés en direct.")
    rows = get_latest_portfolio_v2() or [{"ticker": "", "shares": 0.0, "price": 0.0}]
    new_rows = []
    for i, r in enumerate(rows + [{"ticker": "", "shares": 0.0, "price": 0.0}]):
        c1, c2, c3 = st.columns([2, 1.3, 1.3])
        tk = c1.text_input("Ticker", value=r.get("ticker", ""), key=f"tk{i}", placeholder="VWCE.DE")
        sh = c2.number_input("Parts", value=float(r.get("shares", 0) or 0), min_value=0.0,
                             step=0.001, format="%.4f", key=f"sh{i}")
        px_def = etf_prices.get(tk) or float(r.get("price", 0) or 0)
        px = c3.number_input("Prix/part", value=float(px_def), min_value=0.0, step=1.0, key=f"px{i}")
        if tk and sh > 0:
            new_rows.append({"ticker": tk, "shares": sh, "price": px, "target_pct": 0.0})
    if st.button("Enregistrer le portefeuille", key="save_pf"):
        save_portfolio_v2(new_rows)
        live_prices.clear()
        st.success("Portefeuille mis à jour.")
        st.rerun()

with st.expander("₿  Wallet crypto"):
    st.caption("Quantité par coin (BTC, ETH, USDT, SOL…). Prix live en EUR.")
    cw = get_crypto_wallet() or [{"coin": "", "qty": 0.0}]
    new_cw = []
    for i, w in enumerate(cw + [{"coin": "", "qty": 0.0}]):
        c1, c2 = st.columns([1.4, 2])
        coin = c1.text_input("Coin", value=w.get("coin", ""), key=f"cc{i}", placeholder="BTC")
        qty = c2.number_input("Quantité", value=float(w.get("qty", 0) or 0), min_value=0.0,
                              step=0.0001, format="%.6f", key=f"cq{i}")
        if coin and qty > 0:
            new_cw.append({"coin": coin, "qty": qty})
    if st.button("Enregistrer le wallet", key="save_cw"):
        save_crypto_wallet(new_cw)
        live_prices.clear()
        st.success("Wallet crypto mis à jour.")
        st.rerun()

# ── PROJECTION ───────────────────────────────────────────────────────────────
st.markdown('<div class="sec-label">Projection</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
apport = c1.number_input("Épargne mensuelle (€)", value=int(float(get_setting("proj_apport", 500))),
                         min_value=0, step=50)
rendement = c2.slider("Rendement annuel (%)", 0.0, 15.0,
                      float(get_setting("proj_rendement", 7.0)), 0.5)
annees = c3.slider("Horizon (années)", 1, 40, int(float(get_setting("proj_annees", 20))))
set_setting("proj_apport", apport)
set_setting("proj_rendement", rendement)
set_setting("proj_annees", annees)

r_m = rendement / 100 / 12
mois = annees * 12
serie_val, serie_verse = [], []
val = patrimoine
verse = patrimoine
for m in range(mois + 1):
    serie_val.append(val)
    serie_verse.append(verse)
    val = val * (1 + r_m) + apport
    verse += apport

final, total_verse = serie_val[-1], serie_verse[-1]
interets = final - total_verse
xs = [date.today().year + m / 12 for m in range(mois + 1)]

fig = go.Figure()
fig.add_trace(go.Scatter(x=xs, y=serie_verse, name="Versé", mode="lines",
                         line=dict(color="#616b7c", width=1.5, dash="dot")))
fig.add_trace(go.Scatter(x=xs, y=serie_val, name="Valeur projetée", mode="lines",
                         line=dict(color="#6ba7ff", width=2.5),
                         fill="tonexty", fillcolor="rgba(107,167,255,0.10)"))
fig.update_layout(
    height=300, margin=dict(l=0, r=0, t=10, b=0),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#9aa2b1", size=12),
    legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="left", x=0),
    xaxis=dict(gridcolor="#1c1f26", zeroline=False),
    yaxis=dict(gridcolor="#1c1f26", zeroline=False, tickformat=",.0f", ticksuffix=" €"),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

m1, m2, m3 = st.columns(3)
m1.metric(f"Dans {annees} ans", fmt(final))
m2.metric("Total versé", fmt(total_verse))
m3.metric("Dont intérêts", fmt(interets))
