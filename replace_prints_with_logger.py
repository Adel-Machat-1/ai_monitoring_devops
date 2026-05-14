"""
Script automatique — Remplace tous les print() par logger
dans le projet Agent IA

Usage : python replace_prints_with_logger.py
"""

import os
import re

# ── Fichiers à modifier ───────────────────────────────────────
FILES_TO_UPDATE = [
    "main.py",
    "core/parser.py",
    "core/prometheus.py",
    "core/loki.py",
    "core/kubernetes_events.py",
    "core/gpt4.py",
    "core/queue_worker.py",
    "core/state.py",
    "core/auto_remediation.py",
    "core/anomaly/collector.py",
    "core/anomaly/detector.py",
    "core/anomaly/scheduler.py",
    "reports/pdf_generator.py",
    "reports/minio_uploader.py",
    "reports/email_sender.py",
    "utils/extractors.py",
]

# ── Header à ajouter en haut de chaque fichier ───────────────
LOGGER_HEADER = '''import logging
logger = logging.getLogger(__name__)

'''

def add_logger_import(content: str, filename: str) -> str:
    """Ajoute l'import logger si pas déjà présent"""
    if "import logging" in content:
        return content  # déjà présent

    # Trouver la fin des imports
    lines = content.split("\n")
    last_import_idx = 0

    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            last_import_idx = i

    # Insérer après le dernier import
    lines.insert(last_import_idx + 1, "")
    lines.insert(last_import_idx + 2, "import logging")
    lines.insert(last_import_idx + 3, f'logger = logging.getLogger(__name__)')
    lines.insert(last_import_idx + 4, "")

    return "\n".join(lines)

def replace_prints(content: str) -> tuple:
    """Remplace les print() par logger.info/error/warning"""
    changes = 0

    # print avec ERROR/ERREUR/error → logger.error
    pattern_error = r'print\(f?"?\[?(ERROR|ERREUR|error|Error)\]?[:\s]*(.*?)"?\)'
    def replace_error(m):
        nonlocal changes
        changes += 1
        msg = m.group(0).replace("print(", "logger.error(")
        return msg
    content = re.sub(pattern_error, replace_error, content)

    # print avec WARNING/WARN → logger.warning
    pattern_warn = r'print\(f?"?\[?(WARNING|WARN|warning|warn)\]?[:\s]*(.*?)"?\)'
    def replace_warn(m):
        nonlocal changes
        changes += 1
        msg = m.group(0).replace("print(", "logger.warning(")
        return msg
    content = re.sub(pattern_warn, replace_warn, content)

    # Tous les autres print() → logger.info
    lines = content.split("\n")
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("print(") and "logger" not in line:
            indent = line[:len(line) - len(stripped)]
            new_line = line.replace("print(", "logger.info(", 1)
            new_lines.append(new_line)
            changes += 1
        else:
            new_lines.append(line)

    return "\n".join(new_lines), changes

def process_file(filepath: str):
    """Traite un fichier"""
    if not os.path.exists(filepath):
        print(f"  ⚠️  Fichier non trouvé : {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Ajouter import logger
    content = add_logger_import(content, filepath)

    # Remplacer print()
    content, changes = replace_prints(content)

    # Sauvegarder
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  ✅ {filepath} — {changes} print() remplacés")

def main():
    print("\n🔄 Remplacement des print() par logger...\n")
    print("=" * 50)

    total_changes = 0
    for filepath in FILES_TO_UPDATE:
        process_file(filepath)

    print("=" * 50)
    print(f"\n✅ Terminé ! Tous les print() ont été remplacés.")
    print(f"📄 Les logs seront écrits dans : agent_ia.log")
    print(f"\n💡 Lance maintenant : python main.py")
    print(f"   Puis ouvre le Dashboard → Page 6 Logs\n")

if __name__ == "__main__":
    main()