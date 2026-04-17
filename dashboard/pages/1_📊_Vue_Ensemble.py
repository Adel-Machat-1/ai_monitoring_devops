import streamlit as st
from minio import Minio
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Vue d'ensemble",
    page_icon="📊",
    layout="wide"
)

st.sidebar.title("🤖 Agent IA")
st.sidebar.markdown("Kubernetes Monitoring")
st.sidebar.divider()
st.sidebar.success("✅ Système actif")

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

# ── Titre ─────────────────────────────────────────────────────
st.title("📊 Vue d'ensemble")
st.markdown("Statistiques globales des incidents")
st.divider()

# ── Refresh ───────────────────────────────────────────────────
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()
with col2:
    st.caption(f"Mise à jour : {datetime.now().strftime('%H:%M:%S')}")

df = load_reports()

# ── KPIs ──────────────────────────────────────────────────────
st.subheader("📈 Indicateurs clés")
if not df.empty:
    total     = len(df)
    critical  = len(df[df['severity'] == 'critical'])
    warning   = len(df[df['severity'] == 'warning'])
    today     = len(df[df['date'] == datetime.now().strftime('%Y%m%d')])
    anomalies = len(df[df['type'] == 'Anomalie ML'])
else:
    total = critical = warning = today = anomalies = 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("📊 Total", total)
col2.metric("🔴 Critical", critical)
col3.metric("🟠 Warning", warning)
col4.metric("📅 Aujourd'hui", today)
col5.metric("🧠 Anomalies ML", anomalies)

st.divider()

# ── Graphiques ────────────────────────────────────────────────
if not df.empty:
    st.subheader("📊 Graphiques")

    col1, col2 = st.columns(2)

    with col1:
        app_counts = df['app'].value_counts().reset_index()
        app_counts.columns = ['Application', 'Count']
        fig1 = px.pie(
            app_counts,
            values='Count',
            names='Application',
            title='Incidents par application',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        sev_counts = df['severity'].value_counts().reset_index()
        sev_counts.columns = ['Sévérité', 'Count']
        fig2 = px.bar(
            sev_counts,
            x='Sévérité',
            y='Count',
            title='Critical vs Warning',
            color='Sévérité',
            color_discrete_map={'critical': '#FF4B4B', 'warning': '#FFA500'}
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Timeline
    df['day'] = df['datetime'].dt.strftime('%Y-%m-%d')
    day_counts = df.groupby(['day', 'severity']).size().reset_index(name='count')
    fig3 = px.bar(
        day_counts,
        x='day',
        y='count',
        color='severity',
        title='Incidents par jour',
        color_discrete_map={'critical': '#FF4B4B', 'warning': '#FFA500'},
        barmode='stack'
    )
    st.plotly_chart(fig3, use_container_width=True)

    # Type incidents
    col1, col2 = st.columns(2)
    with col1:
        type_counts = df['type'].value_counts().reset_index()
        type_counts.columns = ['Type', 'Count']
        fig4 = px.pie(
            type_counts,
            values='Count',
            names='Type',
            title='Alertes vs Anomalies ML',
            color_discrete_sequence=['#FF4B4B', '#764ba2']
        )
        st.plotly_chart(fig4, use_container_width=True)

    with col2:
        # Top alertes
        top_alerts = df['alert'].value_counts().head(5).reset_index()
        top_alerts.columns = ['Alerte', 'Count']
        fig5 = px.bar(
            top_alerts,
            x='Count',
            y='Alerte',
            title='Top 5 alertes',
            orientation='h',
            color='Count',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig5, use_container_width=True)
else:
    st.warning("⚠️ Aucun rapport trouvé dans MinIO")