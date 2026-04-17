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


def build_prompt(parsed, metrics_summary, logs_text, events_text):
    pod_name  = parsed['affected_pods'][0] if parsed['affected_pods'] else f"{parsed['service']}-0"
    namespace = parsed['namespace']

    return f"""Tu es un expert SRE/DevOps senior avec 10 ans d'expérience Kubernetes.

Tu reçois des données RÉELLES d'un incident en production.
Analyse TOUTES les données ensemble et propose des solutions PRÉCISES.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 MÉTRIQUES PROMETHEUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Alerte    : {parsed['name']}
Sévérité  : {parsed['severity'].upper()}
Service   : {parsed['service']}
Namespace : {namespace}
Pod       : {pod_name}
Summary   : {parsed['summary']}
Up/Down   : {metrics_summary.get('up', 'N/A')}
Restarts  : {metrics_summary.get('restarts', 'N/A')}
CPU       : {metrics_summary.get('cpu', 'N/A')}
Memory    : {metrics_summary.get('memory', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 LOGS APPLICATIFS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{logs_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 EVENTS KUBERNETES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{events_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 TON ANALYSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analyse les métriques + logs + events ensemble :

1. MÉTRIQUES → Up=0 ? Restarts élevés ? CPU/Memory anormal ?
2. LOGS → Quelle erreur exacte ? Cite-la mot pour mot.
3. EVENTS → Quel type d'event ? Quelle raison ?
4. CAUSE RÉELLE → En combinant tout, qu'est-ce qui se passe vraiment ?
5. SOLUTION → Quelles commandes pour diagnostiquer et corriger ?

RÈGLES STRICTES :
- Utilise toujours pod={pod_name} et namespace={namespace}
- Si tu vois une erreur dans les logs → cite-la EXACTEMENT
- Si up=0 → le service est DOWN → mentionne-le clairement
- Si restarts élevés → c'est un CrashLoop → dis pourquoi
- Si logs vides → base-toi sur les events et métriques
- Tes commandes doivent être basées sur CE QUE TU AS TROUVÉ
- INTERDIT de donner des réponses génériques non liées aux données

Réponds UNIQUEMENT en JSON valide sans markdown :
{{
    "anomalie": "Ce que tu observes en combinant métriques + logs + events — cite les valeurs et erreurs exactes",
    "cause_probable": "La vraie cause identifiée depuis toutes les données — explique le mécanisme",
    "services_impactes": ["services affectés avec leur état"],
    "severite_reelle": "CRITICAL ou HIGH ou MEDIUM ou LOW",
    "actions_correctives": [
        "kubectl <commande 1 basée sur ce que tu as trouvé>",
        "kubectl <commande 2 étape suivante logique>",
        "kubectl <commande 3 correction du problème>",
        "kubectl <commande 4 vérification après correction>"
    ],
    "commandes_diagnostic": [
        "kubectl <commande pour approfondir investigation>",
        "kubectl <commande pour voir état actuel>",
        "kubectl <commande pour confirmer la cause>"
    ],
    "prevention": "Actions préventives SPÉCIFIQUES basées sur la cause identifiée"
}}
"""


def call_gpt4_with_retry(parsed, metrics, logs, events=[], max_retries=3):
    global current_model_index

    metrics_summary = extract_metrics_summary(metrics)
    logs_text       = extract_logs_text(logs, max_lines=50)
    events_text     = format_events_text(events)

    prompt = build_prompt(parsed, metrics_summary, logs_text, events_text)

    for attempt in range(1, max_retries + 1):
        model = MODELS[current_model_index]
        try:
            print(f"[GPT-4] Tentative {attempt}/{max_retries} — {model}")
            response = gpt_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role"   : "system",
                        "content": """Tu es un expert SRE/DevOps senior spécialisé Kubernetes.
Tu analyses des incidents réels en combinant métriques + logs + events.
Tu cites toujours les erreurs EXACTES trouvées dans les logs.
Tu proposes des commandes kubectl PRÉCISES basées sur l'erreur trouvée.
Tu ne donnes JAMAIS de réponses génériques.
Tu réponds toujours en JSON valide sans markdown."""
                    },
                    {
                        "role"   : "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=1500,
            )
            raw = response.choices[0].message.content

            # Nettoyer si markdown présent
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()

            print(f"[GPT-4] ✅ Réponse reçue ({len(raw)} chars) via {model}")
            return json.loads(clean)

        except json.JSONDecodeError:
            print(f"[GPT-4] ⚠️ JSON invalide — retour réponse brute")
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

    if analysis.get('commandes_diagnostic'):
        print(f"\n🖥️  COMMANDES DIAGNOSTIC :")
        for cmd in analysis['commandes_diagnostic']:
            print(f"   $ {cmd}")

    if analysis.get('prevention'):
        print(f"\n🛡️  PRÉVENTION :")
        print(f"   {analysis['prevention']}")

    print("🤖"*30)