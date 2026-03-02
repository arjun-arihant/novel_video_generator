"""
Stage 9: Image Generator
Invokes Wan2GP CLI via subprocess for image generation only.
Streams progress output and updates Rich progress bar.
"""
import json
import logging
import os
import subprocess
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console

from pipeline.config import novel_path, WAN2GP_SCRIPT, WAN2GP_PYTHON

logger = logging.getLogger(__name__)
console = Console()


class Wan2GPError(RuntimeError):
    """Wan2GP process exited with non-zero code."""


def run_wan2gp(queue_path: str, output_dir: str, label: str = "") -> None:
    """
    Invoke Wan2GP CLI for headless queue processing.

    Args:
        queue_path: Absolute path to a queue JSON file.
        output_dir: Absolute path to the output directory.
        label: Human-readable label for the progress bar.

    Raises:
        Wan2GPError: if exit code is non-zero.
    """
    queue_path = str(queue_path)
    output_dir = str(output_dir)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Validate queue
    try:
        import zipfile
        if queue_path.endswith(".zip"):
            with zipfile.ZipFile(queue_path, 'r') as zf:
                queue = json.loads(zf.read("queue.json").decode("utf-8"))
        else:
            queue = json.loads(Path(queue_path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, zipfile.BadZipFile, KeyError) as exc:
        raise Wan2GPError(f"Cannot read queue file: {exc}") from exc

    if not queue:
        logger.info(f"Image Gen — Skipping empty queue: {queue_path}")
        return

    total_tasks = len(queue)

    # Use the Wan2GP conda env's Python so mmgp + all deps are available
    wan2gp_python = WAN2GP_PYTHON

    env = os.environ.copy()
    wan2gp_dir = str(Path(WAN2GP_SCRIPT).parent)
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{wan2gp_dir}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = wan2gp_dir

    # Ensure output directories exist for each task's output_filename
    for task in queue:
        out_file = task.get("params", {}).get("output_filename", "")
        if out_file:
            Path(out_file).parent.mkdir(parents=True, exist_ok=True)

    # Use --process with queue ZIP and pass --output-dir
    # Wan2GP uses the base output_filename inside each task + .jpg
    cmd = [
        wan2gp_python, WAN2GP_SCRIPT,
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
            cwd=wan2gp_dir,
            env=env,
        )

        proc_output = []
        for line in proc.stdout:
            proc_output.append(line)
            line_stripped = line.rstrip()
            if line_stripped:
                logger.debug(f"[wan2gp] {line_stripped}")

            if line_stripped.startswith("[Task "):
                try:
                    parts = line_stripped.split()
                    fraction = parts[1].rstrip("]")
                    completed = int(fraction.split("/")[0])
                    progress.update(task_bar, completed=completed)
                except (IndexError, ValueError):
                    pass

            if "completed" in line_stripped.lower() and "task" in line_stripped.lower():
                try:
                    num = int("".join(c for c in line_stripped.split() if c.isdigit())[:1])
                    progress.update(task_bar, completed=num)
                except (ValueError, IndexError):
                    pass

        proc.wait()

        if proc.returncode != 0:
            full_logs = "".join(proc_output[-30:])
            raise Wan2GPError(
                f"Wan2GP exited with code {proc.returncode} for queue: {queue_path}\n"
                f"--- Wan2GP Output ---\n{full_logs}\n-------------------"
            )

        progress.update(task_bar, completed=total_tasks)

    # Verify generated files
    generated = 0
    missing = []
    for task in queue:
        # e.g., "scene_001"
        out_base = task.get("params", {}).get("output_filename", "")
        if out_base:
            # Wan2GP natively outputs .jpg for z_images
            predicted_file = Path(output_dir) / f"{out_base}.jpg"
            if predicted_file.exists():
                generated += 1
            else:
                missing.append(str(predicted_file))

    if missing:
        console.print(
            f"[yellow]⚠ {display_label} — {generated}/{total_tasks} images saved. "
            f"{len(missing)} missing.[/yellow]"
        )
        for m in missing:
            logger.warning(f"Missing output: {m}")
    else:
        console.print(f"[green]✓ {display_label} — {generated}/{total_tasks} images generated.[/green]")

    return generated


def generate_images(book_slug: str, chapter_id: int) -> int:
    """Generate images for a chapter using Wan2GP. Returns count of generated images."""
    queue_path = novel_path(book_slug, "queues", f"image_queue_ch{chapter_id}.zip")
    output_dir = novel_path(book_slug, "images", f"ch{chapter_id}")

    if not Path(queue_path).exists():
        logger.warning(f"Stage 9 — No image queue for ch{chapter_id}, skipping.")
        return 0

    console.print(f"[bold blue]▶ Stage 9 — Generating images for chapter {chapter_id}[/bold blue]")
    return run_wan2gp(queue_path, output_dir, label=f"Image generation ch{chapter_id}")
