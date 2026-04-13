from utils.extractors import extract_metrics_summary, extract_logs_text
from datetime import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
from core.kubernetes_events import format_events_text


def generate_pdf_report(parsed, metrics, logs, analysis, events=[]):
    print("\n[PDF] Génération du rapport PDF...")

    metrics_summary = extract_metrics_summary(metrics)
    logs_text       = extract_logs_text(logs, max_lines=20)
    timestamp       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename        = f"incident_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{parsed['name']}.pdf"

    # ── Couleurs ──────────────────────────────────────────────
    BLUE       = HexColor("#1F4E79")
    LIGHT_BLUE = HexColor("#2E75B6")
    RED        = HexColor("#C00000")
    ORANGE     = HexColor("#C55A11")
    GREEN      = HexColor("#1E6B3C")
    GRAY       = HexColor("#595959")
    LIGHT_GRAY = HexColor("#F2F2F2")
    WHITE      = HexColor("#FFFFFF")

    sev       = parsed['severity'].lower()
    SEV_COLOR = RED if sev == "critical" else ORANGE if sev == "warning" else GREEN

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm,   bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    # ── Styles ────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "Title", parent=styles["Normal"],
        fontSize=18, textColor=WHITE,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        spaceAfter=4,
        leading=22,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=10, textColor=WHITE,
        alignment=TA_CENTER,
        fontName="Helvetica",
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Normal"],
        fontSize=12, textColor=WHITE,
        fontName="Helvetica-Bold",
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, textColor=HexColor("#000000"),
        fontName="Helvetica",
        spaceAfter=4, leading=14,
        wordWrap='CJK',
    )
    label_style = ParagraphStyle(
        "Label", parent=styles["Normal"],
        fontSize=10, textColor=GRAY,
        fontName="Helvetica-Bold",
    )

    content = []

    # ══════════════════════════════════════════════════════════
    # PAGE 1 — EN-TÊTE + ALERTE + MÉTRIQUES
    # ══════════════════════════════════════════════════════════

    # ── EN-TÊTE ───────────────────────────────────────────────
    header = Table(
        [[Paragraph("Agent IA — Rapport d'Incident Kubernetes", title_style)]],
        colWidths=[17*cm]
    )
    header.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), BLUE),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 20),
        ("BOTTOMPADDING", (0,0), (-1,-1), 20),
    ]))
    content.append(header)

    subheader = Table(
        [[Paragraph(f"Généré le {timestamp}  |  Cluster Kubernetes / k3d", subtitle_style)]],
        colWidths=[17*cm]
    )
    subheader.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LIGHT_BLUE),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    content.append(subheader)
    content.append(Spacer(1, 0.4*cm))

    # ── BADGE SÉVÉRITÉ ────────────────────────────────────────
    badge = Table([[Paragraph(
        f"{parsed['severity'].upper()} — {parsed['name']}",
        ParagraphStyle("Badge", parent=styles["Normal"],
            fontSize=13, textColor=WHITE,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER)
    )]], colWidths=[17*cm])
    badge.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), SEV_COLOR),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
    ]))
    content.append(badge)
    content.append(Spacer(1, 0.5*cm))

    # ── SECTION 1 : INFORMATIONS DE L'ALERTE ─────────────────
    sec1 = Table(
        [[Paragraph("1. Informations de l'Alerte", section_style)]],
        colWidths=[17*cm]
    )
    sec1.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LIGHT_BLUE),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    content.append(sec1)
    content.append(Spacer(1, 0.2*cm))

    description = parsed.get('description', '') or 'N/A'
    if len(description) > 200:
        description = description[:200] + "..."

    alert_rows = [
        [Paragraph("Alert Name",    label_style), Paragraph(parsed['name'],      body_style)],
        [Paragraph("Service",       label_style), Paragraph(parsed['service'],   body_style)],
        [Paragraph("Job",           label_style), Paragraph(parsed['job'],       body_style)],
        [Paragraph("Namespace",     label_style), Paragraph(parsed['namespace'], body_style)],
        [Paragraph("Sévérité",      label_style), Paragraph(
            parsed['severity'].upper(),
            ParagraphStyle("Sev", parent=styles["Normal"],
                fontSize=10, textColor=SEV_COLOR, fontName="Helvetica-Bold"))],
        [Paragraph("Status",        label_style), Paragraph(parsed['status'],    body_style)],
        [Paragraph("Description",   label_style), Paragraph(description,        body_style)],
        [Paragraph("Pods affectés", label_style), Paragraph(str(parsed['affected_pods']), body_style)],
        [Paragraph("Démarré le",    label_style), Paragraph(
            parsed['started_at'][:19].replace("T", " "),  body_style)],
    ]
    t1 = Table(alert_rows, colWidths=[4*cm, 13*cm])
    t1.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), LIGHT_GRAY),
        ("GRID",          (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    content.append(t1)
    content.append(Spacer(1, 0.5*cm))

    # ── SECTION 2 : MÉTRIQUES PROMETHEUS ─────────────────────
    sec2 = Table(
        [[Paragraph("2. Métriques Prometheus", section_style)]],
        colWidths=[17*cm]
    )
    sec2.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LIGHT_BLUE),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    content.append(sec2)
    content.append(Spacer(1, 0.2*cm))

    restarts_val = str(metrics_summary.get('restarts', 'N/A'))
    try:
        restarts_color = RED if int(restarts_val) > 5 else HexColor("#000000")
    except:
        restarts_color = HexColor("#000000")

    metrics_rows = [
        [Paragraph("Pod analysé", label_style), Paragraph(str(metrics_summary.get('pod_used', 'N/A')), body_style)],
        [Paragraph("Up/Down",     label_style), Paragraph(str(metrics_summary.get('up', 'N/A')),       body_style)],
        [Paragraph("Restarts",    label_style), Paragraph(restarts_val,
            ParagraphStyle("R", parent=styles["Normal"],
                fontSize=10, textColor=restarts_color, fontName="Helvetica-Bold"))],
        [Paragraph("CPU Usage",   label_style), Paragraph(str(metrics_summary.get('cpu', 'N/A')),      body_style)],
        [Paragraph("Memory",      label_style), Paragraph(str(metrics_summary.get('memory', 'N/A')),   body_style)],
    ]
    t2 = Table(metrics_rows, colWidths=[4*cm, 13*cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), LIGHT_GRAY),
        ("GRID",          (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    content.append(t2)

    # ══════════════════════════════════════════════════════════
    # PAGE 2 — LOGS + EVENTS
    # ══════════════════════════════════════════════════════════
    content.append(PageBreak())

    # ── SECTION 3 : LOGS LOKI ─────────────────────────────────
    sec3 = Table(
    [[Paragraph("3. Logs Loki (dernières lignes)", section_style)]],
    colWidths=[17*cm]
)
    sec3.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,-1), LIGHT_BLUE),
    ("TOPPADDING",    (0,0), (-1,-1), 6),
    ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ("LEFTPADDING",   (0,0), (-1,-1), 10),
]))
    content.append(sec3)
    content.append(Spacer(1, 0.2*cm))

    logs_para_style = ParagraphStyle(
    "Logs", parent=styles["Normal"],
    fontSize=7,              # ← plus petit pour tout afficher
    fontName="Courier",
    textColor=HexColor("#D4D4D4"),
    leading=10,
    leftIndent=8,
    rightIndent=8,
    wordWrap='CJK',
    splitLongWords=True,
)

    safe_logs = logs_text\
    .replace("&", "&amp;")\
    .replace("<", "&lt;")\
    .replace(">", "&gt;")

    t_logs = Table(
    [[Paragraph(safe_logs.replace("\n", "<br/>"), logs_para_style)]],
    colWidths=[17*cm]
)
    t_logs.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,-1), HexColor("#1E1E1E")),
    ("TOPPADDING",    (0,0), (-1,-1), 10),
    ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ("RIGHTPADDING",  (0,0), (-1,-1), 10),
]))
    content.append(t_logs)
    content.append(Spacer(1, 0.5*cm))
    

    # ── SECTION 4 : EVENTS KUBERNETES ─────────────────────────
    sec4 = Table([[Paragraph("5. Events Kubernetes", section_style)]], colWidths=[17*cm])
    sec4.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), LIGHT_BLUE),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
    ]))
    content.append(sec4)
    content.append(Spacer(1, 0.2*cm))

    events_text = format_events_text(events) if events else "Aucun event disponible."

    events_style = ParagraphStyle("Events", parent=styles["Normal"],
        fontSize=8, fontName="Courier",
        textColor=HexColor("#000000"),
        leading=12, leftIndent=8)

    t_events = Table(
        [[Paragraph(events_text.replace("\n", "<br/>"), events_style)]],
        colWidths=[17*cm]
    )
    t_events.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), HexColor("#F8F9FA")),
        ("GRID",          (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    content.append(t_events)
    content.append(Spacer(1, 0.4*cm))
    # ══════════════════════════════════════════════════════════
    # PAGE 3 — ANALYSE RCA + FOOTER
    # ══════════════════════════════════════════════════════════
    content.append(PageBreak())

    # ── SECTION 5 : ANALYSE RCA ───────────────────────────────
    sec5 = Table(
        [[Paragraph("5. Analyse Root Cause Analysis (GPT-4)", section_style)]],
        colWidths=[17*cm]
    )
    sec5.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LIGHT_BLUE),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    content.append(sec5)
    content.append(Spacer(1, 0.2*cm))

    if "error" not in analysis and "raw_response" not in analysis:

        # Anomalie
        t_anomalie = Table([[
            Paragraph("Anomalie", ParagraphStyle("AL", parent=styles["Normal"],
                fontSize=10, textColor=BLUE, fontName="Helvetica-Bold")),
            Paragraph(analysis.get('anomalie', 'N/A'), body_style)
        ]], colWidths=[4*cm, 13*cm])
        t_anomalie.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (0,-1), HexColor("#D6E4F0")),
            ("GRID",          (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ]))
        content.append(t_anomalie)
        content.append(Spacer(1, 0.2*cm))

        # Cause Root
        t_cause = Table([[
            Paragraph("Cause Root", ParagraphStyle("CL", parent=styles["Normal"],
                fontSize=10, textColor=ORANGE, fontName="Helvetica-Bold")),
            Paragraph(analysis.get('cause_probable', 'N/A'), body_style)
        ]], colWidths=[4*cm, 13*cm])
        t_cause.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (0,-1), HexColor("#FFF3E0")),
            ("GRID",          (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ]))
        content.append(t_cause)
        content.append(Spacer(1, 0.3*cm))

        # Actions Correctives
        actions = analysis.get('actions_correctives', [])
        if actions:
            sec_act = Table(
                [[Paragraph("Actions Correctives", section_style)]],
                colWidths=[17*cm]
            )
            sec_act.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), HexColor("#1E6B3C")),
                ("TOPPADDING",    (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ]))
            content.append(sec_act)
            content.append(Spacer(1, 0.1*cm))

            act_rows = [[
                Paragraph(f"{i}.", ParagraphStyle("N", parent=styles["Normal"],
                    fontSize=10, textColor=GREEN,
                    fontName="Helvetica-Bold",
                    alignment=TA_CENTER)),
                Paragraph(a, body_style)
            ] for i, a in enumerate(actions, 1)]

            t_act = Table(act_rows, colWidths=[1*cm, 16*cm])
            t_act.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), HexColor("#E8F5E9")),
                ("GRID",          (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")),
                ("TOPPADDING",    (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ("LEFTPADDING",   (0,0), (-1,-1), 8),
                ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ]))
            content.append(t_act)
            content.append(Spacer(1, 0.3*cm))

        # Prévention
        prevention = analysis.get('prevention', '')
        if prevention:
            t_prev = Table([[
                Paragraph("Prévention", ParagraphStyle("PL", parent=styles["Normal"],
                    fontSize=10, textColor=GREEN, fontName="Helvetica-Bold")),
                Paragraph(prevention, body_style)
            ]], colWidths=[3.5*cm, 13.5*cm])
            t_prev.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (0,-1), HexColor("#E8F5E9")),
                ("GRID",          (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")),
                ("TOPPADDING",    (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ("LEFTPADDING",   (0,0), (-1,-1), 8),
                ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ]))
            content.append(t_prev)
            content.append(Spacer(1, 0.3*cm))

    else:
        # Cas erreur GPT-4
        err_msg = analysis.get('error', analysis.get('raw_response', 'Analyse non disponible'))
        t_err = Table([[
            Paragraph("Erreur", ParagraphStyle("EL", parent=styles["Normal"],
                fontSize=10, textColor=RED, fontName="Helvetica-Bold")),
            Paragraph(str(err_msg)[:300], body_style)
        ]], colWidths=[4*cm, 13*cm])
        t_err.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (0,-1), HexColor("#FFE0E0")),
            ("GRID",          (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        content.append(t_err)
        content.append(Spacer(1, 0.3*cm))

    # ── FOOTER ────────────────────────────────────────────────
    content.append(Spacer(1, 0.5*cm))
    footer = Table([[Paragraph(
        f"Agent IA Kubernetes  |  Rapport généré automatiquement  |  {timestamp}",
        ParagraphStyle("F", parent=styles["Normal"],
            fontSize=8, textColor=WHITE,
            alignment=TA_CENTER, fontName="Helvetica")
    )]], colWidths=[17*cm])
    footer.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), BLUE),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    content.append(footer)

    doc.build(content)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    print(f"[PDF] ✅ PDF généré : {filename} ({len(pdf_bytes)} bytes)")
    return pdf_bytes, filename