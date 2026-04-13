def extract_logs_text(logs, max_lines=20):
    try:
        streams = logs.get("data", {}).get("result", [])
        if not streams:
            return "Aucun log disponible."

        lines = []
        for stream in streams:
            # ── Ajouter le label du stream ────────────────────
            stream_labels = stream.get("stream", {})
            pod_name      = stream_labels.get("pod", "unknown")
            container     = stream_labels.get("container", "unknown")
            lines.append(f"=== Pod: {pod_name} | Container: {container} ===")

            for ts, line in stream.get("values", []):
                lines.append(line)

            lines.append("")  # ligne vide entre streams

        # Prendre les dernières lignes
        all_lines = lines[-max_lines:]
        return "\n".join(all_lines)
    except:
        return "Erreur lors de l'extraction des logs."

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