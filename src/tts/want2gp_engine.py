"""Want2GP TTS provider implementation."""

import logging
from pathlib import Path
from typing import Optional, Union

import requests

from ..common import get_config
from .base import TTSProvider, VoiceConfig

logger = logging.getLogger(__name__)


class Want2GPTTSProvider(TTSProvider):
    """TTS provider using Want2GP Qwen3 TTS."""

    def __init__(self, model: Optional[str] = None):
        config = get_config().want2gp
        self.api_key = config.api_key
        self.model = model or config.tts_model
        self.base_url = config.base_url.rstrip("/")
        self.timeout = config.timeout

    async def generate_audio(
        self,
        text: str,
        output_path: Union[str, Path],
        voice_config: VoiceConfig,
    ) -> Optional[str]:
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            payload = {
                "model": self.model,
                "input": text,
                "voice": voice_config.name,
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            url = f"{self.base_url}/audio/speech"
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            if response.status_code != 200:
                logger.error(
                    "Want2GP TTS request failed: %s - %s",
                    response.status_code,
                    response.text[:200],
                )
                return None

            content_type = response.headers.get("Content-Type", "")
            audio_bytes: Optional[bytes]
            if content_type.startswith("audio/"):
                audio_bytes = response.content
            else:
                data = response.json()
                audio_bytes = self._extract_audio_bytes(data)

            if not audio_bytes:
                logger.warning("No audio data returned from Want2GP.")
                return None

            with open(output_path, "wb") as f:
                f.write(audio_bytes)

            logger.info("Audio saved to %s", output_path)
            return str(output_path)

        except Exception as e:
            logger.error("Want2GP TTS error: %s", e, exc_info=True)
            return None

    @staticmethod
    def _extract_audio_bytes(data: dict) -> Optional[bytes]:
        if "audio" in data:
            import base64

            return base64.b64decode(data["audio"])
        if "data" in data and data["data"]:
            item = data["data"][0]
            if "b64_json" in item:
                import base64

                return base64.b64decode(item["b64_json"])
            if "url" in item:
                response = requests.get(item["url"], timeout=120)
                response.raise_for_status()
                return response.content
        return None
