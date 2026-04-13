import requests
import time
from config import PROMETHEUS_URL

APPS_METRICS = {
    "keycloak": {
        "metrics": {
            "cpu":      'sum(rate(container_cpu_usage_seconds_total{pod=~"keycloak.*", namespace="apps", container="keycloak"}[5m]))',
            "memory":   'sum(container_memory_usage_bytes{pod=~"keycloak.*", namespace="apps", container="keycloak"})',
            "restarts": 'sum(kube_pod_container_status_restarts_total{pod=~"keycloak.*", namespace="apps"})',
            "up":       'sum(up{job="keycloak-metrics"})',
        }
    },
    "postgresql": {
        "metrics": {
            "cpu":    'sum(rate(container_cpu_usage_seconds_total{pod=~"postgresql.*", namespace="apps"}[5m]))',
            "memory": 'sum(container_memory_usage_bytes{pod=~"postgresql.*", namespace="apps"})',
            "up":     'sum(up{job="postgresql-primary-metrics"})',
        }
    },
    "mongodb": {
        "metrics": {
            "cpu":    'sum(rate(container_cpu_usage_seconds_total{pod=~"mongodb.*", namespace="apps"}[5m]))',
            "memory": 'sum(container_memory_usage_bytes{pod=~"mongodb.*", namespace="apps"})',
            "up":     'sum(up{job="mongodb-metrics"})',
        }
    },
    "redis": {
        "metrics": {
            "cpu":         'sum(rate(container_cpu_usage_seconds_total{pod=~"redis.*", namespace="apps"}[5m]))',
            "memory":      'sum(container_memory_usage_bytes{pod=~"redis.*", namespace="apps"})',
            "connections": 'sum(redis_connected_clients)',
            "up":          'sum(up{job="redis-metrics"})',
        }
    },
    "redpanda": {
        "metrics": {
            "cpu":    'sum(rate(container_cpu_usage_seconds_total{pod=~"redpanda.*", namespace="apps"}[5m]))',
            "memory": 'sum(container_memory_usage_bytes{pod=~"redpanda.*", namespace="apps"})',
            "up":     'sum(up{job="redpanda"})',
        }
    },
}

def query_prometheus(promql):
    """Exécute une query Prometheus et retourne la valeur"""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": promql},
            timeout=5
        )
        result = response.json()
        data   = result.get("data", {}).get("result", [])

        if not data:
            return 0.0

        # Prendre la première valeur (sum() garantit un seul résultat)
        value = data[0].get("value", [None, "0"])[1]
        return float(value)

    except Exception as e:
        print(f"[COLLECTOR] Erreur query: {str(e)}")
        return 0.0

def collect_all_metrics():
    """Collecte toutes les métriques de toutes les apps"""
    timestamp = time.time()
    all_data  = {"timestamp": timestamp}

    print(f"\n[COLLECTOR] Collecte — {__import__('datetime').datetime.now().strftime('%H:%M:%S')}")

    for app_name, app_config in APPS_METRICS.items():
        app_data = {}
        for metric_name, promql in app_config["metrics"].items():
            value = query_prometheus(promql)
            app_data[metric_name] = value
            print(f"  [{app_name}] {metric_name}: {value:.4f}")

        all_data[app_name] = app_data

    return all_data