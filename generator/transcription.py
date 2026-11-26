"""Optional local transcription (Graphify-Labs/graphify video-extra pattern).

faster-whisper + yt-dlp run locally, keep media on the machine and produce the
same ``{word, start, end}`` shape used by the generator's subtitle builder.
Nothing is imported until ``transcribe()`` is called with an explicit flag.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .downloads import download_url


def transcribe(
    media: str | Path,
    *,
    model_size: str = "base",
    device: str = "cpu",
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Transcribe a local file or URL into words + an SRT file."""
    source = str(media)
    if source.startswith(("http://", "https://")):
        output_dir = Path(output_dir or Path.cwd())
        download = download_url(source, output_dir)
        if not download.get("path"):
            return {"success": False, "error": download.get("error", "download failed")}
        source = download["path"]
        url_backend = download["backend"]
    else:
        url_backend = None

    path = Path(source)
    if not path.exists():
        return {"success": False, "error": f"Media file not found: {source}"}

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return {
            "success": False,
            "error": "faster-whisper is not installed; run: pip install faster-whisper",
        }

    try:
        model = WhisperModel(model_size, device=device, compute_type="int8")
        segments, info = model.transcribe(str(path), word_timestamps=True, vad_filter=True)
        words: list[dict[str, Any]] = []
        for segment in segments:
            for word in segment.words or ():
                text = str(word.word).strip()
                if text:
                    words.append({
                        "word": text,
                        "start": round(float(word.start), 3),
                        "end": round(float(word.end), 3),
                    })
        return {
            "success": True,
            "path": str(path.resolve()),
            "language": getattr(info, "language", None),
            "model": model_size,
            "download_backend": url_backend,
            "words": words,
        }
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}
