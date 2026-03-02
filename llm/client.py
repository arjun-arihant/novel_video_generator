"""
Unified LLM client using OpenAI-compatible API (OpenRouter, LM Studio, Ollama, etc.).
Handles retries, JSON parsing, and logging.
"""
import json
import logging
import re
import time
from pathlib import Path

from openai import OpenAI

from pipeline.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_MAX_RETRIES,
    LLM_RETRY_BASE_DELAY,
    novel_path,
)

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """LLM call failed after all retries."""


class LLMParseError(LLMError):
    """LLM returned unparseable content."""


def _get_client(base_url: str | None = None, api_key: str | None = None) -> OpenAI:
    return OpenAI(
        base_url=base_url or LLM_BASE_URL,
        api_key=api_key or LLM_API_KEY,
    )


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response, handling markdown fences and thinking tags."""
    # Strip <think>...</think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    # Try markdown code fence first
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    # Try to find raw JSON object/array
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape = False
        for i, ch in enumerate(text[start:], start):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

    return text.strip()


def call_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    book_slug: str = "",
    call_label: str = "llm_call",
    expect_json: bool = True,
    model: str | None = None,
    temperature: float = 0.6,
    max_tokens: int = 4096,
) -> dict | list | str:
    """
    Call the LLM with retry logic and optional JSON parsing.

    Returns parsed JSON (dict/list) if expect_json=True, raw string otherwise.
    Saves raw responses to novel logs directory for debugging.
    """
    client = _get_client()
    target_model = model or LLM_MODEL

    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            logger.info(f"LLM call [{call_label}] attempt {attempt}/{LLM_MAX_RETRIES}")

            response = client.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            raw = response.choices[0].message.content or ""

            # Save raw response for debugging
            if book_slug:
                log_dir = Path(novel_path(book_slug, "logs"))
                log_dir.mkdir(parents=True, exist_ok=True)
                log_file = log_dir / f"{call_label}_attempt{attempt}.txt"
                log_file.write_text(raw, encoding="utf-8")

            if not expect_json:
                return raw

            json_str = _extract_json(raw)
            parsed = json.loads(json_str)
            logger.info(f"LLM call [{call_label}] succeeded on attempt {attempt}")
            return parsed

        except json.JSONDecodeError as e:
            logger.warning(
                f"LLM call [{call_label}] JSON parse failed (attempt {attempt}): {e}"
            )
            if attempt == LLM_MAX_RETRIES:
                raise LLMParseError(
                    f"Failed to parse JSON from LLM after {LLM_MAX_RETRIES} attempts: {e}"
                ) from e

        except Exception as e:
            logger.warning(f"LLM call [{call_label}] failed (attempt {attempt}): {e}")
            if attempt == LLM_MAX_RETRIES:
                raise LLMError(
                    f"LLM call [{call_label}] failed after {LLM_MAX_RETRIES} attempts: {e}"
                ) from e

        delay = LLM_RETRY_BASE_DELAY * (2 ** (attempt - 1))
        logger.info(f"Retrying in {delay:.1f}s...")
        time.sleep(delay)
