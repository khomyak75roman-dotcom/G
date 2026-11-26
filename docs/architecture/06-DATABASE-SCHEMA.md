# VIDEO COMBINE AI — Database Schema

| Поле | Значення |
|------|----------|
| Статус | **DRAFT — очікує схвалення** |
| Версія | 0.1.0 |
| Двигун | SQLite (профіль `local`) → PostgreSQL (профіль `production`) |

---

## 1. Принципи

- Одна схема для SQLite та PostgreSQL: `TEXT` замість `UUID`/`ENUM`, `CHECK`
  замість enum-типів, `NUMERIC` для дробів.
- JSON зберігається в `TEXT` (SQLite JSON1 / PostgreSQL `jsonb`).
- Усі таблиці мають `created_at`, `updated_at` (UTC, ISO-8601).
- Артефакти зберігаються на дисі/об'єктному сховищі; у БД — лише посилання
  і `sha256`.
- Міграції — версійовані SQL-файли `migrations/NNNN_name.sql` + таблиця
  `schema_migrations`.
- Жодних секретів у БД: ключі лише в env/секретному менеджері.

## 2. Діаграма (логічна)

```
projects ──< runs ──< run_stages ──< artifacts
    │           │            └──< agent_runs
    │           └──< approvals
    ├──< scripts ──< scenes
    ├──< media_assets ──< media_selections
    ├──< clip_sources ──< clip_segments
    ├──< thumbnails ──< thumbnail_layers
    ├──< seo_metadata
    ├──< render_jobs
    └──< quality_reports ──< quality_checks

skill_versions, memory_vault, audit_log, settings — довідкові/системні
```

## 3. DDL (SQLite-сумісний)

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    applied_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id            TEXT PRIMARY KEY,              -- UUID
    title         TEXT NOT NULL,
    topic         TEXT,
    source_url    TEXT,
    source_kind   TEXT NOT NULL DEFAULT 'topic'
                  CHECK (source_kind IN ('topic','url','text','image','video','authorized_source')),
    language      TEXT NOT NULL CHECK (language IN ('uk','en')),
    format        TEXT NOT NULL CHECK (format IN ('long','short')),
    aspect        TEXT NOT NULL CHECK (aspect IN ('16:9','9:16')),
    profile       TEXT NOT NULL CHECK (profile IN ('1080p','720p')),
    status        TEXT NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft','running','awaiting_approval','done','failed','archived')),
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status, updated_at);

CREATE TABLE IF NOT EXISTS runs (
    id            TEXT PRIMARY KEY,
    project_id    TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    attempt       INTEGER NOT NULL DEFAULT 1,
    status        TEXT NOT NULL CHECK (status IN ('queued','running','paused','done','failed','cancelled')),
    budget_policy TEXT NOT NULL DEFAULT 'keyless'
                  CHECK (budget_policy IN ('keyless','opt_in_cloud','gpu_local')),
    current_stage TEXT,
    input_hash    TEXT NOT NULL,
    started_at    TEXT,
    finished_at   TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    UNIQUE(project_id, attempt)
);

CREATE TABLE IF NOT EXISTS run_stages (
    id            TEXT PRIMARY KEY,
    run_id        TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    stage_key     TEXT NOT NULL,                  -- research|script|voice|media|clip|editing|thumbnail|seo|quality
    agent_name    TEXT NOT NULL,
    agent_version TEXT NOT NULL,
    skill_version TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('pending','running','ok','failed','skipped','awaiting_approval')),
    input_hash    TEXT NOT NULL,
    output_hash   TEXT,
    error_code    TEXT,
    error_detail  TEXT,
    attempt       INTEGER NOT NULL DEFAULT 1,
    started_at    TEXT,
    finished_at   TEXT,
    checkpoint    TEXT NOT NULL DEFAULT '{}',     -- JSON: відновлення з THIS stage
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    UNIQUE(run_id, stage_key, attempt)
);
CREATE INDEX IF NOT EXISTS idx_stages_run ON run_stages(run_id, stage_key);

CREATE TABLE IF NOT EXISTS artifacts (
    id            TEXT PRIMARY KEY,
    stage_id      TEXT NOT NULL REFERENCES run_stages(id) ON DELETE CASCADE,
    key           TEXT NOT NULL,                  -- script.json, narration.mp3, final.mp4
    kind          TEXT NOT NULL CHECK (kind IN ('json','text','audio','video','image','srt','project','report')),
    uri           TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    bytes         INTEGER NOT NULL DEFAULT 0,
    mime_type     TEXT,
    created_at    TEXT NOT NULL,
    UNIQUE(stage_id, key)
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id            TEXT PRIMARY KEY,
    stage_id      TEXT NOT NULL REFERENCES run_stages(id) ON DELETE CASCADE,
    agent_name    TEXT NOT NULL,
    version       TEXT NOT NULL,
    status        TEXT NOT NULL,
    input_json    TEXT NOT NULL,
    output_json   TEXT,
    reasoning     TEXT,                           -- короткий summary, не chain-of-thought
    issues_json   TEXT NOT NULL DEFAULT '[]',
    metrics_json  TEXT NOT NULL DEFAULT '{}',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id            TEXT PRIMARY KEY,
    stage_id      TEXT NOT NULL REFERENCES run_stages(id) ON DELETE CASCADE,
    gate_key      TEXT NOT NULL,                  -- G1_facts, G2_script, G4_thumbnail, G5_seo, G6_quality
    status        TEXT NOT NULL CHECK (status IN ('pending','approved','rejected','edited')),
    decided_by    TEXT,
    decided_at    TEXT,
    note          TEXT,
    payload       TEXT,                           -- JSON: що саме затверджено/змінено
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scripts (
    id            TEXT PRIMARY KEY,
    stage_id      TEXT NOT NULL REFERENCES run_stages(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    hook          TEXT,
    body          TEXT NOT NULL,
    style         TEXT,
    duration_target REAL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenes (
    id            TEXT PRIMARY KEY,
    script_id     TEXT NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    idx           INTEGER NOT NULL,
    narration     TEXT,
    visual_intent TEXT,
    overlay_text  TEXT,
    mood          TEXT,
    transition_in TEXT,
    duration_sec  REAL NOT NULL DEFAULT 0,
    media_query   TEXT,
    UNIQUE(script_id, idx)
);

CREATE TABLE IF NOT EXISTS media_assets (
    id            TEXT PRIMARY KEY,
    project_id    TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    origin        TEXT NOT NULL CHECK (origin IN ('stock','user_upload','authorized_source','generated')),
    source_name   TEXT NOT NULL,                  -- wikimedia|nasa|archive_org|local|...
    source_url    TEXT,
    title         TEXT,
    author        TEXT,
    license       TEXT,
    license_url   TEXT,
    downloaded_at TEXT,
    sha256        TEXT,
    uri           TEXT NOT NULL,
    width         INTEGER,
    height        INTEGER,
    duration_sec  REAL,
    approved      INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_media_sha ON media_assets(sha256);

CREATE TABLE IF NOT EXISTS media_selections (
    id            TEXT PRIMARY KEY,
    scene_id      TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    asset_id      TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    relevance     REAL NOT NULL DEFAULT 0,
    reason        TEXT,
    created_at    TEXT NOT NULL,
    UNIQUE(scene_id, asset_id)
);

CREATE TABLE IF NOT EXISTS clip_sources (
    id            TEXT PRIMARY KEY,
    project_id    TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    uri           TEXT NOT NULL,
    title         TEXT,
    author        TEXT,
    source_url    TEXT,
    license       TEXT,
    rights_confirmed INTEGER NOT NULL DEFAULT 0,  -- користувач підтвердив право
    attribution   TEXT NOT NULL DEFAULT '{}',     -- JSON, обов'язковий у звіті
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clip_segments (
    id            TEXT PRIMARY KEY,
    source_id     TEXT NOT NULL REFERENCES clip_sources(id) ON DELETE CASCADE,
    idx           INTEGER NOT NULL,
    start_sec     REAL NOT NULL,
    end_sec       REAL NOT NULL,
    score         REAL,
    reframe       TEXT NOT NULL DEFAULT '{}',
    comment       TEXT,
    UNIQUE(source_id, idx)
);

CREATE TABLE IF NOT EXISTS thumbnails (
    id            TEXT PRIMARY KEY,
    stage_id      TEXT NOT NULL REFERENCES run_stages(id) ON DELETE CASCADE,
    variant       INTEGER NOT NULL,
    aspect        TEXT NOT NULL CHECK (aspect IN ('16:9','9:16')),
    uri           TEXT NOT NULL,
    selected      INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    UNIQUE(stage_id, variant, aspect)
);

CREATE TABLE IF NOT EXISTS thumbnail_layers (
    id            TEXT PRIMARY KEY,
    thumbnail_id  TEXT NOT NULL REFERENCES thumbnails(id) ON DELETE CASCADE,
    kind          TEXT NOT NULL CHECK (kind IN ('background','product','text','badge','shape')),
    z_index       INTEGER NOT NULL,
    data          TEXT NOT NULL                    -- JSON: текст/шрифт/позиція/стиль
);

CREATE TABLE IF NOT EXISTS seo_metadata (
    id            TEXT PRIMARY KEY,
    stage_id      TEXT NOT NULL REFERENCES run_stages(id) ON DELETE CASCADE,
    kind          TEXT NOT NULL CHECK (kind IN ('long','short')),
    language      TEXT NOT NULL CHECK (language IN ('uk','en')),
    title         TEXT NOT NULL,
    description   TEXT NOT NULL,
    tags          TEXT NOT NULL DEFAULT '[]',
    hashtags      TEXT NOT NULL DEFAULT '[]',
    keywords      TEXT NOT NULL DEFAULT '[]',
    pinned_comment TEXT,
    UNIQUE(stage_id, kind, language)
);

CREATE TABLE IF NOT EXISTS render_jobs (
    id            TEXT PRIMARY KEY,
    run_id        TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    timeline_uri  TEXT NOT NULL,
    output_uri    TEXT,
    profile       TEXT NOT NULL CHECK (profile IN ('1080p','720p')),
    aspect        TEXT NOT NULL CHECK (aspect IN ('16:9','9:16')),
    codec         TEXT NOT NULL DEFAULT 'h264',
    status        TEXT NOT NULL CHECK (status IN ('queued','running','done','failed','cancelled')),
    progress      REAL NOT NULL DEFAULT 0,
    log_uri       TEXT,
    worker_id     TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quality_reports (
    id            TEXT PRIMARY KEY,
    run_id        TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    passed        INTEGER NOT NULL,
    blocking_json TEXT NOT NULL DEFAULT '[]',
    summary       TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quality_checks (
    id            TEXT PRIMARY KEY,
    report_id     TEXT NOT NULL REFERENCES quality_reports(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,                  -- black_frame|lufs|asr_match|sync|attribution|profile|secrets
    status        TEXT NOT NULL CHECK (status IN ('pass','warn','fail')),
    detail        TEXT,
    value         TEXT
);

CREATE TABLE IF NOT EXISTS skill_versions (
    name          TEXT NOT NULL,
    version       TEXT NOT NULL,
    status        TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    applied_at    TEXT NOT NULL,
    PRIMARY KEY (name, version)
);

CREATE TABLE IF NOT EXISTS memory_vault (
    id            TEXT PRIMARY KEY,
    instinct      TEXT NOT NULL,
    source_run    TEXT REFERENCES runs(id) ON DELETE SET NULL,
    evidence      TEXT,
    confidence    REAL NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id            TEXT PRIMARY KEY,
    project_id    TEXT,
    run_id        TEXT,
    actor         TEXT NOT NULL,                  -- user|agent:research|system
    action        TEXT NOT NULL,
    detail        TEXT,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_log(run_id, created_at);

CREATE TABLE IF NOT EXISTS settings (
    key           TEXT PRIMARY KEY,
    value_json    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
```

## 4. Resume — як працює checkpoint

1. `run_stages.checkpoint` зберігає `{stage_key, input_hash, output_hash,
   artifacts: [...], agent_version, skill_version}` після кожного успішного етапу.
2. `resume(run_id)` читає етапи в порядку; якщо `status='ok'` і всі артефакти
   існують і мають збіжний `sha256` — етап пропускається.
3. `failed`/`awaiting_approval` повторюється з новим `attempt`; старі артефакти
   лишаються для аудиту (не перезаписуються).
4. Зміна `agent_version`/`skill_version` інвалідує етап — це захищає від
   «тихого» регресу після оновлення коду.

## 5. Міграція на PostgreSQL

| SQLite | PostgreSQL |
|--------|------------|
| `TEXT` UUID | `uuid` (опційно) |
| `TEXT` JSON | `jsonb` + GIN-індекси |
| `INTEGER` bool | `boolean` |
| `CHECK (... IN ...)` | enum-типи або check |
| `INTEGER PRIMARY KEY` | не використовується (усі ID — UUID) |

Міграції виконуються Alembic; схема вважається сумісною, якщо
`alembic upgrade head` проходить на обох двигунах у CI.

## 6. Обов'язкові індекси для черги

- `runs(status, updated_at)` — вибірка активних запусків.
- `render_jobs(status, created_at)` — диспетчеризація Celery.
- `run_stages(run_id, stage_key)` — resume.
- `audit_log(run_id, created_at)` — відлагодження.

---

*Наступний документ: `07-DEPENDENCY-MAP.md`.*
