import requests
import time
from config import PROMETHEUS_URL

import logging
logger = logging.getLogger(__name__)


APPS_METRICS = {
    "keycloak": {
        "metrics": {
            "cpu":    'system_cpu_usage{job="keycloak-metrics"}',
            "memory": 'sum(jvm_memory_used_bytes{job="keycloak-metrics"})',
            "up":     'sum(up{job="keycloak-metrics"})',
        }
    },
    "postgresql": {
        "metrics": {
            "cpu":    'rate(process_cpu_seconds_total{job="postgresql-primary-metrics"}[5m])',
            "memory": 'process_resident_memory_bytes{job="postgresql-primary-metrics"}',
            "up":     'sum(up{job="postgresql-primary-metrics"})',
        }
    },
    "mongodb": {
        "metrics": {
            "cpu":         'rate(process_cpu_seconds_total{job="mongodb-metrics"}[5m])',
            "memory":      'process_resident_memory_bytes{job="mongodb-metrics"}',
            "connections": 'mongodb_connections{job="mongodb-metrics",state="current"}',
            "up":          'sum(up{job="mongodb-metrics"})',
        }
    },
    "redis": {
        "metrics": {
            "cpu":         'rate(process_cpu_seconds_total{job="redis-metrics"}[5m])',
            "memory":      'process_resident_memory_bytes{job="redis-metrics"}',
            "connections": 'redis_connected_clients{job="redis-metrics"}',
            "up":          'sum(up{job="redis-metrics"})',
        }
    },
    "redpanda": {
        "metrics": {
            "cpu":    'sum(vectorized_reactor_utilization{job="redpanda"})',
            "memory": 'sum(vectorized_memory_allocated_memory{job="redpanda"})',
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

        value = data[0].get("value", [None, "0"])[1]
        return float(value)

    except Exception as e:
        logger.info(f"[COLLECTOR] Erreur query: {str(e)}")
        return 0.0

def collect_all_metrics():
    """Collecte toutes les métriques de toutes les apps"""
    timestamp = time.time()
    all_data  = {"timestamp": timestamp}

    logger.info(f"\n[COLLECTOR] Collecte — {__import__('datetime').datetime.now().strftime('%H:%M:%S')}")

    for app_name, app_config in APPS_METRICS.items():
        app_data = {}
        for metric_name, promql in app_config["metrics"].items():
            value = query_prometheus(promql)
            app_data[metric_name] = value
            logger.info(f"  [{app_name}] {metric_name}: {value:.4f}")

        all_data[app_name] = app_data

    return all_data