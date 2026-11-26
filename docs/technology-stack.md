# VIDEO COMBINE AI — Technology Stack

| Field | Value |
|---|---|
| Status | **DRAFT — awaiting approval** |
| Version | 1.0.0 |
| Rule | Prefer local/open-source; cloud providers are optional and opt-in |

---

## 1. Stack by layer

| Layer | Choice | State today | Rationale | Tier | Fallback |
|---|---|---|---|---|---|
| Language/runtime | Python 3.11 | In use (`.python-version`) | Matches existing code and tests | 1 | Python 3.10 (declared in `setup.py`) |
| Core CLI | `generator/` | Working | Keyless dry-run + smoke renders; keep as fallback | 1 | — |
| Tools | `tools/` + `tool_registry.py` | 237 files, working | Capability discovery, fallback, idempotency | 1 | Direct FFmpeg calls |
| API | FastAPI + Pydantic | Backlot exists | Extend with APIRouters; keep `/legacy` routes | 1 | CLI-only operation |
| Frontend | Next.js 15 + React 19 + TypeScript | Planned (`dashboard/`) | 11 sections with typed API client | 1 | Existing vanilla Backlot UI |
| DB | SQLite → PostgreSQL | None today (JSON checkpoints) | SQLite for local/CI; PostgreSQL for production profile | 1 | JSON checkpoints via compat importer |
| Migrations | Alembic | None today | Versioned schema evolution | 1 | Manual init for local dev |
| Queue | LocalRunner → Celery + Redis | In-process SSE queue only | Same `submit/status/cancel` protocol | 1 / later | Synchronous in-process |
| Rendering | FFmpeg + FFprobe | Installed | Core renderer, deterministic, no key | 1 | — |
| Motion graphics | Remotion | `remotion-composer/` present | Optional for title/stat cards; separate package | 2 | FFmpeg text overlays |
| ASR | faster-whisper | Optional dep declared | Local subtitles and analysis | 2 | Script-derived timings |
| TTS | Piper → Kokoro → SAPI → silence | Ladder implemented in `generator/speech.py` | Ukrainian/English keyless narration | 1–2 | Recorded silence (explicit) |
| Image/segmentation | Pillow, rembg/U²-Net, MediaPipe | Optional deps declared | Thumbnails and subject isolation | 1–2 | Crop/pad without model |
| Scene detection | FFmpeg filters / PySceneDetect | FFmpeg available | Simple, no GPU | 1 | Single full-range scene |
| Testing | pytest, pytest-asyncio, httpx | 2938 tests passing | Backend contracts and regression | 1 | — |
| Frontend testing | Vitest + Playwright | None today | Component and 11-route smoke tests | 1 | Manual route check |
| Containers | Docker + compose | None today | Reproducible server deployment | 1 | Native local run |
| CI | GitHub Actions | Exists (`make install-dev`, `lint`, `test`) | Extend with frontend jobs later | 1 | — |

## 2. Declared dependencies (from repository)

- **Core** (`requirements.txt`): pyyaml, pydantic≥2, jsonschema, python-dotenv, Pillow, numpy, requests, certifi, google-auth, google-genai, openai, fastapi, uvicorn, watchfiles, websockets, pythainlp.
- **Keyless CLI** (`requirements-generator.txt`): requests, certifi, edge-tts, Pillow.
- **Optional local** (`requirements-generator-optional.txt`): piper-tts, kokoro, rembg, mediapipe, yt-dlp, gallery-dl, faster-whisper.
- **GPU** (`requirements-gpu.txt`): torch, torchaudio, torchvision — not required, not available here.
- **Dev** (`requirements-dev.txt`): pytest, pytest-asyncio, httpx.

Presence of a package in `requirements.txt` does **not** imply a credential or a working cloud backend. Cloud SDKs are lazily imported and only used on explicit opt-in.

## 3. Planned additions (implementation phases, not now)

| Package | Purpose | Phase |
|---|---|---|
| sqlalchemy≥2.0, alembic≥1.13 | DB models and migrations | Core runtime |
| python-multipart | Media uploads | Core runtime |
| @tanstack/react-query, zod, openapi-typescript | Typed dashboard client | Dashboard |
| vitest, @playwright/test | Frontend tests | Dashboard |
| celery, redis | Production queue | Production profile |

## 4. Profiles

| Profile | Requires | Works in this sandbox? |
|---|---|---|
| `minimal` (Tier 1) | Python, FFmpeg, repo | Yes |
| `local-models` (Tier 2) | Python + downloaded models | Yes, if network allows and paths are ASCII |
| `dev-auth` (Tier 3) | Interactive browser login | No |
| `production` | PostgreSQL, Redis, Docker/GPU optional | No (services absent) |

## 5. Environment reality

This sandbox has Python 3.11 + FFmpeg and a prebuilt `.venv`, but **no Docker, no Redis, no PostgreSQL, no GPU, no `gh` CLI, and Node only at a custom path**. No package installation, model download, or external API call was performed while writing these documents. Installation instructions for a separate machine are in `docs/installation.md`.
