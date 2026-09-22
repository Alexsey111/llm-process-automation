"""Экспорт результатов и журнала аудита в CSV.

Использование:
    python scripts/export_csv.py            # data/export/results.csv + audit_log.csv
    python scripts/export_csv.py financial  # только один кейс
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import BASE_DIR  # noqa: E402
from app.core.audit import list_audit, list_results  # noqa: E402
from app.db.database import init_db  # noqa: E402


def main() -> None:
    case_type = sys.argv[1] if len(sys.argv) > 1 else None
    init_db()

    out_dir = Path(BASE_DIR) / "data" / "export"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = list_results(limit=10000, case_type=case_type)
    with open(out_dir / "results.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["id", "audit_id", "case_type", "created_at", "status", "result_json"])
        for row in rows:
            writer.writerow([row["id"], row["audit_id"], row["case_type"],
                             row["created_at"], row["status"], row["result_json"]])

    audits = list_audit(limit=10000, case_type=case_type)
    with open(out_dir / "audit_log.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["id", "case_type", "source", "created_at", "status",
                         "confidence", "escalate", "error"])
        for row in audits:
            writer.writerow([row["id"], row["case_type"], row["source"], row["created_at"],
                             row["status"], row["confidence"], row["escalate"], row["error"]])

    print(f"Экспортировано: {len(rows)} результатов, {len(audits)} записей аудита")
    print(f"Файлы: {out_dir / 'results.csv'} и {out_dir / 'audit_log.csv'}")


if __name__ == "__main__":
    main()