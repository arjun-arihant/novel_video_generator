"""OpenRouter client utilities."""

import json
import logging
from typing import Any, Dict, List, Optional

import requests

from ..common import get_config

logger = logging.getLogger(__name__)


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

    def generate_json(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate JSON output from the model."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
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
        return json.loads(content)
