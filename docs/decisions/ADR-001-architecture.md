# ADR-001 — Architecture for VIDEO COMBINE AI

| Field | Value |
|---|---|
| Status | **Proposed — awaiting approval** |
| Date | 2026-11-26 |
| Deciders | Project owner; implementation agent |
| Related | `docs/architecture.md`, `PRD.md`, `docs/architecture/00-INDEX.md` |

---

## 1. Context

The repository already contains 2300+ tracked files: a working keyless generator, 237 tools with a capability registry, FastAPI Backlot with SSE, 20+ JSON schemas, checkpoint resume, an optional Remotion composer, and 2938 passing tests. The new product must add an autonomous 11-agent YouTube studio without breaking that baseline. The development sandbox has restricted internet, no package installation rights, no GPU, and no Docker/Redis/PostgreSQL.

## 2. Decision

1. **Evolve, do not rewrite.** Add a `studio/` layer above `generator/`, `tools/`, `lib/`, and `backlot/`; preserve the keyless CLI and Backlot UI (`/legacy`).
2. **Keyless-first.** Tier 1 (offline) and Tier 2 (local models/media) are the default; browser auth is development-only; cloud APIs are explicit opt-in with a budget guard. No credential in code or docs.
3. **FFmpeg is the core renderer.** Remotion is optional for motion graphics; MoviePy is not a core dependency.
4. **SQLite + Alembic first.** JSON checkpoints are imported non-destructively; PostgreSQL enters only in the `production` profile.
5. **One runner protocol.** `submit/status/cancel` for LocalRunner now, Celery/Redis later.
6. **11 registered agents** with versioned schemas, gates, and resume — orchestration stays outside agents.
7. **Two skill planes.** Mistral Vibe/native coding-agent skills guide development; runtime skills live in `skills/` with a registry and are independent of the coding harness.
8. **Rights and metadata integrity.** Rights gate G3 is hard-blocking; metadata must describe actual new editorial content and never conceal sources or evade detection.
9. **Documentation-only Phase 1.** This branch creates docs and architecture; no application modules.

## 3. Alternatives considered

| Alternative | Why rejected |
|---|---|
| Full rewrite of the repository | Discards working keyless core and 2938 tests; high regression risk |
| Cloud-first agent architecture | Violates the no-manual-key requirement; blocks offline operation |
| Celery/Redis/PostgreSQL from day one | Services unavailable in sandbox; complicates local/CI development |
| Remotion as default renderer | Needs Node and JS toolchain; FFmpeg already covers required output |
| Consolidating 1583 skill files | Large churn with no functional gain; registry wrapper is safer |
| Selecting a new license now | Owner approval required; existing `LICENSE` retained |

## 4. Consequences

**Positive**

- Existing commands and tests keep working during migration.
- Clear tier labels prevent false claims about credential-free cloud features.
- Rights gate and redaction are designed in, not retrofitted.

**Negative / trade-offs**

- Some duplication between old and new docs during the transition; new docs declare precedence for the agent roster.
- Two frontend stacks (vanilla Backlot and planned Next.js) coexist until GA.
- Package name stays `openmontage` until a later decision.
- No production queue/DB in this environment; validation happens on a separate machine.

## 5. Approval gate

This ADR is **Proposed**. Implementation of Phase 2 starts only after explicit approval of this document set. Open decisions are listed in `PRD.md` §9 (package rename, legacy UI, Mistral auth, defaults, license).
