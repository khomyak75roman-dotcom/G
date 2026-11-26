# VIDEO COMBINE AI — Repository Structure

| Поле | Значення |
|------|----------|
| Статус | **DRAFT — очікує схвалення** |
| Версія | 0.1.0 |
| Репозиторій | `G` → `origin/main` |

Легенда: **[KEEP]** не змінюємо, **[EXTEND]** доповнюємо, **[NEW]** створюємо.

---

## 1. Цільове дерево (верхній рівень)

```
G/
├── AGENTS.md                       [EXTEND] project-wide rules + VIDEO COMBINE AI
├── AGENT_GUIDE.md                  [KEEP]   існуючий onboarding (734 LOC)
├── PROJECT_CONTEXT.md              [EXTEND] додати studio-шар
├── README.md                       [EXTEND] брендинг + новий quickstart
├── GENERATOR.md                    [KEEP]   keyless CLI
├── LICENSE                         [KEEP]
├── Makefile                        [EXTEND] studio-цілі, frontend-тести, docker
├── config.yaml                     [EXTEND] studio.profiles
├── .env.example                    [KEEP]   порожні змінні, без секретів
├── .python-version / .node-version [KEEP]   3.11 / 22.23.4
├── setup.py                        [EXTEND] package data: studio/skills/schemas
│
├── generator/                      [KEEP]   14 файлів, keyless CLI — не ламаємо
├── tools/                          [KEEP]   237 файлів; нові адаптери — окремо
├── lib/                            [EXTEND] checkpoint/events/paths лишаються
├── schemas/                        [EXTEND] нові схеми агентів/артефактів
├── skills/                         [EXTEND] + studio/*, + registry.yaml
├── .agents/skills/                 [KEEP]   997 файлів
├── .claude/skills/                 [KEEP]   428 файлів
├── pipeline_defs/                  [KEEP]
├── styles/                         [KEEP]
├── backlot/                        [EXTEND] API переноситься в studio/api, UI → legacy
├── remotion-composer/              [KEEP]   опційний render runtime
├── tests/                          [EXTEND] + studio/*, + contracts/*, + e2e/*
├── docs/                           [EXTEND] architecture/, runbooks
│
├── studio/                         [NEW] ядро VIDEO COMBINE AI
├── dashboard/                      [NEW] React/Next.js
├── migrations/                     [NEW] Alembic
├── deploy/                         [NEW] Docker/compose
└── projects/                       [KEEP] gitignored, артефакти/run'и
```

## 2. `studio/` — детально

```
studio/
├── __init__.py
├── config.py                  # Settings, BudgetPolicy, Profiles (Pydantic)
├── protocols.py               # Agent, Runner, ArtifactStore, Repository Protocols
├── core/
│   ├── orchestrator.py        # DAG, стани, retry, resume, approvals
│   ├── dag.py                 # топологічне сортування етапів
│   ├── checkpoint.py          # обгортка над lib/checkpoint.py
│   ├── artifact_store.py      # uri + sha256, atomic write
│   ├── provenance.py          # ліцензійний ліджер, attribution report
│   └── events.py              # місток lib/events.py → audit_log
├── agents/
│   ├── registry.py            # name → (class, version, skill_path, deps)
│   ├── base.py                # BaseAgent, AgentContext, AgentResult, Issue
│   ├── orchestrator_agent.py  # той самий core, але як агент-реєстрант
│   ├── research.py
│   ├── script.py
│   ├── voice.py
│   ├── media.py
│   ├── clip.py
│   ├── thumbnail.py
│   ├── seo.py
│   ├── editing.py
│   └── quality.py
├── api/
│   ├── app.py                 # create_app() = розширення backlot.server
│   ├── deps.py
│   ├── schemas.py             # Pydantic DTO
│   ├── errors.py
│   └── routes/
│       ├── projects.py
│       ├── runs.py
│       ├── media.py
│       ├── studio.py          # script/voice/clip/thumbnail/seo
│       ├── queue.py
│       └── events.py          # SSE (переїжджає з backlot)
├── db/
│   ├── base.py                # SQLAlchemy Core engine/session
│   ├── models.py              # Table-дефініції з 06-DATABASE-SCHEMA.md
│   ├── repositories.py        # CRUD для проєктів/запусків/артефактів
│   └── compat.py              # імпорт старих checkpoint.json → БД
├── runner/
│   ├── base.py                # Runner Protocol
│   ├── local.py               # thread pool, in-process
│   └── celery.py              # tasks.py, worker, Redis
├── tools_adapters/
│   ├── tts_save.py            # обгортка generator.speech
│   ├── media_keyless.py       # обгортка generator.media + stock_sources
│   ├── ffmpeg_timeline.py     # обгортка tools/video/video_compose
│   ├── whisper_srt.py         # generator.transcription
│   └── optional_cloud.py      # явний opt-in, без ключів у коді
└── skills/
    ├── registry.yaml          # версії/статуси/allowlist інструментів
    └── studio/                # SKILL.md для 9 агентів + methodology/editing
```

## 3. `dashboard/` — детально

```
dashboard/
├── package.json               # next 15, react 19, typescript, vitest, playwright
├── next.config.mjs
├── tsconfig.json
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                       # Library / Completed
│   │   ├── projects/new/page.tsx          # New Video Project
│   │   ├── projects/product/page.tsx      # Product Video Generator
│   │   ├── projects/[id]/page.tsx         # Overview + stage rail
│   │   ├── projects/[id]/script/page.tsx  # Script Editor
│   │   ├── projects/[id]/voice/page.tsx   # Voice Studio
│   │   ├── projects/[id]/media/page.tsx   # Media Library
│   │   ├── projects/[id]/clip/page.tsx    # YouTube Clip Studio
│   │   ├── projects/[id]/thumbnail/page.tsx
│   │   ├── projects/[id]/seo/page.tsx
│   │   ├── queue/page.tsx                 # Rendering Queue
│   │   └── settings/page.tsx
│   ├── components/
│   │   ├── StageRail.tsx
│   │   ├── ApprovalGate.tsx
│   │   ├── ProvenanceTable.tsx
│   │   ├── QualityReport.tsx
│   │   └── MediaCard.tsx
│   └── lib/api.ts                         # типізований клієнт (zod + openapi-typescript)
├── tests/
│   ├── unit/*.test.tsx
│   └── e2e/*.spec.ts
└── Dockerfile
```

## 4. `migrations/`, `deploy/`, `tests/`

```
migrations/
├── env.py                     # Alembic (SQLite/PostgreSQL)
└── versions/0001_initial.sql

deploy/
├── Dockerfile                 # Python 3.11 + ffmpeg
├── docker-compose.yml         # local: api + dashboard
├── docker-compose.prod.yml    # + redis + postgres + worker
└── nginx.conf

tests/studio/
├── test_orchestrator.py
├── test_resume.py
├── test_agents_contracts.py
├── test_artifact_store.py
├── test_provenance.py
├── test_api_*.py
├── test_quality_gate.py
└── e2e/test_keyless_smoke.py
```

## 5. Правила розміщення

1. Новий код іде в `studio/**`; старий `generator/**` і `tools/**` **не редагується**
   без окремого коміту з поясненням.
2. Адаптери до існуючих інструментів — у `studio/tools_adapters/`, щоб не
   створювати дублікатів ffmpeg-обгорток.
3. Скіли — у `skills/studio/**`; реєстр `skills/registry.yaml` вказує і на старі.
4. Усі нові pytest-тести — у `tests/studio/**`; контрактні — у `tests/contracts/`.
5. `projects/` залишається gitignored; у Git — лише код/схеми/тести/документи.

## 6. Сумісність

- `python -m generator ...` продовжує працювати без змін.
- `python -m backlot serve` продовжує показувати старий борд (`/legacy`).
- `python -m studio serve` — новий API (Phase 1).
- `make test` запускає і старі, і нові тести; розділення — `make test-studio`.

---

*Наступний документ: `07-DEPENDENCY-MAP.md`.*
