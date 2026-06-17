import requests
import time
import subprocess
import json
from config import PROMETHEUS_URL, APP_POD_PREFIX

import logging
logger = logging.getLogger(__name__)

# Mapping job → pods connus dans le cluster
JOB_PODS = {
    "mongodb-metrics"           : ["mongodb-0", "mongodb-1", "mongodb-2"],
    "redis-metrics"             : ["redis-master-0", "redis-replicas-0", "redis-replicas-1", "redis-replicas-2"],
    "postgresql-primary-metrics": ["postgresql-0"],
    "keycloak-metrics"          : ["keycloak-0", "keycloak-1"],
    "redpanda"                  : ["redpanda-744b7f9cdd-rx2d8"],
}

# Mapping pod prefix → job
POD_JOB_MAP = {
    "mongodb"    : "mongodb-metrics",
    "redis"      : "redis-metrics",
    "postgresql" : "postgresql-primary-metrics",
    "redpanda"   : "redpanda",
    "keycloak"   : "keycloak-metrics",
}

NAMESPACE = "int-ksm-backdata"


def find_pod_from_prometheus(job):
    pods = JOB_PODS.get(job, [])
    if pods:
        logger.info(f"[PROMETHEUS] Pod trouvé : {pods[0]}")
        return pods[0]
    return None


def get_pods_for_prefix(prefix, namespace="int-ksm-backdata", exclude=None):
    exclude = exclude or []
    all_pods = []
    for job, pods in JOB_PODS.items():
        for pod in pods:
            if pod.startswith(prefix) and not any(ex in pod for ex in exclude):
                all_pods.append(pod)
    return sorted(all_pods)


def _q(query):
    try:
        r = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query}, timeout=5).json()
        res = r.get("data", {}).get("result", [])
        return float(res[0]["value"][1]) if res else 0.0
    except Exception:
        return 0.0


def _get_pod_restarts(pod, namespace=NAMESPACE):
    """Récupère les restarts d'un pod via kubectl"""
    try:
        cmd = ["kubectl", "get", "pod", pod, "-n", namespace,
               "-o", "jsonpath={.status.containerStatuses[0].restartCount}"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip())
        return 0
    except Exception:
        return 0


def _get_pod_cpu_mem_kubectl(pod, namespace=NAMESPACE):
    """
    Récupère CPU et mémoire d'un pod via kubectl top
    Retourne (cpu_cores, mem_mb)
    """
    try:
        cmd = ["kubectl", "top", "pod", pod, "-n", namespace, "--no-headers"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split()
            # Format: pod-name  CPU(cores)  MEMORY(bytes)
            # ex: mongodb-0  5m  128Mi
            cpu_str = parts[1]  # ex: "5m" ou "1200m"
            mem_str = parts[2]  # ex: "128Mi" ou "2Gi"

            # Parse CPU
            if cpu_str.endswith('m'):
                cpu = round(float(cpu_str[:-1]) / 1000, 6)  # millicores → cores
            else:
                cpu = round(float(cpu_str), 6)

            # Parse Memory
            if mem_str.endswith('Mi'):
                mem = round(float(mem_str[:-2]), 1)
            elif mem_str.endswith('Gi'):
                mem = round(float(mem_str[:-2]) * 1024, 1)
            elif mem_str.endswith('Ki'):
                mem = round(float(mem_str[:-2]) / 1024, 1)
            else:
                mem = round(float(mem_str) / 1024 / 1024, 1)

            return cpu, mem
    except Exception as e:
        logger.debug(f"[KUBECTL TOP] Erreur pour {pod}: {e}")

    return None, None


def get_pod_metrics(pod):
    """
    Récupère les métriques d'un pod individuel.
    Essaie kubectl top d'abord, fallback sur Prometheus.
    """
    job = next((v for k, v in POD_JOB_MAP.items() if pod.startswith(k)), None)

    # 1. Essai kubectl top (métriques par pod individuelles)
    cpu, mem = _get_pod_cpu_mem_kubectl(pod)

    # 2. Fallback Prometheus si kubectl top échoue
    if cpu is None:
        if job == "redpanda":
            cpu = round(_q('sum(vectorized_reactor_utilization)'), 6)
            mem = round(_q('sum(vectorized_memory_allocated_memory)') / 1024 / 1024, 1)
        elif job == "keycloak-metrics":
            cpu = round(_q(f'system_cpu_usage{{job="{job}"}}'), 6)
            mem = round(_q(f'sum(jvm_memory_used_bytes{{job="{job}"}})') / 1024 / 1024, 1)
        elif job:
            cpu = round(_q(f'rate(process_cpu_seconds_total{{job="{job}"}}[5m])'), 6)
            mem = round(_q(f'process_resident_memory_bytes{{job="{job}"}}') / 1024 / 1024, 1)
        else:
            cpu = 0.0
            mem = 0.0

    # 3. Restarts via kubectl
    restarts = _get_pod_restarts(pod)

    return {
        "cpu"       : cpu or 0.0,
        "memory_mb" : mem or 0.0,
        "restarts"  : restarts,
    }


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
                logger.info(f"[PROMETHEUS] Pod auto-détecté : {pod}")

        job_detected = next((v for k, v in POD_JOB_MAP.items() if pod and pod.startswith(k)), job)

        if pod:
            cpu = _q(f'rate(process_cpu_seconds_total{{job="{job_detected}"}}[5m])')
            mem = _q(f'process_resident_memory_bytes{{job="{job_detected}"}}')

            results["cpu"]      = {"data": {"result": [{"value": [0, str(cpu)]}]}}
            results["memory"]   = {"data": {"result": [{"value": [0, str(mem)]}]}}
            results["restarts"] = {"data": {"result": []}}
            results["pod_used"] = pod

        return results
    except Exception as e:
        return {"error": str(e)}