"""Narration with word-level timings and fail-open fallbacks.

Priority: edge-tts (free, no key, word boundaries) -> Windows SAPI (offline)
-> generated silence. The generator never fails only because TTS is missing.
"""
from __future__ import annotations

import asyncio
import base64
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .script import detect_language


DEFAULT_VOICES = {"uk": "uk-UA-PolinaNeural", "en": "en-US-AriaNeural"}


@dataclass
class SpeechResult:
    path: Path
    duration: float
    words: list[dict[str, Any]]
    engine: str
    voice: str = ""

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["path"] = str(self.path)
        return data


def probe_duration(path: str | Path) -> float:
    """Return media duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {proc.stderr.strip()}")
    return float(proc.stdout.strip())


def _synthetic_words(text: str, duration: float) -> list[dict[str, Any]]:
    words = [w for w in text.split() if w.strip()]
    if not words or duration <= 0:
        return []
    step = duration / len(words)
    return [
        {
            "word": word,
            "start": round(i * step, 3),
            "end": round((i + 1) * step, 3),
        }
        for i, word in enumerate(words)
    ]


def _edge_tts(text: str, voice: str, output: Path, rate: str) -> list[dict[str, Any]] | None:
    try:
        import edge_tts
    except ImportError:
        return None

    async def run() -> list[dict[str, Any]]:
        comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
        audio = bytearray()
        words: list[dict[str, Any]] = []
        async for chunk in comm.stream():
            kind = chunk.get("type")
            if kind == "audio" and chunk.get("data"):
                audio.extend(chunk["data"])
            elif kind == "WordBoundary":
                start = int(chunk.get("offset", 0)) / 10_000_000
                length = int(chunk.get("duration", 0)) / 10_000_000
                words.append({
                    "word": str(chunk.get("text", "")).strip(),
                    "start": round(start, 3),
                    "end": round(start + length, 3),
                })
        if not audio:
            raise RuntimeError("edge-tts returned no audio data")
        output.write_bytes(audio)
        return [w for w in words if w["word"]]

    try:
        return asyncio.run(run())
    except Exception:
        return None


def _windows_sapi(text: str, output: Path) -> bool:
    if not shutil.which("powershell"):
        return False
    text_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as tmp:
            tmp.write(text)
            text_path = Path(tmp.name)
        script = (
            "Add-Type -AssemblyName System.Speech; "
            f"$t = [IO.File]::ReadAllText('{text_path.as_posix()}', [Text.Encoding]::UTF8); "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.SetOutputToWaveFile('{output.as_posix()}'); $s.Speak($t); $s.Dispose()"
        )
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-EncodedCommand", encoded],
            capture_output=True, text=True, timeout=180,
        )
        return proc.returncode == 0 and output.exists() and output.stat().st_size > 1024
    except Exception:
        return False
    finally:
        if text_path is not None:
            try:
                text_path.unlink(missing_ok=True)
            except Exception:
                pass


def _silence(text: str, output: Path) -> float:
    duration = max(2.0, len(text.split()) * 0.42 + 1.0)
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-t", f"{duration:.2f}",
        "-i", "anullsrc=channel_layout=mono:sample_rate=24000",
        "-c:a", "libmp3lame", "-q:a", "9", str(output),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return duration


def synthesize(
    text: str,
    output: str | Path,
    *,
    voice: str | None = None,
    language: str | None = None,
    rate: str = "+0%",
) -> SpeechResult:
    """Synthesize narration and return audio duration + word timings."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    lang = language or detect_language(text)
    chosen_voice = voice or DEFAULT_VOICES.get(lang, DEFAULT_VOICES["en"])

    words = _edge_tts(text, chosen_voice, output, rate)
    engine = "edge-tts"
    if words is None and _windows_sapi(text, output):
        engine = "windows-sapi"
        words = []
    if not output.exists() or output.stat().st_size < 1024:
        duration = _silence(text, output)
        engine = "silence"
        words = []
    else:
        duration = probe_duration(output)

    if not words:
        words = _synthetic_words(text, duration)
    return SpeechResult(output, round(duration, 3), words, engine, chosen_voice)


def save_timing_report(result: SpeechResult, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
