"""Visual acquisition: OpenMontage keyless stock adapters + local fallback.

Uses OpenMontage's ``DirectClipSearch`` (Wikimedia, NASA, Archive.org, LOC,
Coverr — no API keys). When a scene has no usable footage, a local title
card clip is generated with Pillow + FFmpeg so the pipeline always completes.
"""
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path
from typing import Any

from .speech import probe_duration


DEFAULT_SOURCES = ["wikimedia", "nasa", "archive_org", "coverr", "loc"]


def source_summary() -> dict[str, Any]:
    from tools.video.stock_sources import source_summary as _summary

    return _summary()


def _shorten(text: str, width: int = 48) -> str:
    words = text.split()
    return textwrap.shorten(" ".join(words), width=width, placeholder="…")


def acquire_clips(
    *,
    script: dict[str, Any],
    output_dir: str | Path,
    sources: list[str] | None = None,
    clips_per_scene: int = 2,
    timeout: float = 180,
    offline: bool = False,
) -> list[dict[str, Any]]:
    """Return one visual clip per scene, aligned with scene durations later."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    by_slot: dict[str, list[dict[str, Any]]] = {}
    if not offline:
        from tools.video.direct_clip_search import DirectClipSearch

        queries = [
            {"query": scene["visual_query"], "slot_id": f"scene_{scene['index']:02d}", "kind": "video"}
            for scene in script["scenes"]
        ]
        result = DirectClipSearch().execute({
            "output_dir": str(raw_dir),
            "queries": queries,
            "sources": sources or DEFAULT_SOURCES,
            "clips_per_query": clips_per_scene,
            "filters": {"min_duration": 1.5, "max_duration": 60, "min_width": 480},
            "extract_thumbnails": False,
            "skip_existing": True,
            "timeout_seconds": timeout,
        })
        for clip in (result.data or {}).get("clips", []):
            path = Path(clip.get("path", ""))
            if not path.exists():
                continue
            try:
                duration = probe_duration(path)
            except Exception:
                continue
            if duration < 1.5 or not clip.get("duration", duration):
                continue
            by_slot.setdefault(str(clip.get("slot_id", "")), []).append({
                "path": str(path.resolve()),
                "source": clip.get("source", "stock"),
                "source_url": clip.get("source_url", ""),
                "duration": round(duration, 3),
            })

    selected: list[dict[str, Any]] = []
    for i, scene in enumerate(script["scenes"]):
        slot = f"scene_{i + 1:02d}"
        candidates = by_slot.get(slot, [])
        if candidates:
            chosen = dict(candidates[0])
            chosen["slot"] = slot
            chosen["kind"] = "stock"
        else:
            clip_path = output_dir / f"title_{i + 1:02d}.mp4"
            make_title_clip(scene["text"], clip_path, duration=6.0)
            chosen = {
                "path": str(clip_path.resolve()),
                "source": "local-title-card",
                "source_url": "",
                "duration": 6.0,
                "slot": slot,
                "kind": "fallback",
            }
        selected.append(chosen)
    return selected


def make_title_clip(text: str, output: str | Path, duration: float = 6.0) -> Path:
    """Create a simple animated title clip from text (Pillow + FFmpeg)."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1280, 720

    try:
        from PIL import Image, ImageDraw, ImageFont

        image = Image.new("RGB", (width, height), (12, 18, 32))
        draw = ImageDraw.Draw(image)
        for y in range(height):
            shade = int(18 + 26 * y / height)
            draw.line((0, y, width, y), fill=(10, shade, shade + 22))

        font_path = next(
            (p for p in (
                "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ) if Path(p).exists()),
            None,
        )
        title_font = ImageFont.truetype(font_path, 58) if font_path else ImageFont.load_default()
        small_font = ImageFont.truetype(font_path, 30) if font_path else ImageFont.load_default()
        label = "OPENMONTAGE GENERATOR"
        lines = textwrap.wrap(_shorten(text, 90), width=28)[:4]

        draw.text((70, 70), label, font=small_font, fill=(120, 200, 220))
        y = height // 2 - (len(lines) * 70) // 2
        for line in lines:
            draw.text((70, y), line, font=title_font, fill=(245, 247, 250))
            y += 70
        draw.rectangle((70, height - 100, 270, height - 94), fill=(220, 90, 70))
        image_path = output.with_suffix(".png")
        image.save(image_path)
    except Exception:
        # Pillow is optional; a plain colour clip still keeps the pipeline alive.
        image_path = None

    if image_path and image_path.exists():
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
            "-t", f"{duration:.2f}",
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
                   "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,"
                   "fade=t=in:st=0:d=0.4,format=yuv420p",
            "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
            str(output),
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-t", f"{duration:.2f}",
            "-i", "color=c=0x101c2e:s=1280x720:r=30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
            "-pix_fmt", "yuv420p", str(output),
        ]
    subprocess.run(cmd, check=True, capture_output=True)
    if image_path and image_path.exists():
        image_path.unlink(missing_ok=True)
    return output
