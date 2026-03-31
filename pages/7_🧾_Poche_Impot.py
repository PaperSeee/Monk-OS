"""
Module 7 — IMPÔT OU URGENCE
Reserve tracker for taxes/emergencies and other LT deductions.
"""

import streamlit as st
from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import (
    init_db,
    get_setting,
    get_lt_capital,
    create_tax_pocket_entry,
    get_tax_pocket_entries,
    delete_tax_pocket_entry,
    mark_tax_pocket_entry_paid,
)
from utils.helpers import (
    inject_css,
    section_head,
    sub_label,
    fmt,
    get_fx_rates,
    render_long_term_sidebar_nav,
)

st.set_page_config(
    page_title="MONK-OS : Impôt ou Urgence",
    page_icon="🧾",
    layout="wide",
)

init_db()
inject_css()
render_long_term_sidebar_nav("poche_impot")

ccy = st.session_state.get("currency", "EUR")
rates = get_fx_rates() if ccy != "EUR" else {"EUR": 1.0}

section_head("MODULE 07 — IMPÔT OU URGENCE")
sub_label("Déductions LT — impôts, urgences, payouts, business")

entries = get_tax_pocket_entries(limit=300)
total_reserved = sum(float(e.get("amount", 0) or 0) for e in entries)
lt_cash_left = get_lt_capital()
pending_entries = [e for e in entries if str(e.get("status") or "En attente") != "Payé"]
paid_entries = [e for e in entries if str(e.get("status") or "") == "Payé"]

km1, km2, km3 = st.columns(3)
km1.metric("Poche cumulée", fmt(total_reserved, ccy, rates))
km2.metric("En attente", len(pending_entries))
km3.metric("Cash LT restant", fmt(lt_cash_left, ccy, rates))

st.divider()

col_form, col_info = st.columns([1.2, 1])

with col_form:
    amount = st.number_input("Montant à déduire", min_value=0.0, step=10.0, value=0.0)
    link_type = st.selectbox(
        "Lien",
        ["Impôt", "Urgence"],
        index=0,
        help="Choisis l'origine de la déduction",
    )

    source = ""
    urgency_level = ""
    if link_type == "Impôt":
        source = st.selectbox(
            "Source impôt",
            ["Crypto", "Payout", "Business", "Salaire", "Autre"],
            index=0,
            help="D'où vient cet impôt ?",
        )
    elif link_type == "Urgence":
        urgency_level = st.selectbox(
            "Degré d'urgence",
            ["Faible", "Moyen", "Élevé", "Critique"],
            index=1,
            help="Niveau de priorité de cette sortie cash",
        )

    note = st.text_area(
        "Note",
        placeholder="Ex: Provision impôt T2, TVA, réserve IS, correction payout...",
        height=90,
    )

    if st.button("➖ Ajouter à la poche", use_container_width=True):
        if amount > 0:
            create_tax_pocket_entry(
                float(amount),
                link_type,
                note,
                source=source,
                urgency_level=urgency_level,
            )
            st.success("✓ Entrée ajoutée et déduite du capital LT")
            st.rerun()
        else:
            st.error("Le montant doit être supérieur à 0")

with col_info:
    st.info(
        """
Cette page sert à réserver du cash LT pour impôts et urgences.

- Chaque entrée soustrait le montant du capital LT global.
- Le champ Lien contient seulement Impôt ou Urgence.
- Si tu choisis Impôt, précise la source (Crypto, Payout, Business, etc.).
- Si tu choisis Urgence, indique le degré d'urgence.
- Utilise la note pour garder un contexte détaillé.
        """
    )

st.divider()
sub_label("En attente de paiement")

if pending_entries:
    for entry in pending_entries:
        row_col1, row_col2, row_col3, row_col4, row_col5, row_col6 = st.columns([1.3, 0.8, 0.8, 1.1, 0.8, 0.8])
        row_col1.caption(entry.get("created_at", ""))
        row_col2.caption(entry.get("link_type", "Autre"))
        row_col3.caption(fmt(float(entry.get("amount", 0) or 0), ccy, rates))
        src = entry.get("source", "")
        urgency = entry.get("urgency_level", "")
        detail = src if src else (urgency if urgency else "—")
        row_col4.caption(detail)
        with row_col5:
            if st.button("Payé", key=f"paid_tax_{entry['id']}", use_container_width=True, type="secondary"):
                mark_tax_pocket_entry_paid(int(entry["id"]))
                st.success("Entrée marquée comme payée.")
                st.rerun()
        with row_col6:
            if st.button("Annuler", key=f"undo_tax_{entry['id']}", use_container_width=True, type="secondary"):
                refunded = delete_tax_pocket_entry(int(entry["id"]))
                if refunded > 0:
                    st.success(f"Entrée annulée. {fmt(refunded, ccy, rates)} remboursés au LT.")
                else:
                    st.warning("Entrée introuvable ou déjà supprimée.")
                st.rerun()

        if entry.get("note"):
            st.caption(f"Note: {entry['note']}")
        st.divider()
else:
    st.caption("Aucune entrée en attente.")

st.divider()
sub_label("Historique — Impôts & Urgences payés")

if paid_entries:
    for entry in paid_entries:
        row_col1, row_col2, row_col3, row_col4, row_col5 = st.columns([1.3, 0.8, 0.8, 1.1, 1.2])
        row_col1.caption(entry.get("created_at", ""))
        row_col2.caption(entry.get("link_type", "Autre"))
        row_col3.caption(fmt(float(entry.get("amount", 0) or 0), ccy, rates))
        src = entry.get("source", "")
        urgency = entry.get("urgency_level", "")
        detail = src if src else (urgency if urgency else "—")
        row_col4.caption(detail)
        paid_at = entry.get("paid_at", "")
        row_col5.caption(f"Payé: {paid_at[:10] if paid_at else '—'}")

        if entry.get("note"):
            st.caption(f"Note: {entry['note']}")
        st.divider()
else:
    st.caption("Aucun impôt/urgence payé pour l'instant.")
