"""
Module 3 V2 — FREEDOM SIMULATOR
Compound interest, Monte Carlo, Burn Rate, Wealth Velocity, Multi-Scenario
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db.database import init_db, get_setting
from utils.helpers import inject_css, section_head, sub_label, plotly_theme, fmt, get_fx_rates

init_db()
inject_css()

import numpy as np
import plotly.graph_objects as go

section_head("MODULE 03 — FREEDOM SIMULATOR V2")

ccy   = st.session_state.get("currency", "EUR")
rates = get_fx_rates() if ccy != "EUR" else {"EUR": 1.0}

default_savings = float(get_setting("current_savings", "0"))
default_monthly = float(get_setting("monthly_budget", "1250"))

sub_label("Paramètres de simulation")

col_a, col_b, col_c = st.columns(3)
with col_a:
    initial_capital = st.number_input("Capital initial (€)", min_value=0.0,
                                       value=default_savings, step=100.0)
    monthly_contrib = st.number_input("Versement mensuel (€)", min_value=0.0,
                                       value=200.0, step=50.0)
with col_b:
    annual_return   = st.number_input("Rendement annuel moyen (%)", min_value=0.0,
                                       max_value=30.0, value=7.0, step=0.5)
    years           = st.slider("Horizon de projection (ans)", 5, 30, 20)
with col_c:
    volatility      = st.number_input("Volatilité annuelle (%)", min_value=0.0,
                                       max_value=40.0, value=12.0, step=1.0)
    n_simulations   = st.selectbox("Simulations Monte Carlo", [200, 500, 1000], index=1)

col_exp, col_wv = st.columns(2)
with col_exp:
    monthly_expenses = st.number_input("Dépenses mensuelles (€)", min_value=1.0,
                                        value=max(default_monthly - 200, 800.0), step=50.0)
with col_wv:
    weekly_hours = st.number_input("Heures travaillées / semaine", min_value=1.0,
                                    max_value=80.0, value=35.0, step=1.0)

if st.button("🚀  Lancer la simulation", type="primary"):
    r_monthly  = (annual_return / 100) / 12
    sigma_m    = (volatility / 100) / np.sqrt(12)
    n_months   = years * 12
    months_arr = np.arange(n_months + 1)

    # ── Deterministic FV ──────────────────────────────────────────────────
    if r_monthly > 0:
        fv_contrib = monthly_contrib * ((1 + r_monthly)**n_months - 1) / r_monthly
    else:
        fv_contrib = monthly_contrib * n_months
    fv_total = initial_capital * (1 + r_monthly)**n_months + fv_contrib

    # ── Scenario: savings only (0% return) ─────────────────────────────────
    savings_only = [initial_capital + monthly_contrib * m for m in range(n_months + 1)]

    # ── Monte Carlo ───────────────────────────────────────────────────────
    np.random.seed(42)
    results = np.zeros((n_simulations, n_months + 1))
    for i in range(n_simulations):
        portfolio = initial_capital
        rets      = np.random.normal(loc=(annual_return/100)/12, scale=sigma_m, size=n_months)
        results[i, 0] = initial_capital
        for m, ret in enumerate(rets):
            portfolio = portfolio * (1 + ret) + monthly_contrib
            results[i, m + 1] = portfolio

    years_x = months_arr / 12
    p5  = np.percentile(results, 5,  axis=0)
    p25 = np.percentile(results, 25, axis=0)
    p50 = np.percentile(results, 50, axis=0)
    p75 = np.percentile(results, 75, axis=0)
    p95 = np.percentile(results, 95, axis=0)

    # ── Key metrics ───────────────────────────────────────────────────────
    st.divider()
    target_year    = 2026 + years
    total_invested = initial_capital + monthly_contrib * n_months
    gain_base      = p50[-1] - total_invested

    sub_label(f"Résultats — Patrimoine en {target_year}")

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("🐻 Bear (P5)",     fmt(p5[-1], ccy, rates))
    mc2.metric("📊 Médiane (P50)", fmt(p50[-1], ccy, rates))
    mc3.metric("🚀 Bull (P95)",    fmt(p95[-1], ccy, rates))
    mc4.metric("📐 FV Théorique",  fmt(fv_total, ccy, rates))

    st.markdown("<br>", unsafe_allow_html=True)
    mc5, mc6, mc7, mc8 = st.columns(4)
    mc5.metric("Capital investi",  fmt(total_invested, ccy, rates))
    mc6.metric("Gain médian",      fmt(gain_base, ccy, rates),
               delta=f"+{gain_base/total_invested*100:.0f}%" if total_invested else "")
    mc7.metric("Multiplicateur",   f"{p50[-1]/total_invested:.1f}x" if total_invested else "—")
    mc8.metric("Taux de réussite", f"{round(np.mean(results[:,-1] > total_invested)*100)}%")

    # ── WEALTH VELOCITY ────────────────────────────────────────────────────
    st.divider()
    sub_label("Wealth Velocity — Capital accumulé par heure travaillée")

    annual_hours     = weekly_hours * 52
    monthly_hours    = annual_hours / 12
    capital_per_hour = monthly_contrib / monthly_hours if monthly_hours > 0 else 0
    # Add compound gains
    annual_gain_est  = p50[12] - p50[0] if len(p50) > 12 else p50[-1] - p50[0]
    total_per_hour   = (monthly_contrib * 12 + annual_gain_est) / annual_hours if annual_hours > 0 else 0

    wv1, wv2, wv3 = st.columns(3)
    wv1.metric("💶 Épargne / heure travaillée",
               fmt(capital_per_hour, ccy, rates))
    wv2.metric("📈 Capital total accumulé / heure (an 1)",
               fmt(total_per_hour, ccy, rates))
    wv3.metric("🕑 Heures travaillées / an",
               f"{annual_hours:.0f} h")

    st.markdown(f"""
    <div style="font-size:0.75rem; color:#4A5568; margin-top:0.5rem; line-height:1.7;">
        Sur la base de <b style="color:#F0F4FF;">{weekly_hours:.0f}h/semaine</b>
        et <b style="color:#F0F4FF;">{fmt(monthly_contrib, ccy, rates)}/mois</b> investis,
        chaque heure travaillée génère
        <b style="color:#3B82F6; font-family:'JetBrains Mono',monospace;">
            {fmt(total_per_hour, ccy, rates)}
        </b> de patrimoine (avec les intérêts composés).
    </div>
    """, unsafe_allow_html=True)

    # ── Multi-Scenario Chart ───────────────────────────────────────────────
    st.divider()
    sub_label("Multi-Scénarios — Projection comparative")

    fig = go.Figure()

    # Bull/bear bands
    fig.add_trace(go.Scatter(
        x=list(years_x)+list(years_x[::-1]),
        y=list(p95)+list(p5[::-1]),
        fill="toself", fillcolor="rgba(59,130,246,0.05)",
        line=dict(color="rgba(0,0,0,0)"),
        name="P5–P95 (scénario investissement)", showlegend=True,
    ))
    fig.add_trace(go.Scatter(
        x=list(years_x)+list(years_x[::-1]),
        y=list(p75)+list(p25[::-1]),
        fill="toself", fillcolor="rgba(59,130,246,0.10)",
        line=dict(color="rgba(0,0,0,0)"),
        name="P25–P75", showlegend=True,
    ))

    # Scenario 1: Investment at 7%
    fig.add_trace(go.Scatter(
        x=years_x, y=p50,
        line=dict(color="#3B82F6", width=2.5),
        name=f"Médiane invest. {annual_return:.1f}% (P50)",
    ))
    # Scenario 2: Savings only
    fig.add_trace(go.Scatter(
        x=years_x, y=savings_only,
        line=dict(color="#8892AA", width=2, dash="dash"),
        name="Épargne seule (0% rendement)",
    ))
    # Bear
    fig.add_trace(go.Scatter(
        x=years_x, y=p5,
        line=dict(color="#EF4444", width=1.5, dash="dash"),
        name="Pire scénario (P5)",
    ))
    # Bull
    fig.add_trace(go.Scatter(
        x=years_x, y=p95,
        line=dict(color="#10B981", width=1.5, dash="dot"),
        name="Meilleur scénario (P95)",
    ))

    # Difference annotation at end
    diff = p50[-1] - savings_only[-1]
    fig.add_annotation(
        x=years, y=p50[-1],
        text=f"+{fmt(diff, ccy, rates)} vs épargne seule",
        font=dict(size=10, color="#3B82F6", family="Inter"),
        showarrow=True, arrowcolor="#3B82F6",
        arrowhead=2, arrowsize=1, arrowwidth=1,
        bgcolor="#161A22", bordercolor="#3B82F6", borderwidth=1,
        ax=-80, ay=-30,
    )

    fig.update_layout(
        **plotly_theme(), height=420,
        margin=dict(t=20, b=50, l=60, r=20),
        xaxis_title="Années", yaxis_title=f"Patrimoine ({ccy})",
        hovermode="x unified",
        legend=dict(x=0.02, y=0.98,
                    font=dict(size=10, family="Inter", color="#8892AA"),
                    bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_yaxes(tickformat=",.0f", ticksuffix=f" {ccy}")
    st.plotly_chart(fig, use_container_width=True)

    # ── Burn Rate ─────────────────────────────────────────────────────────
    st.divider()
    sub_label("Burn Rate — Combien de temps sans revenus ?")

    burn_months = initial_capital / monthly_expenses if monthly_expenses > 0 else 0
    burn_years  = burn_months / 12

    bc1, bc2, bc3 = st.columns(3)
    bc1.metric("Épargne disponible", fmt(initial_capital, ccy, rates))
    bc2.metric("Dépenses / mois",    fmt(monthly_expenses, ccy, rates))
    bc3.metric("🔥 Survie sans revenus", f"{burn_months:.0f} mois",
               delta=f"{burn_years:.1f} ans")

    gauge_max = max(burn_months * 1.5, 24)
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number",
        value=burn_months,
        number=dict(suffix=" mois", font=dict(color="#F0F4FF", size=40, family="JetBrains Mono")),
        gauge=dict(
            axis=dict(range=[0, gauge_max], tickcolor="#4A5568",
                      tickfont=dict(color="#4A5568", size=10)),
            bar=dict(color="#3B82F6", thickness=0.8),
            bgcolor="#161A22", bordercolor="#232836", borderwidth=1,
            steps=[
                dict(range=[0, 3],          color="#2D1A1A"),
                dict(range=[3, 6],          color="#2A1F10"),
                dict(range=[6, 12],         color="#1A2A1A"),
                dict(range=[12, gauge_max], color="#162035"),
            ],
            threshold=dict(line=dict(color="#EF4444", width=3), value=6),
        ),
        title=dict(text="Mois de runway", font=dict(color="#8892AA", size=13, family="Inter")),
    ))
    fig_g.update_layout(
        paper_bgcolor="#161A22", font=dict(family="Inter"),
        height=280, margin=dict(t=40, b=10, l=30, r=30),
    )
    st.plotly_chart(fig_g, use_container_width=True)

else:
    st.markdown(f"""
    <div class="monk-card" style="text-align:center; padding:3rem; margin-top:1rem;">
        <div style="font-size:2.5rem; margin-bottom:1rem;">🔮</div>
        <div style="font-size:0.85rem; color:#4A5568; line-height:1.8;">
            Configure les paramètres et lance la simulation<br>
            pour projeter ta retraite en {2026+20}.
        </div>
    </div>
    """, unsafe_allow_html=True)
