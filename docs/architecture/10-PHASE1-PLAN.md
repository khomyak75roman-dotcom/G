# VIDEO COMBINE AI — Detailed Phase 1 Plan

| Поле | Значення |
|------|----------|
| Статус | **DRAFT — очікує схвалення** |
| Фаза | Phase 1 — Project foundation and dashboard |
| Тривалість (оцінка) | 1 ітерація; 6–8 робочих блоків |
| Вхід | Схвалена архітектура (Phase 0) |
| Вихід | Працюючий каркас із 11 розділами, API, SQLite, локальний runner |

---

## 1. Що саме будується

### 1.1 Конфігурація та брендинг

- `config.yaml` → додати блок `studio:` з профілями `local`/`ci`/`production`,
  `artifact_root`, `budget_policy: keyless`, `render_profile: 1080p`.
- `studio/config.py` — Pydantic `StudioSettings`, `BudgetPolicy`, `Profile`.
- `AGENTS.md` — додати project-wide правила VIDEO COMBINE AI (наявний 9-рядковий
  вказівник на `AGENT_GUIDE.md` **не видаляємо**).
- `PROJECT_CONTEXT.md` — додати шар `studio/` і нову назву проєкту.
- `README.md` — новий quickstart `python -m studio serve` + `npm run dev`
  поряд із старим keyless-шляхом. `GENERATOR.md` не змінюємо.

### 1.2 База даних

- `requirements-studio.txt`: `sqlalchemy>=2.0`, `alembic>=1.13`,
  `python-multipart>=0.0.9`.
- `migrations/env.py`, `migrations/versions/0001_initial.sql` — усі таблиці з
  `06-DATABASE-SCHEMA.md`.
- `studio/db/base.py` — SQLAlchemy Core engine (`sqlite:///studio.db`), session.
- `studio/db/models.py` — Table-оголошення.
- `studio/db/repositories.py` — `ProjectRepo`, `RunRepo`, `StageRepo`,
  `ArtifactRepo`, `ApprovalRepo`.
- `studio/db/compat.py` — читання старих `projects/*/checkpoint*.json` і
  конвертація в `runs/run_stages/artifacts` при першому відкритті.
- `Makefile`: `migrate`, `db-init` цілі.

### 1.3 API (розширення Backlot)

- `studio/api/app.py` — `create_app()` викликає наявний `backlot.server.create_app()`
  і додає нові `APIRouter`-и; старі маршрути лишаються на `/legacy/*` аліасах.
- `studio/api/schemas.py` — `ProjectCreate`, `ProjectOut`, `RunCreate`,
  `RunOut`, `StageOut`, `ApprovalIn`, `Problem`, `HealthOut`.
- Маршрути:
  - `POST /api/studio/projects`, `GET /api/studio/projects`,
    `GET/PATCH/DELETE /api/studio/projects/{id}`
  - `POST /api/studio/runs`, `GET /api/studio/runs/{id}`,
    `POST /api/studio/runs/{id}/resume`, `/cancel`,
    `POST /api/studio/runs/{id}/approve/{gate}`
  - `GET /api/studio/runs/{id}/stages`, `/events` (SSE), `/artifacts`
  - `POST /api/studio/media/upload` (ліцензійні поля обов'язкові)
  - `GET /api/studio/health`
- `studio/api/errors.py` — Problem+JSON, ключі/проксі redaction.
- `studio/api/deps.py` — DI для Session/Store/Orchestrator.

### 1.4 Orchestrator-каркас (без агентів)

- `studio/protocols.py` — `Agent`, `Runner`, `ArtifactStore`, `Repository`.
- `studio/core/dag.py` — топологічне сортування 9 етапів + гейтів.
- `studio/core/orchestrator.py` — створює `runs`/`run_stages`, керує станами
  `pending → running → ok|failed|awaiting_approval`, `resume()`, `approve()`.
- `studio/runner/local.py` — in-process black-box:`submit/status/cancel`;
  для Phase 1 виконує **no-op stage** з записом checkpoint — реальні агенти
  з'являться в Phase 2+.
- `studio/core/artifact_store.py` — atomic write + sha256.
- `studio/core/events.py` — місток `lib/events.py` → `audit_log`.

> Важливо: Phase 1 **не** імітує генерацію контенту. No-op етапи чесно
> позначаються `skipped` із причиною `agent_not_implemented`.

### 1.5 Dashboard (Next.js)

- `dashboard/package.json` (next ^15, react ^19, typescript ^5.6,
  @tanstack/react-query ^5, zod ^3.23, vitest ^2.1, @playwright/test ^1.48).
- 11 маршрутів з `03-REPOSITORY-STRUCTURE.md`; спільний `AppShell` із навігацією.
- `StageRail.tsx` — статуси етапів із SSE; `ApprovalGate.tsx` — кнопки
  Approve/Reject/Edit (у Phase 1 — реальний виклик API, без контентних дій).
- `ProvenanceTable.tsx`, `QualityReport.tsx`, `MediaCard.tsx` — каркаси з
  типізованими даними (порожні стани з чесними повідомленнями).
- `lib/api.ts` — типізований клієнт, згенерований з OpenAPI (`openapi-typescript`).
- Vitest unit-тести для компонентів + Playwright smoke для 11 маршрутів.

### 1.6 Docker таMake

- `deploy/Dockerfile` (Python 3.11 + ffmpeg), `dashboard/Dockerfile`,
  `deploy/docker-compose.yml` (api + dashboard, без Redis/Postgres).
- `Makefile`: `studio-serve`, `dashboard-dev`, `test-studio`, `test-frontend`,
  `docker-up`.

### 1.7 Документація

- `docs/runbooks/phase1.md` — запуск локально/Docker,міграції, відновлення.
- `docs/api/openapi.md` — довідка по нових маршрутах.
- Оновлення `AGENTS.md`, `PROJECT_CONTEXT.md`, `README.md`.

## 2. Порядок виконання (залежності)

```
1. config + AGENTS.md + requirements-studio.txt
2. DB models + Alembic migration + repositories + compat
3. protocols + dag + orchestrator + local runner + artifact store
4. API routers/schemas/errors + підключення до Backlot
5. Dashboard: shell → 11 route → StageRail/ApprovalGate → api client
6. Frontend tests + backend tests + e2e smoke
7. Docker/compose + Make targets
8. Docs + final make test
```

Кожен крок — окремий commit; фаза закривається фінальним
`feat(phase1): foundation and dashboard`.

## 3. Acceptance criteria (перевіряється перед «done»)

| # | Критерій | Як перевірити |
|---|----------|---------------|
| AC-1 | 11 розділів дашборду відкриваються без 404 | Playwright smoke |
| AC-2 | `POST /api/studio/projects` створює рядок у SQLite | pytest API test |
| AC-3 | `POST /api/studio/runs` створює 9 `run_stages` у DAG-порядку | pytest |
| AC-4 | Resume пропускає `ok`-етапи з валідним sha256 | pytest `test_resume.py` |
| AC-5 | Гейт блокує етап до `approve` | pytest `test_gate.py` |
| AC-6 | Старі `checkpoint.json` імпортуються в БД | pytest `test_compat.py` |
| AC-7 | SSE доставляє зміни стану етапу | pytest + browser smoke |
| AC-8 | Proxy/ключі не з'являються у відповідях/логах | pytest redaction |
| AC-9 | `python -m generator --dry-run ...` працює як раніше | regression smoke |
| AC-10 | `make test` і `npm test` зелені; `docker compose config` валідний | CI |
| AC-11 | Жодного secret у diff; `git diff --check` чистий | gitleaks + diff |
| AC-12 | Документація Phase 1 є й описує реальну поведінку | review |

## 4. Явно відкладено (не в Phase 1)

- Реальні агенти Research/Script/Voice/Media/Clip/Thumbnail/SEO/Editing/Quality.
- Celery/Redis і PostgreSQL (профілі `production`).
- Генерація мініатюр, SEO, Clip Studio,Remotion як дефолт.
- Mistral browser auth (dev-only, окреме схвалення).
- Будь-які платні live-виклики.

## 5. Ризики Phase 1 та мітигації

| Риск | Мітигація |
|------|-----------|
| Зламати Backlot SSE | Новий router додається поруч; старі маршрути лишаються |
| Конфлікт React 18 (Remotion) і React 19 (dashboard) | Окремі `package.json` і node_modules |
| Відсутній Docker на стенді | Спочатку `local` профіль; Docker — останнім кроком |
| Міграція старих checkpoint | `compat.py` не видаляє вихідні JSON |
| No-op етапи можна сприйняти як «реалізовано» | Чесний статус `skipped` + причина в UI й звіті |

---

*Наступний документ: `11-RISKS-AND-GAPS.md`, потім `00-INDEX.md`.*
