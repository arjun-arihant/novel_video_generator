"""OpenRouter client utilities."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import requests

from ..common import get_config

logger = logging.getLogger(__name__)


def _repair_json(raw: str) -> str:
    """Best-effort repair of common LLM JSON issues."""
    text = raw.strip()

    # Strip markdown fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    # Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # If truncated (doesn't end with } or ]), try to close it
    if not text.rstrip().endswith(("}", "]")):
        open_braces = text.count("{") - text.count("}")
        open_brackets = text.count("[") - text.count("]")

        # Trim back to last complete item
        last_complete = max(text.rfind("}"), text.rfind("]"))
        if last_complete > 0:
            text = text[: last_complete + 1]
            # Recount after trim
            open_braces = text.count("{") - text.count("}")
            open_brackets = text.count("[") - text.count("]")

        # Close remaining open brackets/braces
        text += "]" * open_brackets + "}" * open_braces

    # Final cleanup: trailing commas that may have appeared after truncation repair
    text = re.sub(r",\s*([}\]])", r"\1", text)

    return text


class OpenRouterClient:
    """Minimal OpenRouter chat completion client."""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> None:
        config = get_config().openrouter
        self.api_key = config.api_key
        self.model = model or config.model
        self.temperature = temperature if temperature is not None else config.temperature
        self.max_tokens = max_tokens if max_tokens is not None else config.max_output_tokens
        self.timeout = timeout if timeout is not None else config.timeout
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    def generate_json(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate JSON output from the model with robust parsing."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            self.base_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"OpenRouter error {response.status_code}: {response.text[:500]}"
            )
        data = response.json()
        content = data["choices"][0]["message"]["content"]

        # Check for truncation via finish_reason
        finish_reason = data["choices"][0].get("finish_reason", "")
        if finish_reason == "length":
            logger.warning("LLM response was truncated (hit max_tokens), attempting repair")

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("JSON parse failed, attempting repair...")
            repaired = _repair_json(content)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError as e:
                logger.error("JSON repair also failed: %s", e)
                logger.debug("Raw content (first 500 chars): %s", content[:500])
                raise

