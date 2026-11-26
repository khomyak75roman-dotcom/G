"""Deterministic pause removal for word-level timings (no ASR required).

Implements the "Прибери паузи" refinement used by graphify's video extra:
silence is collapsed in the timing stream, so subtitles stay aligned with a
silence-trimmed narration track.
"""
from __future__ import annotations

from typing import Any


GAP_THRESHOLD = 0.35
MIN_GAP = 0.12


def collapse_gaps(
    words: list[dict[str, Any]],
    threshold: float = GAP_THRESHOLD,
    min_gap: float = MIN_GAP,
) -> list[dict[str, Any]]:
    """Shift words left when the gap before them exceeds ``threshold``.

    The original dictionaries are left untouched.  Long pauses shrink to
    ``min_gap``; short pauses are preserved.
    """
    result: list[dict[str, Any]] = []
    shift = 0.0
    previous_end: float | None = None
    for word in sorted(words, key=lambda item: float(item.get("start", 0))):
        start = float(word.get("start", 0)) - shift
        end = float(word.get("end", start)) - shift
        if previous_end is not None:
            gap = start - previous_end
            if gap > threshold:
                removed = gap - min_gap
                shift += removed
                start -= removed
                end -= removed
        start = max(0.0, start)
        end = max(start + 0.01, end)
        item = dict(word)
        item["start"] = round(start, 3)
        item["end"] = round(end, 3)
        result.append(item)
        previous_end = end
    return result
