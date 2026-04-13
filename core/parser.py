from config import APP_NAMESPACES

def parse_alert(alert_data):
    alerts = alert_data.get("alerts", [])
    if not alerts:
        return None

    alert  = alerts[0]
    labels = alert.get("labels", {})

    service = (
        labels.get("pod") or
        labels.get("container") or
        labels.get("job") or
        "unknown"
    )

    affected_pods = list(set([
        a.get("labels", {}).get("pod", "")
        for a in alerts
        if a.get("labels", {}).get("pod")
    ]))

    job       = labels.get("job", "unknown")
    namespace = labels.get("namespace", "default")

    if namespace == "default" and job in APP_NAMESPACES:
        namespace = APP_NAMESPACES[job]
        print(f"[PARSE] Namespace corrigé : default → apps pour job={job}")

    return {
        "name":           labels.get("alertname", "unknown"),
        "service":        service,
        "job":            job,
        "namespace":      namespace,
        "severity":       labels.get("severity", "unknown"),
        "status":         alert.get("status", "unknown"),
        "description":    alert.get("annotations", {}).get("description", ""),
        "summary":        alert.get("annotations", {}).get("summary", ""),
        "started_at":     alert.get("startsAt", ""),
        "affected_pods":  affected_pods,
        "firing_count":   sum(1 for a in alerts if a.get("status") == "firing"),
        "resolved_count": sum(1 for a in alerts if a.get("status") == "resolved"),
        "total_alerts":   len(alerts),
    }