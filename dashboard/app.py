import streamlit as st

st.set_page_config(
    page_title="Agent IA — Kubernetes Monitoring",
    page_icon="🤖",
    layout="wide"
)

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.title("🤖 Agent IA")
st.sidebar.markdown("Kubernetes Monitoring")
st.sidebar.divider()
st.sidebar.success("✅ Système actif")

# ── Page d'accueil ────────────────────────────────────────────
st.title("🤖 Agent IA — Kubernetes Monitoring")
st.markdown("### Dashboard de monitoring intelligent avec RCA automatisé via GPT-4")
st.divider()

# ── Description ───────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ## 🎯 À propos du système

    Cet agent IA surveille automatiquement votre cluster
    Kubernetes et effectue un **Root Cause Analysis**
    automatisé via GPT-4.

    ### Fonctionnalités :
    - 🔴 Détection des incidents via Prometheus
    - 🧠 Détection d'anomalies via Isolation Forest (ML)
    - 🤖 Analyse RCA automatique via GPT-4o-mini
    - 📄 Génération de rapports PDF professionnels
    - 📧 Notifications email automatiques
    - 🗂️ Stockage des rapports dans MinIO
    """)

with col2:
    st.markdown("""
    ## 📱 Navigation

    Utilisez le menu à gauche pour naviguer :

    | Page | Description |
    |------|-------------|
    | 📊 Vue d'ensemble | KPIs et graphiques |
    | 📋 Incidents | Liste des rapports PDF |
    | 🟢 Services | Statut temps réel |
    | 🧠 Anomalies | Détection ML |
    """)

st.divider()

# ── Stack technique ───────────────────────────────────────────
st.markdown("## 🛠️ Stack Technique")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.info("""
    **Infrastructure**
    - Kubernetes (k3d)
    - Prometheus
    - Loki
    - MinIO
    """)

with col2:
    st.info("""
    **Agent IA**
    - Python + Flask
    - GPT-4o-mini
    - Isolation Forest
    - ReportLab PDF
    """)

with col3:
    st.info("""
    **DevOps**
    - Docker
    - Helm
    - GitHub Actions
    - ghcr.io
    """)

with col4:
    st.info("""
    **Applications**
    - Keycloak
    - PostgreSQL
    - MongoDB
    - Redis
    - Redpanda
    """)

st.divider()
st.caption("PFE 2026 — Agent IA Monitoring Kubernetes")