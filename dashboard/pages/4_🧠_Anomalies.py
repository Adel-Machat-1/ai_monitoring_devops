"""
Page 4 — Anomaly Detection ML
Scores d'anomalie en temps réel via Isolation Forest + historique MinIO
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import streamlit as st
import requests
import numpy as np
import joblib
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from minio import Minio

st.set_page_config(page_title="Anomalies ML", page_icon="🧠", layout="wide")

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

    .page-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px; padding: 24px 28px;
        margin-bottom: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    .page-header h1 { color: white; font-size: 24px; font-weight: 700; margin: 0; }
    .page-header p  { color: #a0aec0; font-size: 14px; margin: 4px 0 0; }

    .section-title {
        font-size: 16px; font-weight: 700; color: #2d3748;
        margin: 24px 0 16px; padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
    }

    /* Score card */
    .score-card {
        background: white; border-radius: 14px; padding: 20px 16px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.07);
        text-align: center; position: relative; overflow: hidden;
    }
    .score-card.normal   { border-top: 4px solid #38a169; }
    .score-card.warning  { border-top: 4px solid #ed8936; }
    .score-card.danger   { border-top: 4px solid #e53e3e; }
    .score-card.unknown  { border-top: 4px solid #718096; }
    .score-app   { font-size: 13px; font-weight: 700; color: #4a5568; margin-bottom: 2px; }
    .score-value { font-size: 36px; font-weight: 900; line-height: 1; margin: 6px 0; }
    .score-label { font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
                   padding: 3px 10px; border-radius: 10px; display: inline-block; }
    .label-normal  { background: #f0fff4; color: #38a169; }
    .label-warning { background: #fffaf0; color: #ed8936; }
    .label-danger  { background: #fff5f5; color: #e53e3e; }
    .label-unknown { background: #f7fafc; color: #718096; }
    .label-error   { background: #fff5f5; color: #718096; }
    .score-points  { font-size: 10px; color: #a0aec0; margin-top: 8px; }

    /* Model status */
    .model-badge {
        display: inline-block; padding: 3px 10px; border-radius: 20px;
        font-size: 10px; font-weight: 700;
    }
    .model-ok  { background: #f0fff4; color: #38a169; border: 1px solid #c6f6d5; }
    .model-nok { background: #fff5f5; color: #e53e3e; border: 1px solid #fed7d7; }

    /* History row */
    .hist-row {
        background: white; border-radius: 8px; padding: 12px 16px;
        margin-bottom: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        border-left: 4px solid #805ad5;
        display: flex; align-items: center; gap: 12px;
    }
    .hist-alert { font-size: 13px; font-weight: 600; color: #1a202c; flex: 1; }
    .hist-date  { font-size: 11px; color: #718096; white-space: nowrap; }
    .hist-badge {
        font-size: 10px; font-weight: 700; padding: 2px 8px;
        border-radius: 10px; white-space: nowrap;
    }

    .info-box {
        background: white; border-radius: 12px; padding: 20px 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06); margin-bottom: 16px;
        border-left: 4px solid #805ad5;
    }
    .info-box h4 { color: #1a202c; font-size: 14px; font-weight: 700; margin: 0 0 10px; }
    .info-box p  { color: #4a5568; font-size: 13px; line-height: 1.6; margin: 0; }

    .stButton button {
        background: #805ad5 !important; color: white !important;
        border: none !important; border-radius: 8px !important; font-weight: 600 !important;
    }

    .empty-box {
        background: white; border-radius: 12px; padding: 40px;
        text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        color: #718096; font-size: 14px;
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
    _M(os.getenv("MINIO_ENDPOINT", "localhost:9000"), access_key="minioadmin", secret_key="minioadmin123", secure=False).list_buckets()
    st.sidebar.success("✅ MinIO connecté")
except:
    st.sidebar.error("❌ MinIO déconnecté")

try:
    if requests.get(f"{os.getenv('PROMETHEUS_URL', 'http://localhost:9090')}/-/healthy", timeout=2).status_code == 200:
        st.sidebar.success("✅ Prometheus connecté")
    else:
        st.sidebar.error("❌ Prometheus déconnecté")
except:
    st.sidebar.error("❌ Prometheus déconnecté")

st.sidebar.divider()
st.sidebar.caption(f"Vérification : {datetime.now().strftime('%H:%M:%S')}")

# ── Constantes ────────────────────────────────────────────────
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MODELS_DIR     = os.path.join(os.path.dirname(__file__), '..', '..', 'models')

APP_COLORS = {
    "Keycloak"  : "#3182ce",
    "PostgreSQL": "#38a169",
    "MongoDB"   : "#805ad5",
    "Redis"     : "#e53e3e",
    "Redpanda"  : "#ed8936",
}

# ── Même features que collector.py (ordre identique au modèle entraîné) ──────
APPS_FEATURES = {
    "Keycloak": {
        "key": "keycloak",
        "queries": {
            "cpu":      'sum(rate(container_cpu_usage_seconds_total{pod=~"keycloak.*",namespace="int-ksm-backdata",container="keycloak"}[5m]))',
            "memory":   'sum(container_memory_usage_bytes{pod=~"keycloak.*",namespace="int-ksm-backdata",container="keycloak"})',
            "restarts": 'sum(kube_pod_container_status_restarts_total{pod=~"keycloak.*",namespace="int-ksm-backdata"})',
            "up":       'sum(up{job="keycloak-metrics"})',
        },
    },
    "PostgreSQL": {
        "key": "postgresql",
        "queries": {
            "cpu":    'sum(rate(container_cpu_usage_seconds_total{pod=~"postgresql.*",namespace="int-ksm-backdata"}[5m]))',
            "memory": 'sum(container_memory_usage_bytes{pod=~"postgresql.*",namespace="int-ksm-backdata"})',
            "up":     'sum(up{job="postgresql-primary-metrics"})',
        },
    },
    "MongoDB": {
        "key": "mongodb",
        "queries": {
            "cpu":    'sum(rate(container_cpu_usage_seconds_total{pod=~"mongodb.*",namespace="int-ksm-backdata"}[5m]))',
            "memory": 'sum(container_memory_usage_bytes{pod=~"mongodb.*",namespace="int-ksm-backdata"})',
            "up":     'sum(up{job="mongodb-metrics"})',
        },
    },
    "Redis": {
        "key": "redis",
        "queries": {
            "cpu":         'sum(rate(container_cpu_usage_seconds_total{pod=~"redis.*",namespace="int-ksm-backdata"}[5m]))',
            "memory":      'sum(container_memory_usage_bytes{pod=~"redis.*",namespace="int-ksm-backdata"})',
            "connections": 'sum(redis_connected_clients)',
            "up":          'sum(up{job="redis-metrics"})',
        },
    },
    "Redpanda": {
        "key": "redpanda",
        "queries": {
            "cpu":    'sum(rate(container_cpu_usage_seconds_total{pod=~"redpanda.*",namespace="int-ksm-backdata"}[5m]))',
            "memory": 'sum(container_memory_usage_bytes{pod=~"redpanda.*",namespace="int-ksm-backdata"})',
            "up":     'sum(up{job="redpanda"})',
        },
    },
}

# ── Helpers ───────────────────────────────────────────────────
def _prom(query):
    try:
        r = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                         params={"query": query}, timeout=4).json()
        res = r["data"]["result"]
        return float(res[0]["value"][1]) if res else 0.0
    except:
        return 0.0

def get_anomaly_scores():
    """
    Calcule le score d'anomalie en temps réel.
    Utilise exactement les mêmes features que collector.py
    pour éviter tout mismatch de dimension avec le modèle entraîné.
    """
    results = {}
    for display_name, app_cfg in APPS_FEATURES.items():
        app_key     = app_cfg["key"]
        model_path  = os.path.join(MODELS_DIR, f"{app_key}_model.pkl")
        scaler_path = os.path.join(MODELS_DIR, f"{app_key}_scaler.pkl")

        # ── Collecter les métriques avec les requêtes exactes du collector ──
        raw_metrics = {}
        for metric_name, query in app_cfg["queries"].items():
            raw_metrics[metric_name] = _prom(query)

        # Pour l'affichage des cartes
        cpu      = raw_metrics.get("cpu", 0)
        memory   = raw_metrics.get("memory", 0) / (1024 * 1024)
        restarts = int(raw_metrics.get("restarts", 0))

        model_exists = os.path.exists(model_path)
        model_mtime  = datetime.fromtimestamp(os.path.getmtime(model_path)) if model_exists else None

        # Calculer le score si modèle disponible
        if model_exists:
            try:
                model  = joblib.load(model_path)
                scaler = joblib.load(scaler_path)

                # ── Features dans le même ordre que le collector ──────────
                # Utiliser les valeurs brutes (memory en bytes, pas en MB)
                feature_values = list(raw_metrics.values())
                n_expected = scaler.n_features_in_
                n_got      = len(feature_values)

                if n_got != n_expected:
                    raise ValueError(
                        f"Features mismatch : modèle attend {n_expected}, "
                        f"dashboard envoie {n_got} ({list(raw_metrics.keys())})"
                    )

                features        = np.array(feature_values).reshape(1, -1)
                features_scaled = scaler.transform(features)
                raw_score       = model.score_samples(features_scaled)[0]
                anomaly_score   = max(0.0, min(1.0, -raw_score))
                is_anomaly      = model.predict(features_scaled)[0] == -1 and anomaly_score >= 0.55
                status = "danger"  if (is_anomaly and anomaly_score >= 0.75) \
                    else "warning" if (is_anomaly and anomaly_score >= 0.55) \
                    else "normal"

            except Exception as e:
                anomaly_score = 0.0
                is_anomaly    = False
                status        = "error"   # distingue "sans modèle" de "erreur feature"
                model_exists  = False
        else:
            anomaly_score = 0.0
            is_anomaly    = False
            status        = "unknown"

        results[display_name] = {
            "score"      : anomaly_score,
            "is_anomaly" : is_anomaly,
            "status"     : status,
            "model_ready": model_exists,
            "model_date" : model_mtime,
            "cpu"        : cpu,
            "memory_mb"  : memory,
            "restarts"   : restarts,
            "n_features" : len(raw_metrics),
        }
    return results

@st.cache_data(ttl=60)
def get_anomaly_history():
    """Charge l'historique des anomalies ML depuis MinIO."""
    try:
        client = Minio(MINIO_ENDPOINT, access_key="minioadmin",
                       secret_key="minioadmin123", secure=False)
        rows = []
        for obj in client.list_objects("incident-reports"):
            name = obj.object_name
            if "Anomaly" not in name:
                continue
            parts = name.replace(".pdf", "").split("_")
            if len(parts) >= 5:
                date_str, time_str = parts[1], parts[2]
                alert = "_".join(parts[4:])
            elif len(parts) >= 4:
                date_str, time_str = parts[1], parts[2]
                alert = "_".join(parts[3:])
            else:
                continue
            try:
                dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            except:
                dt = datetime.now()

            app = "Autre"
            for k, v in {"keycloak": "Keycloak", "postgresql": "PostgreSQL",
                          "mongodb": "MongoDB", "redis": "Redis", "redpanda": "Redpanda"}.items():
                if k in alert.lower():
                    app = v
                    break

            score_hint = "warning"
            if "Critical" in alert or "critical" in alert:
                score_hint = "critical"

            rows.append({
                "filename": name,
                "alert"   : alert,
                "app"     : app,
                "datetime": dt,
                "severity": score_hint,
                "size"    : f"{obj.size/1024:.1f} KB",
            })
        df = pd.DataFrame(rows)
        return df.sort_values("datetime", ascending=False) if not df.empty else df
    except:
        return pd.DataFrame()

# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
st.markdown("""
<div class="page-header">
    <h1>🧠 Anomaly Detection ML</h1>
    <p>Scores d'anomalie en temps réel via Isolation Forest · Historique des détections</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# SECTIONS 1 & 2 — SCORES + JAUGES — Fragment auto-refresh 30s
# ══════════════════════════════════════════════════════════════
@st.fragment(run_every=30)
def live_scores():
    scores = get_anomaly_scores()
    now    = datetime.now().strftime('%H:%M:%S')

    # ── Titre + timestamp ─────────────────────────────────────
    st.markdown(
        f'<p class="section-title">🎯 Scores d\'anomalie en temps réel '
        f'<span style="font-size:12px;font-weight:400;color:#a0aec0;">'
        f'● LIVE — mis à jour à {now} (refresh auto 30s)</span></p>',
        unsafe_allow_html=True
    )

    # ── Score cards ───────────────────────────────────────────
    cols = st.columns(5)
    for i, (name, data) in enumerate(scores.items()):
        status = data["status"]
        score  = data["score"]

        if status == "danger":
            score_color = "#e53e3e"
            label_text  = "🔴 ANOMALIE"
            label_class = "label-danger"
        elif status == "warning":
            score_color = "#ed8936"
            label_text  = "⚠️ SUSPECT"
            label_class = "label-warning"
        elif status == "normal":
            score_color = "#38a169"
            label_text  = "✅ NORMAL"
            label_class = "label-normal"
        else:
            # "unknown" ou "error"
            score_color = "#718096"
            label_text  = "⏳ Sans modèle"
            label_class = "label-unknown"

        model_badge = (
            f'<span class="model-badge model-ok">Modèle ✓ ({data["n_features"]} features)</span>'
            if data["model_ready"] else
            f'<span class="model-badge model-nok">Sans modèle</span>'
        )

        with cols[i]:
            st.markdown(f"""
            <div class="score-card {status}">
                <div class="score-app">{name}</div>
                <div class="score-value" style="color:{score_color};">{score:.2f}</div>
                <div><span class="score-label {label_class}">{label_text}</span></div>
                <div style="margin-top:8px;">{model_badge}</div>
                <div class="score-points">
                    🕒 {data['model_date'].strftime('%d/%m %H:%M') if data['model_date'] else 'N/A'}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Jauges Plotly ─────────────────────────────────────────
    st.markdown('<p class="section-title">📊 Jauges de détection</p>',
                unsafe_allow_html=True)

    fig = go.Figure()
    for i, (name, data) in enumerate(scores.items()):
        score     = data["score"]
        bar_color = "#e53e3e" if score >= 0.75 else "#ed8936" if score >= 0.55 else "#38a169"

        fig.add_trace(go.Indicator(
            mode   = "gauge+number",
            value  = round(score, 3),
            title  = {"text": name, "font": {"size": 13, "color": "#2d3748"}},
            domain = {"row": 0, "column": i},
            gauge  = {
                "axis": {"range": [0, 1], "tickwidth": 1, "tickcolor": "#e2e8f0",
                         "tickvals": [0, 0.55, 0.75, 1],
                         "ticktext": ["0", "0.55", "0.75", "1"]},
                "bar":        {"color": bar_color},
                "bgcolor":    "white",
                "borderwidth": 1,
                "bordercolor": "#e2e8f0",
                "steps": [
                    {"range": [0,    0.55], "color": "#f0fff4"},
                    {"range": [0.55, 0.75], "color": "#fffaf0"},
                    {"range": [0.75, 1.0],  "color": "#fff5f5"},
                ],
                "threshold": {"line": {"color": "#e53e3e", "width": 3},
                              "thickness": 0.8, "value": 0.75},
            },
            number = {"font": {"size": 22, "color": bar_color}},
        ))

    fig.update_layout(
        grid          = {"rows": 1, "columns": 5, "pattern": "independent"},
        height        = 240,
        margin        = dict(l=10, r=10, t=30, b=10),
        paper_bgcolor = "#f8fafc",
        plot_bgcolor  = "#f8fafc",
        font          = dict(family="Arial"),
    )
    st.plotly_chart(fig, use_container_width=True)

live_scores()

# Légende seuils
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("""
    <div style="background:white;border-radius:10px;padding:12px 16px;
                box-shadow:0 1px 4px rgba(0,0,0,0.06);
                border-left:4px solid #38a169;text-align:center;">
        <b style="color:#38a169;">Score &lt; 0.55</b>
        <div style="font-size:12px;color:#718096;margin-top:4px;">Normal — Pas d'alerte</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div style="background:white;border-radius:10px;padding:12px 16px;
                box-shadow:0 1px 4px rgba(0,0,0,0.06);
                border-left:4px solid #ed8936;text-align:center;">
        <b style="color:#ed8936;">0.55 — 0.75</b>
        <div style="font-size:12px;color:#718096;margin-top:4px;">Suspect — Alerte WARNING</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown("""
    <div style="background:white;border-radius:10px;padding:12px 16px;
                box-shadow:0 1px 4px rgba(0,0,0,0.06);
                border-left:4px solid #e53e3e;text-align:center;">
        <b style="color:#e53e3e;">Score &gt; 0.75</b>
        <div style="font-size:12px;color:#718096;margin-top:4px;">Anomalie — Alerte CRITICAL</div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# SECTION 3 — HISTORIQUE DES ANOMALIES DÉTECTÉES
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="section-title">📜 Historique des anomalies détectées</p>',
            unsafe_allow_html=True)

history_df = get_anomaly_history()

if history_df.empty:
    st.markdown("""
    <div class="empty-box">
        <div style="font-size:40px;margin-bottom:12px;">🎉</div>
        <b>Aucune anomalie ML détectée pour l'instant</b><br>
        <span style="font-size:12px;">Les modèles surveillent activement le cluster.</span>
    </div>
    """, unsafe_allow_html=True)
else:
    # KPIs historique
    total_anom = len(history_df)
    apps_aff   = history_df['app'].nunique()
    last_anom  = history_df['datetime'].max().strftime('%d/%m/%Y %H:%M')

    k1, k2, k3 = st.columns(3)
    for col, icon, val, label, color in [
        (k1, "🧠", total_anom,  "Total anomalies",       "#805ad5"),
        (k2, "📱", apps_aff,    "Services touchés",      "#3182ce"),
        (k3, "🕒", last_anom,   "Dernière anomalie",     "#ed8936"),
    ]:
        col.markdown(f"""
        <div style="background:white;border-radius:12px;padding:16px;text-align:center;
                    box-shadow:0 2px 8px rgba(0,0,0,0.06);border-top:3px solid {color};">
            <div style="font-size:24px;">{icon}</div>
            <div style="font-size:22px;font-weight:800;color:{color};margin:4px 0;">{val}</div>
            <div style="font-size:11px;color:#718096;text-transform:uppercase;
                        letter-spacing:0.5px;">{label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Graphique timeline
    fig2 = go.Figure()
    for app_name in history_df['app'].unique():
        app_df = history_df[history_df['app'] == app_name].copy()
        app_df['count'] = range(1, len(app_df)+1)
        fig2.add_trace(go.Scatter(
            x    = app_df['datetime'],
            y    = [app_name] * len(app_df),
            mode = "markers",
            name = app_name,
            marker = dict(
                size   = 14,
                color  = APP_COLORS.get(app_name, "#805ad5"),
                symbol = "diamond",
                line   = dict(width=1, color="white"),
            ),
            hovertemplate = (
                "<b>%{y}</b><br>"
                "Date : %{x|%d/%m/%Y %H:%M}<br>"
                "<extra></extra>"
            ),
        ))

    fig2.update_layout(
        title         = "Timeline des anomalies par service",
        height        = 240,
        plot_bgcolor  = "white",
        paper_bgcolor = "#f8fafc",
        font          = dict(family="Arial", size=12, color="#2d3748"),
        margin        = dict(l=20, r=20, t=40, b=20),
        xaxis         = dict(gridcolor="#f0f4f8", title=""),
        yaxis         = dict(gridcolor="#f0f4f8", title=""),
        showlegend    = False,
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Liste détaillée (dernières 10)
    st.markdown('<p class="section-title" style="margin-top:8px;">🔍 Dernières anomalies</p>',
                unsafe_allow_html=True)

    minio_client = Minio(MINIO_ENDPOINT, access_key="minioadmin",
                         secret_key="minioadmin123", secure=False)

    for _, row in history_df.head(10).iterrows():
        sev_color = "#e53e3e" if row['severity'] == 'critical' else "#805ad5"
        sev_bg    = "#fff5f5" if row['severity'] == 'critical' else "#faf5ff"
        sev_txt   = "CRITICAL" if row['severity'] == 'critical' else "ML"

        c1, c2 = st.columns([8, 2])
        with c1:
            st.markdown(f"""
            <div style="background:white;border-radius:8px;padding:12px 16px;
                        margin-bottom:6px;box-shadow:0 1px 4px rgba(0,0,0,0.05);
                        border-left:4px solid {sev_color};">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="font-size:20px;">🧠</span>
                    <div style="flex:1;">
                        <div style="font-size:13px;font-weight:600;color:#1a202c;">
                            {row['alert']}
                        </div>
                        <div style="font-size:11px;color:#718096;margin-top:2px;">
                            📱 {row['app']} &nbsp;·&nbsp;
                            📅 {row['datetime'].strftime('%d/%m/%Y %H:%M')} &nbsp;·&nbsp;
                            📄 {row['size']}
                        </div>
                    </div>
                    <span style="background:{sev_bg};color:{sev_color};
                                 font-size:10px;font-weight:700;padding:3px 10px;
                                 border-radius:10px;">{sev_txt}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            try:
                pdf_bytes = minio_client.get_object(
                    "incident-reports", row['filename']
                ).read()
                st.download_button(
                    label     = "📥 Rapport",
                    data      = pdf_bytes,
                    file_name = row['filename'],
                    mime      = "application/pdf",
                    key       = f"anom_{row['filename']}",
                )
            except:
                st.markdown("❌", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# SECTION 4 — COMMENT ÇA MARCHE (compact)
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="section-title">ℹ️ Fonctionnement</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    <div class="info-box">
        <h4>🔬 Isolation Forest — Pipeline en 3 phases</h4>
        <p>
            ⏱️ <b>Phase 1 — Collecte</b> : métriques toutes les 5 min (CPU, RAM, restarts…)<br><br>
            🧠 <b>Phase 2 — Entraînement</b> : modèle entraîné dès 5 points collectés<br><br>
            🔍 <b>Phase 3 — Détection</b> : score 0→1 calculé à chaque cycle
        </p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="info-box">
        <h4>⚙️ Paramètres clés</h4>
        <p>
            <b>MIN_TRAINING_POINTS</b> : 5 cycles avant le premier modèle<br><br>
            <b>CONTAMINATION</b> : 3 % d'anomalies attendues<br><br>
            <b>SEUIL ALERTE</b> : score ≥ 0.55 (WARNING) · ≥ 0.75 (CRITICAL)<br><br>
            <b>DEDUP</b> : 30 min entre deux alertes identiques
        </p>
    </div>
    """, unsafe_allow_html=True)
