"""
Module 6 — CEO REPORT (PDF Generator)
Monthly PDF report with Net Worth, finances, ETF positions, Freedom snapshot
"""

import streamlit as st
import sys
from pathlib import Path
import io
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from db.database import init_db, get_setting, get_latest_finance, get_latest_portfolio_v2, get_finances, get_sentinel_logs
from utils.helpers import inject_css, section_head, sub_label, fmt, get_fx_rates, ETF_YIELD

init_db()
inject_css()

section_head("MODULE 06 — CEO MONTHLY REPORT")

ccy   = st.session_state.get("currency", "EUR")
rates = get_fx_rates() if ccy != "EUR" else {"EUR": 1.0}

# ── Load data ─────────────────────────────────────────────────────────────────
current_savings  = float(get_setting("current_savings", "0"))
savings_goal     = float(get_setting("savings_goal", "2000"))
monk_end_raw     = get_setting("monk_mode_end_date", "2026-04-09")
portfolio_rows   = get_latest_portfolio_v2()
total_portfolio  = sum(r["shares"] * r["price"] for r in portfolio_rows)
net_worth        = current_savings + total_portfolio
latest_finance   = get_latest_finance()
sentinel_logs    = get_sentinel_logs(10)
finances         = get_finances()

# Dividend estimates
total_annual_div = sum(
    r["shares"] * r["price"] * (ETF_YIELD.get(r["ticker"], 1.5) / 100)
    for r in portfolio_rows
)

today_str = date.today().strftime("%d %B %Y")
tz_name   = st.session_state.get("timezone", "Europe/Paris")

# ── Preview ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="monk-card" style="margin-bottom:1.5rem;">
    <div class="monk-card-title">Aperçu — CEO Report · {today_str}</div>
    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:1rem;">
        <div>
            <div style="font-size:0.62rem; color:#4A5568; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.2rem;">Patrimoine Net</div>
            <div style="font-size:1.6rem; font-weight:800; color:#F0F4FF; font-family:'JetBrains Mono',monospace;">{fmt(net_worth, ccy, rates)}</div>
        </div>
        <div>
            <div style="font-size:0.62rem; color:#4A5568; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.2rem;">Portefeuille ETF</div>
            <div style="font-size:1.6rem; font-weight:800; color:#3B82F6; font-family:'JetBrains Mono',monospace;">{fmt(total_portfolio, ccy, rates)}</div>
        </div>
        <div>
            <div style="font-size:0.62rem; color:#4A5568; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.2rem;">Épargne Cash</div>
            <div style="font-size:1.6rem; font-weight:800; color:#10B981; font-family:'JetBrains Mono',monospace;">{fmt(current_savings, ccy, rates)}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Report configuration ──────────────────────────────────────────────────────
sub_label("Configuration du rapport")

col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
with col_cfg1:
    report_month = st.selectbox(
        "Mois du rapport",
        [date.today().strftime("%B %Y")],
        index=0,
    )
with col_cfg2:
    include_etf    = st.checkbox("Inclure positions ETF",    value=True)
    include_div    = st.checkbox("Inclure Dividend Tracker", value=True)
with col_cfg3:
    include_fin    = st.checkbox("Inclure finances du mois", value=True)
    include_sent   = st.checkbox("Inclure stats Sentinel",   value=True)

st.markdown("<br>", unsafe_allow_html=True)

if st.button("📄  Générer le rapport PDF", type="primary"):
    try:
        from fpdf import FPDF

        class MONKPDF(FPDF):
            def header(self):
                self.set_fill_color(13, 15, 20)
                self.rect(0, 0, 210, 297, 'F')
                # Header bar
                self.set_fill_color(22, 26, 34)
                self.rect(0, 0, 210, 22, 'F')
                # Blue accent line
                self.set_fill_color(59, 130, 246)
                self.rect(0, 22, 210, 1.5, 'F')
                self.set_font("Helvetica", "B", 14)
                self.set_text_color(240, 244, 255)
                self.set_y(6)
                self.cell(0, 10, "MONK-OS  CEO Terminal", align="L")
                self.set_font("Helvetica", "", 8)
                self.set_text_color(74, 85, 104)
                self.set_y(7)
                self.cell(0, 10, f"Monthly CEO Report · {today_str}", align="R")
                self.ln(20)

            def footer(self):
                self.set_y(-12)
                self.set_font("Helvetica", "", 7)
                self.set_text_color(45, 52, 71)
                self.cell(0, 10, f"MONK-OS V2 · Données privées · {tz_name}", align="L")
                self.cell(0, 10, f"Page {self.page_no()}", align="R")

        def h2(pdf, text):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(59, 130, 246)
            pdf.set_fill_color(22, 26, 34)
            pdf.rect(pdf.get_x(), pdf.get_y(), 180, 7, 'F')
            pdf.cell(0, 7, f"  {text.upper()}", ln=True)
            pdf.set_fill_color(59, 130, 246)
            pdf.rect(10, pdf.get_y(), 180, 0.5, 'F')
            pdf.ln(4)

        def row(pdf, label, value, value_color=(240, 244, 255)):
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(136, 146, 170)
            pdf.cell(80, 6, label, ln=False)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*value_color)
            pdf.cell(0, 6, str(value), ln=True)

        # ── Build PDF ─────────────────────────────────────────────────────
        pdf = MONKPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)

        # ── Title block ────────────────────────────────────────────────────
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(240, 244, 255)
        pdf.cell(0, 12, "NET WORTH", ln=True)
        sz = "24" if len(fmt(net_worth, ccy, rates)) < 12 else "18"
        pdf.set_font("Helvetica", "B", int(sz))
        pdf.set_text_color(59, 130, 246)
        pdf.cell(0, 10, fmt(net_worth, ccy, rates), ln=True)
        pdf.ln(3)

        col1_x = 10
        col2_x = 105

        def two_col_metric(pdf, label1, val1, label2, val2):
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(74, 85, 104)
            pdf.set_x(col1_x)
            pdf.cell(90, 4, label1.upper(), ln=False)
            pdf.set_x(col2_x)
            pdf.cell(90, 4, label2.upper(), ln=True)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(240, 244, 255)
            pdf.set_x(col1_x)
            pdf.cell(90, 7, str(val1), ln=False)
            pdf.set_x(col2_x)
            pdf.cell(90, 7, str(val2), ln=True)
            pdf.ln(3)

        two_col_metric(pdf,
            "Épargne Cash", fmt(current_savings, ccy, rates),
            "Portefeuille ETF", fmt(total_portfolio, ccy, rates))
        two_col_metric(pdf,
            "Objectif Fortress", fmt(savings_goal, ccy, rates),
            "Statut", "SÉCURISÉ" if current_savings >= savings_goal else "VULNÉRABLE")
        two_col_metric(pdf,
            "Div. Annuels Estimés", fmt(total_annual_div, ccy, rates),
            "Fin Monk Mode", monk_end_raw)

        # ── Finances ───────────────────────────────────────────────────────
        if include_fin and latest_finance:
            pdf.ln(3)
            h2(pdf, "Finances du mois")
            f = latest_finance
            total_exp = f["rent"] + f["food"] + f["transport"] + f["misc"]
            row(pdf, "Revenu net",       fmt(f["income"], ccy, rates))
            row(pdf, "Total dépenses",   fmt(total_exp, ccy, rates),    (239, 68, 68))
            row(pdf, "Investissements",  fmt(f.get("investments_etf", 0) + f.get("investments_crypto", 0) + f.get("investments_other", 0), ccy, rates), (139, 92, 246))
            row(pdf, "Épargne nette",    fmt(f["savings"], ccy, rates), (16, 185, 129))
            if f.get("note"):
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(74, 85, 104)
                pdf.cell(0, 5, f"Note: {f['note']}", ln=True)

        # ── ETF Positions ──────────────────────────────────────────────────
        if include_etf and portfolio_rows:
            pdf.ln(3)
            h2(pdf, "Positions ETF")
            # Table header
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(59, 130, 246)
            pdf.set_fill_color(22, 26, 34)
            pdf.cell(45, 6, "Ticker", border=0, fill=True)
            pdf.cell(25, 6, "Parts", border=0, fill=True, align="R")
            pdf.cell(35, 6, "Prix", border=0, fill=True, align="R")
            pdf.cell(40, 6, "Valeur", border=0, fill=True, align="R")
            pdf.cell(35, 6, "Cible %", border=0, fill=True, align="R")
            pdf.ln()
            # Rows
            pdf.set_font("Helvetica", "", 9)
            for r in portfolio_rows:
                val = r["shares"] * r["price"]
                pdf.set_text_color(240, 244, 255)
                pdf.cell(45, 5.5, r["ticker"])
                pdf.set_text_color(136, 146, 170)
                pdf.cell(25, 5.5, f"{r['shares']:.2f}", align="R")
                pdf.cell(35, 5.5, fmt(r["price"], ccy, rates), align="R")
                pdf.set_text_color(59, 130, 246)
                pdf.cell(40, 5.5, fmt(val, ccy, rates), align="R")
                pdf.set_text_color(136, 146, 170)
                pdf.cell(35, 5.5, f"{r['target_pct']:.0f}%", align="R")
                pdf.ln()
            # Total
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(59, 130, 246)
            pdf.cell(105, 5.5, "TOTAL")
            pdf.cell(40, 5.5, fmt(total_portfolio, ccy, rates), align="R")
            pdf.ln()

        # ── Dividends ─────────────────────────────────────────────────────
        if include_div and portfolio_rows:
            pdf.ln(3)
            h2(pdf, "Dividend Tracker (théorique)")
            row(pdf, "Dividendes annuels estimés", fmt(total_annual_div, ccy, rates), (16, 185, 129))
            row(pdf, "Dividendes mensuels estimés", fmt(total_annual_div / 12, ccy, rates), (16, 185, 129))
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(74, 85, 104)
            pdf.multi_cell(0, 4, "Note: Ces ETFs sont ACC (accumulants). Ces chiffres representent la croissance implicite reinvestie dans le prix de part.")

        # ── Sentinel ──────────────────────────────────────────────────────
        if include_sent and sentinel_logs:
            pdf.ln(3)
            h2(pdf, "Statistiques Sentinel")
            total_s    = len(sentinel_logs)
            allowed_s  = sum(1 for l in sentinel_logs if l["verdict"] == "AUTORISÉ")
            blocked_s  = sum(1 for l in sentinel_logs if l["verdict"] == "BLOQUÉ")
            disc_score = (allowed_s / total_s * 100) if total_s > 0 else 100
            row(pdf, "Score Discipline",   f"{disc_score:.0f}%",  (16, 185, 129) if disc_score >= 80 else (245, 158, 11))
            row(pdf, "Décisions autorisées", str(allowed_s))
            row(pdf, "Décisions bloquées",   str(blocked_s),        (239, 68, 68))

        # ── Footer note ────────────────────────────────────────────────────
        pdf.ln(6)
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(45, 52, 71)
        pdf.multi_cell(0, 4, f"Généré le {today_str} · MONK-OS V2 CEO Terminal · Données 100% privées sur Mac.")

        # ── Output ─────────────────────────────────────────────────────────
        pdf_bytes = bytes(pdf.output())
        filename  = f"MONK-OS_CEO_Report_{date.today().strftime('%Y-%m')}.pdf"

        st.success("✓ Rapport généré avec succès !")
        st.download_button(
            label="⬇️  Télécharger le PDF",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
        )

    except ImportError:
        st.error("⚠ `fpdf2` n'est pas installé. Lance : `pip install fpdf2`")
    except Exception as e:
        st.error(f"Erreur lors de la génération : {e}")
        import traceback
        st.code(traceback.format_exc())

# ── Summary table preview ─────────────────────────────────────────────────────
st.divider()
sub_label("Historique des rapports — aperçu")

if finances:
    import pandas as pd
    df = pd.DataFrame(finances)
    if "investments_etf" not in df.columns:
        df["investments_etf"] = 0.0
    if "investments_crypto" not in df.columns:
        df["investments_crypto"] = 0.0
    if "investments_other" not in df.columns:
        df["investments_other"] = 0.0
    df["Total Invest."] = df["investments_etf"] + df["investments_crypto"] + df["investments_other"]

    summary = df[["month_key","income","savings","Total Invest."]].copy()
    summary.columns = ["Mois","Revenu","Épargne Nette","Investissements"]

    # Currency conversion for display
    for col in ["Revenu","Épargne Nette","Investissements"]:
        if ccy != "EUR":
            r = rates.get(ccy, 1.0)
            summary[col] = summary[col] * r
        summary[col] = summary[col].map(lambda x: f"{x:,.0f}")

    st.dataframe(summary, use_container_width=True, hide_index=True)
