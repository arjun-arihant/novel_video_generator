"""
Stage 9–12: Generator
Invoke Wan2GP CLI via subprocess for image and audio queue files.
Streams stdout in real time, parses progress, updates Rich live progress bar.
"""
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console

from config import novel_path, WAN2GP_SCRIPT

logger = logging.getLogger(__name__)
console = Console()


class VoiceReferenceError(RuntimeError):
    """Referenced voice file does not exist after Pass A completed."""


class Wan2GPError(RuntimeError):
    """Wan2GP process exited with non-zero code or produced unexpected output."""


def run_wan2gp(queue_path: str, output_dir: str, label: str = "") -> None:
    """
    Invoke Wan2GP CLI headless queue processing.

    Args:
        queue_path:  Absolute path to a queue JSON file.
        output_dir:  Absolute path to the output directory.
        label:       Human-readable label for the progress bar.

    Raises:
        Wan2GPError: if exit code is non-zero.
    """
    queue_path = str(queue_path)
    output_dir = str(output_dir)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Validate queue has at least one task
    try:
        queue = json.loads(Path(queue_path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise Wan2GPError(f"Cannot read queue file: {exc}") from exc

    if not queue:
        logger.info(f"Generator — Skipping empty queue: {queue_path}")
        return

    total_tasks = len(queue)
    
    # We must run Wan2GP using the base Python environment, not this pipeline's venv.
    # Otherwise, Wan2GP will crash missing its own dependencies (like 'mmgp').
    base_python = getattr(sys, "_base_executable", sys.executable)
    
    
    env = os.environ.copy()
    wan2gp_dir = str(Path(WAN2GP_SCRIPT).parent)
    # Ensure Wan2GP directory is in PYTHONPATH so it can import its own modules (like mmgp)
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{wan2gp_dir}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = wan2gp_dir

    cmd = [
        base_python, WAN2GP_SCRIPT,
        "--process", queue_path,
        "--output-dir", output_dir,
        "--verbose", "1",
    ]

    display_label = label or Path(queue_path).name

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    ) as progress:
        task_bar = progress.add_task(display_label, total=total_tasks)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=wan2gp_dir,  # run from Wan2GP directory
            env=env,
        )

        proc_output = []
        for line in proc.stdout:
            proc_output.append(line)
            line_stripped = line.rstrip()
            if line_stripped:
                logger.debug(f"[wan2gp] {line_stripped}")

            # Parse progress: "[Task N/M]" lines
            if line_stripped.startswith("[Task "):
                try:
                    parts = line_stripped.split()  # ["[Task", "2/8]", ...]
                    fraction = parts[1].rstrip("]")
                    completed = int(fraction.split("/")[0])
                    progress.update(task_bar, completed=completed)
                except (IndexError, ValueError):
                    pass

            # "Task N completed" lines
            if "completed" in line_stripped.lower() and "task" in line_stripped.lower():
                try:
                    num = int("".join(c for c in line_stripped.split() if c.isdigit())[:1])
                    progress.update(task_bar, completed=num)
                except (ValueError, IndexError):
                    pass

        proc.wait()

        if proc.returncode != 0:
            full_logs = "".join(proc_output[-30:]) # Grab last 30 lines for the error message
            raise Wan2GPError(
                f"Wan2GP exited with code {proc.returncode} for queue: {queue_path}\n"
                f"--- Wan2GP Output ---\n{full_logs}\n-------------------"
            )

        progress.update(task_bar, completed=total_tasks)

    console.print(f"[green]✓ {display_label} — {total_tasks} task(s) completed.[/green]")


def _verify_voice_refs(pass_c_queue_path: str) -> None:
    """After Pass A, verify all audio_guide files referenced in Pass C actually exist."""
    if not Path(pass_c_queue_path).exists():
        return
    tasks = json.loads(Path(pass_c_queue_path).read_text(encoding="utf-8"))
    missing = []
    for task in tasks:
        audio_guide = task.get("params", {}).get("audio_guide", "")
        if audio_guide and not Path(audio_guide).exists():
            missing.append(audio_guide)
    if missing:
        raise VoiceReferenceError(
            f"Voice reference files missing after Pass A. Cannot run Pass C.\n"
            f"Missing files:\n" + "\n".join(f"  {p}" for p in missing)
        )


def generate_images(book_slug: str, chapter_id: int) -> None:
    queue_path = novel_path(book_slug, "queues", f"image_queue_ch{chapter_id}.json")
    output_dir = novel_path(book_slug, "images", f"ch{chapter_id}")
    console.print(f"[bold blue]> Stage 9 — Generating images for chapter {chapter_id}[/bold blue]")
    run_wan2gp(queue_path, output_dir, label=f"Image generation ch{chapter_id}")


def generate_audio(book_slug: str, chapter_id: int) -> None:
    """Run TTS Pass A → verify voices → Pass B → Pass C."""
    voices_dir = novel_path(book_slug, "voices")
    audio_dir = novel_path(book_slug, "audio", f"ch{chapter_id}")

    pass_a = novel_path(book_slug, "queues", f"audio_queue_ch{chapter_id}_pass_a.json")
    pass_b = novel_path(book_slug, "queues", f"audio_queue_ch{chapter_id}_pass_b.json")
    pass_c = novel_path(book_slug, "queues", f"audio_queue_ch{chapter_id}_pass_c.json")

    # Pass A — voice design (skip if empty)
    a_tasks = json.loads(Path(pass_a).read_text(encoding="utf-8")) if Path(pass_a).exists() else []
    if a_tasks:
        console.print(f"[bold blue]> Stage 10 — TTS Pass A (voice design) ch{chapter_id}[/bold blue]")
        run_wan2gp(pass_a, voices_dir, label=f"TTS Pass A ch{chapter_id}")
        _verify_voice_refs(pass_c)
    else:
        logger.info(f"Stage 10 — Pass A empty for ch{chapter_id}, skipping voice design.")

    # Pass B — narrator / custom voice
    console.print(f"[bold blue]> Stage 11 — TTS Pass B (narrator) ch{chapter_id}[/bold blue]")
    run_wan2gp(pass_b, audio_dir, label=f"TTS Pass B ch{chapter_id}")

    # Pass C — character cloning (skip if empty)
    c_tasks = json.loads(Path(pass_c).read_text(encoding="utf-8")) if Path(pass_c).exists() else []
    if c_tasks:
        console.print(f"[bold blue]> Stage 12 — TTS Pass C (voice cloning) ch{chapter_id}[/bold blue]")
        run_wan2gp(pass_c, audio_dir, label=f"TTS Pass C ch{chapter_id}")
    else:
        logger.info(f"Stage 12 — Pass C empty for ch{chapter_id}, skipping character dialogue.")
