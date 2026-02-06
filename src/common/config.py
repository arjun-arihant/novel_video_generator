"""Configuration management using dataclasses for type safety and validation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any
import os
import yaml


@dataclass
class OpenRouterConfig:
    """Configuration for OpenRouter API."""
    api_key: str
    model: str = "openrouter/auto"
    temperature: float = 0.3
    max_output_tokens: int = 4096
    timeout: int = 60
    
    def __post_init__(self):
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
        if not 0 <= self.temperature <= 1:
            raise ValueError("Temperature must be between 0 and 1")


@dataclass
class Want2GpConfig:
    """Configuration for Want2GP APIs (image + TTS)."""
    api_key: str
    base_url: str = "https://api.want2gp.ai/v1"
    image_model: str = "z-image"
    tts_model: str = "qwen3:tts"
    timeout: int = 120

    def __post_init__(self):
        if not self.api_key:
            raise ValueError("WANT2GP_API_KEY is required")


@dataclass
class ImageGenerationConfig:
    """Configuration for image generation."""
    model: str = "flux"
    width: int = 1280
    height: int = 720
    seed: Optional[int] = None
    max_retries: int = 10
    retry_delay_base: float = 2.0
    timeout: int = 120
    
    def __post_init__(self):
        if self.width < 64 or self.width > 2048:
            raise ValueError("Width must be between 64 and 2048")
        if self.height < 64 or self.height > 2048:
            raise ValueError("Height must be between 64 and 2048")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")


@dataclass
class TTSConfig:
    """Configuration for text-to-speech."""
    model: str = "gemini"
    voice: str = "Puck"
    rate: float = 1.0
    pitch: float = 0.0
    max_concurrent: int = 3
    timeout: int = 30
    
    def __post_init__(self):
        if self.rate < 0.5 or self.rate > 2.0:
            raise ValueError("Rate must be between 0.5 and 2.0")
        if self.pitch < -1.0 or self.pitch > 1.0:
            raise ValueError("Pitch must be between -1.0 and 1.0")
        if self.max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")


@dataclass
class VideoConfig:
    """Configuration for video composition."""
    fps: int = 24
    width: int = 1920
    height: int = 1080
    codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "5000k"
    audio_bitrate: str = "192k"
    ken_burns_intensity: float = 0.05
    ken_burns_speed: float = 0.02
    transition_duration: float = 0.5
    
    def __post_init__(self):
        if self.fps < 1 or self.fps > 120:
            raise ValueError("FPS must be between 1 and 120")
        valid_codecs = ["libx264", "libx265", "h264_nvenc", "h264_amf"]
        if self.codec not in valid_codecs:
            raise ValueError(f"Codec must be one of {valid_codecs}")


@dataclass
class PipelineConfig:
    """Main pipeline configuration."""
    openrouter: OpenRouterConfig
    want2gp: Want2GpConfig
    image: ImageGenerationConfig = field(default_factory=ImageGenerationConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    output_dir: Path = field(default_factory=lambda: Path("data/output"))
    temp_dir: Path = field(default_factory=lambda: Path("data/temp"))
    log_level: str = "INFO"
    continue_on_error: bool = True
    max_scenes: int = 10
    
    def __post_init__(self):
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
    
    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Create configuration from environment variables."""
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        want2gp_key = os.getenv("WANT2GP_API_KEY")
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        if not want2gp_key:
            raise ValueError("WANT2GP_API_KEY environment variable is required")

        openrouter_config = OpenRouterConfig(
            api_key=openrouter_key,
            model=os.getenv("OPENROUTER_MODEL", "openrouter/auto"),
            temperature=float(os.getenv("OPENROUTER_TEMPERATURE", "0.3")),
            max_output_tokens=int(os.getenv("OPENROUTER_MAX_TOKENS", "4096")),
            timeout=int(os.getenv("OPENROUTER_TIMEOUT", "60")),
        )

        want2gp_config = Want2GpConfig(
            api_key=want2gp_key,
            base_url=os.getenv("WANT2GP_BASE_URL", "https://api.want2gp.ai/v1"),
            image_model=os.getenv("WANT2GP_IMAGE_MODEL", "z-image"),
            tts_model=os.getenv("WANT2GP_TTS_MODEL", "qwen3:tts"),
            timeout=int(os.getenv("WANT2GP_TIMEOUT", "120")),
        )
        
        return cls(
            openrouter=openrouter_config,
            want2gp=want2gp_config,
            output_dir=Path(os.getenv("OUTPUT_DIR", "data/output")),
            temp_dir=Path(os.getenv("TEMP_DIR", "data/temp")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            continue_on_error=os.getenv("CONTINUE_ON_ERROR", "true").lower() == "true",
        )
    
    @classmethod
    def from_yaml(cls, path: Path) -> "PipelineConfig":
        """Load configuration from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        openrouter_data = data.get('openrouter', {})
        want2gp_data = data.get('want2gp', {})

        openrouter_config = OpenRouterConfig(
            api_key=os.getenv("OPENROUTER_API_KEY", openrouter_data.get('api_key', '')),
            model=openrouter_data.get('model', 'openrouter/auto'),
            temperature=openrouter_data.get('temperature', 0.3),
            max_output_tokens=openrouter_data.get('max_output_tokens', 4096),
            timeout=openrouter_data.get('timeout', 60),
        )

        want2gp_config = Want2GpConfig(
            api_key=os.getenv("WANT2GP_API_KEY", want2gp_data.get('api_key', '')),
            base_url=want2gp_data.get('base_url', 'https://api.want2gp.ai/v1'),
            image_model=want2gp_data.get('image_model', 'z-image'),
            tts_model=want2gp_data.get('tts_model', 'qwen3:tts'),
            timeout=want2gp_data.get('timeout', 120),
        )
        
        return cls(
            openrouter=openrouter_config,
            want2gp=want2gp_config,
            output_dir=Path(data.get('output_dir', 'data/output')),
            temp_dir=Path(data.get('temp_dir', 'data/temp')),
            log_level=data.get('log_level', 'INFO'),
        )
    
    def to_yaml(self, path: Path) -> None:
        """Save configuration to YAML file."""
        data = {
            'openrouter': {
                'model': self.openrouter.model,
                'temperature': self.openrouter.temperature,
                'max_output_tokens': self.openrouter.max_output_tokens,
                'timeout': self.openrouter.timeout,
            },
            'want2gp': {
                'base_url': self.want2gp.base_url,
                'image_model': self.want2gp.image_model,
                'tts_model': self.want2gp.tts_model,
                'timeout': self.want2gp.timeout,
            },
            'image': {
                'model': self.image.model,
                'width': self.image.width,
                'height': self.image.height,
                'max_retries': self.image.max_retries
            },
            'tts': {
                'voice': self.tts.voice,
                'rate': self.tts.rate,
                'pitch': self.tts.pitch,
                'max_concurrent': self.tts.max_concurrent
            },
            'video': {
                'fps': self.video.fps,
                'width': self.video.width,
                'height': self.video.height,
                'codec': self.video.codec
            },
            'output_dir': str(self.output_dir),
            'temp_dir': str(self.temp_dir),
            'log_level': self.log_level
        }
        
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)


# Global config instance (initialized lazily)
_config: Optional[PipelineConfig] = None


def get_config() -> PipelineConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = PipelineConfig.from_env()
    return _config


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load YAML configuration file if present."""
    config_path = path or Path("configs/voices.yaml")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_api_key(provider: str) -> str:
    """Get API key by provider name."""
    env_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "want2gp": "WANT2GP_API_KEY",
    }
    env_var = env_map.get(provider.lower())
    if not env_var:
        raise ValueError(f"Unknown provider: {provider}")
    api_key = os.getenv(env_var)
    if not api_key:
        raise ValueError(f"{env_var} environment variable is required")
    return api_key


def ensure_output_dir(path: Path) -> None:
    """Ensure output directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def set_config(config: PipelineConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config
    _config = None
