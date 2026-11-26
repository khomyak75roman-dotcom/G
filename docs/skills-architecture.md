# VIDEO COMBINE AI — Skills Architecture

| Field | Value |
|---|---|
| Status | **DRAFT — awaiting approval** |
| Version | 1.0.0 |
| Principle | Skills are versioned instructions; application logic never imports the coding agent's skill files |

---

## 1. Two independent skill planes

| Plane | Location | Consumer | Purpose | Runtime dependency? |
|---|---|---|---|---|
| **Development** | `.agents/skills/`, `.claude/skills/`, `.cursor/`, Mistral Vibe native skills | Coding agent (development time) | Guide how code is written, reviewed, and tested | **No** |
| **Application** | `skills/` + future `skills/registry.yaml` | The 11 runtime agents | Guide production tasks inside the product | **Yes** |

Rules:

- Mistral Vibe native Skills are used where appropriate during development (scaffolding, review, test design), but the shipped application must not call, import, or require them.
- The 1583 existing skill files are wrapped by a registry rather than moved or rewritten in this phase.
- New application skills use the `studio/`-scoped naming and a SemVer version in `registry.yaml`.
- A skill version is recorded in every run checkpoint; changing it invalidates resume for that stage.
- Skill content is untrusted text: no shell execution, no credential access, no prompt-injection payloads.

## 2. Skill template

Every application skill MUST document these six fields:

```markdown
# SKILL-XX — Name
- Purpose: one sentence
- Instructions: ordered steps the agent follows
- Input format: JSON schema reference + example
- Output format: JSON schema reference + example
- Quality criteria: measurable pass conditions
- Error handling: failure codes, retries, fallbacks
- Test scenarios: unit / contract / fixture cases
```

---

## 3. Skill catalogue

### SKILL-01 — Project and run setup

| Field | Content |
|---|---|
| Purpose | Create a project workspace and a resumable run. |
| Instructions | Validate brief → assign profile → create workspace → write initial checkpoint → emit `run.created`. |
| Input format | `ProjectBrief {title, language, format, duration_target, source_ref?}`. |
| Output format | `RunState {run_id, stages[], status}` plus `project.json`. |
| Quality criteria | Exactly 11 agents registered; workspace paths inside `projects/<id>/`; no absolute host paths in artifacts. |
| Error handling | `INVALID_BRIEF` → ask for missing fields; `WORKSPACE_EXISTS` → open, never overwrite. |
| Test scenarios | create/open/idempotent re-open; invalid language; path traversal attempt. |

### SKILL-02 — Capability preflight

| Field | Content |
|---|---|
| Purpose | Discover which tier each feature can use before any work starts. |
| Instructions | Query tool registry → check FFmpeg/models/cache paths → classify Tier 1/2/3/4 → present honest menu → lock profile. |
| Input format | `PreflightInput {allow_network, require_tier, format}`. |
| Output format | `CapabilityReport {features[{name, tier, available, reason}], warnings[]}`. |
| Quality criteria | No "configured" claim without a real probe; cloud features marked unavailable when no opt-in. |
| Error handling | `PROBE_TIMEOUT` → mark unavailable, continue with lower tier; never hang. |
| Test scenarios | no models → Tier 1 only; local Piper present → Tier 2 voice; proxy set → redacted report. |

### SKILL-03 — Research grounding

| Field | Content |
|---|---|
| Purpose | Produce verifiable facts with license and attribution metadata. |
| Instructions | Scope claims → retrieve from allowed sources → record URL/license/author → score confidence → flag gaps. |
| Input format | `ResearchInput {topic, language, max_sources, allow_network}`. |
| Output format | `ResearchPack {claims[], angle, outline, gaps[]}`. |
| Quality criteria | Every claim has a source; no invented citation; gaps listed explicitly. |
| Error handling | `SOURCE_BLOCKED` → try next allowlisted source; `NO_SOURCES` → return gaps, do not fabricate. |
| Test scenarios | offline corpus; blocked domain; duplicate source deduplication. |

### SKILL-04 — Script writing (UA/EN)

| Field | Content |
|---|---|
| Purpose | Convert research into a timed, scene-based script in Ukrainian or English. |
| Instructions | Pick hook → outline scenes → write narration → assign target timings → emit subtitle text. |
| Input format | `ScriptInput {research_pack, language, format, duration_target, style_profile}`. |
| Output format | `Script {hook, scenes[], subtitles_text, duration_estimate_ms}`. |
| Quality criteria | Language matches request; timing within ±10% of target; each scene has a visual cue. |
| Error handling | `DURATION_MISMATCH` → compress/expand once; `LANGUAGE_MISMATCH` → regenerate. |
| Test scenarios | UA long-form, EN Shorts, overlong script, missing research pack. |

### SKILL-05 — Voice selection and synthesis

| Field | Content |
|---|---|
| Purpose | Generate narration with the strongest keyless engine available. |
| Instructions | Probe Piper → Kokoro → SAPI → silence → announce chosen engine → synthesize → capture word timings → normalize. |
| Input format | `VoiceInput {script, language, voice_id?, engine_preference}`. |
| Output format | `VoiceOutput {audio_path, duration_ms, word_timings[], engine, fallback_used}`. |
| Quality criteria | Correct language voice; no clipping; LUFS within target; fallback recorded. |
| Error handling | `ENGINE_MISSING` → next ladder step; `MODEL_DOWNLOAD_REQUIRED` → report Tier 2, never auto-download in sandbox. |
| Test scenarios | UA Piper voice, EN SAPI fallback, all engines missing → silence with explicit flag. |

### SKILL-06 — Media discovery

| Field | Content |
|---|---|
| Purpose | Find media matching the shot list with verified rights metadata. |
| Instructions | Parse shot list → query allowed sources → validate license fields → download/reference → write manifest. |
| Input format | `MediaInput {shot_list, sources[], allow_network}`. |
| Output format | `MediaManifest {items[{id, path, source_url, author, license, attribution_text, verified}], gaps[]}`. |
| Quality criteria | `verified=true` only with license evidence; no item without attribution text. |
| Error handling | `LICENSE_UNKNOWN` → mark unverified; `DOWNLOAD_FAILED` → alternate source or gap. |
| Test scenarios | Wikimedia CC item, NASA public domain, unknown license, offline mode. |

### SKILL-07 — Rights verification

| Field | Content |
|---|---|
| Purpose | Decide whether a source may be analyzed, transformed, and published. |
| Instructions | Collect owner/license/permission → check user-owned flag → check scope → record decision → set gate G3. |
| Input format | `RightsInput {source_ref, claimed_owner, license, permission_proof, user_uploaded, intended_use}`. |
| Output format | `RightsRecord {verified, basis, attribution_text, restrictions[], expires?}`. |
| Quality criteria | No `verified=true` without evidence; restrictions copied into final metadata. |
| Error handling | `PROOF_MISSING` → gate blocked; `RESTRICTED` → refuse extraction. |
| Test scenarios | user-owned upload, CC-BY with attribution, unverified YouTube URL, revoked permission. |

### SKILL-08 — Scene detection

| Field | Content |
|---|---|
| Purpose | Split a source video into scenes for analysis and clip selection. |
| Instructions | Probe video → choose threshold → detect cuts → merge very short scenes → emit time ranges. |
| Input format | `SceneInput {video_path, threshold, min_scene_ms}`. |
| Output format | `SceneList {scenes[{start_ms, end_ms, score}], method, threshold}`. |
| Quality criteria | No overlapping or zero-length ranges; covers full duration. |
| Error handling | `PROBE_FAILED` → FFprobe fallback; `NO_SCENES` → single full-range scene. |
| Test scenarios | synthetic cuts, black frames, unknown duration, missing ffprobe. |

### SKILL-09 — Interesting-moment ranking

| Field | Content |
|---|---|
| Purpose | Rank candidate moments for short-form clips. |
| Instructions | Combine transcript salience, scene score, audio energy, and pacing → rank → deduplicate → explain each choice. |
| Input format | `RankInput {analysis, commentary_focus, count, format}`. |
| Output format | `RankedMoments {moments[{start_ms, end_ms, score, reason}], rejected[]}`. |
| Quality criteria | Every moment has a human-readable reason; no moment crosses a scene boundary without intent. |
| Error handling | `TRANSCRIPT_MISSING` → use audio/scene signals only and flag lower confidence. |
| Test scenarios | podcast, talking head, silent video, too few candidates. |

### SKILL-10 — Timeline editing

| Field | Content |
|---|---|
| Purpose | Author an editable timeline that can be rendered repeatedly. |
| Instructions | Map script scenes to media → set in/out → add overlays/captions → set audio mix → validate → save JSON. |
| Input format | `TimelineInput {script, media_manifest, voice, analysis?, format, profile}`. |
| Output format | `Timeline {tracks[{type, clips[{source, in, out, effects}]}], duration_ms, profile}`. |
| Quality criteria | No gaps unless intentional; all sources exist; duration matches target ±10%. |
| Error handling | `SOURCE_MISSING` → replace with placeholder clip and flag; `DURATION_MISMATCH` → report. |
| Test scenarios | long-form assembly, Shorts reframe, missing media, re-render determinism. |

### SKILL-11 — Subtitle generation

| Field | Content |
|---|---|
| Purpose | Produce aligned SRT from script timings or local ASR. |
| Instructions | Prefer script word timings → fall back to faster-whisper → segment → validate reading speed → write SRT. |
| Input format | `SubtitleInput {script?, audio_path, language, max_chars_per_line}`. |
| Output format | `{srt_path, cues[{start,end,text}], source: script / asr, confidence}`. |
| Quality criteria | No overlapping cues; ≤ 42 chars/line; timing within 150 ms of speech. |
| Error handling | `ASR_MODEL_MISSING` → use script timings; `ALIGNMENT_LOW` → flag in QC. |
| Test scenarios | script-aligned EN, Whisper UA, long line splitting, empty audio. |

### SKILL-12 — Reframing

| Field | Content |
|---|---|
| Purpose | Convert 16:9 material to 9:16 (or reverse) without losing subject. |
| Instructions | Detect subject → choose crop/pad/blur → optionally remove background → render preview → verify. |
| Input format | `ReframeInput {video_path, from_aspect, to_aspect, method, model_available}`. |
| Output format | `{video_path, method, crop_box, fallback_used}`. |
| Quality criteria | Subject visible in >90% of frames; no black bars unless chosen; safe text margins. |
| Error handling | `MODEL_MISSING` → crop/pad fallback; `TRACKING_FAILED` → centered crop with warning. |
| Test scenarios | talking head, wide landscape, model unavailable, already-correct aspect. |

### SKILL-13 — Audio sync and mixing

| Field | Content |
|---|---|
| Purpose | Align narration, music, and source audio; normalize loudness. |
| Instructions | Read word timings → align → remove pauses if requested → loudnorm → duck music → mux. |
| Input format | `AudioInput {voice, source_audio?, music?, timings, target_lufs, duck_db}`. |
| Output format | `{mix_path, loudness, sync_offset_ms, edits[]}`. |
| Quality criteria | LUFS within target ±1.5; no clipping; sync offset < 80 ms. |
| Error handling | `TIMINGS_MISSING` → silence detection alignment; `CLIPPING` → reduce gain and re-render. |
| Test scenarios | voice-only, voice+music, mismatched sample rates, silent track. |

### SKILL-14 — Thumbnail design

| Field | Content |
|---|---|
| Purpose | Create editable, readable thumbnails for 16:9 and 9:16. |
| Instructions | Pick key frame → choose composition → add ≤ 5 words → check contrast → export layers + PNG. |
| Input format | `ThumbnailInput {key_frames, script, format, style_profile}`. |
| Output format | `{layers_path, png_paths[], text_used, readability_score}`. |
| Quality criteria | Text readable at 120 px; no misleading claims; face not obscured. |
| Error handling | `NO_KEY_FRAME` → use title card; `LOW_CONTRAST` → add stroke/scrim. |
| Test scenarios | 16:9 and 9:16 variants, long title, dark frame. |

### SKILL-15 — SEO metadata

| Field | Content |
|---|---|
| Purpose | Write accurate YouTube metadata including source attribution. |
| Instructions | Extract topic/hook → draft title/description → add chapters/tags → append attribution → fact-check claims. |
| Input format | `SEOInput {script, thumbnail, video, language, source_attribution[]}`. |
| Output format | `{title, description, tags[], chapters[], hashtags[], attribution_text, checks[]}`. |
| Quality criteria | Title ≤ 100 chars; no unsupported superlatives; every source named. |
| Error handling | `ATTRIBUTION_MISSING` → block publish; `TITLE_TOO_LONG` → shorten once. |
| Test scenarios | sourced clip, original video, missing attribution, banned claim words. |

### SKILL-16 — Quality gate and reporting

| Field | Content |
|---|---|
| Purpose | Produce the final QC report and gate decision. |
| Instructions | Run all checks → collect measurements → compare thresholds → classify findings → emit verdict. |
| Input format | `QCInput {video, audio, subtitles, seo, provenance, thresholds}`. |
| Output format | `{score, checks[], findings[], verdict: pass / warn / fail}`. |
| Quality criteria | Every check has value + threshold; critical findings block G5; report is reproducible. |
| Error handling | `CHECK_UNAVAILABLE` → mark as skipped with reason, never silently pass. |
| Test scenarios | clean render, black frames, loudness violation, missing rights record, deceptive title. |

## 4. Skill lifecycle

1. Author skill file with the seven-field template.
2. Register name, version, schema paths, and owner in `skills/registry.yaml`.
3. Add at least one unit test and one contract test per skill.
4. Reference the skill from the agent's envelope; version travels with the checkpoint.
5. Deprecate by bumping version, never by silent replacement.
