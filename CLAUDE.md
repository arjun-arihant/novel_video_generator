# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Novel Video Generator is an end-to-end pipeline that converts EPUB webnovel chapters into narrated YouTube videos with AI-generated images. The pipeline runs locally (CPU-based) and uses cloud APIs for image generation and optional TTS acceleration.

## Development Setup

### Environment
- Python 3.11.9 (3.10+ required)
- Virtual environment: `.venv`

### Activation Commands
Windows:
```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:
```bash
source .venv/bin/activate
```

### Dependencies
Install dependencies:
```bash
pip install -r requirements.txt
```

Dependencies include: `ebooklib`, `beautifulsoup4`, `lxml`, `ftfy`, `regex`, `tqdm`

### Environment Variables
API keys should be stored in `.env` (not committed to repository):
```
OPENAI_API_KEY=...
YOUTUBE_CLIENT_SECRET=...
YOUTUBE_REFRESH_TOKEN=...
```

## Pipeline Architecture

The project is organized into a multi-stage pipeline:

1. **EPUB Extraction** (`src/epub/`) - Extract and clean chapters from EPUB files
2. **Scene Extraction** (`src/parser/`) - Use LLM to extract 2-4 major scenes per chapter with character descriptions via Google gemini API
3. **Image Generation** (`src/image/`) - Generate AI images via OpenAI/Stability/Replicate/google gemini api
4. **Text-to-Speech** (`src/tts/`) - Local Maya-1 TTS or cloud GPU TTS
5. **Video Assembly** (`src/video/`) - Use ffmpeg/moviepy with Ken Burns effects, subtitles, music
6. **YouTube Upload** (`src/publishing/`) - Auto-upload with metadata

Additional components:
- `src/core/` - Configuration, utilities, logging, pipeline orchestration
- `src/api/` - Optional FastAPI interface (planned)

## Data Structure

The pipeline uses the following data organization:

```
data/
├── raw_epubs/           # Source EPUB files
├── chapters_raw/        # Raw extracted chapters
├── chapters_clean/      # Cleaned chapter JSON files
│   └── <book_id>/       # e.g., ihacw/
│       └── chapter####.json  # chapter0001.json, chapter0002.json, etc.
└── character_db/        # Character tracking database

assets/                  # Images, audio, music files
outputs/                 # Final videos and logs
configs/                 # YAML configurations for styles/voices/settings
```

### Chapter JSON Format
Cleaned chapters are stored as JSON with this structure:
```json
{
  "id": 1,
  "title": "Chapter 1: Title",
  "paragraphs": ["paragraph1", "paragraph2", ...],
  "word_count": 1284
}
```

## Current Implementation Status

**Implemented:**
- EPUB extraction and cleaning (`src/epub/epub_cleaner.py`)
  - Removes boilerplate (translator notes, ads, links)
  - Cleans HTML to paragraphs
  - Normalizes Unicode, quotes, whitespace
  - Filters junk tags (script, style, iframe, footer, nav)

**Not Yet Implemented:**
- Scene extraction with LLM
- Character tracking database
- Image generation
- TTS narration
- Video assembly
- YouTube upload
- Pipeline scripts
- Configuration files
- Tests

## Running Commands

### EPUB Cleaning (Currently Functional)
```bash
python src/epub/epub_cleaner.py <path_to_epub> --out data/chapters_clean
```

Example:
```bash
python src/epub/epub_cleaner.py data/raw_epubs/mybook.epub --out data/chapters_clean
```

### Planned Commands (Not Yet Implemented)
```bash
# Scene extraction
python scripts/run_scene_extraction.py --chapter 1

# Image generation
python scripts/run_image_generation.py --chapter 1

# TTS narration
python scripts/run_tts.py --chapter 1

# Video assembly
python scripts/run_video_build.py --chapter 1

# Full pipeline with upload
python scripts/run_pipeline.py --upload --chapter 1
```

## Key Technical Details

### EPUB Cleaning Logic
- Boilerplate detection uses pattern matching on lowercase text
- Paragraphs shorter than 10 characters are filtered out
- HTML parsing uses BeautifulSoup with XML parser
- Text encoding issues fixed with `ftfy` library
- Chapter titles extracted from `<h1>` or `<h2>` tags

### Planned Configuration Files
The following YAML configs are referenced but not yet created:
- `configs/style_prompts.yaml` - Art direction for image generation
- `configs/voices.yaml` - Voice presets for narrator and characters
- `configs/pipeline_settings.yaml` - Batch size, concurrency, retry settings

## Important Conventions

- Chapter files use zero-padded 4-digit numbering: `chapter0001.json`
- Book-specific data organized under `data/chapters_clean/<book_id>/`
- Test novel data exists for book ID `ihacw` with 22 chapters
- No git repository initialized yet
- Empty tests directory - testing infrastructure not set up

## When Implementing New Features

1. Follow the modular pipeline structure - each stage should be independent
2. New pipeline stages should read from and write to the `data/` directory
3. Configuration should be externalized to YAML files in `configs/`
4. Scripts should be CLI-based with argparse for easy automation
5. Use logging via Python's logging module (pattern: `logging.getLogger(__name__)`)
6. Dependencies on external APIs (OpenAI, Stability, etc.) should be abstracted for easy swapping
