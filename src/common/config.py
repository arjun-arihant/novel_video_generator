"""Configuration management for the novel video generator."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv

# Load environment variables once
load_dotenv()


def get_api_key(service: str) -> str:
    """
    Get API key for a specific service.

    Args:
        service: Service name (e.g., 'gemini')

    Returns:
        API key string

    Raises:
        ValueError: If API key is not found
    """
    key_map = {
        'gemini': 'GEMINI_API_KEY',
    }

    env_var = key_map.get(service.lower())
    if not env_var:
        raise ValueError(f"Unknown service: {service}")

    api_key = os.getenv(env_var)
    if not api_key:
        raise ValueError(
            f"{env_var} not found in environment. "
            f"Please set it in your .env file."
        )

    return api_key


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file. Defaults to configs/voices.yaml

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "configs" / "voices.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def ensure_output_dir(path: Path) -> Path:
    """
    Ensure output directory exists.

    Args:
        path: Directory path

    Returns:
        The created/existing path
    """
    path.mkdir(parents=True, exist_ok=True)
    return path
