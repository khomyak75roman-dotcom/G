# VIDEO COMBINE AI — Technical Architecture

| Field | Value |
|---|---|
| Status | **DRAFT — awaiting approval** |
| Version | 1.0.0 |
| Scope | Documentation only; no runtime modules created in this phase |

---

## 1. Guiding decision

**Evolve the repository; do not rewrite it.** The existing `G` repository already contains a working keyless generator (14 modules), 237 tools with a capability registry, FastAPI Backlot with SSE, 20+ JSON schemas, checkpoint resume, an optional Remotion composer, and 2938 passing tests. VIDEO COMBINE AI adds a new `studio/` layer above those components rather than replacing them. See `docs/decisions/ADR-001-architecture.md`.

## 2. Layer model

```
┌───────────────────────────────────────────────────────────────┐
│ Presentation   dashboard/ (Next.js, planned)  |  backlot/ui  │
│                11 sections + StageRail + ApprovalGate        │
├───────────────────────────────────────────────────────────────┤
│ API            studio/api/ (planned FastAPI APIRouters)      │
│                extends backlot/server.py; /legacy aliases    │
├───────────────────────────────────────────────────────────────┤
│ Orchestration  studio/core/ (planned): DAG, gates, resume,   │
│                artifact store, event bridge, budget guard    │
├───────────────────────────────────────────────────────────────┤
│ Agents         11 registered agents (docs/agent-architecture)│
│                driven by versioned runtime skills            │
├───────────────────────────────────────────────────────────────┤
│ Skills         skills/ + skills/registry.yaml (planned)      │
│                dev-time Mistral Vibe skills are NOT runtime  │
├───────────────────────────────────────────────────────────────┤
│ Tools/existing generator/, tools/, lib/, schemas/, styles/   │
│                unchanged contract; reused via adapters       │
├───────────────────────────────────────────────────────────────┤
│ Infrastructure SQLite → PostgreSQL; LocalRunner → Celery;    │
│                FFmpeg default; Remotion optional             │
└───────────────────────────────────────────────────────────────┘
```

## 3. Current vs target repository mapping

| Concern | Today | Target |
|---|---|---|
| CLI | `python -m generator` | unchanged + `python -m studio serve` |
| Board | `backlot/server.py`, vanilla UI, SSE | extended by `studio/api`, UI kept at `/legacy` |
| State | `projects/*/checkpoint*.json` | SQLite (`studio.db`) + JSON artifact files |
| Tools | `tools/tool_registry.py` | reused; capability/lazy loading preserved |
| Agents | Markdown instructions only | registered Python classes with schemas |
| Skills | 1583 files in three directories | registry wrapper with SemVer, no bulk move |
| Render | FFmpeg via tools; Remotion optional | FFmpeg default; Remotion opt-in |
| Queue | in-process `asyncio.Queue` for SSE | LocalRunner → Celery/Redis in `production` |
| Frontend | none | `dashboard/` Next.js app (11 routes) |

## 4. Runtime flows

### 4.1 Original long-form video

```
Brief → Research → Script → Voice ┐
                         ↘ Media  ├→ Editing → Thumbnail → SEO → QC → Publish gate
```
Gates: brief approval (G1), script approval (G2), asset approval (G4), publish approval (G5).

### 4.2 Authorized source → clips

```
Source intake → Rights gate (G3) → Analysis → Clip → Commentary voice
             → Editing → Thumbnail → SEO → QC → Publish gate (G5)
```
The rights gate is hard-blocking: without a verified owner/license/permission record, analysis and extraction do not run.

## 5. Data model (summary)

- `projects`, `runs`, `run_stages`, `artifacts`, `approvals`, `events`, `media_sources`, `provenance`, `qc_reports`, `skill_versions`.
- JSON artifacts remain files under `projects/<id>/`; the DB stores paths, hashes, state, and links.
- Migration path: `lib/checkpoint.py` JSON → SQLite via a non-destructive compatibility importer.
- Full schema: `docs/architecture/06-DATABASE-SCHEMA.md` (Phase 0 package).

## 6. Execution profiles

| Profile | DB | Runner | Network | Use |
|---|---|---|---|---|
| `local` (default) | SQLite | in-process LocalRunner | optional | Developer laptop, sandbox, CI |
| `ci` | SQLite | in-process | disabled by socket guard | Automated tests |
| `production` | PostgreSQL | Celery + Redis | allowlisted | Server deployment (later phase) |

No profile requires an API key. Cloud adapters stay opt-in under `budget_policy: keyless`.

## 7. Interfaces

- **Agent protocol:** `submit(envelope) -> receipt`, `status(stage_id)`, `cancel(stage_id)`. All messages are schema-validated; see `docs/agent-architecture.md`.
- **Runner protocol:** the same three methods for LocalRunner and CeleryRunner; orchestrator is runner-agnostic.
- **Artifact store:** atomic write + SHA-256 + MIME + schema version; no partial files.
- **Events:** `lib/events.py` → `audit_log` → SSE to dashboard; secrets/proxy URLs are redacted.
- **Skills:** versioned instructions resolved by name from `skills/registry.yaml`; dev-time agent skills are a separate plane.

## 8. Security boundaries

- No credential in code or docs; `.env` is gitignored; values never printed.
- Subprocess calls use argument lists; uploads validated by MIME/size; paths confined to project workspace.
- Standard `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` / `NO_PROXY` are reported safely; no VPN/DPI/proxy-pool integration.
- See `docs/security.md` and `docs/copyright-and-licensing.md`.

## 9. What this phase does not create

No `studio/`, `dashboard/`, `migrations/`, Docker files, Celery config, or application modules. Phase 1 produces documentation only, on branch `feature/project-foundation`; implementation starts after approval.
