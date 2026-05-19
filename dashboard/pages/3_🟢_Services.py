import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import streamlit as st
import requests
from datetime import datetime
from config import SERVICES_ROLES, PROMETHEUS_URL
from core.prometheus import get_pods_for_prefix, get_pod_metrics

st.set_page_config(page_title="Services", page_icon="🟢", layout="wide")

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
    .status-name { font-size: 15px; font-weight: 700; color: #1a202c; margin: 8px 0 4px; }
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

    .service-block {
        background: white; border-radius: 12px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        margin-bottom: 16px; overflow: hidden;
    }
    .service-header-up   { border-left: 5px solid #38a169; padding: 16px 20px 12px; }
    .service-header-down { border-left: 5px solid #e53e3e; padding: 16px 20px 12px; }
    .service-name { font-size: 17px; font-weight: 700; color: #1a202c; }

    .role-badge {
        display: inline-block; padding: 3px 12px; border-radius: 20px;
        background: #ebf4ff; color: #3182ce;
        font-size: 12px; font-weight: 700; margin: 10px 0 8px;
    }

    .pod-row {
        background: #f8fafc; border-radius: 8px; padding: 12px 16px;
        margin-bottom: 8px; border: 1px solid #e2e8f0;
    }
    .pod-name { font-size: 13px; font-weight: 600; color: #2d3748; margin-bottom: 8px; }

    .metric-box {
        background: white; border-radius: 8px; padding: 10px;
        text-align: center;
    }
    .metric-box.warning { background: #fffaf0; }
    .metric-box.danger  { background: #fff5f5; }
    .metric-label { font-size: 10px; color: #718096; font-weight: 600;
                    text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 18px; font-weight: 800; color: #2d3748; }
    .metric-unit  { font-size: 10px; color: #a0aec0; }

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

# ── Data fetching ─────────────────────────────────────────────

@st.cache_data(ttl=15)
def get_service_up(job):
    try:
        r   = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                           params={"query": f'sum(up{{job="{job}"}})'}, timeout=3).json()
        res = r["data"]["result"]
        return bool(res and float(res[0]["value"][1]) > 0)
    except Exception:
        return False

@st.cache_data(ttl=15)
def fetch_pods(prefix, exclude):
    return get_pods_for_prefix(prefix, exclude=list(exclude))

@st.cache_data(ttl=15)
def fetch_pod_metrics(pod):
    return get_pod_metrics(pod)

# ── Header ────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <h1>🟢 Statut des services</h1>
    <p>Monitoring en temps réel — métriques par pod</p>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns([1, 5])
with c1:
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()
with c2:
    st.caption(f"⏱️ Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")

# ── Niveau 1 : statut global ──────────────────────────────────
st.markdown('<p class="section-title">📡 État des services</p>', unsafe_allow_html=True)

cols = st.columns(len(SERVICES_ROLES))
for i, svc in enumerate(SERVICES_ROLES):
    is_up = get_service_up(svc["job"])
    with cols[i]:
        icon       = "🟢" if is_up else "🔴"
        card_class = "status-card" if is_up else "status-card down"
        badge      = f'<span class="status-badge-up">✅ UP</span>' if is_up \
                     else f'<span class="status-badge-down">❌ DOWN</span>'
        st.markdown(f"""
        <div class="{card_class}">
            <div style="font-size:28px;">{icon}</div>
            <div class="status-name">{svc["name"]}</div>
            {badge}
        </div>
        """, unsafe_allow_html=True)

# ── Niveau 2 & 3 : rôles → pods ──────────────────────────────
st.markdown('<p class="section-title">📊 Métriques par pod</p>', unsafe_allow_html=True)

for svc in SERVICES_ROLES:
    is_up        = get_service_up(svc["job"])
    header_class = "service-header-up" if is_up else "service-header-down"
    status_color = "#38a169" if is_up else "#e53e3e"
    status_label = "UP" if is_up else "DOWN"
    icon         = "🟢" if is_up else "🔴"

    total_pods = sum(
        len(fetch_pods(r["prefix"], tuple(r.get("exclude", []))))
        for r in svc["roles"]
    )

    with st.expander(f"{icon} {svc['name']}  —  {total_pods} pod{'s' if total_pods > 1 else ''}  •  {status_label}", expanded=False):
        for role_cfg in svc["roles"]:
            pods = fetch_pods(role_cfg["prefix"], tuple(role_cfg.get("exclude", [])))
            if not pods:
                continue

            st.markdown(f"""
            <div>
                <span class="role-badge">{role_cfg["role"]}</span>
                <span style="font-size:12px;color:#718096;margin-left:8px;">
                    {len(pods)} pod{'s' if len(pods) > 1 else ''}
                </span>
            </div>
            """, unsafe_allow_html=True)

            for pod in pods:
                metrics  = fetch_pod_metrics(pod)
                cpu      = metrics["cpu"]
                mem_mb   = metrics["memory_mb"]
                restarts = metrics["restarts"]

                restart_cls = "danger" if restarts > 20 else "warning" if restarts > 5 else ""
                restart_color = "#e53e3e" if restarts > 20 else "#ed8936" if restarts > 5 else "#2d3748"

                st.markdown(f"""
                <div class="pod-row">
                    <div class="pod-name">🖥️ {pod}</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">
                        <div class="metric-box">
                            <div class="metric-label">CPU</div>
                            <div class="metric-value">{cpu:.4f}</div>
                            <div class="metric-unit">cores</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-label">Memory</div>
                            <div class="metric-value">{mem_mb:.0f}</div>
                            <div class="metric-unit">MB</div>
                        </div>
                        <div class="metric-box {restart_cls}">
                            <div class="metric-label">Restarts</div>
                            <div class="metric-value" style="color:{restart_color};">{restarts}</div>
                            <div class="metric-unit">total</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
