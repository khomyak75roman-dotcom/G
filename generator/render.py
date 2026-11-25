"""Final assembly using OpenMontage's SubtitleGen + VideoCompose tools."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.media_profiles import get_profile


def build_subtitles(words: list[dict[str, Any]], output: str | Path) -> Path | None:
    """Generate an SRT file from word-level timings via SubtitleGen."""
    if not words:
        return None
    output = Path(output)
    from tools.subtitle.subtitle_gen import SubtitleGen

    result = SubtitleGen().execute({
        "segments": [{"words": words}],
        "format": "srt",
        "output_path": str(output),
        "max_words_per_cue": 7,
        "max_chars_per_line": 42,
    })
    if not result.success:
        raise RuntimeError(f"SubtitleGen failed: {result.error}")
    return output


def compose_video(
    *,
    clips: list[dict[str, Any]],
    scene_durations: list[float],
    output: str | Path,
    audio_path: str | Path | None = None,
    subtitle_path: str | Path | None = None,
    profile: str = "youtube_landscape",
) -> dict[str, Any]:
    """Compose all scene cuts into the final MP4 with FFmpeg."""
    from tools.video.video_compose import VideoCompose

    preset = get_profile(profile)
    portrait = preset.height > preset.width
    cuts: list[dict[str, Any]] = []
    for clip, duration in zip(clips, scene_durations):
        available = float(clip.get("duration", duration))
        use = min(float(duration), max(0.5, available - 0.1))
        in_seconds = max(0.0, (available - use) / 2)
        cuts.append({
            "source": str(Path(clip["path"]).resolve()),
            "in_seconds": round(in_seconds, 3),
            "out_seconds": round(in_seconds + use, 3),
        })

    edit_decisions = {
        "version": "1.0",
        "cuts": cuts,
        "metadata": {
            "compose_target": {
                "width": preset.width,
                "height": preset.height,
                "fit": "cover" if portrait else "pad",
            },
            "generator": "keyless-cli",
        },
    }
    inputs: dict[str, Any] = {
        "operation": "compose",
        "edit_decisions": edit_decisions,
        "profile": profile,
        "codec": "libx264",
        "crf": preset.crf,
        "preset": "medium",
        "output_path": str(output),
    }
    if audio_path and Path(audio_path).exists():
        inputs["audio_path"] = str(audio_path)
    if subtitle_path and Path(subtitle_path).exists():
        inputs["subtitle_path"] = str(subtitle_path)

    result = VideoCompose().execute(inputs)
    if not result.success:
        raise RuntimeError(f"VideoCompose failed: {result.error}")
    return {
        "output": str(Path(output).resolve()),
        "cuts": len(cuts),
        "profile": profile,
        "resolution": f"{preset.width}x{preset.height}",
        "duration": round(sum(c["out_seconds"] - c["in_seconds"] for c in cuts), 2),
        "data": result.data,
    }
