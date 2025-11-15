# 📘 Novel Video Generator

**End-to-end pipeline that converts EPUB webnovel chapters into narrated YouTube videos with AI-generated images.**

This project runs **entirely on your local desktop (CPU)** and uses cloud APIs only for image generation and optional TTS acceleration.

## 🚀 Features

### ✔ EPUB → Clean Text
- Extract chapters from EPUB
- Clean HTML → paragraphs
- Remove boilerplate (translator notes, ads)
- Normalize Unicode, quotes, whitespace

### ✔ Scene + Character Extraction
- Use LLM to extract:
  - 2–4 major scenes per chapter
  - Character descriptions
  - Dialogue and emotion cues
- Generate 1-line image prompts

### ✔ Image Generation
- 2–4 AI images per chapter
- Supports:
  - OpenAI Images
  - Stability/SDXL
  - Replicate/Flux

### ✔ Narration (TTS)
- Local Maya-1 inference for testing (CPU)
- Cloud GPU TTS for full chapters

### ✔ Video Assembly
- ffmpeg/moviepy
- Ken Burns effect on stills
- Background music
- Subtitles (SRT)
- Intro/outro cards

### ✔ YouTube Upload
- Auto upload
- Auto thumbnail
- Auto title, tags, and description

## 📁 Project Structure

```
novel_video_generator/
│
├── src/
│   ├── epub/              # EPUB loading + cleaning
│   ├── parser/            # scene + character extraction
│   ├── tts/               # Maya-1 TTS
│   ├── image/             # image generation
│   ├── video/             # video assembly
│   ├── publishing/        # YouTube uploading
│   ├── core/              # config, utils, logger, pipeline
│   └── api/               # optional FastAPI interface
│
├── data/                  # raw + processed novel data
├── assets/                # images, audio, music
├── outputs/               # final videos + logs
├── configs/               # YAML configs for style/voices/etc.
├── scripts/               # CLI scripts for each pipeline step
├── tests/                 # unit tests
├── models/                # (optional) local model weights
├── .env                   # API keys (not committed)
├── requirements.txt
├── requirements.lock
└── README.md
```

## 🔧 Installation

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/novel_video_generator.git
cd novel_video_generator
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate it

**Windows:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Add API keys to .env

Create `.env`:

```ini
OPENAI_API_KEY=...
YOUTUBE_CLIENT_SECRET=...
YOUTUBE_REFRESH_TOKEN=...
```

## 🧪 Quick Start

### 1. Put your EPUB into:

```bash
data/raw_epubs/
```

### 2. Run EPUB → Clean JSON

```bash
python src/epub/epub_cleaner.py data/raw_epubs/mybook.epub --out data/chapters_clean
```

### 3. Run Scene Extraction

```bash
python scripts/run_scene_extraction.py --chapter 1
```

### 4. Generate Images

```bash
python scripts/run_image_generation.py --chapter 1
```

### 5. Generate Narration

```bash
python scripts/run_tts.py --chapter 1
```

### 6. Build the Video

```bash
python scripts/run_video_build.py --chapter 1
```

### 7. Upload to YouTube

```bash
python scripts/run_pipeline.py --upload --chapter 1
```

## ⚙️ Config Files

**`configs/style_prompts.yaml`**  
Art direction for image generation.

**`configs/voices.yaml`**  
Voice presets for narrator and characters.

**`configs/pipeline_settings.yaml`**  
Batch size, concurrency, retry settings, CPU/GPU flags.

## 🧱 Technologies Used

- Python 3.10+
- ebooklib, bs4, lxml for EPUB parsing
- ffmpeg / moviepy for video
- OpenAI / Stability / Replicate for image generation
- Maya-1 TTS local & cloud inference
- YouTube Data API for uploading

## 🧩 Roadmap

- Character-specific voice cloning
- Character-consistent image generation (LoRA)
- Full novel batch processing
- Web UI
- GPT-powered script editing

## 📝 License

MIT / Apache-2.0 (choose one)