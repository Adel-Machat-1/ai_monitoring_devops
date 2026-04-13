
import os

# ── URLs ──────────────────────────────────────
PROMETHEUS_URL = "http://localhost:9090"
LOKI_URL       = "http://localhost:3100"

# ── GitHub Models (GPT-4) ─────────────────────
# Obtenir sur : https://github.com/settings/tokens
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "ghp_VOTRE_TOKEN_ICI")

# ── Mailtrap SMTP ─────────────────────────────
# Obtenir sur : https://mailtrap.io

MAILTRAP_HOST     = "sandbox.smtp.mailtrap.io"
MAILTRAP_PORT     = 2525
MAILTRAP_USERNAME = os.getenv("MAILTRAP_USERNAME", "VOTRE_USERNAME")
MAILTRAP_PASSWORD = os.getenv("MAILTRAP_PASSWORD", "VOTRE_PASSWORD")
EMAIL_FROM        = "agent-ia@kubernetes-monitoring.com"
EMAIL_TO          = "devops@monitoring.com"

# ── MinIO ─────────────────────────────────────
MINIO_ENDPOINT   = "localhost:9000"
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "VOTRE_SECRET_KEY")
MINIO_BUCKET     = "incident-reports"
MINIO_SECURE     = False



# ── Filtres ───────────────────────────────────
IGNORED_ALERTS = [

      "Watchdog",
    "InfoInhibitor",

    # Composants système Kubernetes
    "KubeProxyDown",
    "KubeSchedulerDown",
    "KubeControllerManagerDown",
    "KubeStatefulSetReplicasMismatch",
    "KubePdbNotEnoughHealthyPods",
    "KubeNodeNotReady",
    "KubeNodeUnreachable",

    # Alertmanager lui-même
    "AlertmanagerFailedToSendAlerts",
    "AlertmanagerClusterFailedToSendAlerts",

    # Monitoring
    "NodeClockNotSynchronising",
    "CPUThrottlingHigh",
    "TargetDown",
]

SKIP_SEVERITIES = ["info", "none"]
DEDUP_WINDOW    = 300

# ── Alertes autorisées ────────────────────────
ALLOWED_ALERTS = [

  # Rule 1 — Exporter unreachable
    "PostgresDown",
    "MongoDBDown",
    "RedisDown",
    "RedpandaDown",
    "KeycloakDown",

    # Rule 2 — Pod not healthy
    "PostgresPodNotRunning",
    "MongoPodNotRunning",
    "RedisPodNotRunning",
    "RedpandaPodNotRunning",
    "KeycloakPodNotRunning",

    # Rule 3 — Crash looping
    "AppCrashLooping",

    # Rule 4 — Deployment unavailable
    "AppDeploymentUnavailable",

    # Rule 5 — Pod not ready
    "AppPodNotReady",

    # Anomaly Detection ML
    "AnomalyDetected_Postgresql",
    "AnomalyDetected_Mongodb",
    "AnomalyDetected_Redis",
    "AnomalyDetected_Keycloak",
    "AnomalyDetected_Redpanda",
]

# ── Apps   ( il faut modifier les nom selo votre kubernetes cluster )──────────────────────────────────────
APP_NAMESPACES = {
    "postgresql-primary-metrics": "apps",
    "mongodb-metrics":            "apps",
    "keycloak-metrics":           "apps",
    "redis-metrics":              "apps",
    "redpanda":                   "apps",
    "kube-state-metrics":         "apps",
}

APP_POD_PREFIX = {
    "postgresql-primary-metrics": "postgresql",
    "mongodb-metrics":            "mongodb",
    "keycloak-metrics":           "keycloak",
    "redis-metrics":              "redis-master",
    "redpanda":                   "redpanda",
}

# ── GPT-4 Models ──────────────────────────────
MODELS = ["gpt-4o-mini", "gpt-4o"]