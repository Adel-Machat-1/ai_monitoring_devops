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
            # ── Chercher les labels dans plusieurs clés ───────
            labels = (
                stream.get("stream") or
                stream.get("labels") or
                stream.get("metric") or
                {}
            )

            # ── Chercher le nom du pod dans plusieurs clés ────
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

            # ── Chercher les valeurs dans plusieurs clés ──────
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
                    # Format {"ts": "...", "line": "..."}
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

        up = metrics.get("up_status", {}).get("data", {}).get("result", [])
        summary["up"] = up[0].get("value", [None, "unknown"])[1] if up else "0 (down)"

        r = metrics.get("restarts", {}).get("data", {}).get("result", [])
        summary["restarts"] = r[0].get("value", [None, "0"])[1] if r else "N/A"

        c = metrics.get("cpu", {}).get("data", {}).get("result", [])
        summary["cpu"] = f"{float(c[0].get('value',[None,'0'])[1]):.4f} cores" if c else "N/A"

        m = metrics.get("memory", {}).get("data", {}).get("result", [])
        summary["memory"] = f"{int(m[0].get('value',[None,'0'])[1]) / 1024 / 1024:.1f} MB" if m else "N/A"

        summary["pod_used"] = metrics.get("pod_used", "N/A")
        return summary

    except Exception as e:
        return {"error": str(e)}