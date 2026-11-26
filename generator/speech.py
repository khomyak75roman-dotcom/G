"""Narration with word-level timings and fail-open fallbacks.

TTS ladder: edge-tts (free, no key, native word boundaries) -> Piper (local
CPU, Ukrainian voices) -> Kokoro (optional GPU tier) -> Windows SAPI (offline)
-> generated silence. The generator never fails only because TTS is missing.

Upstream repos: rany2/edge-tts, rhasspy/piper, rhasspy/piper-voices,
hexgrad/kokoro. See ``generator/external_repos.py`` for the full catalogue.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .script import detect_language


DEFAULT_VOICES = {"uk": "uk-UA-PolinaNeural", "en": "en-US-AriaNeural"}
PIPER_VOICES = {"uk": "uk_UA-lada-x_low", "en": "en_US-lessac-medium"}
KOKORO_VOICES = {"en": "af_heart"}
TTS_BACKENDS = ("auto", "edge", "piper", "kokoro", "sapi")
TTS_LADDER = "tts_save"


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


def _piper_data_dir() -> Path | None:
    """Point the compiled espeak bridge at an ASCII-only data directory.

    piper's Windows extension reads ``ESPEAK_DATA_PATH`` from the process
    environment.  A Cyrillic user profile (e.g. C:\\Users\\Роман) is mangled by
    that bridge, so the bundled data is mirrored to an ASCII location once.
    """
    try:
        import piper
    except ImportError:
        return None
    bundled = Path(piper.__file__).parent / "espeak-ng-data"
    override = os.environ.get("OM_ESPEAK_DATA", "").strip()
    if override:
        target = Path(override)
    elif os.name == "nt":
        try:
            str(bundled).encode("ascii")
            target = bundled
        except UnicodeEncodeError:
            drive = os.environ.get("SystemDrive", "C:").rstrip(":")
            target = Path(f"{drive}:/omtest/piper/espeak-ng-data")
    else:
        target = bundled
    try:
        if target.resolve() != bundled.resolve() and bundled.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            if not (target / "phontab").exists():
                shutil.copytree(bundled, target, dirs_exist_ok=True)
    except Exception:
        return None
    os.environ["ESPEAK_DATA_PATH"] = str(target)
    return target


def _write_wav(samples: bytes, output: Path, sample_rate: int) -> None:
    with wave.open(str(output), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(samples)


def _piper(text: str, output: Path, model: str, voices_dir: Path | None = None) -> bool:
    """Local CPU tier using rhasspy/piper + piper-voices (no API key)."""
    try:
        from piper import PiperVoice
        from piper.download_voices import download_voice
    except ImportError:
        return False
    data_dir = _piper_data_dir()
    if data_dir is None:
        return False
    voice_dir = voices_dir or Path(
        os.environ.get("PIPER_VOICES_DIR", str(Path.home() / ".piper" / "models"))
    )
    wav_path = output.with_name(output.stem + ".piper.wav")
    try:
        voice_dir.mkdir(parents=True, exist_ok=True)
        download_voice(model, voice_dir)
        model_path = voice_dir / f"{model}.onnx"
        config_path = voice_dir / f"{model}.onnx.json"
        if not model_path.exists():
            return False
        voice = PiperVoice.load(model_path, config_path=config_path, espeak_data_dir=data_dir)
        audio = bytearray()
        sample_rate = voice.config.sample_rate
        for chunk in voice.synthesize(text):
            audio.extend(chunk.audio_int16_bytes)
        if not audio:
            return False
        _write_wav(bytes(audio), wav_path, sample_rate)
        if output.suffix.lower() == ".wav":
            shutil.move(str(wav_path), str(output))
        else:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(wav_path), "-c:a", "libmp3lame",
                 "-q:a", "4", str(output)],
                check=True, capture_output=True,
            )
        return output.exists() and output.stat().st_size > 1024
    except Exception:
        return False
    finally:
        wav_path.unlink(missing_ok=True)


def _kokoro(text: str, output: Path, lang: str) -> bool:
    """Optional hexgrad/kokoro tier; activates only when kokoro is installed."""
    if lang != "en":
        return False
    try:
        import numpy as np
        from kokoro import KPipeline
    except ImportError:
        return False
    wav_path = output.with_name(output.stem + ".kokoro.wav")
    try:
        pipeline = KPipeline(lang_code="a")
        voice = os.environ.get("KOKORO_VOICE", KOKORO_VOICES["en"])
        parts: list[np.ndarray] = []
        for _graphemes, _phonemes, audio in pipeline(text, voice=voice):
            parts.append(np.asarray(audio).reshape(-1))
        if not parts:
            return False
        samples = np.concatenate(parts)
        pcm = np.clip(samples * 32767, -32768, 32767).astype("<i2").tobytes()
        _write_wav(pcm, wav_path, 24000)
        if output.suffix.lower() == ".wav":
            shutil.move(str(wav_path), str(output))
        else:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(wav_path), "-c:a", "libmp3lame",
                 "-q:a", "4", str(output)],
                check=True, capture_output=True,
            )
        return output.exists() and output.stat().st_size > 1024
    except Exception:
        return False
    finally:
        wav_path.unlink(missing_ok=True)


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
    backend: str = "auto",
    piper_voice: str | None = None,
) -> SpeechResult:
    """Synthesize narration and return audio duration + word timings.

    ``backend="auto"`` walks the full ladder; an explicit backend tries only
    that tier and still falls back to silence so the CLI never hard-fails.
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    lang = language or detect_language(text)
    chosen_voice = voice or DEFAULT_VOICES.get(lang, DEFAULT_VOICES["en"])
    if backend not in TTS_BACKENDS:
        raise ValueError(f"Unknown TTS backend: {backend}")
    allowed = TTS_BACKENDS[1:] if backend == "auto" else (backend,)

    words: list[dict[str, Any]] | None = None
    engine = "silence"
    if "edge" in allowed:
        words = _edge_tts(text, chosen_voice, output, rate)
        if words is not None:
            engine = "edge-tts"
    if words is None and "piper" in allowed:
        model = piper_voice or PIPER_VOICES.get(lang, PIPER_VOICES["en"])
        if _piper(text, output, model):
            engine = "piper"
            words = []
            chosen_voice = model
    if words is None and "kokoro" in allowed and _kokoro(text, output, lang):
        engine = "kokoro"
        words = []
        chosen_voice = os.environ.get("KOKORO_VOICE", KOKORO_VOICES.get(lang, ""))
    if words is None and "sapi" in allowed and _windows_sapi(text, output):
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
