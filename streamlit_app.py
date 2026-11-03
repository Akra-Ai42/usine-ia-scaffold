"""Vigie SOC — UI Streamlit minimale."""
import os

import requests
import streamlit as st

API_BASE = os.getenv("VIGIE_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Vigie SOC", page_icon="🛡️", layout="wide")

SEVERITY_COLOR = {
    "CRITICAL": "🔴",
    "HIGH": "🟠",
    "MEDIUM": "🟡",
    "LOW": "🟢",
}

STATUS_LABEL = {
    "open": "Ouvert",
    "in_progress": "En cours",
    "resolved": "Résolu",
    "closed": "Clôturé",
}

RECO_STATUS_COLOR = {
    "pending": "⏳",
    "approved": "✅",
    "rejected": "❌",
    "applied": "🔧",
}


def fetch_incidents() -> list[dict]:
    try:
        r = requests.get(f"{API_BASE}/api/incidents", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erreur API : {e}")
        return []


def fetch_incident_detail(incident_id: str) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/api/incidents/{incident_id}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erreur API : {e}")
        return None


def review_recommendation(reco_id: str, status: str, reviewer: str, reason: str = "") -> bool:
    try:
        r = requests.post(
            f"{API_BASE}/api/recommendations/{reco_id}/review",
            json={"status": status, "reviewed_by": reviewer, "reason": reason or None},
            timeout=5,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Erreur révision : {e}")
        return False


# ── Navigation ────────────────────────────────────────────────────────────────

if "page" not in st.session_state:
    st.session_state.page = "dashboard"
if "selected_incident" not in st.session_state:
    st.session_state.selected_incident = None


def go_to_incident(incident_id: str):
    st.session_state.selected_incident = incident_id
    st.session_state.page = "detail"


# ── Dashboard ─────────────────────────────────────────────────────────────────

if st.session_state.page == "dashboard":
    st.title("🛡️ Vigie SOC — AtlasMétaux")
    st.caption("Plateforme de réponse à incident assistée par IA")

    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("⟳ Actualiser"):
            st.rerun()

    incidents = fetch_incidents()

    if not incidents:
        st.info("Aucun incident. L'API est-elle démarrée sur " + API_BASE + " ?")
    else:
        # Métriques
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", len(incidents))
        m2.metric("Critiques", sum(1 for i in incidents if i["severity"] == "CRITICAL"))
        m3.metric("En cours", sum(1 for i in incidents if i["status"] == "in_progress"))
        m4.metric("Résolus", sum(1 for i in incidents if i["status"] == "resolved"))

        st.divider()

        for inc in incidents:
            sev_icon = SEVERITY_COLOR.get(inc["severity"], "⚪")
            status_label = STATUS_LABEL.get(inc["status"], inc["status"])
            col_title, col_status, col_btn = st.columns([5, 2, 1])
            with col_title:
                st.markdown(f"{sev_icon} **{inc['title']}**")
                st.caption(f"ID : {inc['id'][:8]}… · {inc['created_at'][:10]}")
            with col_status:
                st.markdown(f"`{status_label}`")
            with col_btn:
                if st.button("Voir", key=f"btn_{inc['id']}"):
                    go_to_incident(inc["id"])
                    st.rerun()


# ── Détail incident ────────────────────────────────────────────────────────────

elif st.session_state.page == "detail":
    if st.button("← Retour"):
        st.session_state.page = "dashboard"
        st.rerun()

    detail = fetch_incident_detail(st.session_state.selected_incident)
    if not detail:
        st.stop()

    inc = detail["incident"]
    recos = detail["recommendations"]

    sev_icon = SEVERITY_COLOR.get(inc["severity"], "⚪")
    st.title(f"{sev_icon} {inc['title']}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Sévérité", inc["severity"])
    c2.metric("Statut", STATUS_LABEL.get(inc["status"], inc["status"]))
    c3.metric("Recommandations", len(recos))

    if inc.get("mitre_techniques"):
        st.markdown("**Techniques MITRE ATT&CK** : " + " · ".join(
            f"`{t}`" for t in inc["mitre_techniques"]
        ))

    st.divider()
    st.subheader("Recommandations de l'agent")

    if not recos:
        st.info("Aucune recommandation — l'agent tourne peut-être encore en arrière-plan.")
    else:
        reviewer = st.text_input("Votre identifiant (pour l'audit)", value="analyste-soc", key="reviewer")

        for reco in recos:
            status_icon = RECO_STATUS_COLOR.get(reco["status"], "?")
            with st.expander(f"{status_icon} {reco['content'][:80]}…", expanded=reco["status"] == "pending"):
                st.markdown(reco["content"])
                if reco.get("mitre_refs"):
                    st.caption("MITRE refs : " + ", ".join(reco["mitre_refs"]))
                st.caption(f"Confiance : {reco.get('confidence', '—')} · Statut : {reco['status']}")

                if reco["status"] == "pending":
                    reason = st.text_input("Motif (optionnel)", key=f"reason_{reco['id']}")
                    col_a, col_r = st.columns(2)
                    with col_a:
                        if st.button("✅ Approuver", key=f"approve_{reco['id']}"):
                            if review_recommendation(reco["id"], "approved", reviewer, reason):
                                st.success("Approuvée")
                                st.rerun()
                    with col_r:
                        if st.button("❌ Rejeter", key=f"reject_{reco['id']}"):
                            if review_recommendation(reco["id"], "rejected", reviewer, reason):
                                st.warning("Rejetée")
                                st.rerun()
