import streamlit as st
import requests
from datetime import datetime

st.set_page_config(
    page_title="Services",
    page_icon="🟢",
    layout="wide"
)

st.sidebar.title("🤖 Agent IA")
st.sidebar.markdown("Kubernetes Monitoring")
st.sidebar.divider()
st.sidebar.success("✅ Système actif")

PROMETHEUS_URL = "http://localhost:9090"

@st.cache_data(ttl=15)
def get_services_status():
    services = {
        "Keycloak"   : "keycloak-metrics",
        "PostgreSQL" : "postgresql-primary-metrics",
        "MongoDB"    : "mongodb-metrics",
        "Redis"      : "redis-metrics",
        "Redpanda"   : "redpanda",
    }
    status = {}
    for name, job in services.items():
        try:
            r = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": f"sum(up{{job='{job}'}})" },
                timeout=3
            )
            result = r.json()["data"]["result"]
            value  = float(result[0]["value"][1]) if result else 0
            status[name] = {
                "up"   : value > 0,
                "value": value
            }
        except:
            status[name] = {"up": False, "value": 0}
    return status

@st.cache_data(ttl=15)
def get_metrics(job, pod_prefix):
    try:
        metrics = {}
        queries = {
            "cpu"     : f"sum(rate(container_cpu_usage_seconds_total{{pod=~'{pod_prefix}.*'}}[5m]))",
            "memory"  : f"sum(container_memory_usage_bytes{{pod=~'{pod_prefix}.*'}})",
            "restarts": f"sum(kube_pod_container_status_restarts_total{{pod=~'{pod_prefix}.*'}})",
        }
        for key, query in queries.items():
            r      = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=3)
            result = r.json()["data"]["result"]
            value  = float(result[0]["value"][1]) if result else 0
            metrics[key] = value
        return metrics
    except:
        return {"cpu": 0, "memory": 0, "restarts": 0}

# ── Titre ─────────────────────────────────────────────────────
st.title("🟢 Statut des services")
st.markdown("Monitoring en temps réel des applications")
st.divider()

col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()
with col2:
    st.caption(f"Mise à jour : {datetime.now().strftime('%H:%M:%S')} (auto-refresh 15s)")

# ── Statut services ───────────────────────────────────────────
st.subheader("📡 État des services")
status = get_services_status()

cols = st.columns(len(status))
for i, (name, info) in enumerate(status.items()):
    with cols[i]:
        if info["up"]:
            st.success(f"🟢 **{name}**\nUP ✅")
        else:
            st.error(f"🔴 **{name}**\nDOWN ❌")

st.divider()

# ── Métriques détaillées ──────────────────────────────────────
st.subheader("📊 Métriques détaillées")

services_config = {
    "Keycloak"   : {"job": "keycloak-metrics",            "pod": "keycloak"},
    "PostgreSQL" : {"job": "postgresql-primary-metrics",  "pod": "postgresql"},
    "MongoDB"    : {"job": "mongodb-metrics",             "pod": "mongodb"},
    "Redis"      : {"job": "redis-metrics",               "pod": "redis"},
    "Redpanda"   : {"job": "redpanda",                    "pod": "redpanda"},
}

for name, config in services_config.items():
    metrics = get_metrics(config["job"], config["pod"])
    is_up   = status.get(name, {}).get("up", False)
    icon    = "🟢" if is_up else "🔴"

    with st.expander(f"{icon} {name}"):
        col1, col2, col3 = st.columns(3)
        col1.metric("CPU", f"{metrics['cpu']:.4f} cores")
        col2.metric("Memory", f"{metrics['memory'] / 1024 / 1024:.0f} MB")
        col3.metric("Restarts", f"{int(metrics['restarts'])}")