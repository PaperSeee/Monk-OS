"""
MONK-OS — Patrimoine (version minimaliste)
Une seule page : vue du patrimoine · encodage · évolution · projection.
Réutilise la base SQLite existante (aucune donnée perdue).
"""

import math
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
def _last_valid_close(hist) -> float | None:
    """Dernier cours de clôture NON-NaN. Yahoo renvoie souvent une bougie du
    jour à NaN (marché ouvert / donnée pas encore consolidée) : on ignore ces
    NaN et on prend le dernier prix réellement coté."""
    try:
        closes = hist["Close"].dropna()
        if not closes.empty:
            return float(closes.iloc[-1])
    except Exception:
        pass
    return None


@st.cache_data(ttl=900, show_spinner=False)
def live_prices(symbols: tuple) -> dict:
    out = {}
    try:
        import yfinance as yf
        for s in symbols:
            if not s:
                continue
            try:
                h = yf.Ticker(s).history(period="5d")
                px = _last_valid_close(h)
                if px is not None:
                    out[s] = px
            except Exception:
                pass
    except ImportError:
        pass
    return out


@st.cache_data(ttl=900, show_spinner=False)
def usd_eur() -> float:
    try:
        import yfinance as yf
        h = yf.Ticker("EURUSD=X").history(period="5d")
        px = _last_valid_close(h)
        if px:
            return 1 / px
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
    # px valide = nombre fini et > 0 ; sinon repli sur le montant investi.
    if isinstance(px, (int, float)) and math.isfinite(px) and px > 0:
        bourse_live += d["parts"] * px
    else:
        bourse_live += d["invested"]

# Crypto
wallet = get_crypto_wallet()
crypto_syms = tuple(yf_symbol(w["coin"]) for w in wallet)
crypto_prices = live_prices(crypto_syms) if wallet else {}
fx = usd_eur()
crypto_lines = []
crypto_total = 0.0
crypto_warns = []
for w in wallet:
    coin, qty = w["coin"], w["qty"]
    sym = yf_symbol(coin)
    if sym is None:  # stablecoin (USDT/USDC/DAI/BUSD) : ≈ 1 USD → converti en EUR
        val = qty * fx
    else:
        px = crypto_prices.get(sym)
        if px:
            val = qty * px
        else:
            val = 0.0
            crypto_warns.append(coin)  # cours indisponible pour l'instant
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

# ── Répartition globale (sunburst : classes → détail) ────────────────────────
# Anneau intérieur : Épargne / Bourse ETF / Crypto. Anneau extérieur : le
# détail de chaque poche (cash, chaque ETF, chaque coin).
if patrimoine > 0:
    CLASS_COLORS = {"Épargne": "#6ba7ff", "Bourse · ETF": "#3ecf8e", "Crypto": "#f7931a"}
    sb_labels, sb_parents, sb_values, sb_colors = [], [], [], []

    def add(label, parent, value, color):
        sb_labels.append(label); sb_parents.append(parent)
        sb_values.append(max(value, 0)); sb_colors.append(color)

    # Niveau 1 — les 3 poches
    if epargne > 0:
        add("Épargne", "", epargne, CLASS_COLORS["Épargne"])
        add("Cash", "Épargne", epargne, "#8fc0ff")
    if bourse_live > 0:
        add("Bourse · ETF", "", bourse_live, CLASS_COLORS["Bourse · ETF"])
        for tk, d in holdings.items():
            px = etf_prices.get(tk)
            v = d["parts"] * px if px else d["invested"]
            if v > 0:
                add(tk, "Bourse · ETF", v, "#6fe0ac")
    if crypto_total > 0:
        add("Crypto", "", crypto_total, CLASS_COLORS["Crypto"])
        for c in crypto_lines:
            if c["val"] > 0:
                add(c["coin"], "Crypto", c["val"], COIN_COLORS.get(c["coin"], "#ffb45e"))

    sun = go.Figure(go.Sunburst(
        labels=sb_labels, parents=sb_parents, values=sb_values,
        branchvalues="total",
        marker=dict(colors=sb_colors, line=dict(color="#0c0d10", width=2)),
        textinfo="label+percent root",
        textfont=dict(color="#f2f4f8", size=13),
        insidetextorientation="radial",
        hovertemplate="%{label}<br>%{value:,.0f} € · %{percentRoot:.0%} du patrimoine<extra></extra>",
    ))
    sun.update_layout(
        height=340, margin=dict(l=0, r=0, t=6, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.markdown('<div class="sec-label">Répartition du patrimoine</div>', unsafe_allow_html=True)
    st.plotly_chart(sun, use_container_width=True, config={"displayModeBar": False})
    st.caption("Anneau intérieur : les 3 poches · anneau extérieur : le détail (clique une poche pour zoomer).")
    if crypto_warns:
        st.caption(f"⚠️ Cours momentanément indisponible pour : {', '.join(crypto_warns)} "
                   "(valeur à 0 le temps que Yahoo Finance réponde — rafraîchis dans 1 min).")

# ── ÉVOLUTION DU PATRIMOINE (courbe mensuelle) ───────────────────────────────
# 1 point par mois calendaire (month_key = clé primaire en base). Le point du
# MOIS EN COURS est réécrit à chaque visite avec la valeur actuelle, puis se
# fige quand le mois se termine — aucune gestion manuelle des mois.
st.markdown('<div class="sec-label">Évolution du patrimoine</div>', unsafe_allow_html=True)
if history:
    xs = [h["month_key"] for h in history]
    totals = [h["total"] for h in history]

    fig_h = go.Figure()
    # Courbes fines par poche (désactivables via la légende)
    for key, name, color in (("epargne", "Épargne", "#6ba7ff"),
                             ("bourse", "Bourse · ETF", "#3ecf8e"),
                             ("crypto", "Crypto", "#f7931a")):
        fig_h.add_trace(go.Scatter(
            x=xs, y=[h[key] for h in history], name=name, mode="lines",
            line=dict(color=color, width=1.4, dash="dot"), opacity=0.75,
        ))
    # Courbe principale : le total
    fig_h.add_trace(go.Scatter(
        x=xs, y=totals, name="Total", mode="lines+markers",
        line=dict(color="#f2f4f8", width=3, shape="spline", smoothing=0.6),
        marker=dict(size=7, color="#f2f4f8"),
        fill="tozeroy", fillcolor="rgba(242,244,248,0.05)",
    ))
    # Le point du mois en cours (dernier) : marqué "en cours", il bouge encore
    fig_h.add_trace(go.Scatter(
        x=[xs[-1]], y=[totals[-1]], mode="markers", showlegend=False,
        marker=dict(size=13, color="rgba(107,167,255,0.25)",
                    line=dict(color="#6ba7ff", width=2)),
        hovertemplate=f"{xs[-1]} (en cours)<br>%{{y:,.0f}} €<extra></extra>",
    ))
    fig_h.update_layout(
        height=300, margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#9aa2b1", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0),
        xaxis=dict(gridcolor="#1c1f26", zeroline=False, type="category"),
        yaxis=dict(gridcolor="#1c1f26", zeroline=False, tickformat=",.0f",
                   ticksuffix=" €", rangemode="tozero"),
        hovermode="x unified",
        annotations=[dict(x=xs[-1], y=totals[-1], text="mois en cours",
                          showarrow=False, yshift=22,
                          font=dict(color="#6ba7ff", size=11))],
    )
    st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})

    # Stats sous la courbe
    if len(totals) >= 2:
        s1, s2, s3 = st.columns(3)
        last_d = totals[-1] - totals[-2]
        first_d = totals[-1] - totals[0]
        s1.metric("Ce mois vs précédent", fmt(totals[-1]), delta=fmt(last_d))
        s2.metric(f"Depuis {xs[0]}", fmt(first_d),
                  delta=f"{(first_d / totals[0] * 100):+.1f} %" if totals[0] else None)
        best_i = max(range(1, len(totals)), key=lambda i: totals[i] - totals[i - 1])
        s3.metric("Meilleur mois", xs[best_i], delta=fmt(totals[best_i] - totals[best_i - 1]))

    st.caption("Un point par mois. Le point du mois en cours se met à jour tout seul à chaque visite "
               "(dernière valeur du mois), puis se fige quand le mois se termine.")
else:
    st.caption(f"Premier point enregistré ce mois-ci ({fmt(patrimoine)}). "
               "Un point s'ajoutera chaque mois, automatiquement à chaque visite.")

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

# ── PROJECTION ETF ───────────────────────────────────────────────────────────
# Projection sans aucun input : on part de la valeur ACTUELLE de tes ETF et on
# la laisse composer, sans nouvel apport. Trois scénarios de rendement annuel
# (prudent / moyen / optimiste) — uniquement la poche bourse ETF.
st.markdown('<div class="sec-label">Projection ETF</div>', unsafe_allow_html=True)

base_etf = bourse_live  # valeur actuelle des ETF (hors épargne, hors crypto)

if base_etf <= 0:
    st.caption("Ajoute des positions ETF dans le portefeuille bourse pour voir la projection.")
else:
    st.caption(
        f"À partir de tes **{fmt(base_etf)}** d'ETF aujourd'hui, sans nouvel apport — "
        "ce que la seule capitalisation peut donner selon le rendement annuel moyen."
    )

    HORIZON = 30  # années projetées
    SCENARIOS = [
        ("Prudent", 5.0, "#616b7c"),
        ("Moyen",   7.0, "#6ba7ff"),
        ("Optimiste", 9.0, "#3ecf8e"),
    ]
    today_year = date.today().year
    xs = list(range(today_year, today_year + HORIZON + 1))

    fig = go.Figure()
    series = {}
    for name, rate, color in SCENARIOS:
        ys = [base_etf * ((1 + rate / 100) ** y) for y in range(HORIZON + 1)]
        series[name] = ys
        fig.add_trace(go.Scatter(
            x=xs, y=ys, name=f"{name} · {rate:.0f}%/an", mode="lines",
            line=dict(color=color, width=2.5 if name == "Moyen" else 1.8,
                      dash="solid" if name == "Moyen" else "dot"),
            fill="tozeroy" if name == "Moyen" else None,
            fillcolor="rgba(107,167,255,0.08)",
        ))
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

    # Ce que tu peux espérer (scénario moyen) à des horizons clés.
    st.markdown('<div class="sec-label" style="margin-top:.5rem">Ce que tu peux espérer (scénario moyen · 7 %/an)</div>',
                unsafe_allow_html=True)
    cols = st.columns(4)
    for col, h in zip(cols, (5, 10, 20, 30)):
        val_h = base_etf * ((1 + 0.07) ** h)
        col.metric(f"Dans {h} ans", fmt(val_h), delta=fmt(val_h - base_etf))

    st.caption(
        "Hypothèse : capitalisation à rendement constant, dividendes réinvestis, sans nouvel apport ni "
        "impôt/inflation. Le passé ne garantit pas le futur — c'est un ordre de grandeur, pas une promesse."
    )
