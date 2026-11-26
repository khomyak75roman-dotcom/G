"""Command-line entry point for the keyless OpenMontage generator."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from lib.media_profiles import ALL_PROFILES

from . import __version__
from .media import acquire_clips, make_title_clip, source_summary
from .render import build_subtitles, compose_video
from .script import build_script
from .speech import TTS_BACKENDS, synthesize, save_timing_report


_SLUG_TRANSLIT = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e",
    "є": "ie", "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "yi", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ь": "", "ю": "iu", "я": "ia",
})


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower().translate(_SLUG_TRANSLIT)).strip("-")
    return slug[:48] or "video"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m generator",
        description=(
            "Generate an MP4 from a prompt using OpenMontage tools without API keys. "
            "Pipeline: script -> narration -> subtitles -> free stock footage -> FFmpeg."
        ),
    )
    parser.add_argument("prompt", nargs="?", help="Topic or ready-made script text")
    parser.add_argument("--script-file", help="Read the narration from a UTF-8 text file")
    parser.add_argument("--out", help="Final MP4 path (default: inside the project workspace)")
    parser.add_argument("--project-id", help="Project directory name (default: slug + timestamp)")
    parser.add_argument("--scenes", type=int, default=4, help="Number of scenes (default: 4)")
    parser.add_argument("--lang", choices=["uk", "en"], help="Narration language (auto-detected)")
    parser.add_argument("--voice", help="edge-tts voice (default: uk-UA-PolinaNeural / en-US-AriaNeural)")
    parser.add_argument("--tts", choices=TTS_BACKENDS, default="auto",
                        help="tts_save ladder: auto=edge -> piper -> kokoro -> SAPI -> silence")
    parser.add_argument("--piper-voice", help="Piper model name, e.g. uk_UA-tetiana-high")
    parser.add_argument("--rate", default="+0%", help="Speech rate, e.g. +10%% (default: +0%%)")
    parser.add_argument("--profile", choices=sorted(ALL_PROFILES), default="youtube_landscape")
    parser.add_argument("--sources", nargs="+", help="Stock adapters (default: wikimedia nasa archive_org coverr loc)")
    parser.add_argument("--clips-per-scene", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=180.0, help="Stock search deadline in seconds")
    parser.add_argument("--offline", action="store_true", help="Skip stock search; use local title cards")
    parser.add_argument("--no-audio", action="store_true", help="Render without narration")
    parser.add_argument("--no-subtitles", action="store_true", help="Do not burn subtitles")
    parser.add_argument("--scene-seconds", type=float, default=5.0, help="Scene length with --no-audio")
    parser.add_argument("--remove-bg", action="store_true",
                        help="Replace each scene background (rembg/u2net or mediapipe selfie)")
    parser.add_argument("--bg-color", default="#101c2e", help="Replacement background colour (default: #101c2e)")
    parser.add_argument("--bg-image", help="Replacement background image (optional)")
    parser.add_argument("--bg-engine", choices=["rembg", "selfie"], default="rembg",
                        help="Background matting engine (default: rembg)")
    parser.add_argument("--bg-model", default="u2net", help="rembg model: u2net / u2net_human_seg / isnet-general-use")
    parser.add_argument("--selfie-preview", action="store_true",
                        help="Write a mediapipe SelfieSegmentation preview next to the render")
    parser.add_argument("--translate", help="Translate subtitles via LibreTranslate (target language code)")
    parser.add_argument("--remove-pauses", action="store_true",
                        help="Collapse long gaps in word timings before subtitle generation")
    parser.add_argument("--transcribe", help="Media file/URL to transcribe with faster-whisper (faster-whisper + yt-dlp pattern)")
    parser.add_argument("--whisper-model", default="base", help="faster-whisper model for --transcribe (default: base)")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan only; no network or rendering")
    parser.add_argument("--list-sources", action="store_true", help="List stock adapters and exit")
    parser.add_argument("--repos", action="store_true", help="Show status of all integrated upstream repos and exit")
    parser.add_argument("--network-check", action="store_true",
                        help="Probe keyless stock sources through the current proxy environment and exit")
    parser.add_argument("--version", action="version", version=f"generator {__version__}")
    return parser


def _require_tools() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if not shutil.which(name)]
    if missing:
        raise SystemExit(f"Missing required tool(s): {', '.join(missing)}. Install FFmpeg first.")


def _scene_durations(words: list[dict[str, Any]], scene_texts: list[str], total: float) -> list[float]:
    """Distribute narration time across scenes using word boundaries."""
    durations: list[float] = []
    cursor = 0
    for index, text in enumerate(scene_texts):
        expected = max(1, len(text.split()))
        chunk = words[cursor:cursor + expected]
        cursor += expected
        if chunk:
            start = float(chunk[0]["start"])
            end = float(chunk[-1]["end"])
            duration = end - start + 0.55
        else:
            duration = total / len(scene_texts)
        if index == len(scene_texts) - 1 and words:
            duration = max(duration, total - start)
        durations.append(max(1.5, round(duration, 3)))
    return durations


def _adjust_fallbacks(
    clips: list[dict[str, Any]], durations: list[float], scenes: list[dict[str, Any]]
) -> None:
    """Make local title cards long enough for their scene narration."""
    for clip, duration, scene in zip(clips, durations, scenes):
        if clip.get("kind") == "fallback" and clip.get("duration", 0) < duration + 0.2:
            make_title_clip(scene["text"], clip["path"], duration=duration + 0.4)
            clip["duration"] = round(duration + 0.4, 3)


def _transcription_script(media: str, language: str | None) -> dict[str, Any]:
    """Minimal script shape for transcription-only runs (no video generation)."""
    name = media.split("?", 1)[0].rstrip("/").split("/")[-1]
    return {
        "title": Path(name).stem or "transcription",
        "language": language or "uk",
        "narration": "",
        "scenes": [],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    transcribe_only = not args.prompt and not args.script_file and bool(args.transcribe)
    if transcribe_only:
        script = _transcription_script(args.transcribe, args.lang)
    else:
        script = build_script(
            prompt=args.prompt,
            script_file=args.script_file,
            scenes=args.scenes,
            language=args.lang,
        )
    project_id = args.project_id or f"{_slug(script['title'])}-{datetime.now():%Y%m%d-%H%M%S}"

    plan = {
        "project_id": project_id,
        "title": script["title"],
        "language": script["language"],
        "profile": args.profile,
        "scenes": script["scenes"],
        "sources": args.sources,
        "offline": args.offline,
    }
    if args.tts != "auto":
        plan["tts_backend"] = args.tts
    if args.piper_voice:
        plan["piper_voice"] = args.piper_voice
    if args.remove_bg:
        plan["background"] = {"engine": args.bg_engine, "model": args.bg_model, "color": args.bg_color}
    if args.translate:
        plan["translate_to"] = args.translate
    if args.remove_pauses:
        plan["remove_pauses"] = True
    if args.transcribe:
        plan["transcribe"] = args.transcribe
    if args.dry_run:
        return plan

    from lib.checkpoint import init_project

    project_dir = Path(init_project(
        project_id, title=script["title"], pipeline_type="animated-explainer"
    ))
    (project_dir / "artifacts" / "script.json").write_text(
        json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    plan["project_dir"] = str(project_dir.resolve())

    audio_path = project_dir / "assets" / "audio" / "narration.mp3"
    if args.no_audio or transcribe_only:
        speech = None
        durations = [args.scene_seconds for _ in script["scenes"]]
    else:
        speech = synthesize(
            script["narration"], audio_path, voice=args.voice,
            language=script["language"], rate=args.rate,
            backend=args.tts, piper_voice=args.piper_voice,
        )
        if args.remove_pauses:
            from .pause_removal import collapse_gaps
            speech.words = collapse_gaps(speech.words)
        save_timing_report(speech, project_dir / "artifacts" / "narration_timing.json")
        durations = _scene_durations(speech.words, [s["text"] for s in script["scenes"]], speech.duration)
        plan["narration"] = speech.as_dict()

    subtitle_path = None
    if not args.no_audio and not args.no_subtitles and speech and speech.words:
        subtitle_path = build_subtitles(
            speech.words, project_dir / "artifacts" / "subtitles.srt"
        )
        if subtitle_path and args.translate:
            from .translation import translate_srt
            try:
                plan["translation"] = translate_srt(
                    subtitle_path, args.translate, source=script["language"]
                )
            except Exception as exc:
                plan["translation"] = {"success": False, "error": f"{type(exc).__name__}: {exc}"}
        plan["subtitles"] = str(subtitle_path) if subtitle_path else None

    if args.transcribe:
        from .transcription import transcribe
        transcript = transcribe(
            args.transcribe, model_size=args.whisper_model,
            output_dir=project_dir / "artifacts",
        )
        words = transcript.pop("words", [])
        (project_dir / "artifacts" / "transcription.json").write_text(
            json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if transcript.get("success") and words:
            from .pause_removal import collapse_gaps
            srt = build_subtitles(
                collapse_gaps(words) if args.remove_pauses else words,
                project_dir / "artifacts" / "transcription.srt",
            )
            transcript["srt"] = str(srt) if srt else None
        plan["transcription"] = transcript

    if transcribe_only:
        report = project_dir / "artifacts" / "generator_report.json"
        report.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        plan["report"] = str(report.resolve())
        return plan

    clips = acquire_clips(
        script=script,
        output_dir=project_dir / "assets" / "video" / "source",
        sources=args.sources,
        clips_per_scene=args.clips_per_scene,
        timeout=args.timeout,
        offline=args.offline,
    )
    _adjust_fallbacks(clips, durations, script["scenes"])
    if args.remove_bg or args.selfie_preview:
        from .background import replace_background, selfie_preview
        processed_dir = project_dir / "assets" / "video" / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        for index, clip in enumerate(clips):
            if args.remove_bg:
                target = processed_dir / f"bg_{index + 1:02d}.mp4"
                if replace_background(
                    clip["path"], target, engine=args.bg_engine, model=args.bg_model,
                    color=args.bg_color, bg_image=args.bg_image,
                ):
                    clip["path"] = str(target.resolve())
                    clip["source"] = f"{args.bg_engine}-background"
        if args.selfie_preview and clips:
            preview = selfie_preview(
                clips[0]["path"], project_dir / "artifacts" / "selfie_preview.png"
            )
            if preview:
                plan["selfie_preview"] = str(preview.resolve())
    plan["visuals"] = [
        {"scene": i + 1, "source": c["source"], "path": c["path"], "seconds": durations[i]}
        for i, c in enumerate(clips)
    ]

    output = Path(args.out) if args.out else project_dir / "renders" / "final.mp4"
    rendered = compose_video(
        clips=clips,
        scene_durations=durations,
        output=output,
        audio_path=None if args.no_audio else audio_path,
        subtitle_path=subtitle_path,
        profile=args.profile,
    )
    plan["render"] = rendered

    report = project_dir / "artifacts" / "generator_report.json"
    report.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    plan["report"] = str(report.resolve())
    return plan


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.repos:
        from .external_repos import report
        print(json.dumps(report(), ensure_ascii=False, indent=2))
        return 0
    if args.network_check:
        from .network import check_sources
        print(json.dumps(check_sources(), ensure_ascii=False, indent=2))
        return 0
    if args.list_sources:
        print(json.dumps(source_summary(), ensure_ascii=False, indent=2))
        return 0
    if not args.prompt and not args.script_file and not args.transcribe:
        build_parser().print_help()
        return 2
    _require_tools()

    plan = run(args)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if not args.dry_run:
        output = (
            plan.get("render", {}).get("output")
            or plan.get("transcription", {}).get("srt")
            or plan.get("report")
        )
        if output:
            print(f"\nГотово: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
