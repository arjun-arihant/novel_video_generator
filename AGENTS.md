# Novel Video Generator - Agent Guide

## Project Overview

Novel Video Generator is a Python-based pipeline that converts novel chapters into narrated, illustrated videos using state-of-the-art AI. It combines LLM-based scene extraction, local image generation (WanGP), text-to-speech synthesis (Qwen3 via WanGP), and FFmpeg-based video composition.

### Pipeline Flow
```
EPUB/Text → Scene Extraction (OpenRouter LLM) → Images (WanGP/Qwen3) → Audio (Qwen3 TTS) → Video (FFmpeg)
```

### Key Features
- **3-Pass TTS:** Optimized batch processing for Narrator, Voice Design, and Dialogue
- **Voice Cloning:** Characters use consistent voices derived from descriptions (Qwen3)
- **Character Consistency:** Seed-based image generation and rich character profiles
- **Interactive Web UI:** Flask-based interface for scene review and asset regeneration
- **Library Management:** EPUB ingestion with structured novel/chapter organization

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Runtime | Python 3.10+ | Core application |
| Web Framework | Flask 3.0+ | REST API + static files |
| LLM Client | OpenRouter API | Scene extraction, voice design |
| Image Generation | WanGP (local CLI) | Z-Image Turbo 6B model |
| TTS Engine | Qwen3 (via WanGP) | 3-pass voice synthesis |
| Video Composition | FFmpeg | Clip assembly with Ken Burns |
| EPUB Parsing | ebooklib + beautifulsoup4 | Novel ingestion |
| Environment | Conda | WanGP isolation |

---

## Project Structure

```
novel_video_generator/
├── cli.py                  # CLI entry point (argparse-based)
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (API keys, paths)
│
├── src/
│   ├── common/             # Shared utilities
│   │   ├── config.py       # Dataclass-based configuration
│   │   ├── validation.py   # Chapter/scene validators
│   │   ├── retry.py        # Exponential backoff decorator
│   │   └── logging_config.py
│   │
│   ├── web/                # Flask web interface
│   │   ├── web_server.py   # Main Flask app (REST + SSE)
│   │   ├── app.py          # Additional routes
│   │   └── static/         # Frontend (HTML/JS/CSS)
│   │       ├── index.html  # 5-step wizard UI
│   │       ├── app.js      # Frontend logic
│   │       └── style.css   # Aurora theme styling
│   │
│   ├── parser/             # Text parsing modules
│   │   ├── openrouter_parser.py  # LLM scene extraction
│   │   └── gemini_parser.py      # Alternative parser
│   │
│   ├── llm/                # LLM client
│   │   └── openrouter_client.py  # JSON generation with repair
│   │
│   ├── image/              # Image generation
│   │   └── generator.py    # WanGP CLI wrapper
│   │
│   ├── tts/                # Text-to-speech
│   │   ├── manager.py      # 3-pass orchestration
│   │   ├── qwen3.py        # Qwen3 engine (batch processing)
│   │   ├── qwen3_wrapper.py# Conda wrapper script
│   │   └── base.py         # Abstract TTS interface
│   │
│   ├── video/              # Video composition
│   │   └── composer.py     # FFmpeg-based assembly
│   │
│   ├── consistency/        # Character/location tracking
│   │   ├── store.py        # JSON persistence
│   │   └── voice_assigner.py # LLM voice design
│   │
│   ├── core/               # Novel management
│   │   ├── epub_parser.py  # EPUB → chapters
│   │   └── library_manager.py # Novel ecosystem
│   │
│   └── storage/            # Data persistence
│       └── epub_loader.py
│
├── data/                   # Runtime data (gitignored)
│   ├── novels/             # Library storage
│   ├── consistency/        # Character DB
│   ├── uploads/            # Temp uploads
│   └── web_runs/           # Pipeline outputs
│
├── tests/
│   └── verify_pipeline.py  # Integration test
│
└── configs/                # (Optional) YAML configs
```

---

## Configuration

### Environment Variables (`.env`)

```env
# OpenRouter (LLM scene extraction)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=xiaomi/mimo-v2-flash

# WanGP (local CLI image generation)
WANGP_PATH=D:\GeneAI\Wan2GP
WANGP_CONDA_ENV=wan2gp
WANGP_PROFILE=4
WANGP_ATTENTION=sdpa
CONDA_ACTIVATE_PATH=C:\Users\...\Scripts\activate.bat

# FFmpeg (video composition)
FFMPEG_PATH=D:\GeneAI\Wan2GP\ffmpeg_bins
```

### WanGP Settings Templates
- `qwen3_tts_base.json` - Base TTS parameters
- `qwen3_tts_customvoice.json` - Custom voice (narrator)
- `qwen3_tts_voicedesign.json` - Voice design pass
- `z_image_settings.json` - Image generation defaults

---

## Build and Run Commands

### Setup
```bash
# Python environment
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your API keys and paths
```

### Web Interface (Recommended)
```bash
python -m src.web.web_server
# Opens at http://localhost:5000
```

### CLI Usage
```bash
# Full pipeline
python cli.py pipeline chapter.json --output data/runs/001

# Step-by-step
python cli.py extract chapter.json --max-scenes 8
python cli.py images scenes.json --output data/images
python cli.py audio scenes.json --output data/audio
python cli.py video scenes.json --images data/images --audio data/audio

# Single test image
python cli.py image-gen "A wizard casting spells" --output test.png
```

### Verification
```bash
python tests/verify_pipeline.py
```

---

## Code Style Guidelines

### Python Conventions
- **Typing:** Use type hints everywhere (`typing` module)
- **Docstrings:** Google-style docstrings for modules, classes, functions
- **Imports:** Group as: stdlib → third-party → local (absolute imports)
- **Naming:**
  - `snake_case` for functions/variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

### Example Pattern
```python
"""Module description.

Extended description if needed.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from ..common import get_config

logger = logging.getLogger(__name__)

_CONSTANT_VALUE = 42

class MyClass:
    """Class description.
    
    Attributes:
        config: Configuration instance
    """
    
    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or get_config()
    
    def process(
        self, 
        data: Dict[str, Any],
        max_items: int = 10,
    ) -> List[str]:
        """Process data and return results.
        
        Args:
            data: Input dictionary
            max_items: Maximum items to process
            
        Returns:
            List of processed strings
            
        Raises:
            ValueError: If data is invalid
        """
        if not data:
            raise ValueError("Data cannot be empty")
        return [str(v) for v in data.values()[:max_items]]
```

### Error Handling
- Use custom exceptions in `src/common/exceptions.py`
- Log errors with context: `logger.error("Message: %s", e, exc_info=True)`
- Retry with backoff for external calls (see `@retry_with_backoff`)

---

## Testing

### Integration Test
```bash
python tests/verify_pipeline.py
```
Tests the full pipeline with a sample chapter, verifying:
- Environment setup (WanGP, FFmpeg)
- Scene extraction
- Image generation (if WanGP available)
- Audio generation (if TTS engine available)
- Video composition

### Manual Testing
1. Start web server: `python -m src.web.web_server`
2. Upload test EPUB or paste text
3. Run through all 5 steps
4. Verify outputs in `data/web_runs/`

---

## Architecture Patterns

### 1. Configuration Management
Dataclass-based config with validation in `src/common/config.py`:
```python
@dataclass
class OpenRouterConfig:
    api_key: str
    temperature: float = 0.3
    
    def __post_init__(self):
        if not self.api_key:
            raise ValueError("API key required")
```

### 2. Consistency Store
JSON-based persistence for character/location data:
- `ConsistencyStore` class manages `data/consistency/characters.json`
- Tracks appearance evolution per chapter
- Provides image descriptors for prompt enrichment

### 3. 3-Pass TTS Strategy
```
Pass 1: Voice Design (create voice samples for new characters)
Pass 2: Narrator (batch generate all narration)
Pass 3: Dialogue (batch generate all dialogue with voice cloning)
```

### 4. Scene Data Structure
```python
scene = {
    "id": 1,
    "title": "Scene Title",
    "visual_description": "Detailed image prompt...",
    "atmospheric_lighting": "dim distinct shadows",
    "composition_notes": "wide shot, dutch angle",
    "sequence": [
        {"type": "narration", "text": "...", "mood": "tense"},
        {"type": "dialogue", "speaker": "Name", "text": "...", "mood": "angry"}
    ],
    "characters": ["Character Name"],
    "locations": ["Location Name"],
    "time_of_day": "night",
    "lighting": "moonlit",
    "mood": "tense"
}
```

---

## Security Considerations

1. **API Keys:** Store in `.env`, never commit. `.env` is in `.gitignore`.
2. **File Uploads:** Limited to `.epub` and `.json` extensions in web UI.
3. **Path Traversal:** All file paths resolved with `Path().resolve()` before use.
4. **Subprocess:** WanGP calls use shell=True with validated paths - ensure `WANGP_PATH` is trusted.
5. **FFmpeg:** External binary execution - ensure FFmpeg is from trusted source.

---

## Development Workflow

### Adding a New Parser
1. Create module in `src/parser/`
2. Implement `extract_scenes(chapter_text, **kwargs) -> dict`
3. Return format: `{"scenes": [...], "characters": [...], "locations": [...]}`
4. Update `cli.py` to use new parser option

### Adding a New TTS Engine
1. Inherit from `src/tts/base.py` or implement compatible interface
2. Add engine initialization in `src/tts/manager.py`
3. Implement batch generation methods

### Adding Web Endpoints
1. Add route in `src/web/web_server.py`
2. Use existing SSE pattern for long-running tasks
3. Update frontend in `src/web/static/app.js`

---

## Troubleshooting

### WanGP Not Found
- Verify `WANGP_PATH` in `.env` points to WanGP installation
- Check `wgp.py` exists in that directory
- Ensure Conda environment `wan2gp` exists: `conda env list`

### FFmpeg Issues
- Verify FFmpeg in PATH: `ffmpeg -version`
- Or set `FFMPEG_PATH` in `.env`

### OpenRouter Errors
- Check API key in `.env`
- Verify model name is valid
- Check rate limits on OpenRouter dashboard

### TTS Failures
- Verify WanGP has TTS model downloaded
- Check Conda environment activation
- Review logs in terminal output

---

## License

MIT License
