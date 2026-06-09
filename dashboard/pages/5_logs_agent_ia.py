"""
Page 5 — Logs Agent IA — Terminal Log Viewer
Dashboard Streamlit — Agent IA Kubernetes Monitoring
"""

import streamlit as st
import re
from datetime import datetime
from collections import deque
st.set_page_config(page_title="Logs Agent IA", page_icon="🖥️", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }

.page-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;
    border-left: 5px solid #534AB7;
}
.page-header h1 { color: #fff; margin: 0; font-size: 1.5rem; font-weight: 500; }
.page-header p  { color: #9ca3af; margin: 4px 0 0; font-size: 0.85rem; }

.kpi { background: var(--color-background-secondary);
       border-radius: var(--border-radius-md); padding: 14px 16px;
       text-align: center; border: 0.5px solid var(--color-border-tertiary); }
.kpi-val { font-size: 1.8rem; font-weight: 500; margin: 4px 0; }
.kpi-lbl { font-size: 0.72rem; color: var(--color-text-secondary); }

/* Terminal container */
.log-wrap {
    background: #0d1117;
    border: 0.5px solid #21262d;
    border-radius: 10px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}
/* Zone scrollable des lignes de log */
.log-body {
    overflow-y: auto;
    max-height: calc(100vh - 280px);
    min-height: 300px;
    scroll-behavior: smooth;
}
.log-topbar {
    background: #161b22;
    padding: 9px 16px;
    border-bottom: 0.5px solid #21262d;
    display: flex; align-items: center; gap: 8px;
    font-size: 11px; color: #8b949e;
}
.log-dot { width:10px; height:10px; border-radius:50%; display:inline-block; }

/* Log rows */
.log-row {
    display: flex; align-items: baseline;
    padding: 3px 16px; gap: 0;
    border-bottom: 0.5px solid rgba(33,38,45,0.6);
    font-family: 'Courier New', monospace;
    font-size: 12px; line-height: 1.7;
}
.log-row:last-child { border-bottom: none; }

.log-ts  {
    color: #3d444d; font-size: 11px;
    min-width: 92px; flex-shrink: 0; padding-right: 10px;
}
.log-lvl {
    font-size: 9px; font-weight: 700; letter-spacing: .4px;
    padding: 1px 7px; border-radius: 3px;
    min-width: 66px; text-align: center; flex-shrink: 0;
    margin-right: 10px; align-self: center;
}
.log-tag {
    font-size: 9px; font-weight: 600; letter-spacing: .3px;
    padding: 1px 7px; border-radius: 3px;
    min-width: 74px; text-align: center; flex-shrink: 0;
    margin-right: 12px; align-self: center;
    background: #21262d; color: #6e7681;
}
.log-msg { flex: 1; white-space: pre-wrap; word-break: break-word; }

/* Level row backgrounds */
.lvl-success  { background: rgba(86,211,100,0.04); }
.lvl-error    { background: rgba(248,81,73,0.07); }
.lvl-warning  { background: rgba(227,179,65,0.05); }
.lvl-anomaly  { background: rgba(255,123,114,0.07); }
.lvl-critical { background: rgba(248,81,73,0.11); }
.lvl-rca      { background: rgba(192,132,252,0.04); }
.lvl-cmd      { background: rgba(57,197,207,0.04); }
.lvl-skip     { opacity: .45; }
.lvl-info     { background: transparent; }

.log-footer {
    background: #161b22; padding: 7px 16px;
    border-top: 0.5px solid #21262d;
    font-size: 10px; color: #484f58;
    display: flex; justify-content: space-between;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h1>🖥️ Logs Agent IA — Terminal</h1>
    <p>Visualisation en temps réel des logs système — colorisés par type</p>
</div>
""", unsafe_allow_html=True)

# ── Constantes ────────────────────────────────────────────────
_ANSI  = re.compile(r'\x1b\[[0-9;]*[mK]|\[[0-9;]+m')
_TS    = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
_NOISE = re.compile(
    r'^\s*[=\-]{10,}\s*$'
    r'|^🤖{3,}\s*$'
    r'|^\s*$'
    r'|^\*\s+Running on'
    r'|^Press CTRL'
    r'|^127\.0\.0\.1\s+-\s+-'
    r'|^HTTP Request:\s+POST https'
)

TAG_PATTERNS = [
    ("INIT",        r'\[démarrage\]'),
    ("SCHEDULER",   r'\[scheduler\]'),
    ("WEBHOOK",     r'\[alerte reçue\]|\[webhook\]'),
    ("SKIP",        r'\[skip\]'),
    ("COLLECTOR",   r'\[collector\]'),
    ("QUEUE",       r'\[queue\]'),
    ("GPT-4",       r'\[gpt.?4\]|gpt-4o'),
    ("PDF",         r'\[pdf\]'),
    ("MINIO",       r'\[minio\]'),
    ("EMAIL",       r'\[email\]|smtp|send_email'),
    ("KSM",         r'\[ksm\]'),
    ("LOKI",        r'\[loki\]'),
    ("EVENTS",      r'\[events?\]'),
    ("ML",          r'\[(keycloak|postgresql|mongodb|redis|redpanda)\]'),
]

TAG_COLORS = {
    "GPT-4":       ("#534AB7", "#c084fc"),
    "PDF":         ("#1f3a5f", "#79c0ff"),
    "MINIO":       ("#0d3a2e", "#56d364"),
    "EMAIL":       ("#3a1f5f", "#d2a8ff"),
    "KSM":         ("#003a3a", "#00d4d4"),
    "SCHEDULER":   ("#1a2a3a", "#79c0ff"),
    "COLLECTOR":   ("#0d2b1a", "#56d364"),
    "QUEUE":       ("#1c2128", "#8b949e"),
    "WEBHOOK":     ("#2b1a1a", "#ff7b72"),
    "SKIP":        ("#161b22", "#3d444d"),
    "LOKI":        ("#2b1f00", "#e3b341"),
    "EVENTS":      ("#0d2b1a", "#56d364"),
    "INIT":        ("#161b22", "#8b949e"),
    "ML":          ("#1f0d3a", "#bc8cff"),
    "LOG":         ("#161b22", "#6e7681"),
}

LEVEL_BADGE = {
    "success":  ("#0d2b0d", "#56d364", "SUCCESS"),
    "error":    ("#2b0d0d", "#f85149", "ERROR  "),
    "warning":  ("#2b2000", "#e3b341", "WARNING"),
    "anomaly":  ("#2b1200", "#ff7b72", "ANOMALY"),
    "critical": ("#2b0d0d", "#f85149", "CRITICAL"),
    "skip":     ("#161b22", "#3d444d", "SKIP   "),
    "rca":      ("#1f0d3a", "#c084fc", "RCA    "),
    "cmd":      ("#0d2428", "#39c5cf", "CMD    "),
    "info":     ("#161b22", "#8b949e", "INFO   "),
}

MSG_COLORS = {
    "success":  "#56d364",
    "error":    "#f85149",
    "warning":  "#e3b341",
    "anomaly":  "#ff7b72",
    "critical": "#f85149",
    "skip":     "#484f58",
    "rca":      "#c084fc",
    "cmd":      "#39c5cf",
    "info":     "#8b949e",
}

# ── Parser ligne par ligne ────────────────────────────────────
def detect_tag(low, msg_stripped):
    for tag, pat in TAG_PATTERNS:
        if re.search(pat, low):
            return tag
    if msg_stripped and msg_stripped[0] in "📛🔍🎯⚡💥🔧🛡️🖥️":
        return "RCA"
    if re.match(r'^\s*\d+\.\s+kubectl|^\s*\$\s+kubectl', msg_stripped, re.I):
        return "CMD"
    return "LOG"

def detect_level(low, msg_stripped, tag):
    if tag == "SKIP":
        return "skip"

    # ── Contenu RCA/GPT-4 : traité séparément pour éviter les faux ERROR ──
    # Le texte de l'analyse GPT-4 parle d'erreurs cluster → ne pas confondre
    # avec une vraie exception système Python.
    if tag in ("RCA", "GPT-4") or (msg_stripped and msg_stripped[0] in "📛🔍🎯💥🔧🛡️🖥️"):
        # Seuls traceback/exception/❌ indiquent une vraie erreur de l'agent
        if re.search(r'traceback|exception|❌', low):
            return "error"
        if re.search(r'✅|réussi|généré', low):
            return "success"
        if re.search(r'⚡\s*critical', low) or (msg_stripped.startswith("⚡") and "critical" in low):
            return "critical"
        if re.search(r'⚠️', low):
            return "warning"
        return "rca"

    # ── Lignes système normales ────────────────────────────────────────────
    if re.search(r'✅|réussi|généré|complet|reçue?\s+\(|upload réussi|thread démarré', low):
        return "success"
    if re.search(r'error|erreur|failed|exception|traceback|❌', low):
        return "error"
    if re.search(r'🔴|anomalie détectée|score d\'anomalie', low):
        return "anomaly"
    if re.search(r'⚡\s*critical', low) or (msg_stripped.startswith("⚡") and "critical" in low):
        return "critical"
    if re.search(r'⚠️|warning|attente d\'approbation', low):
        return "warning"
    if tag == "CMD" or re.match(r'^\s*\d+\.\s+kubectl|^\s*\$\s+kubectl', msg_stripped, re.I):
        return "cmd"
    return "info"

def parse_logs(log_file, n=3000):
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            raw_lines = list(deque(f, maxlen=n))
    except FileNotFoundError:
        return []

    # Garde uniquement les lignes depuis le dernier démarrage de l'agent
    start_idx = 0
    for i, raw in enumerate(raw_lines):
        if "[démarrage]" in _ANSI.sub('', raw).lower():
            start_idx = i
    raw_lines = raw_lines[start_idx:]

    entries = []
    for raw in raw_lines:
        line = _ANSI.sub('', raw).strip()
        if not line or _NOISE.match(line):
            continue

        m_ts = _TS.search(line)
        ts      = m_ts.group(1) if m_ts else ""
        ts_short = ts[11:] if ts else ""         # HH:MM:SS
        msg     = line[m_ts.end():].strip(" —-|>").strip() if m_ts else line

        if not msg or not msg.strip("= \t"):
            continue

        low          = msg.lower()
        msg_stripped = msg.lstrip()
        tag          = detect_tag(low, msg_stripped)
        level        = detect_level(low, msg_stripped, tag)

        entries.append({
            "ts":       ts,
            "ts_short": ts_short,
            "tag":      tag,
            "level":    level,
            "msg":      msg,
        })

    return entries

def _esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def render_row(entry):
    level = entry["level"]
    tag   = entry["tag"]

    # Badge niveau
    lb_bg, lb_col, lb_txt = LEVEL_BADGE.get(level, LEVEL_BADGE["info"])
    # Badge tag
    tag_bg, tag_col = TAG_COLORS.get(tag, ("#161b22", "#6e7681"))
    # Couleur message
    msg_col = MSG_COLORS.get(level, "#8b949e")

    row_cls = f"log-row lvl-{level}"
    safe_msg = _esc(entry["msg"])

    return (
        f'<div class="{row_cls}">'
        f'<span class="log-ts">{entry["ts_short"]}</span>'
        f'<span class="log-lvl" style="background:{lb_bg};color:{lb_col};">{lb_txt.strip()}</span>'
        f'<span class="log-tag" style="background:{tag_bg};color:{tag_col};">{tag}</span>'
        f'<span class="log-msg" style="color:{msg_col};">{safe_msg}</span>'
        f'</div>'
    )

# ── Valeurs fixes (fichier et tail hardcodés) ─────────────────
log_path = "agent_ia.log"
tail_n   = 200

# ── Sidebar (scope principal — ne recharge pas avec le fragment) ──
with st.sidebar:
    st.markdown("### ⚙️ Filtres")
    filter_level = st.multiselect(
        "Niveau",
        ["success", "error", "warning", "anomaly", "critical", "rca", "cmd", "skip", "info"],
        default=["success", "error", "warning", "anomaly", "critical", "rca", "cmd", "info"],
    )
    all_tags = ["GPT-4","PDF","MINIO","EMAIL","KSM","SCHEDULER",
                "COLLECTOR","QUEUE","WEBHOOK","SKIP","LOKI","EVENTS","INIT","ML","RCA","CMD","LOG"]
    filter_tags = st.multiselect("Tag", all_tags, default=all_tags)

# Barre de recherche (scope principal)
search = st.text_input("🔍  Rechercher dans les logs…", placeholder="ex: keycloak, ✅, kubectl…")

st.markdown("<br>", unsafe_allow_html=True)

# ── Fragment temps réel : relit le fichier toutes les 2s ──────
@st.fragment(run_every=2)
def live_terminal(log_path, filter_level, filter_tags, search, tail_n):
    all_entries = parse_logs(log_path)

    # Filtrage
    entries = all_entries
    if filter_level:
        entries = [e for e in entries if e["level"] in filter_level]
    if filter_tags:
        entries = [e for e in entries if e["tag"] in filter_tags]
    if search.strip():
        q = search.strip().lower()
        entries = [e for e in entries if q in e["msg"].lower()]

    # ── KPIs ──────────────────────────────────────────────────
    total     = len(all_entries)
    n_errors  = sum(1 for e in all_entries if e["level"] in ("error", "critical"))
    n_anom    = sum(1 for e in all_entries if e["level"] == "anomaly")
    n_success = sum(1 for e in all_entries if e["level"] == "success")

    c1, c2, c3, c4 = st.columns(4)
    for col, lbl, val, color in [
        (c1, "Total lignes", total,     "var(--color-text-primary)"),
        (c2, "🔴 Erreurs",   n_errors,  "#f85149"),
        (c3, "⚠️ Anomalies", n_anom,    "#ff7b72"),
        (c4, "✅ Succès",    n_success, "#56d364"),
    ]:
        col.markdown(
            f'<div class="kpi"><div class="kpi-lbl">{lbl}</div>'
            f'<div class="kpi-val" style="color:{color};">{val}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Terminal (tail des N dernières lignes filtrées) ────────
    shown = entries[-tail_n:]

    if not shown:
        st.markdown("""
        <div style="text-align:center;padding:60px;color:var(--color-text-tertiary);">
          Aucun log trouvé.<br>
          <span style="font-size:12px;">Lance python main.py ou ajuste les filtres.</span>
        </div>""", unsafe_allow_html=True)
        return

    rows_html  = "".join(render_row(e) for e in shown)
    now_str    = datetime.now().strftime("%H:%M:%S")
    total_filt = len(entries)

    st.markdown(f"""
    <div class="log-wrap" id="log-terminal">
      <div class="log-topbar">
        <span class="log-dot" style="background:#f85149;"></span>
        <span class="log-dot" style="background:#e3b341;"></span>
        <span class="log-dot" style="background:#56d364;"></span>
        &nbsp;&nbsp;<strong style="color:#c9d1d9;">agent_ia.log</strong>
        &nbsp;·&nbsp; {total_filt} ligne(s) filtrée(s)
        &nbsp;·&nbsp; {len(shown)} affichée(s)
        &nbsp;·&nbsp;
        <span style="color:#56d364;">● LIVE</span>
        &nbsp;·&nbsp; mis à jour {now_str}
      </div>
      <div class="log-body" id="log-body">
        {rows_html}
      </div>
      <div class="log-footer">
        <span>{shown[0]["ts"]} → {shown[-1]["ts"]}</span>
        <span>tail -{tail_n} · {now_str}</span>
      </div>
    </div>
    <script>
      (function() {{
        var body = document.getElementById('log-body');
        if (body) body.scrollTop = body.scrollHeight;
      }})();
    </script>
    """, unsafe_allow_html=True)


live_terminal(log_path, filter_level, filter_tags, search, tail_n)
