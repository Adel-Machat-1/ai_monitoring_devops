import streamlit as st
from minio import Minio
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(
    page_title="Vue d'ensemble",
    page_icon="📊",
    layout="wide"
)

# ── CSS Custom ────────────────────────────────────────────────
st.markdown("""
<style>
    /* Fond général */
    .stApp {
        background-color: #f8fafc;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Cacher le menu hamburger */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Cards KPI */
    .kpi-card {
        background: white;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        border-top: 4px solid #3182ce;
        transition: transform 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.12);
    }
    .kpi-card.critical {
        border-top-color: #e53e3e;
    }
    .kpi-card.warning {
        border-top-color: #ed8936;
    }
    .kpi-card.today {
        border-top-color: #38a169;
    }
    .kpi-card.anomaly {
        border-top-color: #805ad5;
    }
    .kpi-value {
        font-size: 42px;
        font-weight: 800;
        color: #1a202c;
        line-height: 1;
        margin: 8px 0;
    }
    .kpi-label {
        font-size: 13px;
        color: #718096;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .kpi-icon {
        font-size: 24px;
        margin-bottom: 4px;
    }

    /* Header page */
    .page-header {
        background: white;
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border-left: 5px solid #3182ce;
    }
    .page-header h1 {
        color: #1a202c;
        font-size: 24px;
        font-weight: 700;
        margin: 0;
    }
    .page-header p {
        color: #718096;
        font-size: 14px;
        margin: 4px 0 0;
    }

    /* Section title */
    .section-title {
        font-size: 16px;
        font-weight: 700;
        color: #2d3748;
        margin: 24px 0 16px;
        padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
    }

    /* Info box */
    .info-box {
        background: white;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        margin-top: 24px;
    }

    /* Refresh button */
    .stButton button {
        background: #3182ce;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 600;
        transition: background 0.2s;
    }
    .stButton button:hover {
        background: #2b6cb0;
    }

    /* Metric delta */
    [data-testid="stMetricDelta"] {
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="text-align:center;padding:20px 0 10px;">
    <div style="font-size:36px;">🤖</div>
    <div style="font-size:18px;font-weight:700;color:white;margin-top:8px;">
        Agent IA
    </div>
    <div style="font-size:12px;color:#a0aec0;margin-top:4px;">
        Kubernetes Monitoring
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.divider()

# Vérification MinIO
try:
    from minio import Minio as _Minio
    _c = _Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin123", secure=False)
    _c.list_buckets()
    st.sidebar.success("✅ MinIO connecté")
except:
    st.sidebar.error("❌ MinIO déconnecté")

# Vérification Prometheus
try:
    import requests as _req
    _r = _req.get("http://localhost:9090/-/healthy", timeout=2)
    if _r.status_code == 200:
        st.sidebar.success("✅ Prometheus connecté")
    else:
        st.sidebar.error("❌ Prometheus déconnecté")
except:
    st.sidebar.error("❌ Prometheus déconnecté")

st.sidebar.divider()
st.sidebar.caption(f"Dernière vérification : {datetime.now().strftime('%H:%M:%S')}")

# ── Connexion MinIO ───────────────────────────────────────────
@st.cache_resource
def get_minio_client():
    return Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin123",
        secure=False
    )

@st.cache_data(ttl=30)
def load_reports():
    try:
        client  = get_minio_client()
        objects = client.list_objects("incident-reports")
        reports = []
        for obj in objects:
            name  = obj.object_name
            parts = name.replace(".pdf", "").split("_")
            if len(parts) >= 4:
                date_str = parts[1]
                time_str = parts[2]
                alert    = "_".join(parts[3:])
                if "Anomaly" in alert:
                    severity = "warning"
                    type_inc = "Anomalie ML"
                elif any(x in alert for x in ["Down", "Crash", "Unavailable", "NotReady"]):
                    severity = "critical"
                    type_inc = "Alerte Prometheus"
                else:
                    severity = "warning"
                    type_inc = "Alerte Prometheus"
                app = "Autre"
                for a in ["Keycloak", "Postgres", "Mongodb", "Redis", "Redpanda"]:
                    if a.lower() in alert.lower():
                        app = a
                        break
                try:
                    dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                except:
                    dt = datetime.now()
                reports.append({
                    "filename" : name,
                    "alert"    : alert,
                    "date"     : date_str,
                    "time"     : time_str,
                    "datetime" : dt,
                    "severity" : severity,
                    "type"     : type_inc,
                    "app"      : app,
                    "size"     : f"{obj.size / 1024:.1f} KB",
                })
        df = pd.DataFrame(reports)
        if not df.empty:
            df = df.sort_values("datetime", ascending=False)
        return df
    except Exception as e:
        st.error(f"❌ Erreur MinIO : {str(e)}")
        return pd.DataFrame()

# ══════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════
st.markdown("""
<div class="page-header">
    <h1>📊 Vue d'ensemble</h1>
    <p>Tableau de bord global des incidents Kubernetes</p>
</div>
""", unsafe_allow_html=True)

# ── Refresh ───────────────────────────────────────────────────
col_btn, col_time = st.columns([1, 5])
with col_btn:
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()
with col_time:
    st.caption(f"⏱️ Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")

# ── Charger données ───────────────────────────────────────────
df = load_reports()

# ── Calculer KPIs ─────────────────────────────────────────────
if not df.empty:
    total     = len(df)
    critical  = len(df[df['severity'] == 'critical'])
    warning   = len(df[df['severity'] == 'warning'])
    today     = len(df[df['date'] == datetime.now().strftime('%Y%m%d')])
    anomalies = len(df[df['type'] == 'Anomalie ML'])
else:
    total = critical = warning = today = anomalies = 0

# ── KPIs Cards ───────────────────────────────────────────────
st.markdown('<p class="section-title">📈 Indicateurs clés</p>', unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">📊</div>
        <div class="kpi-value">{total}</div>
        <div class="kpi-label">Total Incidents</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card critical">
        <div class="kpi-icon">🔴</div>
        <div class="kpi-value" style="color:#e53e3e;">{critical}</div>
        <div class="kpi-label">Critical</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card warning">
        <div class="kpi-icon">🟠</div>
        <div class="kpi-value" style="color:#ed8936;">{warning}</div>
        <div class="kpi-label">Warning</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card today">
        <div class="kpi-icon">📅</div>
        <div class="kpi-value" style="color:#38a169;">{today}</div>
        <div class="kpi-label">Aujourd'hui</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="kpi-card anomaly">
        <div class="kpi-icon">🧠</div>
        <div class="kpi-value" style="color:#805ad5;">{anomalies}</div>
        <div class="kpi-label">Anomalies ML</div>
    </div>
    """, unsafe_allow_html=True)

# ── Info box ──────────────────────────────────────────────────
st.markdown(f"""
<div class="info-box">
    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td style="text-align:center;padding:8px;">
                <div style="font-size:13px;color:#718096;font-weight:600;">
                    TAUX CRITICAL
                </div>
                <div style="font-size:22px;font-weight:800;color:#e53e3e;">
                    {f"{(critical/total*100):.0f}%" if total > 0 else "0%"}
                </div>
            </td>
            <td style="text-align:center;padding:8px;border-left:1px solid #e2e8f0;">
                <div style="font-size:13px;color:#718096;font-weight:600;">
                    TAUX WARNING
                </div>
                <div style="font-size:22px;font-weight:800;color:#ed8936;">
                    {f"{(warning/total*100):.0f}%" if total > 0 else "0%"}
                </div>
            </td>
            <td style="text-align:center;padding:8px;border-left:1px solid #e2e8f0;">
                <div style="font-size:13px;color:#718096;font-weight:600;">
                    TAUX ANOMALIES ML
                </div>
                <div style="font-size:22px;font-weight:800;color:#805ad5;">
                    {f"{(anomalies/total*100):.0f}%" if total > 0 else "0%"}
                </div>
            </td>
            <td style="text-align:center;padding:8px;border-left:1px solid #e2e8f0;">
                <div style="font-size:13px;color:#718096;font-weight:600;">
                    DERNIÈRE MISE À JOUR
                </div>
                <div style="font-size:16px;font-weight:800;color:#3182ce;">
                    {df['datetime'].max().strftime('%d/%m %H:%M') if not df.empty else 'N/A'}
                </div>
            </td>
        </tr>
    </table>
</div>
""", unsafe_allow_html=True)

# ── Message si pas de données ─────────────────────────────────
if df.empty:
    st.markdown("""
    <div style="background:white;border-radius:12px;padding:40px;
                text-align:center;margin-top:24px;
                box-shadow:0 2px 12px rgba(0,0,0,0.06);">
        <div style="font-size:48px;">📭</div>
        <h3 style="color:#2d3748;margin:16px 0 8px;">Aucun incident trouvé</h3>
        <p style="color:#718096;">
            Aucun rapport n'a été généré encore.<br>
            Le système surveille activement votre cluster.
        </p>
    </div>
    """, unsafe_allow_html=True)