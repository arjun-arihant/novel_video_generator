# Novel Video Generator

A streamlined Python pipeline that converts novel chapters (text) into animated videos with narration.

## Features

- **Scene Extraction**: Uses **Gemini 2.5 Flash** to analyze text and extract visual scenes
- **Image Generation**: Uses **Pollinations.ai Flux models** for Manhua-style images
- **Text-to-Speech**: Uses **Gemini 2.5 Flash Preview TTS** for natural narration
- **Video Assembly**: Combines images and audio with **Ken Burns effects** (pan/zoom)
- **Unified CLI**: Single command-line interface for all operations

## Prerequisites

- Python 3.10+
- **Gemini API Key** (for scene extraction and TTS)
- `ffmpeg` installed and in your system PATH

## Quick Start

### 1. Setup

```bash
# Clone and navigate to repository
git clone <repo-url>
cd novel_video_generator

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate

# Activate (Unix/MacOS)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Run

```bash
# Run full pipeline
python cli.py pipeline data/ihacw/chapters/ihacw_ch0001.json

# Or run individual steps
python cli.py extract chapter.json
python cli.py images scenes.json
python cli.py audio scenes.json
python cli.py video scenes.json
```

## CLI Commands

The unified CLI provides the following commands:

### Full Pipeline
```bash
python cli.py pipeline <chapter.json> [-o output_dir]
```
Runs the complete pipeline: extraction → images → audio → video.

### Individual Steps

**Extract scenes from chapter:**
```bash
python cli.py extract <chapter.json> [-o scenes.json]
```

**Generate images for scenes:**
```bash
python cli.py images <scenes.json> [-o images_dir] [-f] [--continue-on-error]
```
- `-f, --force`: Regenerate existing images
- `--continue-on-error`: Continue if some images fail

**Generate audio for scenes:**
```bash
python cli.py audio <scenes.json> [-o audio_dir] [-c N] [--continue-on-error]
```
- `-c, --concurrent N`: Max concurrent generations (default: 3)
- `--continue-on-error`: Continue if some audio fails

**Build video from components:**
```bash
python cli.py video <scenes.json> --images <images_dir> --audio <audio_dir> [-o output.mp4]
```

### Global Options
```bash
python cli.py --log-level [DEBUG|INFO|WARNING|ERROR] <command> ...
```

## Project Structure

```
novel_video_generator/
├── cli.py                 # Unified CLI entry point
├── src/
│   ├── common/           # Shared utilities (config, retry, validation, logging)
│   ├── parser/           # Scene extraction (Gemini)
│   ├── image/            # Image generation (Pollinations.ai)
│   ├── tts/              # Text-to-speech (Gemini TTS)
│   └── video/            # Video composition (MoviePy)
├── configs/
│   └── voices.yaml       # Voice configuration
├── data/
│   ├── ihacw/chapters/   # Sample chapter files
│   ├── scenes/           # Extracted scenes
│   ├── images/           # Generated images
│   ├── audio/            # Generated audio
│   └── videos/           # Final videos
├── scripts_old/          # Archived scripts (reference only)
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Configuration

### Voice Settings

Edit `configs/voices.yaml` to customize voices:

```yaml
voices:
  narrator:
    name: "Puck"        # Available: Puck, Charon, Kore, Fenrir, Aoede
    provider: "gemini"
    rate: 1.0
    pitch: 0.0

  male_protagonist:
    name: "Fenrir"
    provider: "gemini"
    rate: 1.0
    pitch: 0.0
```

## Input Format

Chapter files should be JSON with this structure:

```json
{
  "chapter_number": 1,
  "title": "Chapter Title",
  "content": [
    "First paragraph...",
    "Second paragraph...",
    ...
  ]
}
```

## Output

Pipeline generates:
- **Scenes**: `data/scenes/ch####_scenes.json` (3-6 scenes per chapter)
- **Images**: `data/images/scene_###.png` (1280x720 PNG files)
- **Audio**: `data/audio/scene_###.mp3` (MP3 narration per scene)
- **Video**: `data/videos/chapter_####.mp4` (1920x1080, 24fps, H.264)

## Architecture

### Scene-Based Pipeline

The pipeline operates on **scenes** (not paragraphs):

1. **Scene Extraction**: Gemini analyzes chapter text and breaks it into 3-6 visual scenes
2. **Image Generation**: Each scene gets a Manhua-style image based on visual description
3. **Audio Generation**: Each scene's text is narrated separately
4. **Video Assembly**: Images and audio are synced with Ken Burns effects

### Key Design Decisions

- **Scene-based**: All components work with scene granularity for better coherence
- **Async TTS**: Audio generation runs concurrently (3 scenes at a time)
- **Retry logic**: Exponential backoff for API calls (10 attempts for images, 7 for scenes)
- **Type safety**: Full type hints throughout codebase
- **Validation**: Input validation for chapter and scene data structures

## Troubleshooting

**Import errors after update:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**GEMINI_API_KEY not found:**
```bash
# Check .env file exists and contains GEMINI_API_KEY
# Make sure .env is in the project root directory
```

**ffmpeg not found:**
```bash
# Install ffmpeg and add to PATH
# Windows: https://www.ffmpeg.org/download.html
# MacOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg
```

**Image generation fails:**
- Pollinations.ai uses free tier and may have rate limits
- Retry logic will wait up to 120 seconds between attempts
- Use `--continue-on-error` to skip failed images

## Migration from Old Scripts

If you were using the old `scripts/` folder, see `scripts_old/README.md` for migration guide.

Key changes:
- Unified CLI interface (all commands in `cli.py`)
- Scene-based TTS (not paragraph-based)
- Better error handling and validation
- Type hints throughout

## Development

```bash
# Run with debug logging
python cli.py --log-level DEBUG pipeline chapter.json

# Test individual components
python -c "from src.parser.gemini_parser import SceneExtractor; print(SceneExtractor())"
```

## License

MIT License (see LICENSE file)

## Contributing

Contributions welcome! Please open an issue or PR.
