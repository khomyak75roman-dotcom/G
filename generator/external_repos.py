"""Catalogue of open-source repos known to the keyless generator.

Entry point: ``python -m generator --repos``.

Nothing here imports a heavy dependency at module import time. Detection is
lazy so the keyless CLI still starts instantly on a machine without PyTorch,
CUDA, Docker or optional media packages.

States
------
active             usable right now (python package or command is installed)
configured         optional HTTP service URL is present in the environment
gpu-required       local engine is supported, but this machine has no CUDA/MPS
not-enabled        supported, but the optional dependency/repo path is absent
upstream           already provided by an existing OpenMontage adapter
reference-only     studied for benchmarks/methodology, never imported or run
needs-verification owner/name or licence was not confirmed in the source list
out-of-scope       networking/traffic tooling; deliberately not integrated

The networking/traffic repositories supplied in "Партія 26" are catalogued as
``out-of-scope``. OpenMontage does not bypass network restrictions, rotate
proxy pools or route media through third-party tunnels, so none of them is
activated by the generator.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


TTS_LADDER = {
    "name": "tts_save",
    "order": ["edge-tts", "piper", "kokoro", "windows-sapi", "silence"],
    "gpu_tiers": ["voxcpm2", "yovoice"],
}


@dataclass(frozen=True)
class RepoSpec:
    key: str
    repo: str
    category: str
    role: str
    module: str = ""
    command: str = ""
    env: str = ""
    gpu: bool = False
    path_env: str = ""
    note: str = ""
    license_note: str = ""
    forced_state: str = ""


def _r(key: str, repo: str, category: str, role: str, **kwargs: Any) -> RepoSpec:
    return RepoSpec(key=key, repo=repo, category=category, role=role, **kwargs)


# Keep the user's grouping. A runtime repo may be represented by an existing
# OpenMontage adapter; benchmark/methodology repos are read-only references.
REPOS: tuple[RepoSpec, ...] = (
    # --- TTS ladder ``tts_save`` -----------------------------------------
    _r("edge_tts", "rany2/edge-tts", "tts", "Level 1: hosted neural TTS with native word boundaries", module="edge_tts"),
    _r("piper", "rhasspy/piper", "tts", "Level 2: the local Ukrainian TTS tier (uk_UA, CPU, MIT)", module="piper", command="piper"),
    _r("piper_voices", "rhasspy/piper-voices", "tts", "Piper voice models (Hugging Face rhasspy/piper-voices)", env="PIPER_VOICES_DIR"),
    _r("voxcpm2", "OpenBMB/VoxCPM2", "tts", "GPU cloning-TTS tier: Apache-2.0 code and weights", gpu=True, path_env="VOXCPM2_REPO", note="weights may be packaged; CUDA/MPS required", license_note="Apache-2.0"),
    _r("kokoro", "hexgrad/kokoro", "tts", "Optional level 3 TTS tier", module="kokoro", gpu=True),
    _r("yovoice", "leemysw/yovoice", "tts", "Deferred own-voice tier (not enabled until stable)", gpu=True, path_env="YOVOICE_REPO"),

    # --- Background replacement -----------------------------------------
    _r("rembg", "danielgatis/rembg", "background", "ffmpeg raw pipe + rembg u2net matting", module="rembg"),
    _r("rvm", "PeterL1n/RobustVideoMatting", "background", "RVM ONNX high-quality video matting", env="RVM_ONNX_DIR"),
    _r("u2net", "xuebinqin/U-2-Net", "background", "U-2-Net backbone behind rembg's u2net session", module="rembg", note="via rembg u2net session"),
    _r("mediapipe", "google-ai-edge/mediapipe", "background", "Selfie segmentation preview", module="mediapipe", note="MediaPipe Selfie Segmentation"),
    _r("backgroundremover", "unverified/backgroundremover", "background", "Alternate matting reference; fallback is ffmpeg chromakey", note="owner not confirmed in source list", forced_state="needs-verification"),

    # --- Download / search / translation ---------------------------------
    _r("yt_dlp", "yt-dlp/yt-dlp", "acquisition", "Primary URL video/audio download", module="yt_dlp"),
    _r("cobalt", "imputnet/cobalt", "acquisition", "Fallback download API behind yt-dlp", env="COBALT_API_URL"),
    _r("gallery_dl", "mikf/gallery-dl", "acquisition", "Third fallback gallery/image downloader", module="gallery_dl", command="gallery-dl"),
    _r("libretranslate", "LibreTranslate/LibreTranslate", "acquisition", "Keyless subtitle translation", env="LIBRETRANSLATE_URL"),
    _r("searxng", "searxng/searxng", "acquisition", "Keyless clip metasearch", env="SEARXNG_URL"),
    _r("openverse", "WordPress/openverse", "acquisition", "Keyless image fallback already in OpenMontage", note="stock_sources/openverse.py"),

    # --- Transcription ----------------------------------------------------
    _r("graphify_video", "Graphify-Labs/graphify", "transcription", "graphify[video] pattern: transcription to SRT without keys", module="faster_whisper", note="re-used in generator/transcription.py"),
    _r("faster_whisper", "SYSTRAN/faster-whisper", "transcription", "Local Whisper engine used by the generator", module="faster_whisper"),
    _r("whisperx", "m-bain/whisperX", "transcription", "Word-level alignment / SRT refinement", module="whisperx", note="optional; not installed here"),

    # --- Local GPU video / avatars ----------------------------------------
    _r("framepack", "lllyasviel/FramePack", "local_video", "Primary local frame generator (~6 GB VRAM)", gpu=True, path_env="FRAMEPACK_REPO"),
    _r("hunyuan_video", "Tencent-Hunyuan/HunyuanVideo", "local_video", "HunyuanVideo local generation engine", gpu=True, path_env="HUNYUAN_VIDEO_REPO"),
    _r("cogvideo", "zai-org/CogVideo", "local_video", "CogVideo / CogVideoX local generation", gpu=True, path_env="COGVIDEO_REPO"),
    _r("ltx_video", "Lightricks/LTX-Video", "local_video", "LTX-Video local clips without keys", gpu=True, path_env="LTX_VIDEO_REPO", note="ltx_video_local tool already registered"),
    _r("wan22", "Wan-Video/Wan2.2", "local_video", "Wan 2.2 local generation", gpu=True, path_env="WAN22_REPO"),
    _r("wan2gp", "LTX/Wan2GP", "local_video", "Wan 2.1/2.2 variant for weaker GPUs", gpu=True, path_env="WAN2GP_REPO"),
    _r("wan30", "AlibabaCloud-Official/Wan3.0", "local_video", "Wan 3.0 local generation engine", gpu=True, path_env="WAN30_REPO", note="name supplied by user; verify before cloning"),
    _r("svd", "Stability-AI/generative-models", "local_video", "Stable Video Diffusion engine", gpu=True, path_env="SVD_REPO"),
    _r("duix_avatar", "duixcom/Duix-Avatar", "local_video", "Offline AI avatar / presenter without keys", gpu=True, path_env="DUIX_AVATAR_REPO"),
    _r("open_higgsfield", "wide-trace/open-higgsfield", "local_video", "Open Higgsfield with self-QC", gpu=True, path_env="HIGGSFIELD_LOCAL_REPO"),
    _r("kandinsky5", "kandinskylab/kandinsky-5", "local_video", "Keyless Kandinsky 5 video engine", gpu=True, path_env="KANDINSKY5_REPO"),

    # --- Benchmarks / competitors (read only) -----------------------------
    _r("moneyprinter_turbo", "harry0703/MoneyPrinterTurbo", "benchmark", "Main competitor: feature benchmark", forced_state="reference-only"),
    _r("vimax", "HKUDS/ViMax", "benchmark", "Main agentic analogue: feature benchmark", forced_state="reference-only"),
    _r("agnes_video", "lcy362/agnes-video-generator", "benchmark", "Closest positioning twin: MIT but not zero-key", license_note="MIT; free != zero-key", forced_state="reference-only"),
    _r("short_video_factory", "YILS-LIN/short-video-factory", "benchmark", "Closest stack analogue: Electron + EdgeTTS", forced_state="reference-only"),
    _r("moneyprinter_plus", "ddean2009/MoneyPrinterPlus", "benchmark", "README-only competitor", license_note="GPL + commercial-use restriction", forced_state="reference-only", note="do not copy code"),
    _r("openmontage_upstream", "calesthio/OpenMontage", "benchmark", "Upstream project benchmark", license_note="AGPL", forced_state="reference-only"),
    _r("chatterbox", "Resemble-AI/Chatterbox", "benchmark", "Retired TTS project: do not build on it", forced_state="reference-only"),

    # --- Methodology / skill sources (read only) --------------------------
    _r("ecc_skills", "affaan-m/ECC", "methodology", "Instincts / Memory Vault mechanics for generator skills", license_note="MIT (as supplied)", forced_state="reference-only"),
    _r("shuohao_skills", "polishuk01/shuohao-skills", "methodology", "Reference chain: outline -> script -> staging -> storyboard with gates", license_note="Apache (as supplied)", forced_state="reference-only"),
    _r("claude_video_toolkit", "digitalsamba/claude-code-video-toolkit", "methodology", "Keyless SFX plus qc.py / sync_check.py patterns", forced_state="reference-only"),
    _r("capsule_cinema", "JuneYaooo/capsule-cinema", "methodology", "Black-frame / LUFS / ASR-agreement gates", forced_state="reference-only"),
    _r("herk_edit_kit", "unverified/herk-edit-kit", "methodology", "15 editing skills", note="owner not confirmed in source list", forced_state="needs-verification"),
    _r("motionmaxxing", "unverified/motionmaxxing", "methodology", "150 motion rules, G0-G5 self-review checklist", note="owner not confirmed in source list", forced_state="needs-verification"),
    _r("openfilm", "unverified/OpenFilm", "methodology", "Self-QC via double render in shuffled order", note="owner not confirmed in source list", forced_state="needs-verification"),
    _r("claude_youtube", "unverified/claude-youtube", "methodology", "Skill-architecture reference", note="owner not confirmed in source list", forced_state="needs-verification"),
    _r("youtube_agent", "darkzOGx/youtube-automation-agent", "methodology", "Evidence desk / Real output only patterns", forced_state="reference-only"),
    _r("video_director", "unverified/video-director", "methodology", "check_timeline.py + qa_video.py self-QC pair", note="owner not confirmed in source list", forced_state="needs-verification"),
    _r("obscura", "h4ckf0r0day/Obscura", "methodology", "Small fetcher without Chromium", note="read license before reusing", forced_state="reference-only"),
    _r("hypit", "unverified/hypit", "methodology", "Video-as-code with word anchors", license_note="read licence before reuse", note="owner not confirmed in source list", forced_state="needs-verification"),

    # --- Networking / "free traffic" (explicitly out of scope) -------------
    # Listed for completeness only. These are NOT imported, installed or
    # invoked by the generator; see the module docstring for the rationale.
    _r("bpb_worker", "bia-pain-bache/BPB-Worker-Panel", "networking", "Free-traffic client config", forced_state="out-of-scope"),
    _r("vpn_configs_ru", "igareck/vpn-configs-for-russia", "networking", "Free-traffic client config", forced_state="out-of-scope"),
    _r("v2ray_config", "barry-far/V2ray-Config", "networking", "Rotating client config", forced_state="out-of-scope"),
    _r("free_vpn_anti_rkn", "Hidashimora/free-vpn-anti-rkn", "networking", "Free-traffic client config", forced_state="out-of-scope"),
    _r("v2rayn", "2dust/v2rayN", "networking", "Free-traffic client", forced_state="out-of-scope"),
    _r("sing_box", "unverified/sing-box", "networking", "Free-traffic client", note="owner not supplied", forced_state="out-of-scope"),
    _r("hiddify", "unverified/hiddify-app", "networking", "Free-traffic client", note="owner not supplied", forced_state="out-of-scope"),
    _r("nekobox", "unverified/NekoBoxForAndroid", "networking", "Free-traffic client", note="owner not supplied", forced_state="out-of-scope"),
    _r("flclash", "unverified/FlClash", "networking", "Free-traffic client", note="owner not supplied", forced_state="out-of-scope"),
    _r("lantern", "getlantern/lantern", "networking", "Free-traffic client", forced_state="out-of-scope"),
    _r("v2ray_agent", "mack-a/v2ray-agent", "networking", "Free-traffic client", forced_state="out-of-scope"),
    _r("panda_vpn_pro", "DiningFactory/panda-vpn-pro", "networking", "Free-traffic client", forced_state="out-of-scope"),
    _r("wgcf", "ViRb3/wgcf", "networking", "Cloudflare WARP config", forced_state="out-of-scope"),
    _r("warp_clash_api", "vvbbnn00/WARP-Clash-API", "networking", "Cloudflare WARP config", forced_state="out-of-scope"),
    _r("oblivion_desktop", "bepass-org/oblivion-desktop", "networking", "Cloudflare WARP config", forced_state="out-of-scope"),
    _r("warp_yg", "yonggekkk/warp-yg", "networking", "Cloudflare WARP config", forced_state="out-of-scope"),
    _r("warp_sh", "P3TERX/warp.sh", "networking", "Cloudflare WARP config", forced_state="out-of-scope"),
    _r("one_click_script", "jinwyp/one_click_script", "networking", "Cloudflare WARP config", forced_state="out-of-scope"),
    _r("goodbyedpi", "ValdikSS/GoodbyeDPI", "networking", "DPI bypass", forced_state="out-of-scope"),
    _r("zapret", "bol-van/zapret", "networking", "DPI bypass", forced_state="out-of-scope"),
    _r("byedpi_android", "dovecoteescapee/ByeDPIAndroid", "networking", "DPI bypass", forced_state="out-of-scope"),
    _r("greentunnel", "unverified/GreenTunnel", "networking", "DPI bypass", note="owner not supplied", forced_state="out-of-scope"),
    _r("zapret_discord_youtube", "Sergeydigl3/zapret-discord-youtube-linux", "networking", "DPI bypass", forced_state="out-of-scope"),
    _r("goodbyedpi_ui", "unverified/goodbyeDPI-UI", "networking", "DPI bypass UI", note="owner not supplied", forced_state="out-of-scope"),
    _r("gui_goodbyedpi", "unverified/GUI-for-GoodbyeDPI", "networking", "DPI bypass UI", note="owner not supplied", forced_state="out-of-scope"),
    _r("mhr_cfw", "denuitt1/mhr-cfw", "networking", "Fronting via Google Apps Script", forced_state="out-of-scope"),
    _r("master_http_relay", "therealaleph/MasterHttpRelayVPN-RUST", "networking", "HTTP relay", forced_state="out-of-scope"),
    _r("dnsveil", "msasanmh/DNSveil", "networking", "DNS tunnel", forced_state="out-of-scope"),
    _r("hysteria", "HyNetworks/hysteria", "networking", "Anti-throttling protocol", forced_state="out-of-scope"),
    _r("frp", "fatedier/frp", "networking", "Tunnel / NAT traversal", forced_state="out-of-scope"),
    _r("rathole", "unverified/rathole", "networking", "Tunnel / NAT traversal", note="owner not supplied", forced_state="out-of-scope"),
    _r("bore", "unverified/bore", "networking", "Tunnel / NAT traversal", note="owner not supplied", forced_state="out-of-scope"),
    _r("gost", "unverified/gost", "networking", "Tunnel / NAT traversal", note="owner not supplied", forced_state="out-of-scope"),
    _r("wstunnel", "unverified/wstunnel", "networking", "Tunnel / NAT traversal", note="owner not supplied", forced_state="out-of-scope"),
    _r("glider", "unverified/glider", "networking", "Tunnel / NAT traversal", note="owner not supplied", forced_state="out-of-scope"),
    _r("orbien", "unverified/orbien", "networking", "Tunnel / NAT traversal", note="owner not supplied", forced_state="out-of-scope"),
    _r("proxy_py", "unverified/proxy.py", "networking", "Tunnel / local proxy", note="owner not supplied", forced_state="out-of-scope"),
    _r("octelium", "unverified/octelium", "networking", "Tunnel / NAT traversal", note="owner not supplied", forced_state="out-of-scope"),
    _r("awesome_tunneling", "anderspitman/awesome-tunneling", "networking", "Tunnel catalogue", forced_state="out-of-scope"),
    _r("proxy_pool", "jhao104/proxy_pool", "networking", "Proxy pool", forced_state="out-of-scope"),
    _r("proxypool_python", "Python3WebSpider/ProxyPool", "networking", "Proxy pool", forced_state="out-of-scope"),
    _r("haipproxy", "unverified/haipproxy", "networking", "Proxy pool", note="owner not supplied", forced_state="out-of-scope"),
    _r("scylla", "unverified/scylla", "networking", "Proxy pool", note="owner not supplied", forced_state="out-of-scope"),
    _r("free_proxy_list", "proxifly/free-proxy-list", "networking", "Proxy pool", forced_state="out-of-scope"),
    _r("requests_ip_rotator", "Ge0rg3/requests-ip-rotator", "networking", "Proxy rotation", forced_state="out-of-scope"),
    _r("mubeng", "unverified/mubeng", "networking", "Proxy rotation", note="owner not supplied", forced_state="out-of-scope"),
    _r("rotating_proxy", "mattes/rotating-proxy", "networking", "Proxy rotation", forced_state="out-of-scope"),
    _r("decodo", "unverified/Decodo", "networking", "Proxy provider", note="owner not supplied", forced_state="out-of-scope"),
    _r("telegram_drive", "caamer20/Telegram-Drive", "networking", "Telegram as storage/transit", forced_state="out-of-scope"),
    _r("pentaract", "Dominux/Pentaract", "networking", "Telegram as storage/transit", forced_state="out-of-scope"),
    _r("unlim_cloud", "inulute/unlim-cloud", "networking", "Telegram as storage/transit", forced_state="out-of-scope"),
    _r("mirror_leech", "anasty17/mirror-leech-telegram-bot", "networking", "Telegram mirror bot", forced_state="out-of-scope"),
    _r("wzmlx", "unverified/WZML-X", "networking", "Telegram mirror bot", note="owner not supplied", forced_state="out-of-scope"),
    _r("download_bot", "unverified/DownloadBot", "networking", "Telegram mirror bot", note="owner not supplied", forced_state="out-of-scope"),
    _r("tortoolkit", "unverified/TorToolkit-Telegram", "networking", "Telegram mirror bot", note="owner not supplied", forced_state="out-of-scope"),
    _r("aria_mirror", "unverified/aria-telegram-mirror-bot", "networking", "Telegram mirror bot", note="owner not supplied", forced_state="out-of-scope"),
    _r("all_url_uploader", "unverified/All-Url-Uploader", "networking", "Telegram uploader", note="owner not supplied", forced_state="out-of-scope"),
    _r("rclone", "rclone/rclone", "networking", "Server-side copy / traffic offload", forced_state="out-of-scope"),
    _r("xdm", "subhra74/xdm", "networking", "Download manager", forced_state="out-of-scope"),
    _r("axel", "unverified/axel", "networking", "Download manager", note="owner not supplied", forced_state="out-of-scope"),
    _r("ipfs_desktop", "ipfs/ipfs-desktop", "networking", "IPFS delivery", forced_state="out-of-scope"),
    _r("awesome_ipfs", "ipfs/awesome-ipfs", "networking", "IPFS catalogue", forced_state="out-of-scope"),
    _r("ipfs_deploy", "unverified/ipfs-deploy", "networking", "IPFS delivery", note="owner not supplied", forced_state="out-of-scope"),
    _r("cloudflare_r2", "cloudflare/r2", "networking", "Zero-egress distribution for setup files", note="not a GitHub repo; service reference only", forced_state="out-of-scope"),
)


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, OSError):
        return False


def _gpu_available() -> bool:
    try:
        import torch
    except Exception:
        return False
    try:
        cuda = bool(torch.cuda.is_available())
    except Exception:
        cuda = False
    try:
        mps_backend = getattr(torch.backends, "mps", None)
        mps = bool(mps_backend and getattr(mps_backend, "is_available", lambda: False)())
    except Exception:
        mps = False
    return cuda or mps


def repo_status(spec: RepoSpec) -> dict[str, Any]:
    """Return a serialisable status entry without downloading anything."""
    data = asdict(spec)
    if spec.forced_state:
        data["state"] = spec.forced_state
        data["ready"] = False
        return data

    has_module = bool(spec.module and _module_available(spec.module))
    has_cmd = bool(spec.command and shutil.which(spec.command) is not None)
    has_env = bool(spec.env and os.environ.get(spec.env, "").strip())
    has_path = False
    if spec.path_env:
        value = os.environ.get(spec.path_env, "").strip()
        has_path = bool(value and Path(value).expanduser().is_dir())

    if spec.key == "openverse":
        state = "upstream"
    elif spec.key == "ltx_video" and not has_path:
        state = "upstream"
    elif spec.key == "piper_voices" and _module_available("piper"):
        state = "active"
    elif has_path:
        state = "active" if _gpu_available() else "gpu-required"
    elif spec.gpu:
        state = "not-enabled" if _gpu_available() else "gpu-required"
    elif has_module or has_cmd:
        state = "active"
    elif has_env:
        state = "configured"
    else:
        state = "not-enabled"

    data["state"] = state
    data["ready"] = state == "active"
    return data


def report() -> dict[str, Any]:
    items = [repo_status(spec) for spec in REPOS]
    by_state: dict[str, int] = {}
    for item in items:
        by_state[item["state"]] = by_state.get(item["state"], 0) + 1
    return {
        "categories": sorted({spec.category for spec in REPOS}),
        "counts": by_state,
        "repos": items,
        "tts_ladder": TTS_LADDER,
        "hint": (
            "python -m generator --repos | set GPU repo paths via *_REPO env vars; "
            "benchmark/methodology repos are read-only; networking repos are out of scope"
        ),
    }
