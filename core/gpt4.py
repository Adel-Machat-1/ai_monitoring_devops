import json
import time
from openai import OpenAI
from config import GITHUB_TOKEN, MODELS
from utils.extractors import extract_metrics_summary, extract_logs_text
from core.kubernetes_events import format_events_text

gpt_client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=GITHUB_TOKEN,
)
current_model_index = 0

def call_gpt4_with_retry(parsed, metrics, logs, events=[], max_retries=3):
    global current_model_index

    metrics_summary = extract_metrics_summary(metrics)
    logs_text       = extract_logs_text(logs, max_lines=20)
    events_text     = format_events_text(events)          # ← events maintenant disponible

    prompt = f"""
Tu es un expert SRE spécialisé en Kubernetes.
Analyse cette alerte et fournis un RCA clair.

## ALERTE
- Alert     : {parsed['name']}
- Service   : {parsed['service']}
- Namespace : {parsed['namespace']}
- Severity  : {parsed['severity']}
- Status    : {parsed['status']}
- Summary   : {parsed['summary']}
- Pods      : {parsed['affected_pods']}
- Firing    : {parsed['firing_count']}

## MÉTRIQUES
- Pod       : {metrics_summary.get('pod_used', 'N/A')}
- Up/Down   : {metrics_summary.get('up', 'N/A')}
- Restarts  : {metrics_summary.get('restarts', 'N/A')}
- CPU       : {metrics_summary.get('cpu', 'N/A')}
- Memory    : {metrics_summary.get('memory', 'N/A')}

## LOGS LOKI
{logs_text}

## EVENTS KUBERNETES
{events_text}

Réponds UNIQUEMENT en JSON valide sans markdown :
{{
    "anomalie": "...",
    "cause_probable": "...",
    "services_impactes": ["..."],
    "severite_reelle": "critical/high/medium/low",
    "actions_correctives": ["Action 1", "Action 2", "Action 3"],
    "prevention": "..."
}}
"""

    for attempt in range(1, max_retries + 1):
        model = MODELS[current_model_index]
        try:
            print(f"[GPT-4] Tentative {attempt}/{max_retries} — {model}")
            response = gpt_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Expert SRE Kubernetes. Réponds toujours en JSON valide sans markdown."},
                    {"role": "user",   "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000,
            )
            raw = response.choices[0].message.content
            print(f"[GPT-4] ✅ Réponse reçue ({len(raw)} chars) via {model}")
            return json.loads(raw)

        except json.JSONDecodeError:
            return {"raw_response": raw}
        except Exception as e:
            err = str(e)
            if "429" in err or "RateLimitReached" in err:
                next_idx = current_model_index + 1
                if next_idx < len(MODELS):
                    current_model_index = next_idx
                    print(f"[GPT-4] Switch → {MODELS[current_model_index]}")
                else:
                    wait = attempt * 15
                    print(f"[GPT-4] ⚠️ Attente {wait}s...")
                    time.sleep(wait)
            else:
                print(f"[GPT-4] ❌ {err}")
                return {"error": err}

    return {"error": "Max retries atteint"}

def print_analysis(analysis, parsed):
    print("\n" + "🤖"*30)
    print("      ANALYSE GPT-4 — ROOT CAUSE ANALYSIS")
    print("🤖"*30)
    if "error" in analysis:
        print(f"❌ {analysis['error']}")
        return
    if "raw_response" in analysis:
        print(f"📝 Réponse brute:\n{analysis['raw_response']}")
        return
    print(f"\n📛 {parsed['name']} ({parsed['severity'].upper()})")
    print(f"🔍 {analysis.get('anomalie', 'N/A')}")
    print(f"🎯 {analysis.get('cause_probable', 'N/A')}")
    print(f"⚡ {analysis.get('severite_reelle', 'N/A').upper()}")
    if analysis.get('services_impactes'):
        print(f"\n💥 SERVICES IMPACTÉS :")
        for s in analysis['services_impactes']:
            print(f"   • {s}")
    if analysis.get('actions_correctives'):
        print(f"\n🔧 ACTIONS CORRECTIVES :")
        for i, a in enumerate(analysis['actions_correctives'], 1):
            print(f"   {i}. {a}")
    if analysis.get('prevention'):
        print(f"\n🛡️  {analysis['prevention']}")
    print("🤖"*30)