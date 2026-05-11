import json
import os

import numpy as np
from PIL import Image


def generate(project_data: dict, output_path: str,
             resolution: tuple = (1920, 1080), fps: int = 24,
             progress_callback=None) -> str:
    from moviepy import (ColorClip, ImageClip, AudioFileClip,
                         CompositeVideoClip, CompositeAudioClip,
                         concatenate_videoclips)

    _report = progress_callback or (lambda p, m: None)

    valid_clips = [
        c for c in project_data.get("children", [])
        if c.get("type") == "video_clip" and (c.get("duration") or 0) > 0
    ]
    if not valid_clips:
        raise ValueError("No video clips with duration > 0")

    built = []
    n = len(valid_clips)
    for i, clip_data in enumerate(valid_clips):
        _report(i / n * 0.85, f"Building clip {i + 1} of {n}…")
        built.append(_build_clip(clip_data, resolution, fps))

    _report(0.87, "Concatenating clips…")
    final = concatenate_videoclips(built, method="compose")

    # fraction=None → caller switches to indeterminate/busy bar
    _report(None, "Encoding — this may take a while…")
    final.write_videofile(
        output_path, fps=fps,
        codec="libx264", audio_codec="aac",
        logger=None,
    )

    _report(1.0, "Done")
    return output_path


def _fit_frame(path: str, resolution: tuple) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    w, h = resolution
    iw, ih = img.size
    scale = min(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", resolution, (0, 0, 0))
    canvas.paste(img, ((w - nw) // 2, (h - nh) // 2))
    return np.array(canvas)


def _build_clip(clip_data: dict, resolution: tuple, fps: int):
    from moviepy import (ColorClip, ImageClip, AudioFileClip,
                         CompositeVideoClip, CompositeAudioClip)

    duration = float(clip_data.get("duration") or 0)
    children = clip_data.get("children", [])

    images = sorted(
        [c for c in children if c.get("type") == "image"],
        key=lambda c: c.get("start_time") or 0.0,
    )
    audios = sorted(
        [c for c in children if c.get("type") == "audio"],
        key=lambda c: c.get("start_time") or 0.0,
    )
    base = ColorClip(size=resolution, color=(0, 0, 0), duration=duration).with_fps(fps)
    layers = [base]

    for j, img_data in enumerate(images):
        path = img_data.get("path")
        if not path or not os.path.exists(path):
            continue
        t_start = float(img_data.get("start_time") or 0.0)
        if j + 1 < len(images):
            t_end = float(images[j + 1].get("start_time") or duration)
        else:
            t_end = duration
        if t_end <= t_start:
            continue
        try:
            frame = _fit_frame(path, resolution)
            clip = (ImageClip(frame, duration=t_end - t_start)
                    .with_fps(fps)
                    .with_start(t_start))
            layers.append(clip)
        except Exception:
            pass

    audio_clips = []
    for audio_data in audios:
        path = audio_data.get("path")
        if not path or not os.path.exists(path):
            continue
        t_start = float(audio_data.get("start_time") or 0.0)
        if t_start >= duration:
            continue
        try:
            ac = AudioFileClip(path)
            ac = ac.subclipped(0, min(ac.duration, duration - t_start))
            ac = ac.with_start(t_start)
            audio_clips.append(ac)
        except Exception:
            pass

    # audio_clip_path property
    ac_path = clip_data.get("audio_clip_path", "")
    if ac_path and os.path.isfile(ac_path):
        try:
            with open(ac_path, "r", encoding="utf-8") as f:
                info = json.load(f)
            audio_path = info.get("audio_path", "")
            if audio_path and os.path.exists(audio_path):
                ac        = AudioFileClip(audio_path)
                use_full  = clip_data.get("audio_clip_use_full", True)
                if use_full is None:
                    use_full = True
                if use_full:
                    t_start = 0.0
                    t_end   = min(ac.duration, duration)
                else:
                    t_start = float(clip_data.get("audio_clip_start") or 0.0)
                    t_end   = float(clip_data.get("audio_clip_end") or ac.duration)
                    t_start = max(0.0, min(t_start, ac.duration))
                    t_end   = max(t_start, min(t_end, ac.duration, duration))
                ac = ac.subclipped(t_start, t_end)
                audio_clips.append(ac)
        except Exception:
            pass

    video = CompositeVideoClip(layers, size=resolution)
    if audio_clips:
        video = video.with_audio(CompositeAudioClip(audio_clips))

    return video
