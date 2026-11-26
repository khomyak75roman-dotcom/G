"""URL download ladder: yt-dlp -> cobalt -> gallery-dl (all keyless).

Repositories: yt-dlp/yt-dlp, imputnet/cobalt, mikf/gallery-dl.
Cobalt is an optional local/remote HTTP endpoint configured with
``COBALT_API_URL``; gallery-dl is used when yt-dlp cannot handle the URL.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


def _newest_file(directory: Path, since: float, suffixes: tuple[str, ...] = ()) -> Path | None:
    files = [
        p for p in directory.iterdir()
        if p.is_file() and p.stat().st_mtime >= since - 2
        and (not suffixes or p.suffix.lower() in suffixes)
    ]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def _with_ytdlp(url: str, output_dir: Path) -> Path | None:
    try:
        import yt_dlp
    except ImportError:
        return None
    before = time.time()
    try:
        options = {
            "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
            "format": "best[height<=720]/best",
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        return _newest_file(output_dir, before)
    except Exception:
        return None


def _with_cobalt(url: str, output_dir: Path) -> Path | None:
    endpoint = os.environ.get("COBALT_API_URL", "").strip().rstrip("/")
    if not endpoint:
        return None
    try:
        payload = json.dumps({"url": url, "videoQuality": "720"}).encode("utf-8")
        request = urllib.request.Request(
            endpoint, data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        target = data.get("url") or data.get("picker", [{}])[0].get("url")
        if not target:
            return None
        with urllib.request.urlopen(target, timeout=60) as response:
            suffix = Path(target.split("?", 1)[0]).suffix or ".mp4"
            result = output_dir / f"cobalt-{int(time.time())}{suffix}"
            result.write_bytes(response.read())
        return result
    except Exception:
        return None


def _with_gallery_dl(url: str, output_dir: Path) -> Path | None:
    before = time.time()
    try:
        subprocess.run(
            [sys.executable, "-m", "gallery_dl", "--destination", str(output_dir), url],
            capture_output=True, timeout=180, check=False,
        )
        return _newest_file(output_dir, before)
    except Exception:
        return None


def download_url(url: str, output_dir: str | Path) -> dict[str, Any]:
    """Download ``url`` with the first working backend; fail closed."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, handler in (
        ("yt-dlp", _with_ytdlp),
        ("cobalt", _with_cobalt),
        ("gallery-dl", _with_gallery_dl),
    ):
        path = handler(url, output_dir)
        if path and path.exists() and path.stat().st_size > 1024:
            return {"backend": name, "path": str(path.resolve())}
    return {
        "backend": None,
        "path": None,
        "error": (
            "Could not download URL with yt-dlp, cobalt or gallery-dl. "
            "Set COBALT_API_URL for a local cobalt instance."
        ),
    }


def has_downloader() -> bool:
    """True when at least one URL backend can be attempted."""
    if shutil.which("gallery-dl"):
        return True
    try:
        import importlib.util
        return any(importlib.util.find_spec(name) for name in ("yt_dlp", "gallery_dl"))
    except (ImportError, ValueError):
        return False
