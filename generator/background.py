"""Optional background replacement for keyless clips.

Engines (all local, no API keys):
  rembg     danielgatis/rembg -- u2net / u2net_human_seg / isnet-general-use
  selfie    google-ai-edge/mediapipe -- SelfieSegmentation (fast preview)

Frames are streamed through ffmpeg raw pipes, so no temporary frame directory
is needed.  Every helper fails open: on any error the caller keeps the
original clip and the render still completes.

Upstreams also represented here: PeterL1n/RobustVideoMatting and
xuebinqin/U-2-Net (the model family behind rembg's u2net session).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

MAX_FPS = 12
MAX_WIDTH = 960


def probe_video(path: str | Path) -> dict[str, Any]:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration:format=duration",
        "-of", "json", str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(proc.stdout)
    stream = (data.get("streams") or [{}])[0]
    duration = stream.get("duration") or data.get("format", {}).get("duration") or 0
    return {
        "width": int(stream.get("width", 1280)),
        "height": int(stream.get("height", 720)),
        "duration": float(duration),
    }


def _size(width: int, height: int) -> tuple[int, int]:
    if width <= MAX_WIDTH:
        return width, height
    scale = MAX_WIDTH / width
    return MAX_WIDTH, max(2, round(height * scale / 2) * 2)


def _parse_color(value: str) -> tuple[int, int, int]:
    text = value.strip().lstrip("#")
    if len(text) == 6:
        try:
            return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            pass
    return (16, 28, 46)


def _background_image(path: str | Path | None, size: tuple[int, int]) -> Any | None:
    if not path:
        return None
    from PIL import Image

    return Image.open(path).convert("RGB").resize(size)


def _compose_frame(frame: Any, mask: Any, background: Any | None, color: tuple[int, int, int]) -> Any:
    import numpy as np
    from PIL import Image

    alpha = np.asarray(mask, dtype=np.float32)
    if alpha.ndim == 3:
        alpha = alpha[..., 0]
    keep = alpha > 0.35
    if background is None:
        canvas = Image.new("RGB", frame.size, color)
    else:
        canvas = background.copy()
    canvas.paste(frame, (0, 0), Image.fromarray((keep * 255).astype("uint8"), mode="L"))
    return canvas


def _selfie_model_path() -> Path:
    override = os.environ.get("OM_MEDIAPIPE_MODEL", "").strip()
    if override:
        return Path(override)
    if os.name == "nt":
        drive = os.environ.get("SystemDrive", "C:").rstrip(":")
        return Path(f"{drive}:/omtest/mediapipe/selfie_segmenter.tflite")
    return Path.home() / ".cache" / "openmontage" / "selfie_segmenter.tflite"


def _selfie_segmenter() -> Any:
    """Support mediapipe 1.x Tasks API and the older solutions API."""
    import urllib.request
    import mediapipe as mp

    if background_module_state.selfie is None:
        if hasattr(mp, "tasks"):
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            model = _selfie_model_path()
            model.parent.mkdir(parents=True, exist_ok=True)
            if not model.exists():
                url = (
                    "https://storage.googleapis.com/mediapipe-models/image_segmenter/"
                    "selfie_segmenter/float16/1/selfie_segmenter.tflite"
                )
                urllib.request.urlretrieve(url, model)
            options = vision.ImageSegmenterOptions(
                base_options=python.BaseOptions(model_asset_path=str(model)),
                running_mode=vision.RunningMode.IMAGE,
                output_category_mask=True,
            )
            background_module_state.selfie = vision.ImageSegmenter.create_from_options(options)
        else:
            background_module_state.selfie = (
                mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=0)
            )
    return background_module_state.selfie


def _selfie_mask(frame: Any) -> Any:
    import numpy as np
    import mediapipe as mp

    rgb = np.asarray(frame)
    segmenter = _selfie_segmenter()
    if hasattr(segmenter, "segment"):
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        return segmenter.segment(image).category_mask.numpy_view()
    import cv2
    return segmenter.process(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)).segmentation_mask


class _State:
    selfie: Any = None


background_module_state = _State()


def selfie_preview(source: str | Path, output: str | Path, seconds: float = 1.0) -> Path | None:
    """Write one mediapipe-segmented preview PNG; never touch the final MP4."""
    try:
        from PIL import Image

        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-v", "error", "-ss", str(seconds), "-i", str(source),
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1",
        ]
        raw = subprocess.run(cmd, capture_output=True, check=True).stdout
        import io
        frame = Image.open(io.BytesIO(raw)).convert("RGB")
        mask = _selfie_mask(frame)
        result = _compose_frame(frame, mask, None, (16, 28, 46))
        result.save(output)
        return output
    except Exception:
        return None


def replace_background(
    source: str | Path,
    output: str | Path,
    *,
    engine: str = "rembg",
    model: str = "u2net",
    color: str = "#101c2e",
    bg_image: str | Path | None = None,
) -> bool:
    """Replace the background of one clip. Returns False on any failure."""
    source = Path(source)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    decoder: subprocess.Popen | None = None
    encoder: subprocess.Popen | None = None
    session: Any = None
    try:
        info = probe_video(source)
        width, height = _size(info["width"], info["height"])
        frame_size = width * height * 3
        fps = MAX_FPS
        rgb = _parse_color(color)
        background = _background_image(bg_image, (width, height))

        if engine == "rembg":
            import rembg
            session = rembg.new_session(model)
            masked = lambda image: rembg.remove(image, session=session, only_mask=True)
        elif engine == "selfie":
            masked = _selfie_mask
        else:
            return False

        decode_cmd = [
            "ffmpeg", "-v", "error", "-i", str(source),
            "-vf", f"fps={fps},scale={width}:{height}",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
        ]
        encode_cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
            "-r", str(fps), "-i", "pipe:0", "-i", str(source),
            "-map", "0:v:0", "-map", "1:a?", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(output),
        ]
        decoder = subprocess.Popen(decode_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        encoder = subprocess.Popen(encode_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        from PIL import Image

        while True:
            raw = decoder.stdout.read(frame_size)
            if len(raw) < frame_size:
                break
            frame = Image.frombytes("RGB", (width, height), raw)
            result = _compose_frame(frame, masked(frame), background, rgb)
            encoder.stdin.write(result.tobytes())
        encoder.stdin.close()
        decoder.stdout.close()
        if encoder.wait(timeout=300) != 0:
            return False
        decoder.wait(timeout=30)
        return output.exists() and output.stat().st_size > 1024
    except Exception:
        return False
    finally:
        if decoder is not None and decoder.poll() is None:
            decoder.kill()
        if encoder is not None and encoder.poll() is None:
            encoder.kill()
        if session is not None:
            try:
                close = getattr(session, "close", None)
                if close:
                    close()
            except Exception:
                pass
