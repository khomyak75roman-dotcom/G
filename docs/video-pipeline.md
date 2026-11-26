# VIDEO COMBINE AI — Video Processing Pipeline

| Field | Value |
|---|---|
| Status | **DRAFT — awaiting approval** |
| Version | 1.0.0 |
| Rendering core | **FFmpeg** |

---

## 1. Tool evaluation

| Tool | Technical purpose | Verdict | Tier | Notes |
|---|---|---|---|---|
| **FFmpeg / FFprobe** | Trim, concat, scale, crop, subtitle burn, loudnorm, encode, probe | **Adopt as core renderer** | 1 | Already installed; deterministic; no key; H.264/AAC output |
| **MoviePy** | Thin Python wrapper for simple compositing | Optional helper only | 1 | Adds no capability FFmpeg lacks; slower; do not make it a core dependency |
| **Remotion** | React-driven motion graphics, title/stat cards, charts | Optional, opt-in | 2 | Separate `remotion-composer/`; needs Node ≥ 22; never silently substituted for FFmpeg |
| **Whisper (faster-whisper)** | Local ASR for subtitles and analysis | Adopt for Tier 2 | 2 | Model download required; CPU-capable; Ukrainian support; no key |
| **Local TTS** | Narration in UA/EN | Adopt as default ladder | 1–2 | Piper `uk_UA-lada-x_low` → Kokoro → SAPI → silence; edge-tts needs network but no key |
| **Scene detection** | Split source into scenes | Adopt | 1 | FFmpeg `select='gt(scene,0.3)'` or PySceneDetect; no GPU needed |
| **Subtitle generation** | SRT creation and burn-in | Adopt | 1–2 | Prefer script word timings; ASR fallback; FFmpeg burn-in |
| **Reframing** | 16:9 → 9:16 and reverse | Adopt with fallbacks | 1–2 | Crop/pad default; rembg/MediaPipe optional for subject isolation |
| **Audio synchronization** | Align narration/music/source; normalize | Adopt | 1 | FFmpeg timestamps, `silencedetect`, `loudnorm`, `atrim`; word timings preferred |

Recommendation rule: a tool is included only when it solves a step that FFmpeg alone cannot, or when it materially improves determinism/quality. No GPU-only tool is a default.

## 2. Stage pipeline

| Stage | Input | Output | Primary tool | Gate |
|---|---|---|---|---|
| 1. Brief | Topic/source | `ProjectBrief` | API/dashboard | G1 |
| 2. Research | Brief | `research.json` | local corpus / open archives | — |
| 3. Script | Research | `script.json`, narration text | skill-driven | G2 |
| 4. Voice | Script | `voice.wav`, word timings | Piper/Kokoro/SAPI | — |
| 5. Media | Shot list | `media_manifest.json` | archive adapters | G4 |
| 6. Analysis | Authorized source | `analysis.json` | FFmpeg/Whisper | G3 (before) |
| 7. Clip | Analysis | `clips[]` | FFmpeg | G3 |
| 8. Editing | 3/4/5/6/7 | `timeline.json`, `final.mp4` | FFmpeg | — |
| 9. Thumbnail | Script/frames | `thumbnail_layers.json`, PNG | Pillow | — |
| 10. SEO | Final artifacts | `seo.json` | skill-driven | — |
| 11. QC | All above | `qc_report.json` | FFprobe/Whisper | G5 |

Stages 6–7 form the clip branch; stages 2–5 the original-content branch. Both converge at stage 8.

## 3. Output profiles

| Profile | Aspect | Resolution | FPS | Codec | Default |
|---|---|---|---|---|---|
| `longform-1080p` | 16:9 | 1920×1080 | 30 | H.264 MP4 + AAC | Yes, long-form |
| `shorts-720p` | 9:16 | 720×1280 | 30 | H.264 MP4 + AAC | Yes, Shorts |
| `draft-720p` | 16:9 | 1280×720 | 24 | H.264 MP4 + AAC | Fast preview |

CRF 23 default; `-movflags +faststart`; deterministic metadata. Profiles live in a single source of truth (existing `config.yaml` `output` block is the seed).

## 4. Editable timeline (proposed shape)

```json
{
  "schema": "timeline/v1",
  "profile": "longform-1080p",
  "duration_ms": 182000,
  "tracks": [
    {"type": "video", "clips": [
      {"source": "assets/clip_01.mp4", "in_ms": 0, "out_ms": 8400,
       "effects": [{"type": "crop", "rect": [0,0,1920,1080]}]}
    ]},
    {"type": "audio", "clips": [
      {"source": "audio/voice.wav", "in_ms": 0, "out_ms": 182000,
       "gain_db": 0.0}
    ]},
    {"type": "caption", "clips": [
      {"source": "subtitles.srt", "style": "bottom-center"}
    ]}
  ]
}
```

Status: **design proposal only**. The schema is finalized in the first implementation phase; no file is written now.

## 5. Clip processing (authorized sources only)

1. **Intake.** User upload or authorized URL; record owner, license, permission proof.
2. **Rights gate (G3).** Hard block if `verified != true`.
3. **Analysis.** Scenes, transcript, audio energy, black frames.
4. **Moment ranking.** Score + human-readable reason per candidate.
5. **Extraction.** FFmpeg cut with re-encode only when needed for frame accuracy.
6. **Original contribution.** Add commentary, new narration, new visual structure, subtitles.
7. **Reframe.** 16:9 → 9:16 with crop/pad or subject isolation.
8. **Attribution.** Description names the original source and license; metadata describes the new editorial content accurately.
9. **QC.** Rights record, attribution presence, metadata accuracy are mandatory checks.

Explicitly prohibited: altering metadata to conceal the original source, evade Content ID, or misdescribe the content. See `docs/copyright-and-licensing.md`.

## 6. Resume, caching, and rendering

- Stage idempotency: `(input_hash, agent_version, profile)`; unchanged inputs reuse cached artifacts.
- `lib/checkpoint.py` JSON checkpoints remain readable; a future importer maps them to SQLite without deleting originals.
- Large operations (render, ASR) run behind the runner protocol; LocalRunner in `local`, Celery/Redis in `production`.
- Every artifact is stored with SHA-256, MIME type, schema version, and a link to its provenance record.

## 7. Known limitations

- No GPU is assumed; local GPU models are optional Tier 2/4 additions.
- Model downloads are not performed in this sandbox (restricted network, no pip installs).
- Whisper Ukrainian accuracy varies with audio quality; QC flags low confidence.
- Remotion is not a default renderer and requires an explicit profile choice.
- Full `make test` takes about 10 minutes on the current machine.
