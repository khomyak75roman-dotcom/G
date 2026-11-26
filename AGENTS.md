# VIDEO COMBINE AI

**MANDATORY: Read `AGENT_GUIDE.md` before responding to ANY user message.**

Do not act on the user's request until you have read AGENT_GUIDE.md.
It contains routing rules that determine your first action based on what the user asked.

## Project-wide instructions

- Platform name: VIDEO COMBINE AI. Repository `G`; package bridge will be `studio/`
  (planned). The existing `generator/`, `tools/`, `lib/` and `backlot/` code is the
  keyless baseline and must keep working.
- Source of truth: `PRD.md`, `docs/architecture.md`, `docs/agent-architecture.md`,
  `docs/skills-architecture.md`, `docs/video-pipeline.md`, `docs/security.md`,
  `docs/copyright-and-licensing.md`, `docs/development-roadmap.md`, plus the
  Phase 0 documents in `docs/architecture/` and `AGENT_GUIDE.md`.
- Core mode is **keyless**: no API key is required for research, script, voice,
  media, editing, thumbnails, SEO or QC. Every feature has a declared
  Tier 1/2/3/4 in `PRD.md`; never claim credential-free cloud AI.
- Never hardcode, print, log or commit credentials. `.env` is gitignored.
  Redact proxy credentials in all outputs.
- Never activate VPN/DPI bypass, proxy pools or Telegram transit. Do not alter
  metadata to conceal a source or evade copyright detection.
- Human approval gates (G1–G5) are first-class states; a gated stage cannot be
  completed without explicit approval.
- Agents declare input/output schemas, version, skill path, error policy and
  tests. Runtime skills are independent of Mistral Vibe / coding-agent skills.
- FFmpeg is the core renderer; Remotion is optional; no paid call is enabled by
  default.
- Every implementation phase requires code + tests + docs + commit; `make lint`
  and `make test` must be green before a phase closes.
- As of Phase 1, only documentation is created. Do not implement application
  modules until the architecture is explicitly approved.
