import requests
import time
from config import PROMETHEUS_URL, APP_POD_PREFIX

def find_pod_from_prometheus(job):
    try:
        prefix = APP_POD_PREFIX.get(job, "")
        if not prefix:
            return None
        result = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": f'kube_pod_info{{namespace="apps", pod=~"{prefix}.*"}}'}, timeout=5).json()
        pods = result.get("data", {}).get("result", [])
        if pods:
            pod_name = pods[0].get("metric", {}).get("pod")
            print(f"[PROMETHEUS] Pod trouvé : {pod_name}")
            return pod_name
        return None
    except Exception as e:
        print(f"[PROMETHEUS] Erreur find_pod: {str(e)}")
        return None

def get_prometheus_metrics(job, pod=None, minutes=10):
    try:
        end   = int(time.time())
        start = end - (minutes * 60)
        results = {}

        results["up_status"] = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": f'up{{job="{job}"}}'}, timeout=5).json()

        results["history"] = requests.get(f"{PROMETHEUS_URL}/api/v1/query_range",
            params={"query": f'up{{job="{job}"}}', "start": start,
                    "end": end, "step": "30s"}, timeout=5).json()

        if not pod:
            pod = find_pod_from_prometheus(job)
            if pod:
                print(f"[PROMETHEUS] Pod auto-détecté : {pod}")

        if pod:
            results["restarts"] = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": f'kube_pod_container_status_restarts_total{{pod="{pod}"}}'}, timeout=5).json()
            results["cpu"] = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": f'rate(container_cpu_usage_seconds_total{{pod="{pod}"}}[5m])'}, timeout=5).json()
            results["memory"] = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": f'container_memory_usage_bytes{{pod="{pod}"}}'}, timeout=5).json()
            results["pod_used"] = pod

        return results
    except Exception as e:
        return {"error": str(e)}