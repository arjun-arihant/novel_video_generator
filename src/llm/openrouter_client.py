"""OpenRouter client utilities."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import requests

from ..common import get_config

logger = logging.getLogger(__name__)


import json_repair


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
            error_text = response.text[:1000]
            # Check for content moderation block
            if "content_filter" in error_text or "Moderation" in error_text:
                raise RuntimeError(
                    f"Content blocked by moderation filter. "
                    f"The text may be malformed or contain sensitive content. "
                    f"Error: {error_text[:300]}"
                )
            raise RuntimeError(
                f"OpenRouter error {response.status_code}: {error_text}"
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
            try:
                # json_repair fixes missing quotes, trailing commas, and unescaped characters 
                repaired_obj = json_repair.loads(content)
                if not isinstance(repaired_obj, dict):
                    raise ValueError(f"Repair succeeded but returned {type(repaired_obj)}, expected dict")
                return repaired_obj
            except Exception as e:
                logger.error("JSON repair also failed: %s", e)
                logger.debug("Raw content (first 500 chars): %s", content[:500])
                raise

