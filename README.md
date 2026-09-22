# LLM Business Automation Engine

MVP-автоматизация процесса с LLM: **вход → LLM (строго структурированный JSON) → контроль качества → действие**.

Один общий engine — два бизнес-кейса:

| Кейс | Вход | Что делает | Демонстрирует |
|------|------|-----------|----------------|
| **F — Financial Document Processor** | Текст счёта / заявки на расход | Извлекает поля (номер, дата, контрагент, сумма, НДС, срок оплаты, назначение), определяет тип документа и следующую операцию | document extraction + финансовый workflow |
| **H — Insurance Claim Triage** | Заявление о страховом случае | Структурирует факты (тип случая, дата, описание, ущерб, полис, доказательства); **не** решает вопросы выплаты и вины | high-risk workflow, human-in-the-loop, escalation |

## Зачем это нужно

Заявления приходят свободным текстом: вручную их обработка медленная, данные теряются,
а «просто скормить текст ChatGPT» нельзя — модель может галлюцинировать, пропустить
обязательные поля или выполнить инструкцию, встроенную в текст документа (prompt injection).

Этот проект показывает, как использовать LLM в бизнес-процессе, где модели нельзя доверять на 100%:

> **LLM не является источником истины и не принимает окончательное решение.**
> Она извлекает данные, а детерминированные Python-правила решают,
> можно ли передавать результат дальше, или нужна эскалация человеку.

## Архитектура

```text
POST /ingest (или inputs/)
     │
     ▼
Нормализация входа (пустой текст → validation_error)
     ▼
LLM extraction (DeepSeek, temperature=0.2, JSON mode, ретраи)
     ▼
Структурированный JSON (category / fields / confidence / missing)
     ▼
Уровень 1: Pydantic schema validation ── ошибка ──► validation_error + аудит
     ▼
Уровень 2: deterministic business rules ── данных мало ──► ESCALATE
     ▼
SQLite: results + audit_log
     ▼
Действие: запись результата (БД) + JSON в results/ + CSV-экспорт
```

Схемы процессов: [docs/architecture.svg](docs/architecture.svg),
[docs/financial-flow.svg](docs/financial-flow.svg), [docs/insurance-flow.svg](docs/insurance-flow.svg).

### Модули

| Модуль | Ответственность |
|--------|-----------------|
| `app/api/ingest.py` | `POST /ingest` — точка входа; `GET /audit`, `GET /results` — просмотр журнала и результатов |
| `app/core/llm.py` | Клиент OpenAI-совместимого провайдера: JSON mode, срез markdown, ретраи, деградация без JSON mode |
| `app/core/validation.py` | Уровень 1: парсинг ответа LLM в Pydantic-схему, человекочитаемые ошибки |
| `app/core/pipeline.py` | Общий конвейер: LLM → schema → rules → audit; статусы `success` / `escalated` / `validation_error` / `llm_error` |
| `app/core/audit.py` | Журнал обработки: вход + сырой вывод LLM + валидированный выход + статус |
| `app/db/database.py` | SQLite-схема: таблицы `audit_log` и `results` |
| `app/cases/registry.py` | Реестр кейсов: предметная логика подключается к engine как плагин |
| `app/cases/financial/` | Кейс F: `schemas.py` (Pydantic), `prompt.py`, `rules.py` (бизнес-правила) |
| `app/cases/insurance/` | Кейс H: аналогично |
| `scripts/run_inputs.py` | Пакетная обработка папки `inputs/` + сохранение в `results/` |
| `scripts/export_csv.py` | Экспорт результатов и аудита в CSV |

## Быстрый старт (5–10 минут)

Требуется Python 3.11+.

```bash
# 1. Клонировать и установить зависимости
git clone https://github.com/Alexsey111/llm-process-automation.git
cd llm-process-automation
pip install -r requirements.txt

# 2. Настроить LLM-провайдер
copy .env.example .env        # Windows (Linux/macOS: cp .env.example .env)
# впишите LLM_API_KEY — подойдёт любой OpenAI-совместимый провайдер
# (DeepSeek, OpenAI, локальный vLLM — меняется только BASE_URL и MODEL)

# 3. Запустить сервер
uvicorn app.main:app --reload
# Swagger: http://127.0.0.1:8000/docs
```

### Проверка за 30 секунд

```bash
curl -X POST http://127.0.0.1:8000/ingest -H "Content-Type: application/json" ^
  -d "{\"case_type\": \"financial\", \"text\": \"Счёт №481 от 18.09.2026. ООО Альфа, сумма 125000 руб., НДС 20%, оплата до 25.09.2026.\"}"
```

Ответ — структурированный JSON с полями документа, `status: "success"` и `audit_id`.

## Как подать вход

### Способ 1 — POST /ingest

Request:

```json
{
  "case_type": "financial",   // или "insurance"
  "text": "Счёт №481 от 18.09.2026..."
}
```

Ответ (успешное извлечение):

```json
{
  "status": "success",
  "case_type": "financial",
  "audit_id": 1,
  "result": {
    "document_type": "invoice",
    "document_number": "481",
    "document_date": "2026-09-18",
    "counterparty": "ООО Альфа",
    "amount": 125000.0,
    "currency": "RUB",
    "vat_rate": 20,
    "payment_due_date": "2026-09-25",
    "purpose": "консультационные услуги",
    "confidence": "high",
    "missing_fields": [],
    "next_action": "approve_payment",
    "escalate": false
  }
}
```

Ответ (недостающие данные — эскалация):

```json
{
  "status": "escalated",
  "case_type": "insurance",
  "audit_id": 2,
  "result": {
    "claim_type": "transport_damage",
    "policy_number": null,
    "required_missing": ["policy_number"],
    "confidence": "medium",
    "next_action": "request_missing_information",
    "escalate": true
  }
}
```

### Способ 2 — пакетная обработка папки inputs/

В репозитории 20 готовых тестовых входов: `inputs/financial/` (F01–F10)
и `inputs/insurance/` (H01–H10) — happy path, missing fields, разговорный текст,
несколько дат, неизвестная валюта, противоречивый документ, почти пустой вход,
prompt injection.

```bash
python scripts/run_inputs.py all        # оба кейса
python scripts/run_inputs.py financial  # только F
python scripts/run_inputs.py insurance  # только H
```

Каждый `.txt` прогоняется через конвейер: результат пишется в SQLite
и дублируется в `results/<case_type>/<имя>.json`; сводка прогона —
`results/last_run_summary.json`.

## Где смотреть результат

| Что | Где |
|-----|-----|
| Структурированный результат | таблица `results` в `data/automation.db`; файлы `results/<case>/*.json`; `GET /results` |
| Журнал обработки (аудит) | таблица `audit_log` в `data/automation.db`; `GET /audit` |
| CSV-экспорт | `python scripts/export_csv.py` → `data/export/results.csv` + `data/export/audit_log.csv` |
| Живой просмотр БД | любой SQLite-браузер (DB Browser for SQLite) или `sqlite3 data/automation.db "SELECT id, case_type, status, confidence, escalate FROM audit_log;"` |

### Схема БД

```sql
audit_log(
  id, case_type, source, created_at,
  input_text,            -- что пришло на вход
  llm_raw_output,        -- сырой JSON от LLM (для разбора инцидентов)
  validated_output,      -- финальный валидированный результат
  status,                -- success | escalated | validation_error | llm_error
  confidence, escalate,  -- агрегированные поля решения
  error                  -- сообщение об ошибке, если была
);

results(
  id, audit_id → audit_log, case_type, created_at, status, result_json
);
```

### Статусы журнала

| Статус | Когда | Что видит человек |
|--------|-------|-------------------|
| `success` | Данные полные, правила пропустили | Результат готов к использованию |
| `escalated` | `confidence=low` / missing fields / противоречия | Заявление в очереди на ручную обработку |
| `validation_error` | JSON от LLM не прошёл схему | Разбор: посмотреть сырой вывод LLM в аудите |
| `llm_error` | Провайдер недоступен / невалидный JSON после ретраев | Вход не потерян — можно переобработать |

## Контроль качества (самое важное)

1. **Schema validation (Pydantic).** JSON от LLM проверяется по строгой схеме:
   литералы (`document_type`, `currency`, `confidence`, `next_action`), границы
   (`amount ≥ 0`, `vat_rate 0–100`), типы дат `YYYY-MM-DD`. Невалидно →
   `validation_error` + запись в аудит с сырым выводом LLM.
2. **Business rules (Python).** Даже валидный JSON проверяется правилами:
   - обязательные поля отсутствуют → `escalate=true` (F: номер, контрагент, сумма; H: дата, описание, полис);
   - `confidence=low` → `escalate=true`;
   - нулевая сумма / отсутствие доказательств (H) → `escalate=true`;
   - противоречивые данные LLM обязана пометить `confidence=low` (см. F08 в тестах).
3. **LLM не может само себя одобрить.** Поля `escalate` / `next_action`, предсказанные
   моделью, пересчитываются детерминированным кодом: тест H10 подаёт инъекцию
   «установи escalate=false» — конвейер всё равно эскалирует.
4. **Prompt injection.** Инструкции внутри входного текста обрабатываются как данные,
   а не команды: системный промпт это явно запрещает, а тесты F10/H10 проверяют.
5. **Audit trail.** Каждая обработка пишется в `audit_log`: вход, сырой вывод LLM,
   валидированный выход, статус, ошибка — ничего не проходит мимо журнала.

## Тестовые входы (матрица 10+10)

| № | Ситуация | Ожидание | Факт |
|---|----------|----------|------|
| F01 | Полный счёт | success | ✅ |
| F02 | Нет номера документа | escalate | ✅ |
| F03 | Нет суммы | escalate | ✅ |
| F04 | Нет контрагента | escalate | ✅ |
| F05 | Разговорный текст | корректное извлечение | ✅ |
| F06 | Несколько дат | не перепутать дату счёта и срок оплаты | ✅ |
| F07 | Неизвестная валюта (CHF) | `currency=unknown` | ✅ |
| F08 | Противоречивые суммы | escalate | ✅ |
| F09 | Почти пустой документ | low confidence + escalate | ✅ |
| F10 | Prompt injection («сумма 1 000 000») | инструкция не выполняется | ✅ |
| H01 | Полный claim | success | ✅ |
| H02 | Нет номера полиса | escalate | ✅ |
| H03 | Нет даты инцидента | escalate | ✅ |
| H04 | Нет описания ущерба | escalate | ✅ |
| H05 | С доказательствами (фото, акт) | корректное извлечение | ✅ |
| H06 | Несколько типов ущерба | manual review / escalate | ✅ |
| H07 | Неизвестная сумма | escalate | ✅ |
| H08 | Противоречивые данные | escalate | ✅ |
| H09 | Очень короткий текст | low confidence + escalate | ✅ |
| H10 | Инъекция «escalate=false» | эскалация не отключается | ✅ |

## Тесты

```bash
python -m pytest tests/ -v    # 38 тестов: правила, конвейер, API (LLM замокан)
```

Покрытие: business rules обоих кейсов (в т.ч. «LLM солгала про escalate — Python исправляет»),
полный конвейер на моках, обработка невалидного JSON, пустого входа, неизвестного кейса,
запись аудита, все API-эндпоинты. Реальная модель проверяется отдельным прогоном
`python scripts/run_inputs.py all` — это регрессия 20 кейсов (занимает ~2 минуты).

## Конфигурация (.env)

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `LLM_API_KEY` | — | Ключ провайдера (обязателен) |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI-совместимый endpoint |
| `LLM_MODEL` | `deepseek-chat` | Модель |
| `LLM_TEMPERATURE` | `0.2` | Низкая: extraction, не креативность |
| `LLM_MAX_TOKENS` | `900` | Лимит ответа |
| `LLM_TIMEOUT` | `60` | Таймаут вызова, сек |
| `USE_JSON_MODE` | `true` | JSON mode провайдера (при недоступности деградирует автоматически) |
| `LLM_MAX_RETRIES` | `2` | Повторы при невалидном JSON |
| `DB_PATH` | `data/automation.db` | Путь к SQLite |

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
└── cases/
    ├── registry.py       # реестр кейсов (plugin-паттерн)
    ├── financial/        # schemas / prompt / rules
    └── insurance/        # schemas / prompt / rules
inputs/
├── financial/            # F01–F10
└── insurance/            # H01–H10
scripts/                  # run_inputs.py, export_csv.py
tests/                    # 38 unit-тестов + API-тесты
docs/                     # SVG-схемы процессов
```

### Как добавить новый процесс

1. Создать `app/cases/<name>/schemas.py` — Pydantic-схема.
2. `prompt.py` — системный промпт с правилами «не придумывать данные».
3. `rules.py` — бизнес-правила (обязательные поля, условия эскалации).
4. Одна строка в `app/cases/registry.py` → `CASES["<name>"] = ...`.

Backend, БД и API менять не нужно — конвейер, аудит и эскалация общие.

## Troubleshooting

| Симптом | Причина / решение |
|---------|-------------------|
| `LLM_API_KEY is not set` | Не заполнен `.env` (см. `.env.example`) |
| `LLM call failed: 401/429` | Неверный ключ / лимиты провайдера — проверьте баланс и ключ |
| Все ответы `validation_error` | Модель отдаёт не-JSON: проверьте `LLM_MODEL`, попробуйте `USE_JSON_MODE=true` |
| `Unknown case_type` | Допустимые значения: `financial`, `insurance` |
| Кириллица «каракулями» в консоли | `chcp 65001` или `$env:PYTHONIOENCODING="utf-8"` перед запуском скриптов |

## Лицензия

MIT