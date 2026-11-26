# VIDEO COMBINE AI — Technical Architecture

| Поле | Значення |
|------|----------|
| Статус | **DRAFT — очікує схвалення** |
| Версія | 0.1.0 |
| Вхідні дані | Фактична інспекція репозиторію `C:\Users\Роман\G` станом на 2026-11-26 |

---

## 1. Рекомендована архітектура (коротко)

**Еволюція, а не перепис.** Існуючий репозиторій уже має працююче keyless-ядро,
237 файлів tools, FastAPI-борд із SSE, 20 JSON-схем артефактів і checkpoint-resume.
Тому рекомендується:

```
React/Next.js dashboard  →  FastAPI (studio/api)  →  Orchestrator (studio/core)
                                                      ↓
                              9 Agents (studio/agents) → Tools (наявні) → FFmpeg
                                                      ↓
                               SQLite (studio.db) + Artifact Store (projects/)
                                                      ↓
                               Local Runner → Celery/Redis (профіль production)
```

Ключові рішення:

| Рішення | Обґрунтування |
|---------|---------------|
| Новий шар `studio/`, а не рефакторинг `generator/` | Keyless CLI вже зелений (2938 тестів); зламувати його заради нової фічі — ризик |
| Backlot FastAPI розширюється APIRouters замість нового сервера | Уже є health/SSE/static/media; додаємо CRUD і схеми, зберігаємо сумісність |
| SQLite як нове джерело істини, JSON-checkpoints лишаються сумісним кешем | Потрібні транзакції, гейти, provenance; але старі проєкти мають читатися |
| Next.js окремою програмою `dashboard/`, Backlot UI — fallback | Вимога React/Next.js; vanilla UI лишається робочим під час міграції |
| Local Runner у профілі `local`, Celery тільки в `production` | Стенд без Redis; розробка не блокується інфраструктурою |
| Remotion лишається опційним адаптером | Уже є `remotion-composer` (4.0.484); FFmpeg залишається дефолтом |

## 2. Фактичний стан (що вже є)

| Підсистема | Стан | Що використовуємо |
|------------|------|--------------------|
| `generator/` (14 файлів, ~1973 LOC) | Працює keyless | `script`, `speech` (`tts_save`), `media`, `render`, нові адаптери |
| `tools/` (237 файлів) | Працює | `tool_registry` (ідемпотентність, fallback, retry), 49 ffmpeg-викликів |
| `backlot/server.py` (381 LOC) | FastAPI, inline routes, SSE | Розширимо до `studio/api/*` routers |
| `backlot/state.py` (742 LOC) | Read-only board model | Залишаємо як read model для дашборду |
| `lib/checkpoint.py` (660 LOC) | Resume за етапом | База для `Orchestrator.resume()` |
| `lib/events.py` | JSONL події | Місток до audit_log |
| `schemas/artifacts/` (20 схем) | JSON Schema | Використовуємо як контракти артефактів |
| `lib/media_profiles.py` | 9 профілів, ffmpeg args | 1080p/720p, 16:9/9:16 вже реалізовані |
| `remotion-composer/` | React 18 + Remotion 4 | Опційний render engine |
| `.agents/skills`, `.claude/skills`, `skills/` | 1583 файли скілів | Реєстр поверх, без перепису |
| `tests/` (214 файлів, 1879 тестів) | `make test` зелений | База для нових контрактних тестів |
| CI `.github/workflows/ci.yml` | lint + test | Розширимо frontend-тестами й Docker build |
| **Відсутнє** | DB, Celery, Docker, Next.js dashboard, агенти, SEO, thumbnails, Clip Studio, QA-агент | Новий скоуп |

## 3. Шари та межі

### 3.1 Presentation — `dashboard/` (Next.js, нове)

- Unix-подібні маршрути для 11 розділів з PRD FR-30.
- SSE-підписка на `/api/project/{id}/events` (уже існує в Backlot).
- API-клієнт із типізованими DTO, згенерованими з Pydantic-схем.
- Існуючий `backlot/ui/*` (vanilla JS) лишається як `/legacy` до Phase 1 GA.

### 3.2 API — `studio/api/` (FastAPI)

Розширення `backlot.server.create_app()`:

```
studio/api/
├── deps.py          # Dependency Injection: Session, ArtifactStore, Orchestrator
├── schemas.py       # Pydantic: ProjectCreate, RunStatus, StageStatus, Approval...
├── routes/
│   ├── projects.py  # CRUD + resume/cancel
│   ├── runs.py      # start, status, stage logs, approve
│   ├── media.py     # library, licensing, upload
│   ├── studio.py    # clip, thumbnail, seo, script, voice
│   ├── queue.py     # render queue
│   └── events.py    # SSE (переїжджає з backlot/server.py)
└── errors.py        # unification: Problem+JSON
```

Правила: ніяких секретів у схемах; усі мутації — з CSRF/локальним токеном;
відповіді містять лише redacted proxy/ключові статуси (наявний `generator/network.py`).

### 3.3 Domain — `studio/core/` + `studio/agents/`

- `Orchestrator`: DAG, стани, гейти, retry, resume (див. `04-AGENT-ARCHITECTURE.md`).
- `AgentRegistry`, `SkillRegistry`, `BudgetPolicy`, `ArtifactStore`, `ProvenanceLedger`.
- Агенти викликають **наявні** tools через `tool_registry` — нових ffmpeg-обгорток не пишемо.

### 3.4 Execution — `studio/runner/`

| Профіль | Реалізація | Коли |
|---------|------------|------|
| `local` | `LocalRunner` (thread pool, in-process, SQLite lock) | За замовчуванням, розробка |
| `production` | `CeleryRunner` (Redis broker) | Масштабування, черга рендерів |

Обидва реалізують `Runner.submit(stage) -> job_id`, `status(job_id)`, `cancel(job_id)`.
Зміна профілю не змінює доменний код.

### 3.5 Persistence — `studio/db/`

- SQLAlchemy Core (не ORM) + Alembic, SQLite → PostgreSQL.
- Схема з `06-DATABASE-SCHEMA.md`.
- `projects/*/checkpoint*.json` читаються міграційним шаром `db/compat.py`
  і конвертуються в `runs/run_stages/artifacts` при першому відкритті.
- Artifact Store: файли під `projects/<id>/artifacts/`, у БД — uri + sha256.

### 3.6 Video engine — існуючі компоненти

| Потреба | Module |
|---------|--------|
| Рендер/переходи/оверлеї | `tools/video/video_compose.py` (`ffmpeg`/`remotion`/`hyperframes`) |
| Склеювання | `tools/video/video_stitch.py` |
| Рефреймінг | `tools/video/auto_reframe.py` |
| Субтитри | `tools/subtitle/subtitle_gen.py`, `generator/render.py::build_subtitles` |
| Аудіо/мікс | `tools/audio/audio_mixer.py`, `silence_cutter.py` |
| Візуальний QA | `tools/analysis/visual_qa.py`, `composition_validator.py` |
| Профілі | `lib/media_profiles.py` |
| Keyless CLI | `generator/cli.py` (залишається працювати окремо) |

## 4. Потоки

### 4.1 Створення та запуск

```
POST /api/projects        → projects row (status=draft)
POST /api/runs            → runs + run_stages (DAG), status=queued
Runner → Research → [G1] → Script → [G2] → (Voice ∥ Media ∥ Clip)
       → Editing → (Thumbnail ∥ SEO) → [G3 Quality] → Export
POST /api/runs/{id}/approve/{gate} → статус awaiting_approval → running
```

### 4.2 Resume

`GET /api/runs/{id}/resume` → для кожного етапу перевіряємо `status=ok` +
`output_hash` + наявність файлів; пропускаємо валідні, повторюємо інші
(`06-DATABASE-SCHEMA.md §4`). Механізм побудований на наявному
`lib/checkpoint.py::get_next_stage()`.

### 4.3 Провайдер/бюджет

`BudgetPolicy` (`keyless` за замовчуванням) перевіряється перед кожним tool-викликом.
Якщо tool має `capability` з платним провайдером і політика `keyless` —
обирається `fallback_tools` із `tool_registry`, або етап `skipped` із причиною.
Платні live-генерації вимагають явного `opt_in_cloud`.

## 5. Конфігурація

| Профіль | DB | Runner | Frontend | Хмара |
|---------|----|--------|----------|-----------|
| `local` | SQLite `studio.db` | in-process | Next.js dev server or Backlot UI | вимкнена |
| `ci` | SQLite in-memory | in-process | build + smoke | вимкнена |
| `production` | PostgreSQL | Redis+Celery | Next.js static | opt-in |

Змінні оточення — тільки імена в `.env.example`, значення не комітуються.
Стандартні proxy env поважаються; VPN/DPI/proxy-pool не активуються.

## 6. Розгортання (додати)

```
Dockerfile              # Python 3.11 + ffmpeg + studio API
dashboard/Dockerfile    # Node 22 build → static serve
docker-compose.yml      # local: api + dashboard (без Redis/Postgres)
docker-compose.prod.yml # prod: api + worker + redis + postgres
```

CI: `make install-dev && make lint && make test && npm test && docker build`.

## 7. Decision log (ADR-lite)

| # | Рішення | Альтернатива | Чому обрано |
|---|---------|--------------|-------------|
| ADR-01 | Новий `studio/` поверх існуючого коду | Повний rewrite | Зберігає 2938 зелених тестів і keyless-CLI |
| ADR-02 | FastAPI розширюється, не замінюється | Новий сервіс | SSE/health/media вже працюють |
| ADR-03 | SQLite + Alembic | Одразу PostgreSQL | Відповідність NFR; простий локальний старт |
| ADR-04 | Next.js + vanilla fallback | Тільки vanilla | Вимога стеку; плавна міграція |
| ADR-05 | Local Runner за замовчуванням | Celery скрізь | Стенд без Redis; менше рухомих частин |
| ADR-06 | FFmpeg дефолт, Remotion optional | Remotion дефолт | Вже працює в 49 місцях; GPU/Node важчі |
| ADR-07 | Скіли-реєстр поверх 3 каталогів | Консолідація вручну | 1583 файли — ризик зламати посилання |

## 8. Що явно не змінюється

- `generator/cli.py`, `speech.py`, `network.py` та `--repos` — публічні інтерфейси.
- Keyless smoke-шлях і дефолтні джерела (Wikimedia/NASA/Archive.org).
- Відмова від VPN/DPI/proxy-пулів і метаданійних трюків.
- Ліцензійний статус `reference-only` репозиторіїв.

---

*Наступний документ: `03-REPOSITORY-STRUCTURE.md`.*
