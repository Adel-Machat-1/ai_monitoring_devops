import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="Anomalies ML",
    page_icon="🧠",
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

    .page-header {
        background: white; border-radius: 12px; padding: 24px 28px;
        margin-bottom: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border-left: 5px solid #805ad5;
    }
    .page-header h1 { color: #1a202c; font-size: 24px; font-weight: 700; margin: 0; }
    .page-header p  { color: #718096; font-size: 14px; margin: 4px 0 0; }

    .section-title {
        font-size: 16px; font-weight: 700; color: #2d3748;
        margin: 24px 0 16px; padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
    }

    .info-box {
        background: white; border-radius: 12px; padding: 20px 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06); margin-bottom: 16px;
        border-left: 4px solid #805ad5;
    }
    .info-box h4 { color: #1a202c; font-size: 14px; font-weight: 700; margin: 0 0 12px; }
    .info-box p  { color: #4a5568; font-size: 13px; line-height: 1.6; margin: 0; }

    .metric-row {
        background: white; border-radius: 10px; padding: 16px 20px;
        margin-bottom: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        border-left: 4px solid #805ad5;
    }
    .metric-app {
        font-size: 14px; font-weight: 700; color: #1a202c;
    }
    .metric-box {
        background: #f8fafc; border-radius: 8px; padding: 10px 14px; text-align: center;
    }
    .metric-box.warning { background: #fffaf0; }
    .metric-box.danger  { background: #fff5f5; }
    .metric-val   { font-size: 18px; font-weight: 800; color: #2d3748; }
    .metric-lbl   { font-size: 10px; color: #718096; font-weight: 600;
                    text-transform: uppercase; letter-spacing: 0.5px; }

    .threshold-card {
        background: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06); text-align: center;
    }
    .threshold-card.normal  { border-top: 4px solid #38a169; }
    .threshold-card.warning { border-top: 4px solid #ed8936; }
    .threshold-card.danger  { border-top: 4px solid #e53e3e; }
    .threshold-score {
        font-size: 22px; font-weight: 800; margin: 8px 0 4px;
    }
    .threshold-label { font-size: 12px; color: #718096; }

    .params-table {
        width: 100%; border-collapse: collapse;
    }
    .params-table th {
        background: #f0f4f8; padding: 10px 16px; text-align: left;
        font-size: 12px; font-weight: 700; color: #4a5568; text-transform: uppercase;
    }
    .params-table td {
        padding: 10px 16px; font-size: 13px; color: #2d3748;
        border-bottom: 1px solid #f0f4f8;
    }
    .params-table tr:last-child td { border-bottom: none; }
    .params-table tr:hover td { background: #f7fafc; }

    .stButton button {
        background: #805ad5 !important; color: white !important;
        border: none !important; border-radius: 8px !important; font-weight: 600 !important;
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

PROMETHEUS_URL = "http://localhost:9090"

@st.cache_data(ttl=30)
def get_current_metrics():
    apps = {
        "Keycloak"  : {"cpu": "keycloak",    "mem": "keycloak"},
        "PostgreSQL": {"cpu": "postgresql",   "mem": "postgresql"},
        "MongoDB"   : {"cpu": "mongodb",      "mem": "mongodb"},
        "Redis"     : {"cpu": "redis",        "mem": "redis"},
        "Redpanda"  : {"cpu": "redpanda",     "mem": "redpanda"},
    }
    results = {}
    for name, config in apps.items():
        try:
            cpu_r = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": f"sum(rate(container_cpu_usage_seconds_total{{pod=~'{config['cpu']}.*'}}[5m]))"}, timeout=3
            ).json()["data"]["result"]
            mem_r = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": f"sum(container_memory_usage_bytes{{pod=~'{config['mem']}.*'}})"}, timeout=3
            ).json()["data"]["result"]
            rst_r = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": f"sum(kube_pod_container_status_restarts_total{{pod=~'{config['cpu']}.*'}})"}, timeout=3
            ).json()["data"]["result"]
            results[name] = {
                "cpu"     : float(cpu_r[0]["value"][1]) if cpu_r else 0,
                "memory"  : float(mem_r[0]["value"][1]) / 1024 / 1024 if mem_r else 0,
                "restarts": int(float(rst_r[0]["value"][1])) if rst_r else 0,
            }
        except:
            results[name] = {"cpu": 0, "memory": 0, "restarts": 0}
    return results

# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
st.markdown("""
<div class="page-header">
    <h1>🧠 Anomaly Detection ML</h1>
    <p>Détection proactive d'anomalies via Isolation Forest</p>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns([1, 5])
with c1:
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()
with c2:
    st.caption(f"⏱️ Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")

# ══════════════════════════════════════════════════════════════
# COMMENT ÇA MARCHE
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="section-title">ℹ️ Comment fonctionne la détection d\'anomalies ?</p>',
            unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="info-box">
        <h4>🔬 Algorithme : Isolation Forest</h4>
        <p>
            L'agent utilise l'algorithme <b>Isolation Forest</b> pour détecter
            les comportements anormaux en 3 phases :
            <br><br>
            ⏱️ <b>Phase 1</b> (50 min) : Collecte des métriques toutes les 5 min<br>
            🧠 <b>Phase 2</b> : Entraînement du modèle ML<br>
            🔍 <b>Phase 3</b> : Détection en temps réel
        </p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="info-box">
        <h4>⚙️ Paramètres du modèle</h4>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <table class="params-table">
        <thead>
            <tr>
                <th>Paramètre</th>
                <th>Valeur</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>MIN_TRAINING_POINTS</td>
                <td><b>10</b></td>
                <td>Cycles avant entraînement</td>
            </tr>
            <tr>
                <td>CONTAMINATION</td>
                <td><b>0.03</b></td>
                <td>% anomalies attendues</td>
            </tr>
            <tr>
                <td>MIN_ANOMALY_SCORE</td>
                <td><b>0.65</b></td>
                <td>Seuil faux positifs</td>
            </tr>
            <tr>
                <td>DEDUP_WINDOW</td>
                <td><b>30 min</b></td>
                <td>Anti-doublons</td>
            </tr>
        </tbody>
    </table>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# MÉTRIQUES ACTUELLES
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="section-title">📊 Métriques actuelles</p>', unsafe_allow_html=True)

metrics = get_current_metrics()

for name, m in metrics.items():
    restarts     = m['restarts']
    restart_cls  = "danger" if restarts > 20 else "warning" if restarts > 5 else ""
    restart_col  = "#e53e3e" if restarts > 20 else "#ed8936" if restarts > 5 else "#2d3748"

    c1, c2, c3, c4 = st.columns([2, 3, 3, 2])

    with c1:
        st.markdown(f"""
        <div style="padding:16px 12px;background:white;border-radius:10px;
                    box-shadow:0 1px 4px rgba(0,0,0,0.06);
                    border-left:4px solid #805ad5;margin-bottom:8px;">
            <div class="metric-app">{name}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="metric-box" style="margin-bottom:8px;">
            <div class="metric-lbl">CPU Usage</div>
            <div class="metric-val">{m['cpu']:.4f}</div>
            <div style="font-size:10px;color:#a0aec0;">cores</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-box" style="margin-bottom:8px;">
            <div class="metric-lbl">Memory</div>
            <div class="metric-val">{m['memory']:.0f}</div>
            <div style="font-size:10px;color:#a0aec0;">MB</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="metric-box {restart_cls}" style="margin-bottom:8px;">
            <div class="metric-lbl">Restarts</div>
            <div class="metric-val" style="color:{restart_col};">{restarts}</div>
            <div style="font-size:10px;color:#a0aec0;">total</div>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# GRAPHIQUE
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="section-title">📈 Visualisation des métriques</p>', unsafe_allow_html=True)

categories = list(metrics.keys())
cpu_values = [m['cpu'] * 100 for m in metrics.values()]
mem_values = [m['memory'] / 100 for m in metrics.values()]

fig = go.Figure()
fig.add_trace(go.Bar(name='CPU (×100)',    x=categories, y=cpu_values, marker_color='#805ad5'))
fig.add_trace(go.Bar(name='Memory (MB/100)', x=categories, y=mem_values, marker_color='#3182ce'))
fig.update_layout(
    title='CPU et Memory par application',
    barmode='group', height=380,
    plot_bgcolor='white', paper_bgcolor='white',
    font=dict(family="Arial", size=12, color="#2d3748"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=20, r=20, t=60, b=20),
)
fig.update_xaxes(gridcolor='#f0f4f8')
fig.update_yaxes(gridcolor='#f0f4f8')
st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# SEUILS
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="section-title">⚙️ Seuils de détection</p>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("""
    <div class="threshold-card normal">
        <div style="font-size:28px;">✅</div>
        <div class="threshold-score" style="color:#38a169;">Score &lt; 0.65</div>
        <div style="font-size:14px;font-weight:700;color:#1a202c;margin:4px 0;">Normal</div>
        <div class="threshold-label">Comportement normal<br>Pas d'alerte générée</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="threshold-card warning">
        <div style="font-size:28px;">⚠️</div>
        <div class="threshold-score" style="color:#ed8936;">0.65 — 0.75</div>
        <div style="font-size:14px;font-weight:700;color:#1a202c;margin:4px 0;">Anomalie modérée</div>
        <div class="threshold-label">Comportement suspect<br>Alerte WARNING générée</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class="threshold-card danger">
        <div style="font-size:28px;">🔴</div>
        <div class="threshold-score" style="color:#e53e3e;">Score &gt; 0.75</div>
        <div style="font-size:14px;font-weight:700;color:#1a202c;margin:4px 0;">Anomalie critique</div>
        <div class="threshold-label">Comportement anormal<br>Alerte CRITICAL générée</div>
    </div>
    """, unsafe_allow_html=True)

    