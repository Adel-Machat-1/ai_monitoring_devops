import os
import streamlit as st
import requests
from minio import Minio
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")

st.set_page_config(page_title="Vue d'ensemble", page_icon="📊", layout="wide")

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    [data-testid="stSidebar"] * { color: white !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .kpi-card {
        background: white; border-radius: 12px; padding: 22px;
        text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        border-top: 4px solid #3182ce; transition: transform 0.2s;
    }
    .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,0,0,0.12); }
    .kpi-card.critical  { border-top-color: #e53e3e; }
    .kpi-card.warning   { border-top-color: #ed8936; }
    .kpi-card.today     { border-top-color: #38a169; }
    .kpi-card.anomaly   { border-top-color: #805ad5; }
    .kpi-value { font-size: 40px; font-weight: 800; color: #1a202c; line-height: 1; margin: 6px 0; }
    .kpi-label { font-size: 12px; color: #718096; font-weight: 600;
                 text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-icon  { font-size: 22px; margin-bottom: 4px; }

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

    /* Agent health card */
    .agent-card {
        background: white; border-radius: 12px; padding: 20px 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06); height: 100%;
    }
    .agent-status-ok   { color: #38a169; font-weight: 800; font-size: 15px; }
    .agent-status-down { color: #e53e3e; font-weight: 800; font-size: 15px; }
    .agent-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 8px 0; border-bottom: 1px solid #f0f4f8; font-size: 13px;
    }
    .agent-row:last-child { border-bottom: none; }
    .agent-key { color: #718096; }
    .agent-val { color: #1a202c; font-weight: 700; }

    /* Recent incidents */
    .incident-row {
        background: white; border-radius: 8px; padding: 12px 16px;
        margin-bottom: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .inc-alert { font-size: 13px; font-weight: 600; color: #1a202c; }
    .inc-meta  { font-size: 11px; color: #718096; margin-top: 3px; }
    .badge {
        display: inline-block; padding: 2px 8px; border-radius: 10px;
        font-size: 10px; font-weight: 700;
    }
    .badge-critical { background: #fff5f5; color: #e53e3e; border: 1px solid #fed7d7; }
    .badge-warning  { background: #fffaf0; color: #ed8936; border: 1px solid #fbd38d; }
    .badge-ml       { background: #faf5ff; color: #805ad5; border: 1px solid #e9d8fd; }
    .badge-prom     { background: #ebf8ff; color: #3182ce; border: 1px solid #bee3f8; }

    .stButton button {
        background: #3182ce; color: white; border: none;
        border-radius: 8px; padding: 8px 20px;
        font-weight: 600; transition: background 0.2s;
    }
    .stButton button:hover { background: #2b6cb0; }
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
    _M(MINIO_ENDPOINT, access_key="minioadmin", secret_key="minioadmin", secure=False, region="us-east-1").list_buckets()
    st.sidebar.success("✅ MinIO connecté")
except Exception as e:
    st.sidebar.error(f"❌ MinIO déconnecté: {e}")

try:
    if requests.get(f"{PROMETHEUS_URL}/-/healthy", timeout=2).status_code == 200:
        st.sidebar.success("✅ Prometheus connecté")
    else:
        st.sidebar.error("❌ Prometheus déconnecté")
except:
    st.sidebar.error("❌ Prometheus déconnecté")

st.sidebar.divider()
st.sidebar.caption(f"Dernière vérification : {datetime.now().strftime('%H:%M:%S')}")

# ── Data functions ────────────────────────────────────────────
@st.cache_resource

def get_minio_client():
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    return Minio(endpoint, access_key="minioadmin",
                 secret_key="minioadmin", secure=False)

@st.cache_data(ttl=30)
def load_reports():
    try:
        reports = []
        for obj in get_minio_client().list_objects("incident-reports"):
            name  = obj.object_name
            parts = name.replace(".pdf", "").split("_")
            if len(parts) >= 5:
                date_str, time_str = parts[1], parts[2]
                alert = "_".join(parts[4:])
            elif len(parts) >= 4:
                date_str, time_str = parts[1], parts[2]
                alert = "_".join(parts[3:])
            else:
                continue
            severity = "critical" if any(x in alert for x in ["Down","Crash","Unavailable","NotReady"]) else "warning"
            type_inc = "Anomalie ML" if "Anomaly" in alert else "Alerte Prometheus"
            app = "Autre"
            for k, v in {"keycloak":"Keycloak","postgres":"PostgreSQL","postgresql":"PostgreSQL",
                         "mongodb":"MongoDB","mongo":"MongoDB","redis":"Redis","redpanda":"Redpanda"}.items():
                if k in alert.lower():
                    app = v; break
            try:
                dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            except:
                dt = datetime.now()
            reports.append({"filename":name,"alert":alert,"date":date_str,
                            "datetime":dt,"severity":severity,"type":type_inc,"app":app,
                            "size":f"{obj.size/1024:.1f} KB"})
        df = pd.DataFrame(reports)
        return df.sort_values("datetime", ascending=False) if not df.empty else df
    except Exception as e:
        return pd.DataFrame()
@st.cache_data(ttl=30)
def get_agent_health():
    try:
        AGENT_URL = os.getenv("AGENT_URL", "http://localhost:5000")
        r = requests.get(f"{AGENT_URL}/health", timeout=3)
        if r.status_code == 200:
            return r.json(), True
    except:
        pass
    return {}, False

# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
st.markdown("""
<div class="page-header">
    <h1>📊 Vue d'ensemble</h1>
    <p>Tableau de bord global des incidents Kubernetes</p>
</div>
""", unsafe_allow_html=True)

col_btn, col_time = st.columns([1, 5])
with col_btn:
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()
with col_time:
    st.caption(f"⏱️ Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")

# ── Charger données ───────────────────────────────────────────
df          = load_reports()
health_data, agent_ok = get_agent_health()

total     = len(df)
critical  = len(df[df['severity'] == 'critical'])  if not df.empty else 0
warning   = len(df[df['severity'] == 'warning'])   if not df.empty else 0
today     = len(df[df['date'] == datetime.now().strftime('%Y%m%d')]) if not df.empty else 0
anomalies = len(df[df['type'] == 'Anomalie ML'])   if not df.empty else 0

# ══════════════════════════════════════════════════════════════
# SECTION 1 — KPIs
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="section-title">📈 Indicateurs clés</p>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)

for col, css, icon, val, label, color in [
    (c1, "",         "📊", total,     "Total Incidents", "#1a202c"),
    (c2, "critical", "🔴", critical,  "Critical",        "#e53e3e"),
    (c3, "warning",  "🟠", warning,   "Warning",         "#ed8936"),
    (c4, "today",    "📅", today,     "Aujourd'hui",     "#38a169"),
    (c5, "anomaly",  "🧠", anomalies, "Anomalies ML",    "#805ad5"),
]:
    with col:
        st.markdown(f"""
        <div class="kpi-card {css}">
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-value" style="color:{color};">{val}</div>
            <div class="kpi-label">{label}</div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# SECTION 2 — AGENT HEALTH + TAUX
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="section-title">🤖 Santé de l\'agent & Ratios</p>', unsafe_allow_html=True)

col_health, col_rates = st.columns([2, 3])

with col_health:
    status_class = "agent-status-ok" if agent_ok else "agent-status-down"
    status_text  = "🟢 EN LIGNE" if agent_ok else "🔴 HORS LIGNE"
    queue_size   = health_data.get("queue_size", None)
    model        = health_data.get("model", "—")

    if queue_size is None:
        queue_display = "—"
        queue_color   = "#718096"
    elif queue_size == 0:
        queue_display = "✅ Vide — tout traité"
        queue_color   = "#38a169"
    else:
        queue_display = f"⏳ {queue_size} en attente"
        queue_color   = "#ed8936"
    ts           = health_data.get("timestamp", "")
    if ts:
        try:
            ts = datetime.fromisoformat(ts).strftime('%d/%m %H:%M:%S')
        except:
            ts = "—"

    st.markdown(f"""
    <div class="agent-card">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
            <span style="font-size:28px;">🤖</span>
            <div>
                <div style="font-size:14px;font-weight:700;color:#1a202c;">Agent IA Flask</div>
                <div class="{status_class}">{status_text}</div>
            </div>
        </div>
        <div class="agent-row">
            <span class="agent-key">⏱️ Dernière réponse</span>
            <span class="agent-val">{ts or '—'}</span>
        </div>
        <div class="agent-row">
            <span class="agent-key">📬 Queue alertes</span>
            <span class="agent-val" style="color:{queue_color};">{queue_display}</span>
        </div>
        <div class="agent-row">
            <span class="agent-key">🧠 Modèle GPT actif</span>
            <span class="agent-val">{model}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_rates:
    rate_critical = (critical  / total * 100) if total > 0 else 0
    rate_warning  = (warning   / total * 100) if total > 0 else 0
    rate_anomaly  = (anomalies / total * 100) if total > 0 else 0

    fig_rates = go.Figure()
    fig_rates.add_trace(go.Bar(
        x            = ["Critical", "Warning", "Anomalies ML"],
        y            = [rate_critical, rate_warning, rate_anomaly],
        marker_color = ["#e53e3e", "#ed8936", "#805ad5"],
        text         = [f"{v:.0f}%" for v in [rate_critical, rate_warning, rate_anomaly]],
        textposition = "outside",
        width        = 0.5,
    ))
    fig_rates.update_layout(
        title        = "Répartition des incidents (%)",
        height       = 220,
        plot_bgcolor = "white", paper_bgcolor = "white",
        font         = dict(family="Arial", size=12, color="#2d3748"),
        margin       = dict(l=10, r=10, t=40, b=10),
        yaxis        = dict(range=[0, max(rate_critical, rate_warning, rate_anomaly, 1) * 1.3],
                            gridcolor="#f0f4f8", showgrid=True),
        xaxis        = dict(gridcolor="#f0f4f8"),
        showlegend   = False,
    )
    st.plotly_chart(fig_rates, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# SECTION 3 — INCIDENTS PAR JOUR + RÉPARTITION PAR APP
# ══════════════════════════════════════════════════════════════
if not df.empty:
    st.markdown('<p class="section-title">📅 Évolution & Répartition</p>', unsafe_allow_html=True)

    col_trend, col_donut = st.columns([3, 2])

    with col_trend:
        # Incidents par jour — 14 derniers jours
        today_dt = datetime.now().date()
        days     = [(today_dt - timedelta(days=i)) for i in range(13, -1, -1)]

        df["date_dt"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce").dt.date

        counts_crit = []
        counts_warn = []
        labels      = []
        for d in days:
            day_df = df[df["date_dt"] == d]
            counts_crit.append(len(day_df[day_df["severity"] == "critical"]))
            counts_warn.append(len(day_df[day_df["severity"] == "warning"]))
            labels.append(d.strftime("%d/%m"))

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            name="Critical", x=labels, y=counts_crit,
            marker_color="#e53e3e", opacity=0.85,
        ))
        fig_trend.add_trace(go.Bar(
            name="Warning", x=labels, y=counts_warn,
            marker_color="#ed8936", opacity=0.85,
        ))
        fig_trend.update_layout(
            title        = "Incidents par jour — 14 derniers jours",
            barmode      = "stack",
            height       = 280,
            plot_bgcolor = "white", paper_bgcolor = "white",
            font         = dict(family="Arial", size=11, color="#2d3748"),
            margin       = dict(l=10, r=10, t=40, b=10),
            legend       = dict(orientation="h", yanchor="bottom", y=1.02,
                                xanchor="right", x=1),
            yaxis        = dict(gridcolor="#f0f4f8", tickformat="d"),
            xaxis        = dict(gridcolor="#f0f4f8"),
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_donut:
        # Répartition par application
        app_counts = df['app'].value_counts()
        colors_map = {
            "Keycloak"  : "#3182ce",
            "PostgreSQL": "#38a169",
            "MongoDB"   : "#805ad5",
            "Redis"     : "#e53e3e",
            "Redpanda"  : "#ed8936",
            "Autre"     : "#a0aec0",
        }
        colors = [colors_map.get(a, "#a0aec0") for a in app_counts.index]

        fig_donut = go.Figure(go.Pie(
            labels       = app_counts.index.tolist(),
            values       = app_counts.values.tolist(),
            hole         = 0.55,
            marker       = dict(colors=colors, line=dict(color="white", width=2)),
            textinfo     = "label+percent",
            textfont     = dict(size=11),
            hovertemplate= "<b>%{label}</b><br>%{value} incident(s) — %{percent}<extra></extra>",
        ))
        fig_donut.update_layout(
            title        = "Répartition par application",
            height       = 280,
            paper_bgcolor= "white",
            margin       = dict(l=10, r=10, t=40, b=10),
            showlegend   = False,
            annotations  = [dict(
                text      = f"<b>{total}</b><br>incidents",
                x=0.5, y=0.5, font_size=14, showarrow=False,
                font_color="#1a202c",
            )],
        )
        st.plotly_chart(fig_donut, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# SECTION 4 — DERNIERS INCIDENTS
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="section-title">🕒 Derniers incidents</p>', unsafe_allow_html=True)

if df.empty:
    st.markdown("""
    <div style="background:white;border-radius:12px;padding:40px;text-align:center;
                box-shadow:0 2px 12px rgba(0,0,0,0.06);">
        <div style="font-size:48px;">📭</div>
        <h3 style="color:#2d3748;margin:16px 0 8px;">Aucun incident trouvé</h3>
        <p style="color:#718096;">Le système surveille activement votre cluster.</p>
    </div>""", unsafe_allow_html=True)
else:
    last5 = df.head(5)

    # En-tête colonnes
    h1, h2, h3, h4, h5 = st.columns([3, 1.2, 1.5, 1.5, 1])
    for h, txt in zip([h1,h2,h3,h4,h5],
                      ["Alerte","Sévérité","Type","Application","Date & Heure"]):
        h.markdown(
            f'<div style="background:#f0f4f8;padding:8px 12px;border-radius:6px;'
            f'font-size:11px;font-weight:700;color:#4a5568;text-transform:uppercase;'
            f'letter-spacing:0.5px;">{txt}</div>',
            unsafe_allow_html=True
        )

    for _, row in last5.iterrows():
        is_crit  = row["severity"] == "critical"
        border   = "#e53e3e" if is_crit else "#ed8936"
        b_sev    = "badge-critical" if is_crit else "badge-warning"
        b_type   = "badge-ml" if row["type"] == "Anomalie ML" else "badge-prom"
        sev_lbl  = "CRITICAL" if is_crit else "WARNING"

        c1, c2, c3, c4, c5 = st.columns([3, 1.2, 1.5, 1.5, 1])

        with c1:
            st.markdown(f"""
            <div style="padding:10px 12px;border-left:4px solid {border};
                        background:white;border-radius:6px;margin-bottom:4px;
                        box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                <div class="inc-alert">{'🔴' if is_crit else '🟠'} {row['alert']}</div>
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
                        font-size:12px;color:#4a5568;">{row['app']}</div>""",
            unsafe_allow_html=True)
        with c5:
            st.markdown(f"""
            <div style="padding:10px 8px;background:white;border-radius:6px;
                        margin-bottom:4px;box-shadow:0 1px 3px rgba(0,0,0,0.05);
                        font-size:11px;color:#718096;">
                {row['datetime'].strftime('%d/%m %H:%M')}
            </div>""", unsafe_allow_html=True)

    if len(df) > 5:
        st.markdown(
            f'<div style="text-align:center;padding:12px;color:#718096;font-size:13px;">'
            f'… et <b>{len(df)-5}</b> autres incidents — voir page <b>📋 Incidents</b>'
            f'</div>',
            unsafe_allow_html=True
        )
