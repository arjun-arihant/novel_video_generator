"""Kokoro TTS provider implementation.

Uses the Kokoro-82M REST API running at localhost:8000.
API Reference: KOKORO_TTS_API_REFERENCE.md
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Union

import requests

from .base import TTSProvider, VoiceConfig

logger = logging.getLogger(__name__)

KOKORO_DEFAULT_URL = "http://localhost:8000"


class KokoroTTSProvider(TTSProvider):
    """TTS provider using Kokoro-82M neural TTS (24kHz, 54 voices, 9 languages)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_format: Optional[str] = None,
        timeout: int = 60,
    ):
        self.base_url = (base_url or os.getenv("KOKORO_BASE_URL", KOKORO_DEFAULT_URL)).rstrip("/")
        self.default_format = default_format or os.getenv("KOKORO_FORMAT", "wav")
        self.timeout = timeout
        logger.info("Kokoro TTS provider: %s (format=%s)", self.base_url, self.default_format)

    def health_check(self) -> dict:
        """Check if Kokoro service is running."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Kokoro health check failed: %s", e)
            return {"status": "error", "detail": str(e)}

    def list_voices(self, lang: Optional[str] = None) -> dict:
        """List available voices, optionally filtered by language code."""
        params = {}
        if lang:
            params["lang"] = lang
        try:
            resp = requests.get(
                f"{self.base_url}/voices", params=params, timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Failed to list Kokoro voices: %s", e)
            return {}

    async def generate_audio(
        self,
        text: str,
        output_path: Union[str, Path],
        voice_config: VoiceConfig,
    ) -> Optional[str]:
        """Generate audio using Kokoro POST /generate endpoint."""
        if not text or not text.strip():
            logger.warning("Empty text, skipping TTS generation")
            return None

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ext = output_path.suffix.lstrip(".").lower()
        audio_format = ext if ext in ("wav", "mp3", "ogg", "flac") else self.default_format

        payload = {
            "text": text,
            "voice": voice_config.name,
            "speed": voice_config.speed,
            "format": audio_format,
        }

        try:
            logger.info(
                "Kokoro TTS: voice=%s, speed=%.1f, format=%s, text=%s...",
                voice_config.name,
                voice_config.speed,
                audio_format,
                text[:60],
            )

            resp = requests.post(
                f"{self.base_url}/generate",
                json=payload,
                timeout=self.timeout,
            )

            if resp.status_code != 200:
                error_detail = ""
                try:
                    error_detail = resp.json().get("detail", resp.text[:200])
                except Exception:
                    error_detail = resp.text[:200]
                logger.error(
                    "Kokoro TTS failed (%s): %s", resp.status_code, error_detail
                )
                return None

            content_type = resp.headers.get("Content-Type", "")
            if not content_type.startswith("audio/"):
                logger.error("Unexpected content type: %s", content_type)
                return None

            with open(output_path, "wb") as f:
                f.write(resp.content)

            logger.info("Audio saved: %s (%d bytes)", output_path, len(resp.content))
            return str(output_path)

        except requests.Timeout:
            logger.error("Kokoro TTS request timed out after %ds", self.timeout)
            return None
        except requests.ConnectionError:
            logger.error(
                "Cannot connect to Kokoro TTS at %s. Is the service running?",
                self.base_url,
            )
            return None
        except Exception as e:
            logger.error("Kokoro TTS error: %s", e, exc_info=True)
            return None

    async def generate_with_mix(
        self,
        text: str,
        output_path: Union[str, Path],
        voices: List[str],
        speed: float = 1.0,
    ) -> Optional[str]:
        """Generate audio using a mix of 2-5 voices via /voices/mix endpoint."""
        if not text or not text.strip():
            return None
        if len(voices) < 2:
            # Fall back to standard generation with single voice
            vc = VoiceConfig(name=voices[0] if voices else "am_puck", speed=speed)
            return await self.generate_audio(text, output_path, vc)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ext = output_path.suffix.lstrip(".").lower()
        audio_format = ext if ext in ("wav", "mp3", "ogg", "flac") else self.default_format

        payload = {
            "voices": voices[:5],
            "text": text,
            "speed": speed,
            "format": audio_format,
        }

        try:
            logger.info("Kokoro voice mix: %s, text=%s...", voices, text[:60])
            resp = requests.post(
                f"{self.base_url}/voices/mix",
                json=payload,
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                logger.error("Voice mix failed (%s), falling back to first voice", resp.status_code)
                vc = VoiceConfig(name=voices[0], speed=speed)
                return await self.generate_audio(text, output_path, vc)

            with open(output_path, "wb") as f:
                f.write(resp.content)
            logger.info("Mixed voice audio saved: %s (%d bytes)", output_path, len(resp.content))
            return str(output_path)

        except Exception as e:
            logger.error("Voice mix error: %s, falling back", e)
            vc = VoiceConfig(name=voices[0], speed=speed)
            return await self.generate_audio(text, output_path, vc)

