import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ── Test 1 : Imports ──────────────────────────────────────────
def test_import_parser():
    from core.parser import parse_alert
    assert parse_alert is not None

def test_import_prometheus():
    from core.prometheus import get_prometheus_metrics
    assert get_prometheus_metrics is not None

def test_import_loki():
    from core.loki import get_loki_logs
    assert get_loki_logs is not None

def test_import_extractors():
    from utils.extractors import extract_logs_text, extract_metrics_summary
    assert extract_logs_text is not None
    assert extract_metrics_summary is not None

# ── Test 2 : Parse Alert ──────────────────────────────────────
def test_parse_alert_keycloak():
    from core.parser import parse_alert
    fake_alert = {
        "alerts": [{
            "labels": {
                "alertname": "KeycloakDown",
                "severity": "critical",
                "job": "keycloak-metrics",
                "namespace": "apps"
            },
            "status": "firing",
            "startsAt": "2026-04-10T10:00:00Z",
            "annotations": {
                "summary": "Keycloak is DOWN",
                "description": "Keycloak exporter not responding"
            }
        }]
    }
    result = parse_alert(fake_alert)
    assert result is not None
    assert result["name"] == "KeycloakDown"
    assert result["severity"] == "critical"
    assert result["namespace"] == "apps"

def test_parse_alert_postgresql():
    from core.parser import parse_alert
    fake_alert = {
        "alerts": [{
            "labels": {
                "alertname": "PostgresDown",
                "severity": "critical",
                "job": "postgresql-primary-metrics",
            },
            "status": "firing",
            "startsAt": "2026-04-10T10:00:00Z",
            "annotations": {"summary": "PostgreSQL is DOWN", "description": ""}
        }]
    }
    result = parse_alert(fake_alert)
    assert result["name"] == "PostgresDown"
    assert result["namespace"] == "apps"  # auto-correction default → apps

def test_parse_alert_empty():
    from core.parser import parse_alert
    result = parse_alert({"alerts": []})
    assert result is None

# ── Test 3 : Filtres Config ───────────────────────────────────
def test_ignored_alerts():
    from config import IGNORED_ALERTS
    assert "Watchdog" in IGNORED_ALERTS
    assert "KubeProxyDown" in IGNORED_ALERTS
    assert "KubeSchedulerDown" in IGNORED_ALERTS
    assert "AlertmanagerFailedToSendAlerts" in IGNORED_ALERTS

def test_allowed_alerts():
    from config import ALLOWED_ALERTS
    assert "KeycloakDown" in ALLOWED_ALERTS
    assert "PostgresDown" in ALLOWED_ALERTS
    assert "MongoDBDown" in ALLOWED_ALERTS
    assert "AppCrashLooping" in ALLOWED_ALERTS
    assert "AnomalyDetected_Postgresql" in ALLOWED_ALERTS

def test_skip_severities():
    from config import SKIP_SEVERITIES
    assert "info" in SKIP_SEVERITIES
    assert "none" in SKIP_SEVERITIES

# ── Test 4 : Extractors ───────────────────────────────────────
def test_extract_logs_empty():
    from utils.extractors import extract_logs_text
    result = extract_logs_text({"data": {"result": []}})
    assert result == "Aucun log disponible."

def test_extract_logs_with_data():
    from utils.extractors import extract_logs_text
    fake_logs = {
        "data": {
            "result": [{
                "stream": {"pod": "keycloak-0"},
                "values": [
                    ["1234567890", "ERROR: Connection refused"],
                    ["1234567891", "WARN: Retry attempt 1"],
                ]
            }]
        }
    }
    result = extract_logs_text(fake_logs)
    assert "Connection refused" in result
    assert "Retry attempt" in result

def test_extract_metrics_summary():
    from utils.extractors import extract_metrics_summary
    fake_metrics = {
        "up_status": {"data": {"result": [{"value": [0, "1"]}]}},
        "restarts":  {"data": {"result": [{"value": [0, "5"]}]}},
        "cpu":       {"data": {"result": [{"value": [0, "0.0185"]}]}},
        "memory":    {"data": {"result": [{"value": [0, "939991040"]}]}},
        "pod_used":  "keycloak-0"
    }
    result = extract_metrics_summary(fake_metrics)
    assert result["up"] == "1"
    assert result["restarts"] == "5"
    assert "cores" in result["cpu"]
    assert "MB" in result["memory"]

def test_extract_metrics_empty():
    from utils.extractors import extract_metrics_summary
    result = extract_metrics_summary({})
    assert result["up"] == "0 (down)"
    assert result["restarts"] == "N/A"

# ── Test 5 : Anomaly Detection Config ────────────────────────
def test_anomaly_detector_params():
    from core.anomaly.detector import MIN_ANOMALY_SCORE, CONTAMINATION
    assert MIN_ANOMALY_SCORE == 0.65
    assert CONTAMINATION == 0.03

def test_anomaly_collector_apps():
    from core.anomaly.collector import APPS_METRICS
    assert "keycloak" in APPS_METRICS
    assert "postgresql" in APPS_METRICS
    assert "mongodb" in APPS_METRICS
    assert "redis" in APPS_METRICS
    assert "redpanda" in APPS_METRICS

def test_anomaly_scheduler_mapping():
    from core.anomaly.scheduler import SERVICE_MAPPING
    assert "keycloak" in SERVICE_MAPPING
    assert SERVICE_MAPPING["redis"] == "redis-master-0"
    assert SERVICE_MAPPING["postgresql"] == "postgresql-primary-0"