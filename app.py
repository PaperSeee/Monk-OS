"""
MONK-OS — Patrimoine (version minimaliste)
Une seule page : vue du patrimoine · encodage · projection.
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
)

st.set_page_config(page_title="MONK-OS — Patrimoine", page_icon="assets/monk_favicon.svg",
                   layout="wide", initial_sidebar_state="collapsed")
init_db()

# ── CSS minimaliste ──────────────────────────────────────────────────────────
css_path = Path(__file__).parent / "assets" / "minimal.css"
st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

SYM = "€"


def fmt(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ") + " " + SYM


# ── Récupération des prix live (avec cache 15 min) ───────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def live_prices(tickers: tuple) -> dict:
    out = {}
    try:
        import yfinance as yf
        for t in tickers:
            try:
                h = yf.Ticker(t).history(period="2d")
                if not h.empty:
                    out[t] = float(h["Close"].iloc[-1])
            except Exception:
                pass
    except ImportError:
        pass
    return out


# ── Données patrimoine ───────────────────────────────────────────────────────
epargne = get_lt_capital()
holdings = get_portfolio_holdings()
prices = live_prices(tuple(holdings.keys())) if holdings else {}

bourse_live = 0.0
bourse_invested = 0.0
for tk, d in holdings.items():
    parts = d["parts"]
    bourse_invested += d["invested"]
    px = prices.get(tk)
    bourse_live += parts * px if px else d["invested"]

patrimoine = epargne + bourse_live
plus_value = bourse_live - bourse_invested

# ── HERO ─────────────────────────────────────────────────────────────────────
pv_cls = "up" if plus_value >= 0 else "down"
pv_sign = "+" if plus_value >= 0 else ""
st.markdown(f"""
<div class="hero">
  <div class="eyebrow">Patrimoine total</div>
  <div class="total">{fmt(patrimoine)}</div>
  <div class="delta">Portefeuille bourse : <span class="{pv_cls}">{pv_sign}{fmt(plus_value)}</span> de plus-value latente</div>
</div>
""", unsafe_allow_html=True)

# ── RÉPARTITION ──────────────────────────────────────────────────────────────
p_ep = (epargne / patrimoine * 100) if patrimoine else 0
p_bo = (bourse_live / patrimoine * 100) if patrimoine else 0
st.markdown(f"""
<div class="alloc">
  <div class="acard">
    <div class="lab"><span class="dot" style="background:#6ba7ff"></span>Épargne · cash</div>
    <div class="v">{fmt(epargne)}</div>
    <div class="pct">{p_ep:.0f} % du patrimoine</div>
  </div>
  <div class="acard">
    <div class="lab"><span class="dot" style="background:#3ecf8e"></span>Bourse · ETF</div>
    <div class="v">{fmt(bourse_live)}</div>
    <div class="pct">{p_bo:.0f} % · investi {fmt(bourse_invested)}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── ENCODAGE ─────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-label">Encoder</div>', unsafe_allow_html=True)

with st.expander("💰  Mettre à jour mon épargne (cash)"):
    new_ep = st.number_input("Montant total sur mes comptes épargne / courant",
                             value=float(epargne), min_value=0.0, step=100.0, key="ep")
    if st.button("Enregistrer l'épargne", key="save_ep"):
        set_lt_capital(new_ep)
        st.success("Épargne mise à jour.")
        st.rerun()

with st.expander("📈  Mettre à jour mon portefeuille bourse (ETF)"):
    st.caption("Nombre de parts détenues par ligne. Les prix sont récupérés en direct.")
    rows = get_latest_portfolio_v2()
    if not rows:
        rows = [{"ticker": "", "shares": 0.0, "price": 0.0, "target_pct": 0.0}]
    new_rows = []
    for i, r in enumerate(rows + [{"ticker": "", "shares": 0.0, "price": 0.0, "target_pct": 0.0}]):
        c1, c2, c3 = st.columns([2, 1.3, 1.3])
        tk = c1.text_input("Ticker", value=r.get("ticker", ""), key=f"tk{i}", placeholder="ex : VWCE.DE")
        sh = c2.number_input("Parts", value=float(r.get("shares", 0) or 0), min_value=0.0,
                             step=0.001, format="%.4f", key=f"sh{i}")
        live_px = prices.get(tk)
        px_default = live_px if live_px else float(r.get("price", 0) or 0)
        px = c3.number_input("Prix / part", value=float(px_default), min_value=0.0,
                             step=1.0, key=f"px{i}", help="Prix live pré-rempli si disponible")
        if tk and sh > 0:
            new_rows.append({"ticker": tk, "shares": sh, "price": px, "target_pct": 0.0})
    if st.button("Enregistrer le portefeuille", key="save_pf"):
        save_portfolio_v2(new_rows)
        live_prices.clear()
        st.success("Portefeuille mis à jour.")
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

# Intérêts composés mensuels
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

final = serie_val[-1]
total_verse = serie_verse[-1]
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
