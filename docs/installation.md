# VIDEO COMBINE AI — Installation Guide

| Field | Value |
|---|---|
| Status | **DRAFT — awaiting approval** |
| Version | 1.0.0 |
| Note | No `pip install`, model download, or external API call was performed in the documentation sandbox |

---

## 1. Prerequisites on the target machine

| Requirement | Version | Needed for |
|---|---|---|
| Python | 3.11 (3.10+ accepted by `setup.py`) | All backend/CLI work |
| Git | any recent | Clone and branch workflow |
| FFmpeg + FFprobe | recent build with libx264/AAC | Rendering, probing, subtitles |
| Node.js + npm | ≥ 22 | Only for `dashboard/` and optional Remotion |
| Docker + compose | optional | `production` profile only |
| GPU / CUDA | optional | GPU-only local models; never required |
| Disk | ~2–6 GB with local models | Tier 2 caches |

## 2. Minimal keyless setup (Tier 1)

```bash
git clone https://github.com/khomyak75roman-dotcom/G.git
cd G
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-generator.txt
python -m generator "чому небо синє" --dry-run
```

This path uses only local code and FFmpeg; no credential and no model download.

## 3. Full development setup (Tier 1 + 2)

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
make setup
make install-dev
make preflight
make lint
make hyperframes-doctor
```

Optional local backends:

```bash
python -m pip install -r requirements-generator-optional.txt
```

GPU-only (skip unless a compatible GPU exists):

```bash
python -m pip install -r requirements-gpu.txt
```

## 4. Local model downloads (one-time, Tier 2)

These commands are **instructions only**; they were not executed here.

| Capability | Action | Notes |
|---|---|---|
| Ukrainian voice | Install `piper-tts`, download `uk_UA-lada-x_low` voice into a local voices directory | Set `PIPER_VOICES_DIR` if non-default |
| ASR | faster-whisper downloads a model on first use | Choose a small/medium model for CPU |
| Background removal | rembg downloads `u2net` | Set `OM_MEDIAPIPE_MODEL` / local cache |
| Selfie segmentation | MediaPipe `.tflite` model | Keep the path ASCII on Windows |
| Stock media | Fetched on demand from allowlisted archives | Respect license fields |

Windows note: this user profile has a Cyrillic path. Keep model caches on an ASCII path such as `C:/omtest/piper/espeak-ng-data` and `C:/omtest/mediapipe/selfie_segmenter.tflite`; set `OM_ESPEAK_DATA` accordingly.

## 5. Configuration

1. Copy `.env.example` → `.env` **on your own machine only**.
2. Leave every key empty unless you explicitly opt into a Tier 4 provider.
3. Never commit `.env`; it is covered by `.gitignore`.
4. `config.yaml` holds the keyless defaults (`budget.mode`, `output` profile, paths).

No credential is needed for research, script, voice, media discovery from open archives, editing, thumbnails, SEO, or QC.

## 6. Verification

```bash
python -m generator "чому небо синє" --dry-run
python -m generator --network-check
python -m generator --repos
python -m backlot open <project-id>
make test                 # ~10 minutes; currently 2938 passed, 18 skipped
```

`--network-check` reports proxy usage with credentials redacted. `--repos` currently lists 143 catalogue entries with runtime/reference/out-of-scope states.

## 7. Profiles

| Profile | Command shape | Services |
|---|---|---|
| `minimal` | `python -m generator ...` | None |
| `local` | `python -m studio serve` + `npm run dev` (from `dashboard/`) | SQLite, LocalRunner |
| `ci` | CI workflow | SQLite, network guard |
| `production` | `docker compose up` (later phase) | PostgreSQL, Redis, Celery |

`studio`, `dashboard`, and compose files are planned, not present in Phase 1.

## 8. Restricted-sandbox limitations

The current documentation environment has restricted internet and no package installation rights. Therefore:

- No pip install, model download, or external API integration was attempted.
- No GPU is assumed; all CPU paths are designed to work without one.
- Docker, Redis, PostgreSQL, `gh` CLI, and Node on PATH are unavailable here.
- The application is designed to be installed and run on a separate Windows/Linux computer or server using the steps above.

## 9. Troubleshooting

| Symptom | Resolution |
|---|---|
| `loc.gov` returns 403 / Cloudflare challenge | Use Wikimedia, NASA, Archive.org defaults |
| Proxy credentials appear in output | Report a bug; redaction must remove them |
| Piper/MediaPipe fails on Windows | Move caches to ASCII paths; set env vars |
| No voice model available | Ladder falls back to SAPI then recorded silence, flagged in QC |
| `make test` is slow | Run targeted test files during development; full suite in CI |
| Cloud provider unavailable | Expected in keyless mode; enable only with explicit opt-in |
