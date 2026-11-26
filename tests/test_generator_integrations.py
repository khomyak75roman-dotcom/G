"""Tests for the optional open-source integrations of the keyless generator."""
from __future__ import annotations

import io
import json
import os
import sys
import types
from pathlib import Path

import pytest

from generator import downloads, external_repos, network, pause_removal, translation
from generator.cli import build_parser, main, run
from generator.speech import PIPER_VOICES, TTS_LADDER, synthesize


def test_collapse_gaps_shrinks_only_long_pauses():
    words = [
        {"word": "a", "start": 0.0, "end": 0.2},
        {"word": "b", "start": 0.3, "end": 0.5},
        {"word": "c", "start": 2.0, "end": 2.3},
        {"word": "d", "start": 2.4, "end": 2.6},
    ]
    result = pause_removal.collapse_gaps(words, threshold=0.5)
    assert [w["word"] for w in result] == ["a", "b", "c", "d"]
    assert result[1]["start"] == 0.3
    assert result[2]["start"] == pytest.approx(0.62, abs=0.01)
    assert result[3]["start"] == pytest.approx(1.02, abs=0.01)
    assert words[2]["start"] == 2.0  # inputs are not mutated


def test_repo_report_has_all_repo_groups_and_honest_states():
    report = external_repos.report()
    categories = set(report["categories"])
    assert {
        "tts", "background", "acquisition", "transcription", "local_video",
        "benchmark", "methodology", "networking",
    } <= categories
    assert sum(report["counts"].values()) == len(external_repos.REPOS)
    states = {item["state"] for item in report["repos"]}
    assert states <= {
        "active", "configured", "gpu-required", "not-enabled", "upstream",
        "reference-only", "needs-verification", "out-of-scope",
    }
    items = {item["key"]: item for item in report["repos"]}
    assert items["edge_tts"]["repo"] == "rany2/edge-tts"
    assert items["openverse"]["state"] == "upstream"
    assert items["rembg"]["state"] == "active"
    assert items["faster_whisper"]["repo"] == "SYSTRAN/faster-whisper"
    assert items["hunyuan_video"]["repo"] == "Tencent-Hunyuan/HunyuanVideo"
    assert items["duix_avatar"]["repo"] == "duixcom/Duix-Avatar"
    assert report["tts_ladder"]["name"] == TTS_LADDER == "tts_save"
    assert report["tts_ladder"]["order"][:2] == ["edge-tts", "piper"]
    assert all({"repo", "category", "role", "state", "ready"} <= set(item) for item in report["repos"])


def test_references_and_networking_repos_are_never_activated():
    report = external_repos.report()
    items = {item["key"]: item for item in report["repos"]}
    assert items["moneyprinter_turbo"]["state"] == "reference-only"
    assert items["chatterbox"]["state"] == "reference-only"
    assert items["herk_edit_kit"]["state"] == "needs-verification"
    assert items["goodbyedpi"]["state"] == "out-of-scope"
    assert items["cloudflare_r2"]["state"] == "out-of-scope"
    non_runtime = {k: v for k, v in items.items() if v["state"] in {
        "reference-only", "needs-verification", "out-of-scope",
    }}
    assert non_runtime and all(not item["ready"] for item in non_runtime.values())


def test_searxng_adapter_is_keyless_but_opt_in(monkeypatch):
    from tools.video.stock_sources import get_source

    source = get_source("searxng")
    monkeypatch.delenv("SEARXNG_URL", raising=False)
    assert source.is_available() is False
    monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
    assert source.is_available() is True


def test_speech_rejects_unknown_backend(tmp_path):
    with pytest.raises(ValueError):
        synthesize("text", tmp_path / "a.mp3", backend="unknown")
    assert PIPER_VOICES["uk"].startswith("uk_UA-")


def test_download_ladder_uses_first_backend(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(downloads, "_with_ytdlp", lambda url, out: calls.append("yt") or None)
    monkeypatch.setattr(downloads, "_with_cobalt", lambda url, out: calls.append("co") or None)

    def gallery(_url, out):
        calls.append("gallery")
        target = out / "clip.mp4"
        target.write_bytes(b"x" * 2048)
        return target

    monkeypatch.setattr(downloads, "_with_gallery_dl", gallery)
    result = downloads.download_url("https://example.test/clip", tmp_path)
    assert calls == ["yt", "co", "gallery"]
    assert result == {"backend": "gallery-dl", "path": str((tmp_path / "clip.mp4").resolve())}


def test_download_ladder_fails_closed(monkeypatch, tmp_path):
    for name in ("_with_ytdlp", "_with_cobalt", "_with_gallery_dl"):
        monkeypatch.setattr(downloads, name, lambda _url, _out: None)
    result = downloads.download_url("https://example.test/clip", tmp_path)
    assert result["backend"] is None and result["path"] is None


def test_transcription_maps_whisper_words(monkeypatch, tmp_path):
    media = tmp_path / "voice.wav"
    media.write_bytes(b"RIFF" + b"0" * 100)

    segment = types.SimpleNamespace(
        words=[
            types.SimpleNamespace(word=" привіт", start=0.1, end=0.4),
            types.SimpleNamespace(word=" світ", start=0.5, end=0.9),
        ]
    )

    class FakeWhisperModel:
        def __init__(self, model_size, device, compute_type):
            assert (model_size, device, compute_type) == ("tiny", "cpu", "int8")

        def transcribe(self, path, **kwargs):
            assert kwargs["word_timestamps"] is True
            return iter([segment]), types.SimpleNamespace(language="uk")

    fake = types.ModuleType("faster_whisper")
    fake.WhisperModel = FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake)

    from generator.transcription import transcribe
    result = transcribe(str(media), model_size="tiny")
    assert result["success"] is True
    assert result["language"] == "uk"
    assert [w["word"] for w in result["words"]] == ["привіт", "світ"]


def test_translate_srt_preserves_timings(monkeypatch, tmp_path):
    srt = tmp_path / "sub.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nПривіт світ\n\n"
        "2\n00:00:01,000 --> 00:00:02,000\nДругий рядок\n",
        encoding="utf-8",
    )

    class FakeResponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout=30):
        payload = json.loads(request.data)
        return FakeResponse(json.dumps({"translatedText": f"EN:{payload['q']}"}).encode())

    monkeypatch.setattr(translation.urllib.request, "urlopen", fake_urlopen)
    result = translation.translate_srt(srt, "en", source="uk", endpoint="http://localhost:5000")
    assert result["cues"] == 2
    text = srt.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:01,000" in text
    assert "EN:Привіт світ" in text


def test_new_flags_are_opt_in_for_dry_run():
    parser = build_parser()
    args = parser.parse_args(["тема", "--dry-run"])
    assert args.tts == "auto" and args.bg_engine == "rembg"
    plan = run(args)
    assert set(plan) == {"project_id", "title", "language", "profile", "scenes", "sources", "offline"}

    args = parser.parse_args(["тема", "--dry-run", "--tts", "piper", "--remove-bg", "--translate", "en"])
    plan = run(args)
    assert plan["tts_backend"] == "piper"
    assert plan["background"]["engine"] == "rembg"
    assert plan["translate_to"] == "en"


def test_transcription_only_dry_run_needs_no_topic(capsys):
    assert main(["--transcribe", "C:/tmp/lecture.mp4", "--dry-run"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["title"] == "lecture"
    assert plan["transcribe"] == "C:/tmp/lecture.mp4"
    assert main([]) == 2


def test_transcribe_only_skips_narration(monkeypatch, tmp_path):
    from generator import cli

    (tmp_path / "artifacts").mkdir()
    monkeypatch.setattr("lib.checkpoint.init_project", lambda *_a, **_k: str(tmp_path))

    def forbidden_synthesize(*_a, **_k):
        pytest.fail("transcription-only runs must not synthesize narration")

    monkeypatch.setattr(cli, "synthesize", forbidden_synthesize)
    monkeypatch.setattr(
        "generator.transcription.transcribe",
        lambda *_a, **_k: {"success": True, "path": "voice.wav", "language": "uk"},
    )
    plan = run(build_parser().parse_args(["--transcribe", "voice.wav"]))
    assert "narration" not in plan
    assert plan["transcription"]["success"] is True


def test_proxy_report_redacts_credentials(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://user:secret@proxy.example:8080")
    monkeypatch.setenv("NO_PROXY", "localhost")
    report = network.proxy_report()
    assert report["proxy_env_configured"] is True
    assert report["endpoints"]["HTTPS_PROXY"] == "http://proxy.example:8080"
    assert report["endpoints"]["NO_PROXY"] == "<all hosts>"
    assert "secret" not in json.dumps(report)
    assert "user" not in json.dumps(report)


def test_network_check_needs_no_prompt(monkeypatch, capsys):
    monkeypatch.setattr(
        network, "check_sources",
        lambda: {"sources": {}, "reachable": [], "proxy": network.proxy_report()},
    )
    assert main(["--network-check"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["reachable"] == []


def test_optional_model_caches_live_outside_the_repository():
    from generator.background import _selfie_model_path
    from generator.speech import _piper_data_dir

    repo = Path(__file__).resolve().parents[1]
    paths = [_selfie_model_path()]
    if os.name == "nt" and pytest.importorskip("piper"):
        piper_dir = _piper_data_dir()
        if piper_dir:
            paths.append(piper_dir)
    for path in paths:
        assert path.is_absolute()
        assert repo not in path.resolve().parents
