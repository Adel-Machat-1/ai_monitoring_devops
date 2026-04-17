import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="Anomalies ML",
    page_icon="🧠",
    layout="wide"
)

st.sidebar.title("🤖 Agent IA")
st.sidebar.markdown("Kubernetes Monitoring")
st.sidebar.divider()
st.sidebar.success("✅ Système actif")

PROMETHEUS_URL = "http://localhost:9090"

@st.cache_data(ttl=30)
def get_current_metrics():
    apps = {
        "Keycloak"  : {"cpu": "keycloak", "mem": "keycloak"},
        "PostgreSQL": {"cpu": "postgresql", "mem": "postgresql"},
        "MongoDB"   : {"cpu": "mongodb", "mem": "mongodb"},
        "Redis"     : {"cpu": "redis", "mem": "redis"},
        "Redpanda"  : {"cpu": "redpanda", "mem": "redpanda"},
    }
    results = {}
    for name, config in apps.items():
        try:
            cpu_r = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": f"sum(rate(container_cpu_usage_seconds_total{{pod=~'{config['cpu']}.*'}}[5m]))"},
                timeout=3
            ).json()["data"]["result"]
            mem_r = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": f"sum(container_memory_usage_bytes{{pod=~'{config['mem']}.*'}})"},
                timeout=3
            ).json()["data"]["result"]
            rst_r = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": f"sum(kube_pod_container_status_restarts_total{{pod=~'{config['cpu']}.*'}})"},
                timeout=3
            ).json()["data"]["result"]

            results[name] = {
                "cpu"     : float(cpu_r[0]["value"][1]) if cpu_r else 0,
                "memory"  : float(mem_r[0]["value"][1]) / 1024 / 1024 if mem_r else 0,
                "restarts": int(float(rst_r[0]["value"][1])) if rst_r else 0,
            }
        except:
            results[name] = {"cpu": 0, "memory": 0, "restarts": 0}
    return results

# ── Titre ─────────────────────────────────────────────────────
st.title("🧠 Anomaly Detection ML")
st.markdown("Détection proactive d'anomalies via Isolation Forest")
st.divider()

col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()
with col2:
    st.caption(f"Mise à jour : {datetime.now().strftime('%H:%M:%S')}")

# ── Explication ML ────────────────────────────────────────────
with st.expander("ℹ️ Comment fonctionne la détection d'anomalies ?"):
    st.markdown("""
    ### Algorithme : Isolation Forest

    L'agent utilise l'algorithme **Isolation Forest** pour détecter
    les comportements anormaux :

    - **Phase 1** (50 min) : Collecte des métriques toutes les 5 min
    - **Phase 2** : Entraînement du modèle ML
    - **Phase 3** : Détection en temps réel

    ### Paramètres
    | Paramètre | Valeur | Description |
    |-----------|--------|-------------|
    | MIN_TRAINING_POINTS | 10 | Cycles avant entraînement |
    | CONTAMINATION | 0.03 | % anomalies attendues |
    | MIN_ANOMALY_SCORE | 0.65 | Seuil faux positifs |
    | DEDUP_WINDOW | 30 min | Anti-doublons |
    """)

st.divider()

# ── Métriques actuelles ───────────────────────────────────────
st.subheader("📊 Métriques actuelles")
metrics = get_current_metrics()

for name, m in metrics.items():
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    with col1:
        st.write(f"**{name}**")
    with col2:
        st.metric("CPU", f"{m['cpu']:.4f} cores")
    with col3:
        mem_mb = m['memory']
        st.metric("Memory", f"{mem_mb:.0f} MB")
    with col4:
        restarts = m['restarts']
        if restarts > 10:
            st.metric("Restarts", restarts, delta=f"+{restarts}", delta_color="inverse")
        else:
            st.metric("Restarts", restarts)

st.divider()

# ── Graphique radar ───────────────────────────────────────────
st.subheader("📈 Visualisation des métriques")

categories = list(metrics.keys())
cpu_values = [m['cpu'] * 100 for m in metrics.values()]
mem_values = [m['memory'] / 100 for m in metrics.values()]

fig = go.Figure()
fig.add_trace(go.Bar(
    name='CPU (×100)',
    x=categories,
    y=cpu_values,
    marker_color='#FF4B4B'
))
fig.add_trace(go.Bar(
    name='Memory (MB/100)',
    x=categories,
    y=mem_values,
    marker_color='#764ba2'
))
fig.update_layout(
    title='CPU et Memory par application',
    barmode='group',
    height=400
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Info seuils ───────────────────────────────────────────────
st.subheader("⚙️ Seuils de détection")
col1, col2, col3 = st.columns(3)
col1.info("**Score < 0.65**\n\n✅ Normal\nPas d'alerte")
col2.warning("**Score 0.65 - 0.75**\n\n⚠️ Anomalie modérée\nAlerte WARNING")
col3.error("**Score > 0.75**\n\n🔴 Anomalie critique\nAlerte CRITICAL")