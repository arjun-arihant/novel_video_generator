"""
LLM client — OpenRouter API wrapper.
Uses requests (no openai SDK). All prompts come from llm/prompts.py.
Retries with exponential backoff on rate limit / server errors.
Logs token usage per call to the novel's log file.
"""
import json
import time
import logging
from pathlib import Path
from typing import Any

import requests

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OPENROUTER_ENDPOINT,
    LLM_MAX_RETRIES,
    LLM_RETRY_BASE_DELAY,
    novel_path,
)

logger = logging.getLogger(__name__)

# ─── Exceptions ───────────────────────────────────────────────────────────────

class LLMError(Exception):
    """Base LLM error."""

class LLMRateLimitError(LLMError):
    """429 rate limit hit after all retries exhausted."""

class LLMParseError(LLMError):
    """The model returned a response that could not be parsed as JSON."""


# ─── Token Usage Logging ──────────────────────────────────────────────────────

def _append_usage_log(book_slug: str, call_label: str, usage: dict) -> None:
    """Append a token-usage record to the novel's LLM usage log."""
    log_path = Path(novel_path(book_slug, "logs", "llm_usage_log.json"))
    log_path.parent.mkdir(parents=True, exist_ok=True)

    records: list = []
    if log_path.exists():
        try:
            records = json.loads(log_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            records = []

    records.append({
        "call_label": call_label,
        "model": OPENROUTER_MODEL,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    log_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")


# ─── Core Client ──────────────────────────────────────────────────────────────

def call_llm(
    system_prompt: str,
    user_prompt: str,
    book_slug: str,
    call_label: str = "unnamed",
    expect_json: bool = True,
    model: str | None = None,
) -> dict | str:
    """
    Make a single chat-completion call to OpenRouter.

    Returns:
        dict  — if expect_json=True (parses content as JSON)
        str   — if expect_json=False (returns raw content string)

    Raises:
        LLMRateLimitError — if 429 persists after all retries
        LLMError          — for other HTTP or response errors
        LLMParseError     — if JSON parsing fails (expect_json=True only)
    """
    if not OPENROUTER_API_KEY:
        raise LLMError("OPENROUTER_API_KEY is not set. Check your .env file.")

    selected_model = model or OPENROUTER_MODEL
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/epub-pipeline",
        "X-Title": "EPUB Video Pipeline",
    }
    payload: dict[str, Any] = {
        "model": selected_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if expect_json:
        payload["response_format"] = {"type": "json_object"}

    delay = LLM_RETRY_BASE_DELAY
    last_error: Exception | None = None

    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            resp = requests.post(
                OPENROUTER_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=120,
            )
        except requests.RequestException as exc:
            last_error = LLMError(f"Network error on attempt {attempt}: {exc}")
            logger.warning(str(last_error))
            time.sleep(delay)
            delay *= 2
            continue

        if resp.status_code == 429:
            last_error = LLMRateLimitError(f"Rate limited (attempt {attempt}/{LLM_MAX_RETRIES})")
            logger.warning(str(last_error))
            time.sleep(delay)
            delay *= 2
            continue

        if resp.status_code >= 500:
            last_error = LLMError(f"Server error {resp.status_code} on attempt {attempt}")
            logger.warning(str(last_error))
            time.sleep(delay)
            delay *= 2
            continue

        if not resp.ok:
            raise LLMError(f"HTTP {resp.status_code}: {resp.text[:400]}")

        data = resp.json()
        content: str = data["choices"][0]["message"]["content"]
        usage: dict = data.get("usage", {})

        _append_usage_log(book_slug, call_label, usage)

        if not expect_json:
            return content

        # Strip markdown fences if model wrapped the JSON anyway
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            # remove first (```json) and last (```) lines
            stripped = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise LLMParseError(
                f"Could not parse LLM response as JSON.\n"
                f"Error: {exc}\n"
                f"Raw content (first 500 chars): {content[:500]}"
            ) from exc

    raise last_error or LLMError("LLM call failed after all retries.")
