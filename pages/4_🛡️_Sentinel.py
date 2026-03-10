"""
Module 4 V2 — THE SENTINEL
Anti-Tilt journal, Fear/Greed index, discipline lock integration
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db.database import init_db, log_sentinel, get_sentinel_logs, get_setting
from utils.helpers import inject_css, section_head, sub_label

init_db()
inject_css()

import pandas as pd
import random

section_head("MODULE 04 — THE SENTINEL V2")

st.markdown("""
<div class="monk-card" style="margin-bottom:1.5rem;">
    <div class="monk-card-title">Le Mur de Discipline</div>
    <div style="font-size:0.82rem; color:#8892AA; line-height:1.8;">
        Avant tout trade ou dépense non planifiée, réponds honnêtement. 
        Le Sentinel enregistre et te protège de toi-même.
    </div>
</div>
""", unsafe_allow_html=True)

# ── Fear & Greed Index ────────────────────────────────────────────────────────
sub_label("Indice Peur / Gourmandise — Évalue ton état du marché")

st.markdown("""
<div class="greed-meter-bar"></div>
<div style="display:flex; justify-content:space-between; font-size:0.6rem;
            color:#4A5568; margin-bottom:0.5rem; letter-spacing:0.05em;">
    <span>😱 Peur Extrême</span>
    <span>😰 Peur</span>
    <span>😐 Neutre</span>
    <span>😏 Gourmandise</span>
    <span>🤑 Euphorie</span>
</div>
""", unsafe_allow_html=True)

greed_index = st.slider(
    "Mon état d'esprit du marché aujourd'hui",
    min_value=0, max_value=100, value=50, step=5,
    help="0 = Peur extrême, 100 = Euphorie totale",
    label_visibility="collapsed",
)

# Greed/Fear labels
if greed_index >= 80:
    greed_label = "🤑 EUPHORIE"
    greed_color = "#EF4444"
    greed_badge = "badge-vulnerable"
elif greed_index >= 60:
    greed_label = "😏 GOURMANDISE"
    greed_color = "#F59E0B"
    greed_badge = "badge-warning"
elif greed_index >= 40:
    greed_label = "😐 NEUTRE"
    greed_color = "#3B82F6"
    greed_badge = "badge-neutral"
elif greed_index >= 20:
    greed_label = "😰 PEUR"
    greed_color = "#8B5CF6"
    greed_badge = "badge-neutral"
else:
    greed_label = "😱 PEUR EXTRÊME"
    greed_color = "#8B5CF6"
    greed_badge = "badge-neutral"

st.markdown(f"""
<div style="text-align:center; margin:0.5rem 0 1rem 0;">
    <span class="{greed_badge}">{greed_label} — {greed_index}/100</span>
</div>
""", unsafe_allow_html=True)

# Contextual warnings
if greed_index >= 70:
    st.markdown(f"""
    <div class="monk-card" style="border-color:#EF4444; margin-bottom:1rem;">
        <div style="font-size:0.85rem; font-weight:700; color:#EF4444;
                    font-family:'JetBrains Mono',monospace; margin-bottom:0.5rem;">
            📉 RAPPEL SENTINEL — MARS 2026
        </div>
        <div style="font-size:0.78rem; color:#8892AA; line-height:1.7;">
            Tu es en mode <b style="color:#EF4444;">Gourmandise ({greed_index}/100)</b>.
            En mars 2026, le marché a corrigé de -15% en quelques semaines.<br>
            Les décisions prises en euphorie génèrent des pertes réelles.<br>
            <b style="color:#F0F4FF;">Ta Forteresse d'abord. Le marché sera là demain.</b>
        </div>
    </div>
    """, unsafe_allow_html=True)
elif greed_index <= 20:
    st.markdown(f"""
    <div class="monk-card" style="border-color:#8B5CF6; margin-bottom:1rem;">
        <div style="font-size:0.85rem; font-weight:700; color:#8B5CF6;
                    font-family:'JetBrains Mono',monospace; margin-bottom:0.5rem;">
            🤔 SIGNAL SENTINEL — PEUR EXTRÊME
        </div>
        <div style="font-size:0.78rem; color:#8892AA; line-height:1.7;">
            Le marché t'effraie. Ce sentiment peut être fondé — ou c'est une opportunité.<br>
            <b style="color:#F0F4FF;">Attends 48h avant toute décision.</b> Les fondamentaux changent rarement en 24h.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Discipline Questionnaire ─────────────────────────────────────────────────
sub_label("Protocole d'évaluation")

col_q1, col_q2 = st.columns(2)
with col_q1:
    is_calm = st.radio(
        "Question 1 — État émotionnel",
        ["✅ Oui, je suis calme et rationnel",
         "❌ Non, je suis sous pression / émotionnel"],
        index=0, help="Si tu n'es PAS calme, le Monk Mode interdit tout trade."
    )
with col_q2:
    is_planned = st.radio(
        "Question 2 — Type de décision",
        ["✅ Achat programmé (dans le plan)",
         "⚠️  Légère déviation (cas exceptionnel)",
         "🚨 Achat impulsif (hors plan total)"],
        index=0, help="Tout achat impulsif déclenche l'alerte Sentinel."
    )

action_desc = st.text_area(
    "Décris ton action",
    placeholder="Ex: Achat de 5 parts VWCE.DE pour 340 € — versement mensuel programmé",
    height=90,
)

# ── Verdict ──────────────────────────────────────────────────────────────────
calm_val = "OUI" if "Oui" in is_calm else "NON"
plan_val = ("PROGRAMMÉ" if "programmé" in is_planned.lower()
            else "DÉVIATION" if "déviation" in is_planned.lower()
            else "IMPULSIF")

# Greed override
if greed_index >= 70 and plan_val != "PROGRAMMÉ":
    verdict = "BLOQUÉ"
elif calm_val == "NON" or plan_val == "IMPULSIF":
    verdict = "BLOQUÉ"
elif plan_val == "DÉVIATION" or greed_index >= 60:
    verdict = "AVERTISSEMENT"
else:
    verdict = "AUTORISÉ"

st.markdown("<br>", unsafe_allow_html=True)

if verdict == "BLOQUÉ":
    st.markdown("""
    <div class="sentinel-alert">
        <div class="sentinel-alert-text">
            ⛔ ALERTE : COMPORTEMENT DE JOUEUR DÉTECTÉ<br>
            REVIENS AU MONK MODE.
        </div>
        <div style="font-size:0.82rem; color:#EF4444; margin-top:1rem; font-weight:400;
                    font-family:'Inter',sans-serif;">
            Tu n'es pas en état de trader. Ferme cette page.<br>
            Reviens demain, tête froide.
        </div>
    </div>
    """, unsafe_allow_html=True)
elif verdict == "AVERTISSEMENT":
    st.markdown(f"""
    <div class="monk-card" style="border-color:#F59E0B; text-align:center;">
        <div style="color:#F59E0B; font-weight:700; font-family:'JetBrains Mono',monospace;
                    letter-spacing:0.06em;">⚠️ DÉVIATION DÉTECTÉE</div>
        <div style="font-size:0.8rem; color:#8892AA; margin-top:0.5rem; line-height:1.6;">
            {"Ton indice de gourmandise est élevé (" + str(greed_index) + "/100). " if greed_index >= 60 else ""}
            Tu t'écartes du plan. Es-tu vraiment certain ?
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="monk-card" style="border-color:#10B981; text-align:center;">
        <div style="color:#10B981; font-weight:700; font-family:'JetBrains Mono',monospace;
                    letter-spacing:0.06em;">✓ MONK MODE VALIDÉ</div>
        <div style="font-size:0.8rem; color:#8892AA; margin-top:0.5rem;">
            Discipline confirmée. Tu peux procéder selon ton plan.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col_s, col_sp = st.columns([1, 3])
with col_s:
    if st.button("📋  Enregistrer dans le journal", type="primary"):
        if not action_desc.strip():
            st.error("⚠ Décris ton action avant d'enregistrer.")
        else:
            log_sentinel(calm_val, plan_val, action_desc, verdict, greed_index)
            if verdict == "BLOQUÉ":
                st.error("🚨 Action BLOQUÉE enregistrée.")
            elif verdict == "AVERTISSEMENT":
                st.warning("⚠ Action avec avertissement enregistrée.")
            else:
                st.success("✓ Action AUTORISÉE enregistrée.")

# ── Analytics ─────────────────────────────────────────────────────────────────
st.divider()
logs = get_sentinel_logs(20)
if logs:
    total      = len(logs)
    blocked_n  = sum(1 for l in logs if l["verdict"] == "BLOQUÉ")
    allowed_n  = sum(1 for l in logs if l["verdict"] == "AUTORISÉ")
    warn_n     = sum(1 for l in logs if l["verdict"] == "AVERTISSEMENT")
    disc_score = (allowed_n / total * 100) if total > 0 else 100
    avg_greed  = sum(l.get("greed_index", 50) for l in logs) / total

    sa, sb, sc, sd, se = st.columns(5)
    sa.metric("Score Discipline",   f"{disc_score:.0f}%")
    sb.metric("✅ Autorisés",        allowed_n)
    sc.metric("⚠️  Avertissements",  warn_n)
    sd.metric("🚨 Bloqués",          blocked_n)
    se.metric("😏 Greed Moyen",      f"{avg_greed:.0f}/100")

    st.markdown("<br>", unsafe_allow_html=True)
    sub_label("Journal — 20 dernières entrées")

    df = pd.DataFrame(logs)[["timestamp","is_calm","is_planned","action","verdict","greed_index"]]
    df.columns = ["Horodatage","Calme","Type","Action","Verdict","Greed"]

    def color_verdict(val):
        if val == "BLOQUÉ":          return "color: #EF4444; font-weight: 600;"
        elif val == "AVERTISSEMENT": return "color: #F59E0B; font-weight: 600;"
        return "color: #10B981; font-weight: 600;"

    styled = df.style.applymap(color_verdict, subset=["Verdict"])
    st.dataframe(styled, use_container_width=True, hide_index=True)
else:
    st.markdown("""
    <div class="monk-card" style="text-align:center; padding:2.5rem;">
        <div style="font-size:0.85rem; color:#4A5568;">
            Aucune entrée. Commence à enregistrer tes décisions.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Quotes ───────────────────────────────────────────────────────────────────
st.divider()
quotes = [
    "« La discipline est le pont entre les objectifs et les accomplissements. »",
    "« L'impulsion d'aujourd'hui est la perte de demain. »",
    "« Le marché récompense la patience, pas l'activité. »",
    "« Be fearful when others are greedy. Be greedy when others are fearful. — Buffett »",
    "« In investing, what is comfortable is rarely profitable. — Robert Arnott »",
    "« The stock market is designed to transfer money from the Active to the Patient. — Buffett »",
]
st.markdown(f"""
<div style="text-align:center; padding:1.5rem 0;">
    <div style="font-size:0.78rem; color:#4A5568; font-style:italic; line-height:1.8;
                max-width:600px; margin:0 auto;">
        {random.choice(quotes)}
    </div>
</div>
""", unsafe_allow_html=True)
