"""
Script automatique — Revert : Remplace tous les logger.* par print()
dans le projet Agent IA (retour à l'état initial)

Usage : python restore_prints.py
"""

import os
import re

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


def remove_logger_import(content: str) -> str:
    """Supprime les lignes import logging et logger = logging.getLogger(...)"""
    lines = content.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "import logging" or line.strip().startswith("logger = logging.getLogger("):
            # Supprimer aussi la ligne vide qui suit si elle est isolée
            i += 1
            continue
        new_lines.append(line)
        i += 1

    # Nettoyer les doubles lignes vides consécutives créées par la suppression
    cleaned = []
    prev_blank = False
    for line in new_lines:
        if line.strip() == "":
            if not prev_blank:
                cleaned.append(line)
            prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False

    return "\n".join(cleaned)


def restore_prints(content: str) -> tuple:
    """Remplace logger.info/error/warning par print()"""
    changes = 0
    lines = content.split("\n")
    new_lines = []

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("logger.info(") or \
           stripped.startswith("logger.error(") or \
           stripped.startswith("logger.warning(") or \
           stripped.startswith("logger.debug(") or \
           stripped.startswith("logger.critical("):

            new_line = re.sub(r'logger\.(info|error|warning|debug|critical)\(', 'print(', line, count=1)
            new_lines.append(new_line)
            changes += 1
        else:
            new_lines.append(line)

    return "\n".join(new_lines), changes


def process_file(filepath: str):
    """Traite un fichier"""
    if not os.path.exists(filepath):
        print(f"  [SKIP] Fichier non trouve : {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    content, changes = restore_prints(content)
    content = remove_logger_import(content)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  [OK] {filepath} — {changes} logger remplace(s) par print()")


def main():
    print("\n--- Revert : logger -> print() ---\n")
    print("=" * 50)

    for filepath in FILES_TO_UPDATE:
        process_file(filepath)

    print("=" * 50)
    print("\n[DONE] Tous les logger ont ete remis en print().")
    print("Lance maintenant : python main.py\n")


if __name__ == "__main__":
    main()
