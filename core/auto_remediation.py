import subprocess
import time

SAFE_COMMANDS = [
    "kubectl get",
    "kubectl describe",
    "kubectl logs",
    "kubectl rollout restart",
    "kubectl scale",
    "kubectl delete pod",
    "kubectl top",
]

DANGEROUS_COMMANDS = [
    "kubectl delete namespace",
    "kubectl delete deployment",
    "kubectl delete statefulset",
    "kubectl delete service",
    "kubectl apply",
    "rm ",
    "dd ",
]

def clean_command(cmd):
    """Supprime les options bloquantes"""
    cmd = cmd.replace("--watch", "").strip()
    cmd = cmd.replace(" -w ", " ").strip()
    cmd = cmd.replace("exec -it", "exec").strip()
    cmd = cmd.replace("exec -i ", "exec ").strip()
    # Fix statefulset vs deployment
    cmd = cmd.replace(
        "rollout restart deployment keycloak",
        "rollout restart statefulset/keycloak"
    )
    cmd = cmd.replace(
        "rollout restart deployment postgresql",
        "rollout restart statefulset/postgresql-primary"
    )
    cmd = cmd.replace(
        "rollout restart deployment mongodb",
        "rollout restart statefulset/mongodb"
    )
    cmd = cmd.replace(
        "rollout restart deployment redis",
        "rollout restart statefulset/redis-master"
    )
    cmd = cmd.replace(
        "rollout restart deployment redpanda",
        "rollout restart statefulset/redpanda"
    )
    return cmd

def is_safe_command(cmd):
    cmd_lower = cmd.lower().strip()
    for dangerous in DANGEROUS_COMMANDS:
        if dangerous in cmd_lower:
            print(f"[REMEDIATION] ❌ Commande dangereuse bloquée : {cmd}")
            return False
    for safe in SAFE_COMMANDS:
        if cmd_lower.startswith(safe.lower()):
            return True
    print(f"[REMEDIATION] ⚠️ Commande non autorisée : {cmd}")
    return False

def execute_command(cmd):
    """Execute une commande kubectl"""
    # Nettoyer les options bloquantes
    cmd_clean = clean_command(cmd)
    if cmd_clean != cmd:
        print(f"[REMEDIATION] 🔧 Commande adaptée : {cmd_clean}")

    try:
        result = subprocess.run(
            cmd_clean,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output  = result.stdout.strip() or result.stderr.strip()
        success = result.returncode == 0
        return success, output

    except subprocess.TimeoutExpired:
        return False, "Timeout — commande trop longue"
    except Exception as e:
        return False, str(e)

def execute_remediation(analysis):
    actions = analysis.get('actions_correctives', [])
    results = []
    total   = len(actions)

    if not actions:
        print("[REMEDIATION] ⚠️ Aucune action corrective à executer")
        return results

    print(f"\n[REMEDIATION] 🔧 Début remédiation — {total} commande(s)")
    print("="*60)

    for i, cmd in enumerate(actions, 1):
        print(f"\n[REMEDIATION] ▶️ Commande {i}/{total}")
        print(f"[REMEDIATION] $ {cmd}")

        if not is_safe_command(cmd):
            results.append({
                "command": cmd,
                "success": False,
                "output" : "Commande bloquée — non autorisée",
                "skipped": True
            })
            continue

        success, output = execute_command(cmd)

        if success:
            print(f"[REMEDIATION] ✅ Succès")
        else:
            print(f"[REMEDIATION] ❌ Échec")

        if output:
            print(f"[REMEDIATION] Output : {output[:200]}")

        results.append({
            "command": cmd,
            "success": success,
            "output" : output[:500],
            "skipped": False
        })

        time.sleep(2)

    success_count = sum(1 for r in results if r['success'])
    print(f"\n[REMEDIATION] 📊 Résultat : {success_count}/{total} commandes réussies")
    print("="*60)

    return results

def format_remediation_results(results):
    if not results:
        return "Aucune remédiation effectuée."
    lines = []
    for i, r in enumerate(results, 1):
        status = "✅" if r['success'] else "❌" if not r.get('skipped') else "⚠️"
        lines.append(f"{status} Commande {i}: {r['command']}")
        if r['output']:
            lines.append(f"   → {r['output'][:200]}")
    return "\n".join(lines)