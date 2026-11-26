# VIDEO COMBINE AI — Architecture Package (Phase 0)

| Поле | Значення |
|------|----------|
| Статус | **DRAFT — ОЧІКУЄ СХВАЛЕННЯ АРХІТЕКТУРИ** |
| Версія | 0.1.0 |
| Дата | 2026-11-26 |
| Репозиторій | `G` (`origin/main`) |
| Мова | Українська |

---

## 1. Рекомендація одним абзацом

**Будувати новий шар `studio/` поверх уже працюючого keyless-ядра**, а не
переписувати репозиторій. Поточний `G` — це не порожній проєкт: 2306 tracked
файлів, 237 tools, FastAPI Backlot із SSE, 20 JSON-схем, checkpoint-resume,
Remotion-композер і 2938 зелених тестів. VIDEO COMBINE AI додає: SQLite +
Alembic, APIRouters і Pydantic поверх Backlot, Next.js дашборд (11 розділів),
дев'ять агентів із реєстром і версіями, Orchestrator із гейтами/resume,
LocalRunner → Celery, Thumbnail Agent, SEO Agent, Clip Studio і Quality Agent.
FFmpeg залишається дефолтним рендером; хмарні ключі — опційні; ніяких
VPN/DPI/proxy-пулів і метаданійних трюків.

## 2. Документи

| # | Файл | Зміст |
|---|------|-------|
| 00 | `00-INDEX.md` | Цей вказівник і gate схвалення |
| 01 | `01-PRD.md` | Повний Product Requirements Document (FR-01…FR-34, NFR-01…NFR-10) |
| 02 | `02-TECHNICAL-ARCHITECTURE.md` | Шари, інтерфейси, потоки, ADR-lite, фактичний стан |
| 03 | `03-REPOSITORY-STRUCTURE.md` | Цільове дерево `studio/`, `dashboard/`, `migrations/`, `deploy/` |
| 04 | `04-AGENT-ARCHITECTURE.md` | Orchestrator + 9 агентів, контракти, гейти, resume |
| 05 | `05-SKILLS-ARCHITECTURE.md` | Версійовані SKILL.md, реєстр поверх 1583 файлів |
| 06 | `06-DATABASE-SCHEMA.md` | SQLite/PostgreSQL DDL, provenance, checkpoint |
| 07 | `07-DEPENDENCY-MAP.md` | Наявні та нові залежності, профілі, lazy import |
| 08 | `08-ROADMAP.md` | Phase 0–10, acceptance criteria, commit-план |
| 09 | `09-SECURITY-COPYRIGHT.md` | Секрети, ліцензії, ToS, inject-захист, supply chain |
| 10 | `10-PHASE1-PLAN.md` | Детальний план першої фази + AC-1…AC-12 |
| 11 | `11-RISKS-AND-GAPS.md` | 18 ризиків, gap list, відкриті питання |

## 3. Що змінюється відносно OpenMontage

| Залишається | Додається |
|-------------|-----------|
| `generator/` CLI і keyless-шлях | `studio/` domain layer |
| `tools/` (237 файлів) і tool_registry | `studio/api` CRUD поверх Backlot |
| Backlot SSE + board | Next.js dashboard (11 розділів) |
| JSON-checkpoints | SQLite + Alembic + compat |
| Remotion (опційний) | LocalRunner → Celery (production) |
| 3 каталоги скілів | `skills/registry.yaml` + `studio/*` |
| 143-запис `--repos` | provenance ledger у БД |

## 4. Пропоновані зміни до `AGENTS.md` (застосувати після схвалення)

Поточний `AGENTS.md` — 9 рядків із обов'язковим посиланням на `AGENT_GUIDE.md`.
Пропонується доповнити (не замінити):

```markdown
# VIDEO COMBINE AI — project-wide instructions

- Platform name: VIDEO COMBINE AI (repo `G`, package bridge `studio/`).
- Source of truth: docs/architecture/*.md + AGENT_GUIDE.md + PROJECT_CONTEXT.md.
- Core mode is keyless: no API key is required for research, script, voice,
  media, editing, thumbnails, SEO or QC. Cloud adapters are explicit opt-in.
- Never hardcode or print credentials. Never activate VPN/DPI/proxy pools or
  manipulate metadata to hide authorship / bypass Content ID.
- New code goes to `studio/**`; do not edit `generator/**` or `tools/**`
  without a separate commit explaining why.
- Every phase requires implementation + tests + docs + commit; no phase is
  "done" until `make test` and frontend tests are green.
- Agents must declare input/output schemas, version, skill path, error policy
  and tests. Human approval gates are first-class states.
- Read-only repos (benchmarks, GPL/AGPL, proprietary) are never imported.
```

## 5. Approval gate

**Реалізація не починалась.** Перед Phase 1 потрібна одна відповідь:

> **Схвалюю архітектуру VIDEO COMBINE AI (docs/architecture/00-INDEX.md … 11-RISKS-AND-GAPS.md) і дозволяю Phase 1.**

Також бажано підтвердити чотири рішення з `11-RISKS-AND-GAPS.md §5`:
пакет лишається `openmontage` до Phase 10; Backlot UI лишається `/legacy`;
Mistral browser auth — dev-only, поза Phase 1; дефолт 1080p long / 720p Shorts.

Після схвалення:
1. застосувати зміни до `AGENTS.md`, `PROJECT_CONTEXT.md`, `README.md`;
2. виконати Phase 1 за `10-PHASE1-PLAN.md` із тестами й окремими комітами;
3. запушити в `origin/main`.

## 6. Стан репозиторію на момент написання

- Останній запушений коміт: `3774c75 Integrate keyless open-source backends into generator`.
- Некомічені зміни попередньої задачі: `GENERATOR.md`,
  `generator/external_repos.py`, `tests/test_generator_integrations.py`
  (розширення каталогу до 143 записів) — чекає на завершення повного `make test`.
- Ці документи створені як **DRAFT**, ще не запушені.

---

*Презентація архітектури завершено. Очікується рішення користувача.*
