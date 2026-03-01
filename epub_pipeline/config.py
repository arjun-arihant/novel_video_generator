"""
Central configuration for the EPUB-to-Video pipeline.
All constants and path helpers live here. Nothing else should import from novels/.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the repo root (one level up from epub_pipeline/)
_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(_ENV_PATH)

# ─── LLM ──────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "xiaomi/mimo-v2-flash")
OPENROUTER_ENDPOINT: str = "https://openrouter.ai/api/v1/chat/completions"

# ─── Wan2GP ───────────────────────────────────────────────────────────────────
# WANGP_PATH points to the Wan2GP directory (wgp.py lives there)
_WAN2GP_DIR: str = os.getenv("WANGP_PATH", r"D:\GeneAI\Wan2GP")
WAN2GP_SCRIPT: str = str(Path(_WAN2GP_DIR) / "wgp.py")

# ─── TTS Voice Config ─────────────────────────────────────────────────────────
# model_mode value for qwen3_tts_customvoice — selects built-in voice identity
NARRATOR_VOICE_ID: str = "aiden"
FALLBACK_VOICE_ID: str = "aiden"

# ─── Scene Limits ─────────────────────────────────────────────────────────────
MAX_SCENES_PER_CHAPTER: int = 8
MIN_SCENES_PER_CHAPTER: int = 4
MIN_CHAPTER_WORD_COUNT: int = 300       # chapters below this are flagged, not processed
MAX_NEW_CHARACTERS_PER_CHAPTER: int = 5

# ─── Image Generation ─────────────────────────────────────────────────────────
IMAGE_RESOLUTION: str = "1920x1088"
IMAGE_LORAS: list[str] = ["z-image-anime-2.5D-01.safetensors"]
IMAGE_INFERENCE_STEPS: int = 8
IMAGE_NEGATIVE_PROMPT: str = (
    "blurry, low quality, watermark, text, signature, ugly, deformed"
)
IMAGE_VIDEO_LENGTH: int = 1  # 1 = still image in Wan2GP z_image mode

# ─── Storage ──────────────────────────────────────────────────────────────────
# All novel data lives under this directory. Each novel is a self-contained subfolder.
NOVELS_DIR: str = str(Path(__file__).parent.parent / "data" / "novels")

# ─── LLM Retry ────────────────────────────────────────────────────────────────
LLM_MAX_RETRIES: int = 3
LLM_RETRY_BASE_DELAY: float = 2.0  # seconds; doubles on each retry


# ─── Path Helper ──────────────────────────────────────────────────────────────
def novel_path(book_slug: str, *subpaths: str) -> str:
    """Return an absolute path scoped to a specific novel's folder.

    Usage: novel_path("dune", "db", "character_db.json")
    """
    return str(Path(NOVELS_DIR) / book_slug / Path(*subpaths) if subpaths else Path(NOVELS_DIR) / book_slug)


def ensure_novel_dirs(book_slug: str) -> None:
    """Create the full novels/{book_slug}/ directory tree if it doesn't exist."""
    dirs = [
        novel_path(book_slug),
        novel_path(book_slug, "chapters", "raw"),
        novel_path(book_slug, "chapters", "normalized"),
        novel_path(book_slug, "chapters", "scenes"),
        novel_path(book_slug, "db"),
        novel_path(book_slug, "voices"),
        novel_path(book_slug, "prompts"),
        novel_path(book_slug, "queues"),
        novel_path(book_slug, "logs"),
        novel_path(book_slug, "output"),
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
