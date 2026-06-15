import logging
logger = logging.getLogger(__name__)

def extract_logs_text(logs, max_lines=20):

    try:
        # ── Cas 1 : Structure Loki complète ───────────────────
        if isinstance(logs, dict):
            streams = logs.get("data", {}).get("result", [])

        # ── Cas 2 : Liste de streams directement ─────────────
        elif isinstance(logs, list):
            streams = logs
        else:
            return "Aucun log disponible."

        if not streams:
            return "Aucun log disponible."

        lines = []
        for stream in streams:
            labels = (
                stream.get("stream") or
                stream.get("labels") or
                stream.get("metric") or
                {}
            )

            pod_name = (
                labels.get("pod") or
                labels.get("pod_name") or
                labels.get("app") or
                labels.get("container") or
                labels.get("job") or
                "unknown"
            )

            container = (
                labels.get("container") or
                labels.get("container_name") or
                labels.get("app") or
                "unknown"
            )

            lines.append(f"=== Pod: {pod_name} | Container: {container} ===")

            values = (
                stream.get("values") or
                stream.get("entries") or
                stream.get("lines") or
                []
            )

            for entry in values:
                if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                    lines.append(str(entry[1]))
                elif isinstance(entry, dict):
                    line = entry.get("line") or entry.get("log") or str(entry)
                    lines.append(line)
                elif isinstance(entry, str):
                    lines.append(entry)

            lines.append("")

        all_lines = lines[-max_lines:]
        result    = "\n".join(all_lines)
        return result if result.strip() else "Aucun log disponible."

    except Exception as e:
        return f"Erreur logs : {str(e)}"

def extract_metrics_summary(metrics):
    try:
        summary = {}

        # ── Up/Down ───────────────────────────────────────────
        try:
            up = metrics.get("up_status", {}).get("data", {}).get("result", [])
            summary["up"] = up[0].get("value", [None, "unknown"])[1] if up else "0 (down)"
        except:
            summary["up"] = "N/A"

        # ── Restarts ──────────────────────────────────────────
        try:
            r = metrics.get("restarts", {}).get("data", {}).get("result", [])
            summary["restarts"] = r[0].get("value", [None, "0"])[1] if r else "0"
        except:
            summary["restarts"] = "0"

        # ── CPU ───────────────────────────────────────────────
        try:
            c = metrics.get("cpu", {}).get("data", {}).get("result", [])
            if c:
                cpu_val = float(c[0].get("value", [None, "0"])[1])
                summary["cpu"] = f"{cpu_val:.6f} cores"
            else:
                summary["cpu"] = "N/A"
        except:
            summary["cpu"] = "N/A"

        # ── Memory ────────────────────────────────────────────
        try:
            m = metrics.get("memory", {}).get("data", {}).get("result", [])
            if m:
                mem_val = float(m[0].get("value", [None, "0"])[1])
                summary["memory"] = f"{mem_val / 1024 / 1024:.1f} MB"
            else:
                summary["memory"] = "N/A"
        except:
            summary["memory"] = "N/A"

        # ── Pod ───────────────────────────────────────────────
        summary["pod_used"] = metrics.get("pod_used", "N/A")

        return summary

    except Exception as e:
        logger.error(f"[EXTRACTORS] Erreur extract_metrics_summary: {e}")
        return {"error": str(e), "up": "N/A", "restarts": "N/A", "cpu": "N/A", "memory": "N/A", "pod_used": "N/A"}