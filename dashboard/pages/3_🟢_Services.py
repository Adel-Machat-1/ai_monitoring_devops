import streamlit as st
import requests
from datetime import datetime

st.set_page_config(
    page_title="Services",
    page_icon="🟢",
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
        border-left: 5px solid #38a169;
    }
    .page-header h1 { color: #1a202c; font-size: 24px; font-weight: 700; margin: 0; }
    .page-header p  { color: #718096; font-size: 14px; margin: 4px 0 0; }

    .section-title {
        font-size: 16px; font-weight: 700; color: #2d3748;
        margin: 24px 0 16px; padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
    }

    .status-card {
        background: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        text-align: center; border-top: 4px solid #38a169;
    }
    .status-card.down { border-top-color: #e53e3e; }

    .status-name {
        font-size: 15px; font-weight: 700; color: #1a202c;
        margin: 8px 0 4px;
    }
    .status-badge-up {
        display: inline-block; padding: 4px 14px; border-radius: 20px;
        background: #f0fff4; color: #38a169;
        border: 1px solid #c6f6d5; font-size: 12px; font-weight: 700;
    }
    .status-badge-down {
        display: inline-block; padding: 4px 14px; border-radius: 20px;
        background: #fff5f5; color: #e53e3e;
        border: 1px solid #fed7d7; font-size: 12px; font-weight: 700;
    }

    .metric-card {
        background: white; border-radius: 12px; padding: 20px 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        margin-bottom: 12px; border-left: 4px solid #3182ce;
    }
    .metric-card.down { border-left-color: #e53e3e; }
    .metric-card.up   { border-left-color: #38a169; }

    .metric-name {
        font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 12px;
    }
    .metric-value {
        font-size: 20px; font-weight: 800; color: #2d3748;
    }
    .metric-label {
        font-size: 11px; color: #718096; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    .metric-box {
        background: #f8fafc; border-radius: 8px; padding: 12px 16px;
        text-align: center;
    }
    .metric-box.warning { background: #fffaf0; }
    .metric-box.danger  { background: #fff5f5; }

    .stButton button {
        background: #3182ce !important; color: white !important;
        border: none !important; border-radius: 8px !important;
        font-weight: 600 !important;
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
            r      = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                                  params={"query": f"sum(up{{job='{job}'}})"}, timeout=3)
            result = r.json()["data"]["result"]
            value  = float(result[0]["value"][1]) if result else 0
            status[name] = {"up": value > 0, "value": value}
        except:
            status[name] = {"up": False, "value": 0}
    return status

@st.cache_data(ttl=15)
def get_metrics(pod_prefix):
    try:
        queries = {
            "cpu"     : f"sum(rate(container_cpu_usage_seconds_total{{pod=~'{pod_prefix}.*'}}[5m]))",
            "memory"  : f"sum(container_memory_usage_bytes{{pod=~'{pod_prefix}.*'}})",
            "restarts": f"sum(kube_pod_container_status_restarts_total{{pod=~'{pod_prefix}.*'}})",
        }
        result = {}
        for key, query in queries.items():
            r = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=3)
            res = r.json()["data"]["result"]
            result[key] = float(res[0]["value"][1]) if res else 0
        return result
    except:
        return {"cpu": 0, "memory": 0, "restarts": 0}

# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
st.markdown("""
<div class="page-header">
    <h1>🟢 Statut des services</h1>
    <p>Monitoring en temps réel des applications Kubernetes</p>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns([1, 5])
with c1:
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()
with c2:
    st.caption(f"⏱️ Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")

status = get_services_status()

# ══════════════════════════════════════════════════════════════
# STATUT CARDS
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="section-title">📡 État des services</p>', unsafe_allow_html=True)

cols = st.columns(5)
for i, (name, info) in enumerate(status.items()):
    with cols[i]:
        is_up      = info["up"]
        icon       = "🟢" if is_up else "🔴"
        card_class = "status-card" if is_up else "status-card down"
        badge      = f'<span class="status-badge-up">✅ UP</span>' if is_up else \
                     f'<span class="status-badge-down">❌ DOWN</span>'
        st.markdown(f"""
        <div class="{card_class}">
            <div style="font-size:28px;">{icon}</div>
            <div class="status-name">{name}</div>
            {badge}
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# MÉTRIQUES DÉTAILLÉES
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="section-title">📊 Métriques détaillées</p>', unsafe_allow_html=True)

services_config = {
    "Keycloak"   : {"pod": "keycloak"},
    "PostgreSQL" : {"pod": "postgresql"},
    "MongoDB"    : {"pod": "mongodb"},
    "Redis"      : {"pod": "redis"},
    "Redpanda"   : {"pod": "redpanda"},
}

for name, config in services_config.items():
    metrics   = get_metrics(config["pod"])
    is_up     = status.get(name, {}).get("up", False)
    icon      = "🟢" if is_up else "🔴"
    card_cls  = "metric-card up" if is_up else "metric-card down"
    status_lbl= "UP" if is_up else "DOWN"
    status_col= "#38a169" if is_up else "#e53e3e"

    cpu_mb    = metrics['cpu']
    mem_mb    = metrics['memory'] / 1024 / 1024
    restarts  = int(metrics['restarts'])

    # Couleur restarts
    restart_cls = "danger" if restarts > 20 else "warning" if restarts > 5 else ""

    st.markdown(f"""
    <div class="{card_cls}">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td width="20%">
                    <div class="metric-name">
                        {icon} {name}
                        <span style="background:{'#f0fff4' if is_up else '#fff5f5'};
                                     color:{status_col};padding:2px 8px;
                                     border-radius:10px;font-size:11px;
                                     margin-left:8px;">{status_lbl}</span>
                    </div>
                </td>
                <td width="27%">
                    <div class="metric-box">
                        <div class="metric-label">CPU Usage</div>
                        <div class="metric-value">{cpu_mb:.4f}</div>
                        <div style="font-size:11px;color:#a0aec0;">cores</div>
                    </div>
                </td>
                <td width="5%"></td>
                <td width="27%">
                    <div class="metric-box">
                        <div class="metric-label">Memory</div>
                        <div class="metric-value">{mem_mb:.0f}</div>
                        <div style="font-size:11px;color:#a0aec0;">MB</div>
                    </div>
                </td>
                <td width="5%"></td>
                <td width="16%">
                    <div class="metric-box {restart_cls}">
                        <div class="metric-label">Restarts</div>
                        <div class="metric-value" style="color:{'#e53e3e' if restarts > 20 else '#ed8936' if restarts > 5 else '#2d3748'};">
                            {restarts}
                        </div>
                        <div style="font-size:11px;color:#a0aec0;">total</div>
                    </div>
                </td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)