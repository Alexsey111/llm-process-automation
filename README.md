# LLM Business Automation Engine

MVP-автоматизация процесса с LLM: **вход → LLM (строго структурированный JSON) → контроль качества → действие**.

Один общий engine — два бизнес-кейса:

| Кейс | Что делает | Демонстрирует |
|------|-----------|----------------|
| **F — Financial Document Processor** | Извлекает поля из счёта/заявки на расход (номер, дата, контрагент, сумма, НДС, срок оплаты, назначение) | document extraction + финансовый workflow |
| **H — Insurance Claim Triage** | Структурирует заявление о страховом случае (тип, дата, ущерб, полис, доказательства) | high-risk workflow, human-in-the-loop, escalation |

Ключевой принцип: **LLM не является источником истины и не принимает окончательное решение**. Она извлекает данные, а детерминированные Python-правила решают, можно ли передавать результат дальше, или нужна эскалация человеку.

## Архитектура

```text
POST /ingest (или inputs/)
     │
     ▼
Нормализация входа
     ▼
LLM extraction (temperature=0.2, JSON mode)
     ▼
Структурированный JSON
     ▼
Уровень 1: Pydantic schema validation ── ошибка ──► ESCALATE (validation_error)
     ▼
Уровень 2: deterministic business rules ── данных мало ──► ESCALATE
     ▼
SQLite: results + audit_log
```

Подробные схемы: `docs/architecture.svg`, `docs/financial-flow.svg`, `docs/insurance-flow.svg`.

## Быстрый старт (5–10 минут)

Требуется Python 3.11+.

```bash
# 1. Клонировать и установить зависимости
git clone <repo-url> && cd llm-process-automation
pip install -r requirements.txt

# 2. Настроить LLM-провайдер
copy .env.example .env        # Windows (Linux/macOS: cp .env.example .env)
# вписать LLM_API_KEY (подойдёт любой OpenAI-совместимый провайдер: DeepSeek, OpenAI, vLLM)

# 3. Запустить сервер
uvicorn app.main:app --reload
# Swagger: http://127.0.0.1:8000/docs
```

## Как подать вход

### Способ 1 — POST /ingest

```bash
curl -X POST http://127.0.0.1:8000/ingest ^
  -H "Content-Type: application/json" ^
  -d "{\"case_type\": \"financial\", \"text\": \"Счёт №481 от 18.09.2026. ООО Альфа, сумма 125000 руб., НДС 20%, оплата до 25.09.2026.\"}"
```

```bash
curl -X POST http://127.0.0.1:8000/ingest ^
  -H "Content-Type: application/json" ^
  -d "{\"case_type\": \"insurance\", \"text\": \"18 сентября при перевозке повреждён станок, ущерб 180000 руб., полиса нет.\"}"
```

Ответ:

```json
{
  "status": "escalated",
  "case_type": "insurance",
  "audit_id": 2,
  "result": {
    "policy_number": null,
    "required_missing": ["policy_number"],
    "confidence": "medium",
    "next_action": "request_missing_information",
    "escalate": true
  }
}
```

### Способ 2 — пакетная обработка папки inputs/

20 готовых тестовых входов лежат в `inputs/financial/` (F01–F10) и `inputs/insurance/` (H01–H10):

```bash
python scripts/run_inputs.py all        # оба кейса
python scripts/run_inputs.py financial  # только F
```

Каждый файл прогоняется через конвейер, результат сохраняется в `results/<case_type>/<имя>.json` и в БД.

## Где смотреть результат

| Что | Где |
|-----|-----|
| Структурированный результат | таблица `results` в `data/automation.db`, файлы `results/`, `GET /results` |
| Журнал обработки (аудит) | таблица `audit_log` в `data/automation.db`, `GET /audit` |
| CSV-экспорт | `python scripts/export_csv.py` → `data/export/results.csv`, `data/export/audit_log.csv` |

Статусы в журнале: `success` / `escalated` / `validation_error` / `llm_error`.

## Контроль качества

1. **Schema validation (Pydantic).** JSON от LLM проверяется по строгой схеме: литералы (`document_type`, `currency`, `confidence`, `next_action`), границы (`amount >= 0`, `vat_rate 0..100`), типы дат. Невалидно → `validation_error` + запись в аудит.
2. **Business rules (Python).** Даже валидный JSON проверяется правилами: обязательные поля отсутствуют → `escalate=true`; `confidence=low` → `escalate=true`; нулевая сумма / нет доказательств (кейс H) → `escalate=true`. LLM-поля `escalate`/`next_action` **корректируются** детерминированным кодом — LLM не может «само себя одобрить».
3. **Audit trail.** Каждый вход фиксируется: вход + сырой вывод LLM + валидированный выход + статус + ошибка.
4. **Prompt injection.** Входные тексты с инъекциями (F10, H10) обрабатываются как данные, а не команды; системный промпт явно это запрещает, тест подтверждает безопасную эскалацию.

## Тесты

```bash
python -m pytest tests/ -v        # unit-тесты на моках LLM: 20 входов + правила + API
```

Конвейер покрыт тестами на всех 20 тестовых входах (10 для F + 10 для H) — включая missing fields, противоречивые документы, неизвестную валюту, low confidence и prompt injection.

## Структура проекта

```text
app/
├── main.py               # FastAPI-приложение
├── api/ingest.py         # POST /ingest, GET /audit, GET /results
├── core/
│   ├── config.py         # конфиг из .env
│   ├── llm.py            # LLM-клиент (OpenAI-совместимый)
│   ├── validation.py     # уровень 1: Pydantic
│   ├── pipeline.py       # общий конвейер
│   └── audit.py          # журнал обработки
├── db/database.py        # SQLite: audit_log + results
└── cases/                # предметная логика подключается через registry
    ├── registry.py
    ├── financial/        # schemas / prompt / rules
    └── insurance/        # schemas / prompt / rules
inputs/                   # 10 + 10 тестовых входов
scripts/                  # run_inputs.py, export_csv.py
tests/                    # unit-тесты (моки LLM) + API-тесты
docs/                     # SVG-схемы
```

Добавление нового процесса = 3 файла (schema/prompt/rules) + одна строка в `registry.py`. Backend трогать не нужно.