"""
Central configuration for the EPUB-to-Video pipeline.
All constants, paths, and environment loading live here.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
_ENV_PATH = ROOT_DIR / ".env"
load_dotenv(_ENV_PATH)

# ─── LLM (OpenRouter / OpenAI-compatible) ────────────────────────────────────
LLM_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen/qwen3-235b-a22b")

# ─── Wan2GP (images only) ────────────────────────────────────────────────────
_WAN2GP_DIR: str = os.getenv("WANGP_PATH", r"D:\GeneAI\Wan2GP")
WAN2GP_SCRIPT: str = str(Path(_WAN2GP_DIR) / "wgp.py")
WAN2GP_PYTHON: str = os.getenv(
    "WAN2GP_PYTHON",
    r"C:\Users\Psyka\miniconda3\envs\wan2gp\python.exe",
)

# ─── TTS (Alexandria / Qwen3-TTS) ────────────────────────────────────────────
TTS_DEVICE: str = os.getenv("TTS_DEVICE", "auto")
TTS_LANGUAGE: str = os.getenv("TTS_LANGUAGE", "English")
TTS_PARALLEL_WORKERS: int = int(os.getenv("TTS_PARALLEL_WORKERS", "4"))
TTS_COMPILE_CODEC: bool = os.getenv("TTS_COMPILE_CODEC", "false").lower() == "true"
NARRATOR_VOICE: str = os.getenv("NARRATOR_VOICE", "Ryan")
NARRATOR_STYLE: str = os.getenv("NARRATOR_STYLE", "calm, measured storyteller narration")

# ─── Scene Limits ─────────────────────────────────────────────────────────────
MAX_SCENES_PER_CHAPTER: int = 8
MIN_SCENES_PER_CHAPTER: int = 4
MIN_CHAPTER_WORD_COUNT: int = 300
MAX_NEW_CHARACTERS_PER_CHAPTER: int = 5

# ─── Image Generation (Wan2GP) ────────────────────────────────────────────────
IMAGE_RESOLUTION: str = "1280x720"
IMAGE_LORAS: list[str] = ["z-image-anime-2.5D-01.safetensors"]
IMAGE_INFERENCE_STEPS: int = 8
IMAGE_NEGATIVE_PROMPT: str = (
    "blurry, low quality, watermark, text, signature, ugly, deformed"
)
IMAGE_VIDEO_LENGTH: int = 1  # 1 = still image in Wan2GP z_image mode

# ─── LLM Retry ────────────────────────────────────────────────────────────────
LLM_MAX_RETRIES: int = 3
LLM_RETRY_BASE_DELAY: float = 2.0

# ─── Storage ──────────────────────────────────────────────────────────────────
NOVELS_DIR: str = str(ROOT_DIR / "data" / "novels")

# ─── Web UI ───────────────────────────────────────────────────────────────────
WEB_UI_HOST: str = os.getenv("WEB_UI_HOST", "127.0.0.1")
WEB_UI_PORT: int = int(os.getenv("WEB_UI_PORT", "4200"))


def novel_path(book_slug: str, *subpaths: str) -> str:
    """Return an absolute path scoped to a specific novel's folder."""
    base = Path(NOVELS_DIR) / book_slug
    if subpaths:
        return str(base / Path(*subpaths))
    return str(base)


def ensure_novel_dirs(book_slug: str) -> None:
    """Create the full novels/{book_slug}/ directory tree."""
    dirs = [
        novel_path(book_slug),
        novel_path(book_slug, "chapters", "raw"),
        novel_path(book_slug, "chapters", "normalized"),
        novel_path(book_slug, "chapters", "scenes"),
        novel_path(book_slug, "db"),
        novel_path(book_slug, "voices"),
        novel_path(book_slug, "prompts"),
        novel_path(book_slug, "queues"),
        novel_path(book_slug, "audio"),
        novel_path(book_slug, "images"),
        novel_path(book_slug, "output"),
        novel_path(book_slug, "logs"),
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
