# import subprocess
# import time
#
# import logging
# logger = logging.getLogger(__name__)
#
#
# # ── Commandes autorisées ──────────────────────────────────────
# SAFE_COMMANDS = [
#     "kubectl get",
#     "kubectl describe",
#     "kubectl logs",
#     "kubectl rollout restart",
#     "kubectl rollout status",
#     "kubectl scale",
#     "kubectl delete pod",
#     "kubectl top",
#     "kubectl edit",
# ]
#
# # ── Commandes interdites ──────────────────────────────────────
# DANGEROUS_COMMANDS = [
#     "kubectl delete namespace",
#     "kubectl delete deployment",
#     "kubectl delete statefulset",
#     "kubectl delete service",
#     "kubectl delete configmap",
#     "kubectl delete secret",
#     "kubectl apply",
#     "rm ",
#     "dd ",
# ]
#
# def clean_command(cmd):
#     """Nettoie et adapte les commandes bloquantes"""
#
#     # ── 1. Supprimer --watch / -w ─────────────────────────────
#     cmd = cmd.replace("--watch", "").strip()
#     cmd = cmd.replace(" -w ",    " ").strip()
#
#     # ── 2. Supprimer --follow / -f (logs stream infini) ───────
#     cmd = cmd.replace("--follow", "").strip()
#     cmd = cmd.replace(" -f ",     " ").strip()
#
#     # ── 3. exec -it → supprimer interactif ───────────────────
#     cmd = cmd.replace("exec -it", "exec").strip()
#     cmd = cmd.replace("exec -i ", "exec ").strip()
#
#     # ── 4. delete pod → forcer suppression rapide ────────────
#     if "kubectl delete pod" in cmd:
#         if "--grace-period" not in cmd:
#             cmd = cmd.replace(
#                 "kubectl delete pod",
#                 "kubectl delete pod --grace-period=0 --force"
#             )
#
#     # ── 5. Fix deployment → statefulset ──────────────────────
#     replacements = {
#         "rollout restart deployment keycloak"   : "rollout restart statefulset/keycloak",
#         "rollout restart deployment keycloak-0" : "rollout restart statefulset/keycloak",
#         "rollout restart deployment keycloak-1" : "rollout restart statefulset/keycloak",
#         "rollout restart deployment postgresql" : "rollout restart statefulset/postgresql-primary",
#         "rollout restart deployment mongodb"    : "rollout restart statefulset/mongodb",
#         "rollout restart deployment redis"      : "rollout restart statefulset/redis-master",
#         "rollout restart deployment redpanda"   : "rollout restart statefulset/redpanda",
#
#         "rollout status deployment/postgresql"  : "rollout status statefulset/postgresql-primary",
#         "rollout status deployment/keycloak"    : "rollout status statefulset/keycloak",
#         "rollout status deployment/mongodb"     : "rollout status statefulset/mongodb",
#         "rollout status deployment/redis"       : "rollout status statefulset/redis-master",
#         "rollout status deployment/redpanda"    : "rollout status statefulset/redpanda",
#         "rollout status deployment postgresql"  : "rollout status statefulset/postgresql-primary",
#         "rollout status deployment keycloak"    : "rollout status statefulset/keycloak",
#         "rollout status deployment mongodb"     : "rollout status statefulset/mongodb",
#         "rollout status deployment redis"       : "rollout status statefulset/redis-master",
#         "rollout status deployment redpanda"    : "rollout status statefulset/redpanda",
#     }
#     for old, new in replacements.items():
#         cmd = cmd.replace(old, new)
#
#     return cmd.strip()
#
# def is_safe_command(cmd):
#     """Vérifie si la commande est safe à exécuter"""
#     cmd_lower = cmd.lower().strip()
#
#     # Vérifier commandes dangereuses
#     for dangerous in DANGEROUS_COMMANDS:
#         if dangerous in cmd_lower:
#             logger.info(f"[REMEDIATION] ❌ Commande dangereuse bloquée : {cmd}")
#             return False
#
#     # Vérifier commandes autorisées
#     for safe in SAFE_COMMANDS:
#         if cmd_lower.startswith(safe.lower()):
#             return True
#
#     logger.info(f"[REMEDIATION] ⚠️ Commande non autorisée : {cmd}")
#     return False
#
# def execute_command(cmd):
#     """Execute une commande kubectl et retourne le résultat"""
#
#     # Nettoyer les options bloquantes
#     cmd_clean = clean_command(cmd)
#     if cmd_clean != cmd:
#         logger.info(f"[REMEDIATION] 🔧 Commande adaptée : {cmd_clean}")
#
#     try:
#         result = subprocess.run(
#             cmd_clean,
#             shell=True,
#             capture_output=True,
#             text=True,
#             timeout=30
#         )
#         output  = result.stdout.strip() or result.stderr.strip()
#         success = result.returncode == 0
#         return success, output
#
#     except subprocess.TimeoutExpired:
#         return False, "Timeout — commande trop longue"
#     except Exception as e:
#         return False, str(e)
#
# def execute_remediation(analysis):
#     """Execute toutes les actions correctives"""
#     actions = analysis.get('actions_correctives', [])
#     results = []
#     total   = len(actions)
#
#     if not actions:
#         logger.info("[REMEDIATION] ⚠️ Aucune action corrective à executer")
#         return results
#
#     logger.info(f"\n[REMEDIATION] 🔧 Début remédiation — {total} commande(s)")
#     logger.info("="*60)
#
#     for i, cmd in enumerate(actions, 1):
#         logger.info(f"\n[REMEDIATION] ▶️ Commande {i}/{total}")
#         logger.info(f"[REMEDIATION] $ {cmd}")
#
#         if not is_safe_command(cmd):
#             results.append({
#                 "command": cmd,
#                 "success": False,
#                 "output" : "Commande bloquée — non autorisée",
#                 "skipped": True
#             })
#             continue
#
#         success, output = execute_command(cmd)
#
#         if success:
#             logger.info(f"[REMEDIATION] ✅ Succès")
#         else:
#             logger.info(f"[REMEDIATION] ❌ Échec")
#
#         if output:
#             logger.info(f"[REMEDIATION] Output : {output[:200]}")
#
#         results.append({
#             "command": cmd,
#             "success": success,
#             "output" : output[:500],
#             "skipped": False
#         })
#
#         # Pause entre commandes
#         time.sleep(2)
#
#     success_count = sum(1 for r in results if r['success'])
#     logger.info(f"\n[REMEDIATION] 📊 Résultat : {success_count}/{total} commandes réussies")
#     logger.info("="*60)
#
#     return results
#
# def format_remediation_results(results):
#     """Formate les résultats pour le PDF et l'email"""
#     if not results:
#         return "Aucune remédiation effectuée."
#
#     lines = []
#     for i, r in enumerate(results, 1):
#         status = "✅" if r['success'] else "❌" if not r.get('skipped') else "⚠️"
#         lines.append(f"{status} Commande {i}: {r['command']}")
#         if r['output']:
#             lines.append(f"   → {r['output'][:200]}")
#     return "\n".join(lines)
