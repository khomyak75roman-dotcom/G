# VIDEO COMBINE AI — Agent Architecture

| Field | Value |
|---|---|
| Status | **DRAFT — awaiting approval** |
| Version | 1.0.0 |
| Agents | 11 (Orchestrator + 10 specialized) |

> The agents below are a **design contract**. No runtime classes are implemented in Phase 1.

---

## 1. Common communication protocol

All agents exchange a versioned envelope. Transport is the orchestrator's `AgentRunner` protocol (`submit/status/cancel`); state is mirrored to `run_stages` in the DB; progress is streamed via SSE from `lib/events.py`.

### 1.1 Request envelope

```json
{
  "envelope": "vcai/1",
  "run_id": "uuid",
  "stage_id": "uuid",
  "agent": "research",
  "agent_version": "1.0.0",
  "input_hash": "sha256-of-payload-and-dependencies",
  "attempt": 1,
  "payload": {},
  "provenance": [],
  "budget": {"policy": "keyless", "max_usd": 0},
  "deadline_ms": 60000
}
```

### 1.2 Response envelope

```json
{
  "envelope": "vcai/1",
  "run_id": "uuid",
  "stage_id": "uuid",
  "status": "ok | failed | awaiting_approval | skipped",
  "result": {},
  "artifacts": [{"path": "...", "sha256": "...", "mime": "...", "schema": "..."}],
  "provenance": [],
  "quality": {"score": 0.0, "findings": []},
  "error": {"code": "...", "retryable": true, "message": "..."}
}
```

Rules:

- Idempotency key = `(stage_id, input_hash, agent_version, attempt)`.
- `skipped` always carries `error.code = "agent_not_implemented"` or `"gate_not_approved"`.
- No response may contain a credential, token, or raw proxy URL.
- Every agent declares its skill path and version; both are written to the checkpoint.

## 2. DAG and gates

```
                 ┌──────────┐
                 │Orchestr. │
                 └────┬─────┘
        ┌────────────┴────────────┐
        │                         │
  Research → Script → Voice   Media intake → Rights gate
        │          │              │
        └────┬─────┘         Analysis → Clip
             │                    │
             └────────┬───────────┘
                      ↓
        Editing → Thumbnail → SEO → Quality → Publish gate
```

| Gate | Name | Blocks | Approver |
|---|---|---|---|
| G1 | Brief | Script | Human |
| G2 | Script | Voice/Media | Human |
| G3 | Rights | Analysis/Clip | Human, mandatory for external sources |
| G4 | Assets | Editing | Human |
| G5 | Publish | Distribution | Human, after QC |

## 3. Agent specifications

### 3.1 Orchestrator Agent (`orchestrator`, v1.0.0)

| Field | Definition |
|---|---|
| Responsibilities | Build DAG, schedule ready stages, enforce gates, resume from checkpoints, retry with backoff, enforce `budget_policy`, emit events, aggregate final report. |
| Input schema | `ProjectBrief {title, language, format, duration_target, source_ref?, style?}`, `RunPlan?`, `approvals{}`. |
| Output schema | `RunState {run_id, stages[], status, current_gate, budget_spend, artifacts[]}`. |
| Dependencies | DB repositories, ArtifactStore, EventBus, AgentRegistry, LocalRunner/CeleryRunner. |
| Protocol | Issues `submit()` envelopes; consumes responses; writes `run_stages`; never executes agent logic itself. |

### 3.2 Research Agent (`research`, v1.0.0)

| Field | Definition |
|---|---|
| Responsibilities | Ground the topic in facts, collect source URLs, license/attribution metadata, and a differentiation angle. Tier 1: local corpus; Tier 2: Wikimedia/NASA/Archive.org; Tier 4: optional search APIs. |
| Input schema | `ResearchInput {topic, language, format, source_ref?, max_sources, allow_network}`. |
| Output schema | `ResearchPack {claims[{text, source_url, license, attribution, confidence}], angle, outline, gaps[]}`. |
| Dependencies | Local corpus, open-archive adapters, optional search adapter, provenance store. |
| Protocol | `submit` → `ok` with `research.json`; unresolved sources become `quality.findings`, never silent omissions. |

### 3.3 Script Writer Agent (`script`, v1.0.0)

| Field | Definition |
|---|---|
| Responsibilities | Turn a research pack into a structured, timed script in Ukrainian or English for long-form or Shorts. |
| Input schema | `ScriptInput {research_pack, language, format, duration_target, tone, style_profile}`. |
| Output schema | `Script {title, hook, scenes[{id, narration, visual_cue, target_ms}], subtitles_text, word_timings_hint}`. |
| Dependencies | Research Agent output, style playbooks in `styles/`, script skill. |
| Protocol | Writes `script.json` + plain-text narration; G2 gate before voice/media. |

### 3.4 Voice Generation Agent (`voice`, v1.0.0)

| Field | Definition |
|---|---|
| Responsibilities | Synthesize narration via keyless ladder: Piper (UA/EN) → Kokoro → Windows SAPI → recorded silence; optional cloud TTS only on explicit opt-in. |
| Input schema | `VoiceInput {script, language, voice_id?, engine_preference, sample_rate}`. |
| Output schema | `VoiceOutput {audio_path, duration_ms, word_timings[], engine,voice_id, fallback_used, license_note}`. |
| Dependencies | FFmpeg, local TTS runtimes, `tts_save` ladder in `generator/speech.py`. |
| Protocol | `ok` with `voice.wav` + timings; every fallback is recorded in `decisions`/`quality`. |

### 3.5 Media Discovery Agent (`media`, v1.0.0)

| Field | Definition |
|---|---|
| Responsibilities | Find images/video/audio matching the shot list; verify license fields; download or reference; record provenance. |
| Input schema | `MediaInput {script, shot_list, format, allow_network, sources[]}`. |
| Output schema | `MediaManifest {items[{id, path, type, source_url, author, license, attribution_text, verified}], gaps[]}`. |
| Dependencies | Open-archive adapters, user media drop path, provenance store. |
| Protocol | Any item without a verified license is marked `unverified` and cannot pass G4. |

### 3.6 Video Analysis Agent (`analysis`, v1.0.0)

| Field | Definition |
|---|---|
| Responsibilities | Analyze authorized/user-owned source video: scenes, interesting moments, transcript, loudness, black frames, frame samples. |
| Input schema | `AnalysisInput {source_path, rights_record, scene_threshold, transcript_lang, sample_count}`. |
| Output schema | `AnalysisReport {scenes[{start,end,score}], moments[{start,reason,score}], transcript, audio_metrics, black_frames[]}`. |
| Dependencies | FFmpeg, scene detection, faster-whisper (Tier 2), rights gate G3. |
| Protocol | Refuses to run if `rights_record.verified != true`; emits `analysis.json`. |

### 3.7 Video Editing Agent (`editing`, v1.0.0)

| Field | Definition |
|---|---|
| Responsibilities | Build an editable timeline, apply cuts/overlays/captions/reframing, mix audio, render H.264 MP4 via FFmpeg. |
| Input schema | `EditInput {script, voice, media_manifest, analysis?, format, profile, timeline?}`. |
| Output schema | `EditOutput {timeline_path, render_path, render_report, subtitles_path, profile_used}`. |
| Dependencies | FFmpeg, Remotion (optional), timeline schema, artifact store. |
| Protocol | Timeline is data; render is derived. Re-render from the same timeline must be byte-stable within a profile. |

### 3.8 YouTube Clip Agent (`clip`, v1.0.0)

| Field | Definition |
|---|---|
| Responsibilities | Select moments from authorized sources, extract clips, add original commentary, new narration, subtitles, and a new visual structure. |
| Input schema | `ClipInput {source_path, rights_record, analysis, commentary, language, format, count}`. |
| Output schema | `ClipSet {clips[{id, path, start, end, commentary, narration_path, subtitles_path, provenance}], attribution_text}`. |
| Dependencies | Analysis Agent, Rights gate G3, Editing Agent, voice/subtitle tools. |
| Protocol | Hard-blocked without rights verification; metadata must describe the new editorial content and name the source. |

### 3.9 Thumbnail Agent (`thumbnail`, v1.0.0)

| Field | Definition |
|---|---|
| Responsibilities | Design layered thumbnails for 16:9 and 9:16 from script/key frames; export editable layer JSON and flattened PNG. |
| Input schema | `ThumbnailInput {script, key_frames, format, style_profile, text_limit}`. |
| Output schema | `ThumbnailOutput {layers_path, png_paths[], text_used, readability_score}`. |
| Dependencies | Key frames from Editing/Analysis, Pillow, optional local image model (Tier 2/4). |
| Protocol | No misleading text; face/text placement checked by QC. |

### 3.10 SEO Agent (`seo`, v1.0.0)

| Field | Definition |
|---|---|
| Responsibilities | Produce title, description, tags, chapters, hashtags, and accurate attribution text from final artifacts. |
| Input schema | `SEOInput {script, thumbnail, video, format, language, source_attribution[]}`. |
| Output schema | `SEOPackage {title, description, tags[], chapters[], hashtags[], attribution_text, claims_check[]}`. |
| Dependencies | Script, thumbnail, rights records, QC findings. |
| Protocol | No clickbait that misdescribes content; no omission of required source attribution. |

### 3.11 Quality Control Agent (`quality`, v1.0.0)

| Field | Definition |
|---|---|
| Responsibilities | Validate ASR accuracy, loudness (LUFS), black frames, caption sync, rights completeness, provenance, and metadata accuracy; decide pass/fail for G5. |
| Input schema | `QCInput {video, audio, subtitles, script, seo, provenance, thresholds}`. |
| Output schema | `QCReport {score, checks[{name, status, value, threshold}], findings[], verdict: pass / warn / fail}`. |
| Dependencies | FFprobe, faster-whisper, rights records, all prior artifacts. |
| Protocol | `verdict=fail` sets gate G5 to blocked; critical findings cannot be overridden silently. |

## 4. Registration and evolution

- Each agent declares `name`, `version`, `skill_path`, `input_schema`, `output_schema`, `error_policy`, and `tests`.
- Versions are recorded per run; changing a version invalidates resume for that stage.
- Agents are pure adapters: orchestration, storage, and UI never live inside an agent.
- Adding an agent requires a registry entry, a skill, a schema, and tests — not edits to the orchestrator.
