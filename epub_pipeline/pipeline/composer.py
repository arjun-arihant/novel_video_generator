"""
Stage 13: Video Composer
FFmpeg via subprocess. Combines scene images + audio into chapter MP4.
No moviepy. Pure FFmpeg filter graphs.
"""
import json
import logging
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console

from config import novel_path

logger = logging.getLogger(__name__)
console = Console()


class FFmpegError(RuntimeError):
    """FFmpeg subprocess failed."""


def _run_ffmpeg(cmd: list[str], label: str = "FFmpeg") -> None:
    """Execute an FFmpeg command, raise FFmpegError on non-zero exit."""
    logger.debug(f"FFmpeg: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise FFmpegError(
            f"{label} failed (exit {result.returncode}):\n{result.stderr[-2000:]}"
        )


def _get_audio_duration(wav_path: str) -> float:
    """Use ffprobe to get audio duration in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        wav_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 5.0  # fallback if probe fails


def _concat_audio_for_scene(
    book_slug: str, chapter_id: int, scene_id: int, out_wav: str
) -> float:
    """
    Concatenate all seq_{scene_id}_*.wav files for a scene into one WAV.
    Returns total duration in seconds.
    """
    audio_dir = Path(novel_path(book_slug, "audio", f"ch{chapter_id}"))
    pattern = f"seq_{scene_id:03d}_*.wav"
    wav_files = sorted(audio_dir.glob(pattern))

    if not wav_files:
        logger.warning(f"No audio files found for scene {scene_id} ch{chapter_id}.")
        return 0.0

    if len(wav_files) == 1:
        # Only one file, just copy
        import shutil
        shutil.copy2(str(wav_files[0]), out_wav)
        return _get_audio_duration(out_wav)

    # Build concat filter
    inputs = []
    for wav in wav_files:
        inputs += ["-i", str(wav)]

    n = len(wav_files)
    filter_str = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[outa]"

    cmd = (
        ["ffmpeg", "-y"]
        + inputs
        + ["-filter_complex", filter_str, "-map", "[outa]", out_wav]
    )
    _run_ffmpeg(cmd, label=f"concat_audio_scene_{scene_id}")
    return _get_audio_duration(out_wav)


def _make_scene_clip(
    image_path: str, audio_path: str, duration: float, out_path: str
) -> None:
    """Combine a static image + audio WAV into an MP4 clip of `duration` seconds."""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",  # ensure even dimensions
        "-shortest",
        out_path,
    ]
    _run_ffmpeg(cmd, label=f"scene_clip {Path(out_path).name}")


def _concat_clips_with_crossfade(clip_paths: list[str], out_path: str) -> None:
    """
    Concatenate scene clips with a 0.3s crossfade between each using xfade filter.
    Falls back to simple concat if there's only 1 clip.
    """
    if len(clip_paths) == 1:
        import shutil
        shutil.copy2(clip_paths[0], out_path)
        return

    FADE = 0.3

    # Get durations of all clips
    durations = [_get_audio_duration(p) for p in clip_paths]

    inputs = []
    for p in clip_paths:
        inputs += ["-i", p]

    n = len(clip_paths)
    # Build chained xfade filter
    # xfade offset = sum(durations of clips before) - FADE * clip_index
    filter_parts = []
    stream_label = "[0:v]"
    audio_parts = []

    offset = 0.0
    for i in range(1, n):
        offset += durations[i - 1] - FADE
        next_label = f"[xf{i}]" if i < n - 1 else "[vout]"
        filter_parts.append(
            f"{stream_label}[{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.3f}{next_label}"
        )
        stream_label = f"[xf{i}]"

    # Audio concat (simple, no crossfade on audio)
    audio_filter = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[aout]"

    full_filter = ";".join(filter_parts) + ";" + audio_filter

    cmd = (
        ["ffmpeg", "-y"]
        + inputs
        + [
            "-filter_complex", full_filter,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            out_path,
        ]
    )
    _run_ffmpeg(cmd, label="chapter_concat_xfade")


def compose_chapter(book_slug: str, chapter_id: int) -> str:
    """
    Compose a chapter video from scene images and audio.
    Returns path to output MP4.
    """
    out_mp4 = novel_path(book_slug, "output", f"chapter_{chapter_id}.mp4")
    if Path(out_mp4).exists():
        logger.info(f"Stage 13 — chapter_{chapter_id}.mp4 already exists, skipping.")
        return out_mp4

    Path(out_mp4).parent.mkdir(parents=True, exist_ok=True)

    canonical_path = novel_path(
        book_slug, "chapters", "scenes", f"scenes_canonical_ch{chapter_id}.json"
    )
    scenes_data = json.loads(Path(canonical_path).read_text(encoding="utf-8"))
    scenes = scenes_data.get("scenes", [])

    console.print(
        f"[bold blue]▶ Stage 13 — Composing chapter {chapter_id} ({len(scenes)} scenes)[/bold blue]"
    )

    clip_paths = []

    with tempfile.TemporaryDirectory(prefix="epub_pipeline_") as tmpdir:
        for scene in scenes:
            scene_id = scene["scene_id"]
            image_path = novel_path(
                book_slug, "images", f"ch{chapter_id}", f"scene_{scene_id:03d}.png"
            )
            if not Path(image_path).exists():
                logger.warning(
                    f"Missing image for scene {scene_id}, ch{chapter_id}. Skipping scene."
                )
                continue

            # Concatenate all audio segments for this scene
            scene_audio = str(Path(tmpdir) / f"scene_{scene_id:03d}_audio.wav")
            duration = _concat_audio_for_scene(book_slug, chapter_id, scene_id, scene_audio)

            if duration <= 0:
                logger.warning(f"Scene {scene_id} has no audio. Skipping.")
                continue

            # Create scene clip (image + audio)
            scene_clip = str(Path(tmpdir) / f"scene_{scene_id:03d}_clip.mp4")
            _make_scene_clip(image_path, scene_audio, duration, scene_clip)
            clip_paths.append(scene_clip)

        if not clip_paths:
            logger.error(f"No valid clips for chapter {chapter_id}. Cannot compose video.")
            return ""

        # Concatenate all scene clips with crossfade
        _concat_clips_with_crossfade(clip_paths, out_mp4)

    console.print(
        f"[bold green]✓ Chapter {chapter_id} composed → {out_mp4}[/bold green]"
    )
    return out_mp4
