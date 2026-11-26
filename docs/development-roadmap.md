# VIDEO COMBINE AI — Development Roadmap

| Field | Value |
|---|---|
| Status | **DRAFT — awaiting approval** |
| Version | 1.0.0 |
| Current | Phase 1 — documentation and architecture (this branch) |

---

## 1. Phase map

| Phase | Name | Deliverables | Exit criteria |
|---|---|---|---|
| 0 | Assessment and architecture (complete) | Repository inspection, 12 docs in `docs/architecture/`, commits `d06af36`, `4966752` | Pushed to `origin/main` |
| **1** | **Foundation and documentation (current)** | 13 requested docs, 11 agents, skills catalogue, pipeline/tool evaluation, rights policy, installation guide, ADR-001, branch `feature/project-foundation` | Markdown validation green; no app modules; `main` untouched |
| 2 | Core runtime skeleton | `studio/` config/protocols, SQLite + Alembic, repositories, APIRouters on Backlot, LocalRunner, no-op stages honestly marked `skipped` | AC: project CRUD, 11 stages in DAG, resume, gates, redaction, regression CLI |
| 3 | Research + Script + Voice vertical slice | Three agents and skills, UA/EN script, Piper ladder, word timings | End-to-end `research.json` → `script.json` → `voice.wav` on CPU |
| 4 | Media + Editing long-form | Rights-aware media manifest, timeline v1, FFmpeg render 1080p | Reproducible MP4 from timeline; provenance complete |
| 5 | Clip Studio | Analysis, moment ranking, rights gate, clip extraction, commentary/narration/subtitles, 9:16 | User-owned source → N clips with attribution; blocked when rights unverified |
| 6 | Thumbnail + SEO | Layered thumbnails 16:9/9:16; metadata generator with attribution | QC-verifiable outputs; no deceptive metadata |
| 7 | Quality Control + publish gate | QC report, thresholds, G5 block, replay harness | Critical findings block publish; deterministic reports |
| 8 | Dashboard | Next.js 11 sections, typed API client, SSE stage rail, approval UI | Route smoke tests + component tests green |
| 9 | Production profile | PostgreSQL, Celery/Redis, Docker/compose, CI frontend jobs | `production` profile validated; `local` still default |
| 10 | Hardening and GA | Optional package rename, license decision, full eval suite, docs refresh | Full `make test` green; approval for rename/license |

## 2. Mapping to the earlier Phase 0 plan

`docs/architecture/10-PHASE1-PLAN.md` used "Phase 1" for what this roadmap calls **Phase 2** (core runtime skeleton). No contradiction in scope: this branch delivers documentation only, as requested. The earlier plan remains the implementation checklist for Phase 2.

## 3. Phase gating rules

- A phase is not done until implementation + tests + docs + commit are present.
- `make lint`, `make test` and frontend tests must be green; full suite currently takes ~10 minutes.
- No phase may introduce a mandatory key, paid call, VPN/DPI bypass, or metadata deception.
- Every phase adds or updates tests for the agents/skills it touches.

## 4. Next phase preview (Phase 2, after approval)

1. `studio/config.py`, `studio/protocols.py`, `studio/core/dag.py`, `studio/core/orchestrator.py`.
2. `migrations/0001_initial.sql` + SQLAlchemy models + repositories.
3. `studio/api/` routers/schemas/errors attached to `backlot.server.create_app()`; legacy routes preserved.
4. `studio/runner/local.py` with explicit `skipped/agent_not_implemented` stages.
5. Tests: project CRUD, DAG order, gate blocking, resume, redaction, CLI regression.

No application module is created in Phase 1.
