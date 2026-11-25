"""Smoke tests for the keyless generator (no network, no API keys)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from generator.cli import _scene_durations, build_parser, run
from generator.script import build_script, detect_language


class ScriptTests(unittest.TestCase):
    def test_language_detection(self) -> None:
        self.assertEqual(detect_language("Чому небо синє?"), "uk")
        self.assertEqual(detect_language("Why is the sky blue?"), "en")

    def test_template_script(self) -> None:
        script = build_script(prompt="чому небо синє", scenes=3, language="uk")
        self.assertEqual(len(script["scenes"]), 3)
        self.assertIn("небо синє", script["narration"])

    def test_script_file_is_split(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "script.txt"
            path.write_text("First scene here.\n\nSecond scene here.", encoding="utf-8")
            script = build_script(script_file=path, scenes=2, language="en")
            self.assertEqual(len(script["scenes"]), 2)


class CliTests(unittest.TestCase):
    def test_dry_run(self) -> None:
        args = build_parser().parse_args(["чому небо синє", "--dry-run", "--scenes", "2"])
        plan = run(args)
        self.assertEqual(plan["language"], "uk")
        self.assertEqual(len(plan["scenes"]), 2)
        self.assertFalse(Path(plan.get("project_dir", "missing")).exists())

    def test_scene_durations(self) -> None:
        words = [
            {"word": "one", "start": 0.0, "end": 0.5},
            {"word": "two", "start": 0.6, "end": 1.1},
        ]
        durations = _scene_durations(words, ["one two", "three"], 4.0)
        self.assertEqual(len(durations), 2)
        self.assertTrue(all(d >= 1.5 for d in durations))


if __name__ == "__main__":
    unittest.main()
