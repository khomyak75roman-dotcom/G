# VIDEO COMBINE AI — Product Requirements Document

| Field | Value |
|---|---|
| Status | **DRAFT — awaiting approval** |
| Version | 1.0.0 |
| Phase | Phase 1 — technical foundation and architecture documentation |
| Date | 2026-11-26 |
| Supersedes in part | `docs/architecture/01-PRD.md` (agent roster extended from 9 to 11) |

---

## 1. Vision

An autonomous AI-powered YouTube production studio that turns a topic, a user-owned video, or an authorized source into a complete publish-ready package: script, voiceover, edited video, short-form clips, thumbnail, SEO metadata, and a quality-control report — with no manually entered API keys required for the core path.

## 2. Problem

Existing video tooling is fragmented: research, scripting, TTS, stock discovery, editing, captions, thumbnails, SEO, and QC live in separate tools with incompatible contracts. Manual pipelines are slow and hard to resume. Cloud-first products require credentials and paid calls for even a draft.

## 3. Target users

| User | Need |
|---|---|
| Solo Ukrainian/English creator | Long-form explainers and Shorts without a production team |
| Channel editor | Repurpose authorized/user-owned footage into clips with new commentary |
| Developer/operator | Extensible, testable, local-first studio with auditable provenance |

## 4. Capability tiers (critical requirement)

The product MUST NOT promise that all cloud AI capabilities work without credentials. Every feature is classified into exactly one tier:

| Tier | Name | Meaning | Examples | Key required? |
|---|---|---|---|---|
| 1 | **Fully offline** | Works with repository files, local FFmpeg, and local DB; no network at all | Project CRUD, timeline editing, FFmpeg cut/concat/reframe, subtitle burn-in, local QC checks, checkpoint resume, metadata authoring | No |
| 2 | **Local models / downloaded media** | Needs one-time download of model weights or media, then runs locally | Piper `uk_UA` TTS, Kokoro, faster-whisper ASR, rembg/U²-Net, MediaPipe selfie, Wikimedia/NASA/Archive.org stock, yt-dlp fetch of authorized URLs | No |
| 3 | **User authentication** | Needs an interactive login or account consent | Mistral browser auth (development only, where supported), YouTube OAuth for user-owned uploads/publishing, platform accounts | Yes, interactive — never stored in the repo |
| 4 | **Optional paid integrations** | Explicit opt-in with budget guard | FAL, ElevenLabs, OpenAI, Gemini, Replicate, other cloud providers | Yes, opt-in only |

Rules:

- Tier 1 is the default and must never regress.
- Tier 2 is advertised only after `preflight` confirms local assets are present.
- Tier 3 is never a precondition for Tier 1/2 features.
- Tier 4 is disabled unless the user explicitly enables it; no key is hardcoded, printed, or committed.
- The UI/CLI must display the active tier per feature before execution.

## 5. Functional requirements

### 5.1 Studio foundation

| ID | Requirement |
|---|---|
| FR-01 | Create, open, list, update, and delete video projects with persistent state. |
| FR-02 | Run a 11-agent DAG with explicit states and resumable checkpoints. |
| FR-03 | Enforce human approval gates at brief, script, rights, assets, and publish. |
| FR-04 | Store every artifact with SHA-256, MIME type, schema version, and provenance link. |

### 5.2 Research and script

| ID | Requirement |
|---|---|
| FR-05 | Gather grounded facts with source URLs and license/attribution metadata. |
| FR-06 | Produce structured scripts for Ukrainian and English with scene timing. |
| FR-07 | Support long-form (16:9, 1080p) and Shorts (9:16, 720p) profiles. |
| FR-08 | Export script text suitable for subtitle generation. |

### 5.3 Voice

| ID | Requirement |
|---|---|
| FR-09 | Synthesize Ukrainian and English narration using a keyless ladder: local Piper → Kokoro → SAPI → recorded silence. |
| FR-10 | Record per-word timings for caption alignment when the engine supports it. |
| FR-11 | Never require a cloud TTS key for a complete draft. |

### 5.4 Media and editing

| ID | Requirement |
|---|---|
| FR-12 | Discover media from open archives with verified license fields. |
| FR-13 | Accept user-supplied media with explicit rights declaration. |
| FR-14 | Detect scenes and rank interesting moments from authorized source video. |
| FR-15 | Assemble an editable timeline (JSON) and render with FFmpeg to H.264 MP4/AAC. |
| FR-16 | Support reframing 16:9 → 9:16 with crop/pad and optional background removal. |

### 5.5 Clip studio

| ID | Requirement |
|---|---|
| FR-17 | Ingest user-owned uploads and authorized URLs only. |
| FR-18 | Run a rights gate before any analysis or extraction. |
| FR-19 | Generate clips with original commentary, new narration, subtitles, and a new visual structure. |
| FR-20 | Describe the new editorial content accurately in metadata; never conceal the source. |

### 5.6 Thumbnail, SEO, QC

| ID | Requirement |
|---|---|
| FR-21 | Generate layered thumbnails in 16:9 and 9:16 from script and key frames. |
| FR-22 | Generate titles, descriptions, tags, chapters, and hashtags without deceptive claims. |
| FR-23 | Provide a QC report covering ASR accuracy, loudness, black frames, caption sync, rights completeness, and metadata accuracy. |
| FR-24 | Block publish when QC has critical findings or the rights gate is unresolved. |

### 5.7 Platform

| ID | Requirement |
|---|---|
| FR-25 | Expose a REST API and typed schemas for all studio operations. |
| FR-26 | Stream stage events to the dashboard via SSE. |
| FR-27 | Register agents and skills with versions; record versions in each run checkpoint. |
| FR-28 | Redact secrets and proxy credentials in all logs and API responses. |
| FR-29 | Provide `local` (SQLite/in-process) and `production` (PostgreSQL/Redis/Celery) profiles. |
| FR-30 | Keep the existing keyless CLI and Backlot board working as a fallback. |

## 6. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | Core path runs without network access after local assets are installed. |
| NFR-02 | No credential value appears in source, docs, CI logs, or API responses. |
| NFR-03 | Deterministic resume: identical `input_hash` + agent version yields identical stage output. |
| NFR-04 | All external calls are wrapped with timeout, retry, and explicit fallback. |
| NFR-05 | Subprocess invocations use argument lists, never shell string interpolation. |
| NFR-06 | Ukrainian and English are first-class in UI, schemas, and voice. |
| NFR-07 | H.264 MP4 + AAC output; 1080p long-form, 720p Shorts defaults. |
| NFR-08 | Edits are stored as data (timeline JSON), not baked-only renders. |
| NFR-09 | Python 3.11, pytest + Vitest + Playwright, `make lint`/`make test` green before a phase closes. |
| NFR-10 | Extensible via registered agents/skills; no hardcoded provider lists in runtime logic. |
| NFR-11 | Respect YouTube terms, copyright, and source attribution; no metadata deception. |
| NFR-12 | No VPN, DPI bypass, proxy-pool, or Telegram-transit integration. |

## 7. Explicit non-goals

- No mandatory paid API, no hardcoded key, no credential creation in this repository.
- No metadata manipulation to hide authorship, evade Content ID, or misdescribe content.
- No rewriting of the working `generator/`, `tools/`, `lib/`, or `backlot/` code in this phase.
- No application modules are implemented in Phase 1 — documentation and architecture only.
- No project license is selected without explicit approval; existing `LICENSE` is untouched.

## 8. Acceptance criteria for Phase 1

1. All 13 requested files exist, are non-empty, and pass Markdown/link validation.
2. All 11 agents have responsibilities, I/O schemas, dependencies, and protocols documented.
3. Every production skill documents the six required fields.
4. Capability tiers are explicit; no document claims credential-free cloud AI.
5. Rights gate and accurate-metadata rules are documented.
6. `feature/project-foundation` is pushed; `main` is unchanged.
7. No secrets, keys, or credentials are added.

## 9. Open questions for approval

| # | Question | Recommendation |
|---|---|---|
| Q1 | Keep package name `openmontage` until GA? | Yes, rename late to avoid breaking imports |
| Q2 | Keep Backlot UI as `/legacy` after dashboard GA? | Yes, until Phase 10 |
| Q3 | Mistral browser auth in Phase 1? | No — development-only, separate approval |
| Q4 | Default profiles 1080p long / 720p Shorts? | Yes |
| Q5 | Choose a new project license now? | No — keep existing `LICENSE` untouched |

## 10. Related documents

See `docs/architecture.md` for the layer model, `docs/agent-architecture.md` for the 11 agents, `docs/skills-architecture.md` for skills, `docs/video-pipeline.md` for processing, and `docs/decisions/ADR-001-architecture.md` for the decision record. Earlier Phase 0 material is in `docs/architecture/`.
