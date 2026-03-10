"""
MONK-OS V2 — Shared Utilities & Helpers
Currency formatting, FX rates, Plotly theme, ETF catalog
"""

import streamlit as st
import yfinance as yf
from datetime import datetime
import pytz

# ══════════════════════════════════════════════════════════
#  ETF CATALOG
# ══════════════════════════════════════════════════════════

ETF_CATALOG = {
    "VWCE.DE":  "Vanguard All-World (ACC)",
    "SXRV.DE":  "iShares Nasdaq 100 (ACC)",
    "MEUD.PA":  "Amundi MSCI Europe (ACC)",
    "EIMI.PA":  "iShares EM IMI (ACC)",
    "IUSN.DE":  "iShares MSCI World Small Cap",
    "IWDA.AS":  "iShares Core MSCI World (ACC)",
    "CSPX.L":   "iShares S&P 500 (ACC)",
    "EXSA.DE":  "iShares EURO STOXX 50 (DIS)",
    "XDWD.DE":  "Xtrackers MSCI World (ACC)",
    "GSBE07.MI":"BTP Italia 2027",
    "BTC-USD":  "Bitcoin (via Coinbase)",
    "ETH-USD":  "Ethereum",
}

# Estimated annual dividend/yield % (for accumulating ETFs: theoretical reinvested)
ETF_YIELD = {
    "VWCE.DE": 1.8,
    "SXRV.DE": 0.5,
    "MEUD.PA": 2.5,
    "EIMI.PA": 2.2,
    "IUSN.DE": 1.5,
    "IWDA.AS": 1.6,
    "CSPX.L":  1.3,
    "EXSA.DE": 3.2,
    "XDWD.DE": 1.7,
    "BTC-USD":  0.0,
    "ETH-USD":  0.0,
}

# ══════════════════════════════════════════════════════════
#  CURRENCY
# ══════════════════════════════════════════════════════════

CURRENCY_SYMBOLS = {
    "EUR": "€",
    "USD": "$",
    "AED": "د.إ",
}

CURRENCY_LOCALES = {
    "EUR": "fr_FR",
    "USD": "en_US",
    "AED": "ar_AE",
}

CURRENCY_PAIRS = {
    "USD": "EURUSD=X",
    "AED": "EURAED=X",
}


@st.cache_data(ttl=3600)
def get_fx_rates() -> dict:
    """Returns EUR → other currency rates. EUR base = 1.0."""
    rates = {"EUR": 1.0}
    for ccy, ticker in CURRENCY_PAIRS.items():
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if not hist.empty:
                rates[ccy] = float(hist["Close"].iloc[-1])
            else:
                rates[ccy] = _fallback_rate(ccy)
        except Exception:
            rates[ccy] = _fallback_rate(ccy)
    return rates


def _fallback_rate(ccy: str) -> float:
    return {"USD": 1.09, "AED": 4.00}.get(ccy, 1.0)


def convert(val: float, target_ccy: str, rates: dict) -> float:
    """Convert a EUR value to target currency."""
    return val * rates.get(target_ccy, 1.0)


def fmt(val: float, ccy: str = "EUR", rates: dict | None = None) -> str:
    """Format a monetary value with currency symbol."""
    if rates and ccy != "EUR":
        val = convert(val, ccy, rates)
    sym = CURRENCY_SYMBOLS.get(ccy, "€")
    if ccy == "AED":
        return f"{val:,.0f} {sym}"
    return f"{sym}{val:,.2f}"


# ══════════════════════════════════════════════════════════
#  PLOTLY THEME
# ══════════════════════════════════════════════════════════

def plotly_theme() -> dict:
    return dict(
        paper_bgcolor="#161A22",
        plot_bgcolor="#161A22",
        font=dict(family="Inter, sans-serif", color="#8892AA", size=12),
        xaxis=dict(
            gridcolor="#232836",
            linecolor="#232836",
            tickfont=dict(color="#4A5568", size=11),
        ),
        yaxis=dict(
            gridcolor="#232836",
            linecolor="#232836",
            tickfont=dict(color="#4A5568", size=11),
        ),
    )


# ══════════════════════════════════════════════════════════
#  DATETIME
# ══════════════════════════════════════════════════════════

TIMEZONES = {
    "🇧🇪 Bruxelles": "Europe/Brussels",
    "🇫🇷 Paris":     "Europe/Paris",
    "🇦🇪 Dubaï":     "Asia/Dubai",
    "🇬🇧 Londres":   "Europe/London",
    "🌐 UTC":        "UTC",
    "🇺🇸 New York":  "America/New_York",
}


def get_now_str(tz_name: str = "Europe/Paris") -> tuple[str, str]:
    """Returns (date_str, time_str) in the given timezone."""
    tz  = pytz.timezone(tz_name)
    now = datetime.now(tz)
    return now.strftime("%A %d %B %Y"), now.strftime("%H:%M")


# ══════════════════════════════════════════════════════════
#  SHARED CSS INJECTOR
# ══════════════════════════════════════════════════════════

def inject_css():
    from pathlib import Path
    css_path = Path(__file__).parent.parent / "assets" / "style.css"
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def section_head(label: str):
    st.markdown(f'<div class="section-head">{label}</div>', unsafe_allow_html=True)


def sub_label(text: str):
    st.markdown(f"""
    <div style="font-size:0.62rem; color:#4A5568; letter-spacing:0.2em;
                text-transform:uppercase; margin-bottom:0.8rem; font-weight:500;">
        ▸ {text}
    </div>
    """, unsafe_allow_html=True)
