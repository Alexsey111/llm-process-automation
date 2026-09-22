"""CLI: обработка всех файлов из inputs/<case_type>/ через общий конвейер.

Использование:
    python scripts/run_inputs.py financial
    python scripts/run_inputs.py insurance
    python scripts/run_inputs.py all

Каждый входной файл (.txt) читается как текст, прогоняется через
LLM -> validation -> rules -> audit, результат пишется в SQLite
и продублирован в results/<case_type>/<имя_файла>.json.
"""
import json
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import INPUTS_DIR, RESULTS_DIR  # noqa: E402
from app.core.pipeline import process_text  # noqa: E402
from app.db.database import init_db  # noqa: E402


def run_case(case_type: str) -> list[dict]:
    folder = INPUTS_DIR / case_type
    if not folder.is_dir():
        print(f"[skip] папка {folder} не найдена")
        return []

    files = sorted(p for p in folder.glob("*.txt") if p.is_file())
    if not files:
        print(f"[skip] в {folder} нет .txt файлов")
        return []

    init_db()
    summary = []
    for path in files:
        text = path.read_text(encoding="utf-8").strip()
        outcome = process_text(case_type, text, source=f"file:{path.name}")

        out_dir = RESULTS_DIR / case_type
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / (path.stem + ".json")
        out_path.write_text(
            json.dumps(
                {
                    "input_file": path.name,
                    "status": outcome.status,
                    "audit_id": outcome.audit_id,
                    "result": outcome.result,
                    "error": outcome.error,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(f"[{case_type}] {path.name}: status={outcome.status} audit_id={outcome.audit_id}")
        summary.append({"file": path.name, "status": outcome.status, "audit_id": outcome.audit_id})

    return summary


def main() -> None:
    target = (sys.argv[1] if len(sys.argv) > 1 else "all").lower()
    if target not in {"all", "financial", "insurance"}:
        print("Использование: python scripts/run_inputs.py [all|financial|insurance]")
        raise SystemExit(2)

    targets = ["financial", "insurance"] if target == "all" else [target]
    all_summary = {}
    for case_type in targets:
        all_summary[case_type] = run_case(case_type)

    (RESULTS_DIR / "last_run_summary.json").write_text(
        json.dumps(all_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nГотово. Сводка: results/last_run_summary.json; журнал: таблица audit_log в БД.")


if __name__ == "__main__":
    main()