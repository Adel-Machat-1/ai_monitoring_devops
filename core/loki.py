import requests
import time
from config import LOKI_URL

APP_MAPPING = {
    "keycloak": "keycloak", "mongodb": "mongodb", "mongo": "mongodb",
    "postgresql": "postgresql", "postgres": "postgresql",
    "redis": "redis", "redpanda": "redpanda", "pgadmin": "pgadmin",
}

def get_loki_logs(service, namespace="apps", minutes=10):
    try:
        end      = int(time.time() * 1e9)
        start    = int((time.time() - minutes * 60) * 1e9)
        app_name = service.split("-")[0] if service else ""
        app_label = APP_MAPPING.get(app_name, app_name)

        for query in [
            f'{{pod="{service}", namespace="{namespace}"}}',
            f'{{app="{app_label}", namespace="{namespace}"}}',
            f'{{app="{service}", namespace="{namespace}"}}',
            f'{{namespace="{namespace}", app=~"{app_name}.*"}}',
        ]:
            result  = requests.get(f"{LOKI_URL}/loki/api/v1/query_range",
                params={"query": query, "start": start, "end": end, "limit": 50}, timeout=5).json()
            streams = result.get("data", {}).get("result", [])
            if streams:
                total = sum(len(s.get("values", [])) for s in streams)
                print(f"[LOKI] ✅ {len(streams)} stream(s) | {total} lignes")
                return result

        print(f"[LOKI] ❌ Aucun log pour service={service}")
        return {"data": {"result": []}}
    except Exception as e:
        print(f"[LOKI] ERROR: {str(e)}")
        return {"error": str(e)}