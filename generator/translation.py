"""Optional subtitle translation via LibreTranslate (no API key required).

Point ``LIBRETRANSLATE_URL`` at a local or trusted instance (default:
http://localhost:5000).  Translation is strictly opt-in; if the service is
unreachable the original SRT is returned unchanged.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

TIMING = re.compile(r"^\s*\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*")


def translate_srt(
    srt_path: str | Path,
    target: str,
    source: str = "auto",
    endpoint: str | None = None,
) -> dict[str, object]:
    """Translate cue text in place. Returns a small status dictionary."""
    path = Path(srt_path)
    if not path.exists():
        return {"success": False, "error": f"SRT not found: {path}"}
    url = (endpoint or os.environ.get("LIBRETRANSLATE_URL", "http://localhost:5000")).rstrip("/")
    raw = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", raw.strip())
    cues: list[tuple[list[str], list[str]]] = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3 or not any(TIMING.match(line) for line in lines):
            continue
        index = next(i for i, line in enumerate(lines) if TIMING.match(line))
        cues.append((lines[:index + 1], [line for line in lines[index + 1:] if line.strip()]))

    translated: list[str] = []
    for prefix, text_lines in cues:
        text = " ".join(text_lines)
        if not text:
            translated.append("\n".join(prefix))
            continue
        payload = json.dumps({
            "q": text, "source": source, "target": target, "format": "text",
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{url}/translate", data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        rendered = str(result.get("translatedText", text))
        translated.append("\n".join([*prefix, rendered]))

    if translated:
        path.write_text("\n\n".join(translated) + "\n", encoding="utf-8")
    return {
        "success": True,
        "target": target,
        "source": source,
        "endpoint": url,
        "cues": len(cues),
        "path": str(path.resolve()),
    }
