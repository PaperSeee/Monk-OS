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
    "SXR8.DE":  "iShares Core S&P 500 USD (ACC)",
    "IUSN.DE":  "iShares MSCI World Small Cap USD (ACC)",
    "IS3N.DE":  "iShares Core MSCI EM IMI USD (ACC)",
    "MEUD.PA":  "Amundi Core STOXX Europe 600 EUR (ACC)",
    "VWCE.DE":  "Vanguard All-World (ACC)",
    "SXRV.DE":  "iShares Nasdaq 100 (ACC)",
    "EIMI.PA":  "iShares EM IMI (ACC)",
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
    "SXR8.DE": 1.3,
    "IUSN.DE": 1.5,
    "IS3N.DE": 2.2,
    "MEUD.PA": 2.8,
    "VWCE.DE": 1.8,
    "SXRV.DE": 0.5,

    "EIMI.PA": 2.2,
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


def render_pillar_top_nav(current_page: str):
    """Render a compact top-right custom menu for Dashboard/LT/MT/CT pages."""
    items = {
        "app": ("🏠 Dashboard", "app.py"),
        "lt": ("🏰 LT Épargne", "pages/1_🏰_Fortress_One.py"),
        "mt": ("📈 MT Trading", "pages/_2_MT_Trading.py"),
        "ct": ("💰 CT Business", "pages/_3_CT_Business.py"),
    }

    options = ["app", "lt", "mt", "ct"]
    labels = {key: items[key][0] for key in options}

    spacer_col, nav_col = st.columns([3.8, 1.2])
    with nav_col:
        selected = st.selectbox(
            "Navigation",
            options,
            format_func=lambda value: labels[value],
            index=options.index(current_page),
            key=f"top_nav_{current_page}",
            label_visibility="collapsed",
        )
        if selected != current_page:
            st.switch_page(items[selected][1])


def render_modules_quick_menu(key_suffix: str = "default"):
    """Render quick access to classic MONK-OS module pages."""
    module_items = {
        "🏰 Fortress One": "pages/1_🏰_Fortress_One.py",
        "📈 Equity Engine": "pages/2_📈_Equity_Engine.py",
        "🔮 Freedom Simulator": "pages/3_🔮_Freedom_Simulator.py",
        "🛡️ Sentinel": "pages/4_🛡️_Sentinel.py",
        "📄 CEO Report": "pages/6_📄_CEO_Report.py",
        "🧾 Impôt ou Urgence": "pages/7_🧾_Poche_Impot.py",
    }

    st.markdown("""
    <div style="font-size:0.58rem; color:#4A5568; letter-spacing:0.2em;
                text-transform:uppercase; margin-bottom:0.5rem; font-weight:500;">
        Modules historiques
    </div>
    """, unsafe_allow_html=True)

    module_labels = list(module_items.keys())
    selected_module = st.selectbox(
        "Choisir un module",
        module_labels,
        key=f"modules_quick_select_{key_suffix}",
        label_visibility="collapsed",
    )

    last_key = f"modules_quick_last_{key_suffix}"
    if last_key not in st.session_state:
        st.session_state[last_key] = selected_module
    elif selected_module != st.session_state[last_key]:
        st.session_state[last_key] = selected_module
        st.switch_page(module_items[selected_module])


def render_long_term_sidebar_nav(key_suffix: str = "default"):
    """Render shared sidebar nav for long-term module pages."""
    with st.sidebar:
        st.markdown('<div style="padding:0.4rem 0 0.2rem 0; border-bottom:1px solid #232836;">', unsafe_allow_html=True)
        st.image("assets/monk_logo.svg", use_container_width=True)
        st.markdown("""
        <div style="text-align:center; padding-bottom:0.5rem;">
            <div style="font-size:0.56rem; color:#5DA8FF; letter-spacing:0.26em; text-transform:uppercase; margin-top:0.32rem; font-weight:700;">
                Fortress Stack
            </div>
        </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
        if st.button("← Dashboard", use_container_width=True, key=f"go_dashboard_{key_suffix}"):
            st.switch_page("app.py")

        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        render_modules_quick_menu(key_suffix)
