import streamlit as st
from minio import Minio
from datetime import datetime, timedelta, date
import pandas as pd

st.set_page_config(page_title="Incidents", page_icon="📋", layout="wide")

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
        border-left: 5px solid #3182ce;
    }
    .page-header h1 { color: #1a202c; font-size: 24px; font-weight: 700; margin: 0; }
    .page-header p  { color: #718096; font-size: 14px; margin: 4px 0 0; }

    .section-title {
        font-size: 16px; font-weight: 700; color: #2d3748;
        margin: 24px 0 16px; padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
    }

    .row-item {
        background: white; border-radius: 8px; padding: 12px 16px;
        margin-bottom: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        border-left: 4px solid #e53e3e;
    }
    .row-item.warning { border-left-color: #ed8936; }

    .badge {
        display: inline-block; padding: 2px 8px; border-radius: 10px;
        font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
    }
    .badge-critical { background: #fff5f5; color: #e53e3e; border: 1px solid #fed7d7; }
    .badge-warning  { background: #fffaf0; color: #ed8936; border: 1px solid #fbd38d; }
    .badge-ml       { background: #faf5ff; color: #805ad5; border: 1px solid #e9d8fd; }
    .badge-prom     { background: #ebf8ff; color: #3182ce; border: 1px solid #bee3f8; }

    .col-header {
        background: #f0f4f8; padding: 10px 16px; border-radius: 8px;
        font-size: 11px; font-weight: 700; color: #4a5568;
        text-transform: uppercase; letter-spacing: 0.5px;
        margin-bottom: 6px;
    }

    .empty-state {
        background: white; border-radius: 12px; padding: 60px 40px;
        text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    }
    .stButton button {
        background: #3182ce !important; color: white !important;
        border: none !important; border-radius: 8px !important; font-weight: 600 !important;
    }
    .stDownloadButton button {
        background: #38a169 !important; color: white !important;
        border: none !important; border-radius: 6px !important;
        font-size: 11px !important; padding: 4px 8px !important;
        width: 100% !important;
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
    import requests as _r
    if _r.get("http://localhost:9090/-/healthy", timeout=2).status_code == 200:
        st.sidebar.success("✅ Prometheus connecté")
    else:
        st.sidebar.error("❌ Prometheus déconnecté")
except:
    st.sidebar.error("❌ Prometheus déconnecté")

st.sidebar.divider()
st.sidebar.caption(f"Vérification : {datetime.now().strftime('%H:%M:%S')}")

# ── MinIO ─────────────────────────────────────────────────────
@st.cache_resource
def get_minio_client():
    return Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin123", secure=False)

@st.cache_data(ttl=30)
def load_reports():
    try:
        reports = []
        for obj in get_minio_client().list_objects("incident-reports"):
            name  = obj.object_name
            parts = name.replace(".pdf", "").split("_")
            if len(parts) >= 4:
                alert = "_".join(parts[3:])
                severity = "warning"
                type_inc = "Anomalie ML" if "Anomaly" in alert else "Alerte Prometheus"
                if any(x in alert for x in ["Down", "Crash", "Unavailable", "NotReady"]):
                    severity = "critical"
                app = "Autre"
                for k, v in {"keycloak":"Keycloak","postgres":"PostgreSQL","postgresql":"PostgreSQL",
                             "mongodb":"MongoDB","mongo":"MongoDB","redis":"Redis","redpanda":"Redpanda"}.items():
                    if k in alert.lower():
                        app = v
                        break
                try:
                    dt = datetime.strptime(f"{parts[1]}_{parts[2]}", "%Y%m%d_%H%M%S")
                except:
                    dt = datetime.now()
                reports.append({
                    "filename": name, "alert": alert, "date": dt.date(),
                    "datetime": dt, "severity": severity, "type": type_inc,
                    "app": app, "size": f"{obj.size/1024:.1f} KB"
                })
        df = pd.DataFrame(reports)
        return df.sort_values("datetime", ascending=False) if not df.empty else df
    except Exception as e:
        st.error(f"❌ MinIO : {e}")
        return pd.DataFrame()

# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
st.markdown("""
<div class="page-header">
    <h1>📋 Incidents</h1>
    <p>Liste complète des incidents détectés sur le cluster Kubernetes</p>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns([1, 5])
with c1:
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()
with c2:
    st.caption(f"⏱️ {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")

df = load_reports()

# ── Filtres ───────────────────────────────────────────────────
st.markdown('<p class="section-title">🔍 Filtres</p>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    apps = ["Toutes"] + sorted(df['app'].unique().tolist()) if not df.empty else ["Toutes"]
    app_filter = st.selectbox("📱 Application", apps)
with c2:
    sev_filter = st.selectbox("⚡ Sévérité", ["Toutes", "critical", "warning"])
with c3:
    type_filter = st.selectbox("🏷️ Type", ["Tous", "Alerte Prometheus", "Anomalie ML"])
with c4:
    selected_date = st.date_input("📅 Jour", value=None, max_value=datetime.now().date(), format="DD/MM/YYYY")

if "prev_date" not in st.session_state:
    st.session_state.prev_date = None
if st.session_state.prev_date != selected_date:
    st.session_state.prev_date = selected_date
    st.rerun()

# ── Filtrage ──────────────────────────────────────────────────
fdf = df.copy() if not df.empty else df
if not fdf.empty:
    if app_filter  != "Toutes": fdf = fdf[fdf['app']      == app_filter]
    if sev_filter  != "Toutes": fdf = fdf[fdf['severity'] == sev_filter]
    if type_filter != "Tous":   fdf = fdf[fdf['type']     == type_filter]
    if selected_date is not None:
        fdf = fdf[fdf['date'] == selected_date]

if selected_date:
    st.info(f"📅 {selected_date.strftime('%d/%m/%Y')} — {len(fdf)} incident(s)")

# ── Pagination ────────────────────────────────────────────────
PER_PAGE    = 6
total       = len(fdf)
total_pages = max(1, -(-total // PER_PAGE))

if "page" not in st.session_state:
    st.session_state.page = 1
if st.session_state.page > total_pages:
    st.session_state.page = 1

page     = st.session_state.page
start    = (page - 1) * PER_PAGE
end      = start + PER_PAGE
page_df  = fdf.iloc[start:end]

# ══════════════════════════════════════════════════════════════
# TABLEAU — Header colonnes Streamlit
# ══════════════════════════════════════════════════════════════
st.markdown(
    f'<p class="section-title">📋 Incidents ({total}) — Page {page}/{total_pages}</p>',
    unsafe_allow_html=True
)

if not fdf.empty:

    # Header colonnes
    h1, h2, h3, h4, h5, h6, h7 = st.columns([3, 1.5, 2, 1.5, 2, 1, 1.2])
    h1.markdown('<div class="col-header">Alerte</div>', unsafe_allow_html=True)
    h2.markdown('<div class="col-header">Sévérité</div>', unsafe_allow_html=True)
    h3.markdown('<div class="col-header">Type</div>', unsafe_allow_html=True)
    h4.markdown('<div class="col-header">Application</div>', unsafe_allow_html=True)
    h5.markdown('<div class="col-header">Date & Heure</div>', unsafe_allow_html=True)
    h6.markdown('<div class="col-header">Taille</div>', unsafe_allow_html=True)
    h7.markdown('<div class="col-header">PDF</div>', unsafe_allow_html=True)

    # Lignes
    for _, row in page_df.iterrows():
        is_crit   = row['severity'] == 'critical'
        icon      = "🔴" if is_crit else "🟠"
        b_sev     = "badge-critical" if is_crit else "badge-warning"
        b_type    = "badge-ml" if row['type'] == "Anomalie ML" else "badge-prom"
        sev_lbl   = "CRITICAL" if is_crit else "WARNING"
        border    = "#e53e3e" if is_crit else "#ed8936"

        c1, c2, c3, c4, c5, c6, c7 = st.columns([3, 1.5, 2, 1.5, 2, 1, 1.2])

        with c1:
            st.markdown(f"""
            <div style="padding:10px 12px;border-left:4px solid {border};
                        background:white;border-radius:6px;margin-bottom:4px;
                        box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                <span style="font-size:13px;font-weight:600;color:#1a202c;">
                    {icon} {row['alert']}
                </span>
            </div>""", unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div style="padding:10px 8px;background:white;border-radius:6px;
                        margin-bottom:4px;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                <span class="badge {b_sev}">{sev_lbl}</span>
            </div>""", unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div style="padding:10px 8px;background:white;border-radius:6px;
                        margin-bottom:4px;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                <span class="badge {b_type}">{row['type']}</span>
            </div>""", unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div style="padding:10px 8px;background:white;border-radius:6px;
                        margin-bottom:4px;box-shadow:0 1px 3px rgba(0,0,0,0.05);
                        font-size:12px;color:#4a5568;">
                {row['app']}
            </div>""", unsafe_allow_html=True)

        with c5:
            st.markdown(f"""
            <div style="padding:10px 8px;background:white;border-radius:6px;
                        margin-bottom:4px;box-shadow:0 1px 3px rgba(0,0,0,0.05);
                        font-size:12px;color:#718096;">
                📅 {row['datetime'].strftime('%d/%m/%Y %H:%M')}
            </div>""", unsafe_allow_html=True)

        with c6:
            st.markdown(f"""
            <div style="padding:10px 8px;background:white;border-radius:6px;
                        margin-bottom:4px;box-shadow:0 1px 3px rgba(0,0,0,0.05);
                        font-size:12px;color:#718096;">
                {row['size']}
            </div>""", unsafe_allow_html=True)

        with c7:
            try:
                pdf_bytes = get_minio_client().get_object(
                    "incident-reports", row['filename']
                ).read()
                st.download_button(
                    label="📥 PDF",
                    data=pdf_bytes,
                    file_name=row['filename'],
                    mime="application/pdf",
                    key=f"dl_{row['filename']}"
                )
            except:
                st.error("❌")

    # ── Pagination ────────────────────────────────────────────
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    p1, p2, p3 = st.columns([2, 6, 2])

    with p1:
        if st.button("← Précédent", disabled=page <= 1):
            st.session_state.page -= 1
            st.rerun()

    with p2:
        st.markdown(
            f"""<div style="text-align:center;padding:8px;color:#718096;font-size:13px;">
                Page <b>{page}</b> sur <b>{total_pages}</b>
                &nbsp;|&nbsp; {total} incident(s)
                &nbsp;|&nbsp; {start+1}–{min(end,total)} affichés
            </div>""",
            unsafe_allow_html=True
        )

    with p3:
        if st.button("Suivant →", disabled=page >= total_pages):
            st.session_state.page += 1
            st.rerun()

else:
    st.markdown("""
    <div class="empty-state">
        <div style="font-size:48px;">📭</div>
        <h3 style="color:#2d3748;margin:16px 0 8px;">Aucun incident trouvé</h3>
        <p style="color:#718096;">Aucun incident ne correspond à vos filtres.</p>
    </div>
    """, unsafe_allow_html=True)