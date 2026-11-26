# VIDEO COMBINE AI — Technical Risks and Missing Components

| Поле | Значення |
|------|----------|
| Статус | **DRAFT — очікує схвалення** |
| Версія | 0.1.0 |
| База | Інспекція репозиторію 2026-11-26 (2306 tracked файлів) |

---

## 1. Технічні ризики

| # | Риск | Імовірність | Вплив | Мітигація |
|---|------|-------------|-------|-----------|
| R-01 | Рефакторинг `backlot/server.py` зламає SSE/борд | середня | високий | Новий router поруч, старі маршрути лишаються, регресійні тести Backlot |
| R-02 | Міграція JSON-checkpoint → SQLite втратить стан проєкту | середня | високий | `compat.py` конвертує, вихідні JSON не видаляються, тест на фікстурах |
| R-03 | Конфлікт React 18 (Remotion) і React 19 (dashboard) | висока | середній | Два окремі `package.json`, жодного спільного node_modules |
| R-04 | Немає frontend-тестів у репозиторії | факт | середній | Vitest + Playwright додаються в Phase 1 |
| R-05 | Немає Docker/compose/CD | факт | середній | Local-профіль працює без Docker; compose додається наприкінці Phase 1 |
| R-06 | Celery/Redis відсутні, а черга потрібна | факт | середній | `Runner` Protocol; LocalRunner за замовчуванням, Celery у Phase 9 |
| R-07 | Відсутнє GPU на стенді | факт | високий для GPU-фіч | GPU-рушії лише каталог; keyless CPU-ядро не залежить від них |
| R-08 | Мережева нестабільність (loc.gov 403, Cloudflare 1010) | висока | середній | Дефолт Wikimedia/NASA/Archive.org, `--network-check`, UA-заголовок, фолбеки |
| R-09 | Piper/MediaPipe потребують ASCII-шляхів на Windows | факт | середній | Кеші в `C:/omtest/...`, `ESPEAK_DATA_PATH`, `OM_MEDIAPIPE_MODEL` |
| R-10 | 1583 файли скілів без версійного реєстру | факт | високий | Реєстр поверх; нові скіли з префіксом `studio/`; версії в checkpoint |
| R-11 | Orchestrator resume з кількома паралельними гілками | середня | високий | ідемпотентність за `input_hash`, версії агентів, `attempt` в БД |
| R-12 | Quality-гейти без еталону (ASR/LUFS/чорні кадри) | середня | високий | Фіксовані пороги + replay harness (`tests/eval/`), людина-затверджувач |
| R-13 | Випадкові платні виклики | низька | критичний | `BudgetPolicy=keyless`, redaction, socket-guard у тестах, opt-in |
| R-14 | Формат editable timeline не визначений | висока | середній | Визначити JSON-схему в Phase 5, спиратись на 20 наявних схем |
| R-15 | Формат шарів мініатюри не визначений | висока | середній | `thumbnail_layers.data` JSON (див. 06), валідація в Phase 7 |
| R-16 | Повний `make test` ~10.5 хв | факт | середній | Розділити `test-studio`/`test-contracts`, CI parallel, нічні повні прогони |
| R-17 | Брендинг: репозиторій/package досі `openmontage` | факт | низький | Поетапно: docs → studio package → setup.py, без злому існуючих імпортів |
| R-18 | Платна/заборонена ліцензія вихідного коду конкурентів | середня | критичний | `reference-only`, README-only для GPL/AGPL/пропрієтарних, жодного копіювання |

## 2. Відсутні компоненти (gap list)

| Компонент | Стан сьогодні | Потрібно | Фаза |
|-----------|---------------|----------|------|
| Central Orchestrator | лише опис у `AGENT_GUIDE.md` + `get_next_stage()` | DAG, стани, гейти, resume, retry | 9 (каркас у 1) |
| 9 агентів | markdown-директори, без Python-рантайму | класи + контракти + SKILL.md + тести | 2–9 |
| DB | немає SQL/CREATE TABLE/Alembic | SQLite→PostgreSQL, 20+ таблиць | 1 |
| Міграції | немає | Alembic + `0001_initial` | 1 |
| API CRUD | Backlot — observer, inline routes | APIRouters + Pydantic | 1 |
| Dashboard 11 розділів | 2 vanilla-сторінки | Next.js App | 1 |
| Frontend tests | немає | Vitest + Playwright | 1 |
| Render queue | `asyncio.Queue` лише для SSE | Celery/Redis (prod) | 9 |
| Thumbnail generator | тільки viewer-кеш `/thumb` | Agent, 16:9/9:16, шари | 7 |
| SEO generator | тільки промпти в `skills/` | Agent + UI + схеми | 8 |
| Clip Studio | немає модуля | rights gate, аналіз, рефрейм, атрибуція | 6 |
| Quality Agent | розкидані tools | єдиний гейт із звітом | 10 |
| Provenance ledger | поля в `Candidate`/`ClipRecord` | таблиці + `provenance.json` | 4 |
| Skill version registry | ручні версії в INDEX | `registry.yaml` + CI lint | 1/2 |
| Docker/compose/CD | немає | 3 файли + CI job | 1/10 |
| Mistral browser auth | немає коду | dev-only, після схвалення | окремо |

## 3. Що вже працює і не потребує перепису

- Keyless CLI: `python -m generator ...`, 5 демо, smoke-рендери.
- `tts_save`: edge → Piper `uk_UA` → Kokoro → SAPI → silence.
- Завантаження: yt-dlp → cobalt → gallery-dl; транскрипція faster-whisper;
  переклад SRT; прибирання пауз; заміна фону rembg/MediaPipe.
- `--repos` (143 записи) і `--network-check` із redaction проксі.
- Tool registry з idempotency/fallback/capability metadata; 20 JSON-схем.
- Backlot SSE-борд, `lib/checkpoint.py`, `lib/events.py`.
- Повний тестовий набір: **2938 passed, 18 skipped** (останній зелений прогон).

## 4. Рекомендація «найпростішої надійної архітектури»

1. **Не rewrite.** `studio/` обгортає `generator/`, `tools/`, `lib/`, `backlot/`.
2. **Одинrunner-інтерфейс** (`submit/status/cancel`) для local і Celery.
3. **Одна база** як джерело істини; JSON-артефакти — файли, у БД лише посилання.
4. **Один реєстр агентів** і **один реєстр скілів**; версії в checkpoint.
5. **Keyless за замовчуванням**, будь-яка хмара — явний opt-in із бюджетом.
6. **Вертикальний зріз у Phase 1–5** (тема → сценарій → голос → медіа → MP4),
   повна автоматизація — у Phase 9.
7. **Кожна фаза = тести + документація + коміт**; без green tests фаза не закривається.

## 5. Питання, що потребують рішення до Phase 1

1. Чи офіційно перейменовуємо пакет `openmontage` → `vidcombine` у `setup.py`
   зараз, чи після Phase 10? (рекомендація: після Phase 10)
2. Чи залишаємо Backlot UI як `/legacy` назавжди, чи видаляємо після Phase 1 GA?
   (рекомендація: залишати до Phase 10)
3. Чи потрібен Mistral browser auth у Phase 1? (рекомендація: ні, dev-only окремо)
4. Чи фіксуємо 1080p як дефолт для long-form і 720p для Shorts?
   (рекомендація: так, через `lib/media_profiles.py`)

---

*Наступний документ: `00-INDEX.md` (index + approval gate).*
