"""Deterministic prompt -> narration script conversion.

No LLM or API key is needed: a topic becomes a short structured explainer,
or a user-supplied script file is split into scene-sized chunks.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


CYRILLIC_RE = re.compile(r"[А-Яа-яІіЇїЄєҐґ]")
SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")

UK_TEMPLATES = [
    "Сьогодні ми розглянемо тему: {topic}.",
    "Чому це важливо? {topic_cap} впливає на те, як ми бачимо звичні речі щодня.",
    "Розберімося крок за кроком і знайдемо головну ідею.",
    "Коротко про головне: {topic} — це цікавий напрямок, який варто дослідити.",
]

EN_TEMPLATES = [
    "Today we will look at {topic}.",
    "Why does it matter? {topic_cap} changes the way we see familiar things.",
    "Let us break it down step by step and find the main idea.",
    "In short, {topic} is a direction worth exploring.",
]


def detect_language(text: str) -> str:
    """Return 'uk' when Cyrillic dominates, otherwise 'en'."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "en"
    cyrillic = sum(1 for c in letters if CYRILLIC_RE.match(c))
    return "uk" if cyrillic / len(letters) > 0.15 else "en"


def clean_topic(prompt: str) -> str:
    """Normalize a prompt into a short topic phrase."""
    topic = " ".join(prompt.strip().split())
    topic = topic.strip("\"'«»„“” \t\n")
    # A long free-form prompt is already a script; use its first sentence.
    if len(topic) > 160:
        topic = SENTENCE_RE.split(topic)[0]
    return topic.rstrip(".") or "нова ідея"


def split_text(text: str, count: int) -> list[str]:
    """Split text into at most ``count`` readable scene chunks."""
    text = " ".join(text.split())
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units = paragraphs if len(paragraphs) > 1 else SENTENCE_RE.split(text)
    units = [u.strip() for u in units if u.strip()]
    if len(units) <= count:
        return units

    # Greedy grouping by word count so scenes have similar reading length.
    target = max(1, len(text.split()) // count)
    chunks: list[list[str]] = [[]]
    for unit in units:
        if chunks[-1] and sum(len(c.split()) for c in chunks[-1]) + len(unit.split()) > target:
            chunks.append([])
        chunks[-1].append(unit)
    return [" ".join(chunk) for chunk in chunks[:count] if chunk]


def _template_scenes(topic: str, count: int, language: str) -> list[str]:
    templates = UK_TEMPLATES if language == "uk" else EN_TEMPLATES
    topic_cap = topic[:1].upper() + topic[1:]
    scenes = [t.format(topic=topic, topic_cap=topic_cap) for t in templates]
    while len(scenes) < count:
        n = len(scenes) + 1
        if language == "uk":
            scenes.append(f"Ось кілька думок, які допоможуть зрозуміти тему ближче, крок {n}.")
        else:
            scenes.append(f"Here are a few thoughts that bring us closer to the idea, step {n}.")
    return scenes[:count]


def build_script(
    *,
    prompt: str | None = None,
    script_file: str | Path | None = None,
    scenes: int = 4,
    language: str | None = None,
) -> dict[str, Any]:
    """Build a script dictionary with title, language and scene texts."""
    if scenes < 1:
        raise ValueError("scenes must be >= 1")

    if script_file:
        source = Path(script_file).read_text(encoding="utf-8")
    elif prompt:
        source = prompt.strip()
    else:
        raise ValueError("Provide a prompt or a --script-file")

    lang = language or detect_language(source)
    if lang not in ("uk", "en"):
        raise ValueError("language must be 'uk' or 'en'")

    topic = clean_topic(source)
    if script_file or len(SENTENCE_RE.split(source.strip())) > 1:
        scene_texts = split_text(source, scenes)
    else:
        scene_texts = _template_scenes(topic, scenes, lang)
    if not scene_texts:
        raise ValueError("No script text found")

    return {
        "title": topic,
        "language": lang,
        "narration": " ".join(scene_texts),
        "scenes": [
            {"index": i + 1, "text": text, "visual_query": _visual_query(text, lang)}
            for i, text in enumerate(scene_texts)
        ],
    }


def _visual_query(text: str, language: str) -> str:
    """Make a short stock-footage search query from a scene sentence."""
    stop = {
        "uk": {"сьогодні", "ми", "розглянемо", "тему", "чому", "це", "важливо",
               "як", "що", "про", "і", "в", "на", "з", "до", "для", "або"},
        "en": {"today", "we", "will", "look", "at", "why", "does", "it", "matter",
               "the", "a", "an", "and", "of", "to", "in", "for", "is"},
    }[language]
    words = re.findall(r"[\wА-Яа-яІіЇїЄєҐґ-]+", text.lower())
    kept = [w for w in words if w not in stop and len(w) > 2][:6]
    return " ".join(kept) or ("city" if language == "en" else "місто")
