import streamlit as st
from minio import Minio
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(
    page_title="Incidents",
    page_icon="📋",
    layout="wide"
)

st.sidebar.title("🤖 Agent IA")
st.sidebar.markdown("Kubernetes Monitoring")
st.sidebar.divider()
st.sidebar.success("✅ Système actif")

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
st.title("📋 Incidents")
st.markdown("Liste complète des incidents détectés")
st.divider()

col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()
with col2:
    st.caption(f"Mise à jour : {datetime.now().strftime('%H:%M:%S')}")

df = load_reports()

# ── Filtres ───────────────────────────────────────────────────
st.subheader("🔍 Filtres")
col1, col2, col3, col4 = st.columns(4)

with col1:
    apps = ["Toutes"] + sorted(df['app'].unique().tolist()) if not df.empty else ["Toutes"]
    app_filter = st.selectbox("Application", apps)

with col2:
    sev_filter = st.selectbox("Sévérité", ["Toutes", "critical", "warning"])

with col3:
    type_filter = st.selectbox("Type", ["Tous", "Alerte Prometheus", "Anomalie ML"])

with col4:
    period_filter = st.selectbox("Période", ["Tous", "Aujourd'hui", "7 derniers jours", "30 derniers jours"])

# ── Appliquer filtres ─────────────────────────────────────────
filtered_df = df.copy() if not df.empty else df

if not filtered_df.empty:
    if app_filter != "Toutes":
        filtered_df = filtered_df[filtered_df['app'] == app_filter]
    if sev_filter != "Toutes":
        filtered_df = filtered_df[filtered_df['severity'] == sev_filter]
    if type_filter != "Tous":
        filtered_df = filtered_df[filtered_df['type'] == type_filter]
    if period_filter == "Aujourd'hui":
        filtered_df = filtered_df[filtered_df['date'] == datetime.now().strftime('%Y%m%d')]
    elif period_filter == "7 derniers jours":
        cutoff = datetime.now() - timedelta(days=7)
        filtered_df = filtered_df[filtered_df['datetime'] >= cutoff]
    elif period_filter == "30 derniers jours":
        cutoff = datetime.now() - timedelta(days=30)
        filtered_df = filtered_df[filtered_df['datetime'] >= cutoff]

st.divider()

# ── Liste incidents ───────────────────────────────────────────
st.subheader(f"📋 Incidents ({len(filtered_df)})")

if not filtered_df.empty:
    for _, row in filtered_df.iterrows():
        icon = "🔴" if row['severity'] == 'critical' else "🟠"
        with st.expander(f"{icon} {row['alert']} — {row['severity'].upper()} — {row['datetime'].strftime('%d/%m/%Y %H:%M')}"):
            col1, col2, col3, col4 = st.columns(4)
            col1.write(f"**Application :** {row['app']}")
            col2.write(f"**Type :** {row['type']}")
            col3.write(f"**Sévérité :** {row['severity'].upper()}")
            col4.write(f"**Taille :** {row['size']}")
            try:
                client    = get_minio_client()
                pdf_data  = client.get_object("incident-reports", row['filename'])
                pdf_bytes = pdf_data.read()
                st.download_button(
                    label     = "📥 Télécharger le rapport PDF",
                    data      = pdf_bytes,
                    file_name = row['filename'],
                    mime      = "application/pdf",
                    key       = row['filename']
                )
            except Exception as e:
                st.error(f"Erreur PDF : {str(e)}")
else:
    st.warning("⚠️ Aucun incident trouvé avec ces filtres")