import streamlit as st
import requests
from datetime import datetime

st.set_page_config(
    page_title="Agent IA — Kubernetes Monitoring",
    page_icon="🤖",
    layout="wide"
)


st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    [data-testid="stSidebar"] * { color: white !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .hero {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 16px; padding: 40px; text-align: center;
        margin-bottom: 24px; box-shadow: 0 8px 30px rgba(0,0,0,0.15);
    }
    .hero h1 { color: white; font-size: 28px; font-weight: 800; margin: 12px 0 8px; }
    .hero p   { color: #a0aec0; font-size: 15px; margin: 0; }

    .section-title {
        font-size: 16px; font-weight: 700; color: #2d3748;
        margin: 24px 0 16px; padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
    }

    .info-card {
        background: white; border-radius: 12px; padding: 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06); height: 100%;
    }
    .info-card h3 {
        color: #1a202c; font-size: 16px; font-weight: 700;
        margin: 0 0 16px; border-left: 4px solid #3182ce; padding-left: 12px;
    }
    .info-card ul { list-style: none; padding: 0; margin: 0; }
    .info-card ul li {
        padding: 6px 0; font-size: 13px; color: #4a5568;
        border-bottom: 1px solid #f0f4f8;
    }
    .info-card ul li:last-child { border-bottom: none; }

    .nav-table { width: 100%; border-collapse: collapse; }
    .nav-table th {
        background: #f0f4f8; padding: 10px 16px; text-align: left;
        font-size: 12px; font-weight: 700; color: #4a5568; text-transform: uppercase;
    }
    .nav-table td {
        padding: 12px 16px; font-size: 13px; color: #2d3748;
        border-bottom: 1px solid #f0f4f8;
    }
    .nav-table tr:hover td { background: #f7fafc; }

    .stack-card {
        background: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        text-align: center; border-top: 4px solid #3182ce;
    }
    .stack-card.green  { border-top-color: #38a169; }
    .stack-card.purple { border-top-color: #805ad5; }
    .stack-card.orange { border-top-color: #ed8936; }
    .stack-title { font-size: 14px; font-weight: 700; color: #1a202c; margin: 8px 0 12px; }
    .stack-item  { font-size: 12px; color: #4a5568; padding: 4px 0; border-bottom: 1px solid #f0f4f8; }
    .stack-item:last-child { border-bottom: none; }

    .footer {
        background: white; border-radius: 12px; padding: 16px 24px;
        text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        margin-top: 24px; color: #718096; font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="text-align:center;padding:20px 0 10px;">
    <div style="font-size:36px;">🤖</div>
    <div style="font-size:18px;font-weight:700;color:white;margin-top:8px;">Agent IA</div>
    <div style="font-size:12px;color:#a0aec0;margin-top:4px;">Kubernetes Monitoring</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.divider()

try:
    from minio import Minio as _M
    _M("localhost:9000", access_key="minioadmin", secret_key="minioadmin123", secure=False).list_buckets()
    st.sidebar.success("✅ MinIO connecté")
except:
    st.sidebar.error("❌ MinIO déconnecté")

try:
    if requests.get("http://localhost:9090/-/healthy", timeout=2).status_code == 200:
        st.sidebar.success("✅ Prometheus connecté")
    else:
        st.sidebar.error("❌ Prometheus déconnecté")
except:
    st.sidebar.error("❌ Prometheus déconnecté")

st.sidebar.divider()
st.sidebar.caption(f"Vérification : {datetime.now().strftime('%H:%M:%S')}")

# ══════════════════════════════════════════════════════════════
# HERO
# ══════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
    <div style="font-size:48px;">🤖</div>
    <h1>Agent IA — Kubernetes Monitoring</h1>
    <p>Dashboard de monitoring intelligent avec RCA automatisé via GPT-4</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# À PROPOS + NAVIGATION
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="section-title">📖 À propos du système</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="info-card">
        <h3>🎯 À propos du système</h3>
        <p style="color:#4a5568;font-size:13px;line-height:1.6;margin-bottom:16px;">
            Cet agent IA surveille automatiquement votre cluster Kubernetes
            et effectue un <b>Root Cause Analysis</b> automatisé via GPT-4.
        </p>
        <h3 style="margin-top:0;">✨ Fonctionnalités</h3>
        <ul>
            <li>🔴 Détection des incidents via Prometheus</li>
            <li>🧠 Détection d'anomalies via Isolation Forest (ML)</li>
            <li>🤖 Analyse RCA automatique via GPT-4o-mini</li>
            <li>📄 Génération de rapports PDF professionnels</li>
            <li>📧 Notifications email automatiques</li>
            <li>🗂️ Stockage des rapports dans MinIO</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="info-card">
        <h3>📱 Navigation</h3>
        <p style="color:#4a5568;font-size:13px;margin-bottom:16px;">
            Utilisez le menu à gauche pour naviguer :
        </p>
        <table class="nav-table">
            <thead>
                <tr>
                    <th>Page</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>📊 Vue d'ensemble</td>
                    <td>KPIs et graphiques</td>
                </tr>
                <tr>
                    <td>📋 Incidents</td>
                    <td>Liste des rapports PDF</td>
                </tr>
                <tr>
                    <td>🟢 Services</td>
                    <td>Statut temps réel</td>
                </tr>
                <tr>
                    <td>🧠 Anomalies</td>
                    <td>Détection ML</td>
                </tr>
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# STACK TECHNIQUE
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="section-title">🛠️ Stack Technique</p>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("""
    <div class="stack-card">
        <div style="font-size:28px;">☸️</div>
        <div class="stack-title">Infrastructure</div>
        <div class="stack-item">Kubernetes (k3d)</div>
        <div class="stack-item">Prometheus</div>
        <div class="stack-item">Loki</div>
        <div class="stack-item">MinIO</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="stack-card green">
        <div style="font-size:28px;">🤖</div>
        <div class="stack-title">Agent IA</div>
        <div class="stack-item">Python + Flask</div>
        <div class="stack-item">GPT-4o-mini</div>
        <div class="stack-item">Isolation Forest</div>
        <div class="stack-item">ReportLab PDF</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class="stack-card purple">
        <div style="font-size:28px;">⚙️</div>
        <div class="stack-title">DevOps</div>
        <div class="stack-item">Docker</div>
        <div class="stack-item">Helm</div>
        <div class="stack-item">GitHub Actions</div>
        <div class="stack-item">ghcr.io</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown("""
    <div class="stack-card orange">
        <div style="font-size:28px;">📦</div>
        <div class="stack-title">Applications</div>
        <div class="stack-item">Keycloak</div>
        <div class="stack-item">PostgreSQL</div>
        <div class="stack-item">MongoDB</div>
        <div class="stack-item">Redis + Redpanda</div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="footer">
    🤖 Agent IA Kubernetes — Monitoring automatisé &nbsp;|&nbsp;
    PFE 2026 &nbsp;|&nbsp;
    {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}
</div>
""", unsafe_allow_html=True)