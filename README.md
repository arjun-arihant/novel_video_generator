# 📖 Novel Video Generator

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()

Turn any EPUB ebook into an immersive, narrated video experience. **Novel Video Generator** is an automated pipeline that ingests ebooks, uses LLMs to break chapters into visually compelling scenes, generates AI voiceovers with **Qwen3-TTS**, creates images with **Wan2GP**, and composites everything into chapter-by-chapter videos.

---

## 🚀 Features

- **📖 EPUB Ingestion**: Automatically parses structural chapter data from raw `.epub` files.
- **🧠 4-Pass LLM Architecture**: Scene extraction → Speaker annotation → Script review → Visual prompt refinement.
- **🗣️ AI Voice Generation**: Powered by [Alexandria Audiobook](https://github.com/Finrandojin/alexandria-audiobook)'s Qwen3-TTS engine — supports custom voices, voice cloning, voice design, and LoRA training.
- **🎨 Image Generation**: Plugs into **Wan2GP** for headless, batch image generation.
- **🎞️ Video Compositing**: FFmpeg-based composition with crossfade transitions.
- **💾 Full Resumption**: If the pipeline fails, it resumes exactly where it left off.
- **🌐 Interactive Web UI**: Browser-based editor for fine-tuning voices, editing audio, reviewing images, and managing the pipeline.

## 📁 Repository Structure

```plaintext
novel_video_generator/
├── app/                 # Alexandria-based web UI (FastAPI)
│   ├── tts.py           # Qwen3-TTS engine
│   ├── project.py       # Project management
│   ├── generate_script.py  # Speaker annotation (Pass 2)
│   ├── review_script.py    # Script review (Pass 3)
│   └── static/          # Web UI frontend
├── pipeline/            # Core pipeline stages (10 stages)
│   ├── config.py        # Central configuration
│   ├── ingestor.py      # Stage 1: EPUB parsing
│   ├── normalizer.py    # Stage 2: HTML → text
│   ├── scene_extractor.py  # Stage 3: LLM scene splitting
│   ├── entity_resolver.py  # Stage 4: Name canonicalization
│   ├── speaker_annotator.py  # Stages 5-6: Speaker annotation + review
│   ├── prompt_builder.py   # Stage 7: Visual + TTS prompts
│   ├── image_queue.py   # Stage 8: Wan2GP queue builder
│   ├── image_generator.py  # Stage 9: Wan2GP images
│   ├── audio_generator.py  # Stage 10: Qwen3-TTS audio
│   ├── composer.py      # Stage 11: FFmpeg video
│   ├── voice_manager.py # Voice config management
│   ├── state_manager.py # Pipeline state + resumption
│   └── validator.py     # Asset validation
├── llm/                 # LLM client utilities
│   ├── client.py        # OpenAI-compatible API client
│   └── prompts.py       # System/user prompts
├── data/novels/         # Generated novel data
├── main.py              # CLI entrypoint
└── requirements.txt     # Python dependencies
```

## 🛠️ Setup & Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/arjun-arihant/novel_video_generator.git
   cd novel_video_generator
   ```

2. **Install PyTorch** (with CUDA support for GPU):
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables** (`.env`):
   ```env
   OPENROUTER_API_KEY="your_api_key"
   WANGP_PATH="C:\path\to\Wan2GP"
   LLM_MODEL="qwen/qwen3-235b-a22b"
   TTS_DEVICE=auto
   NARRATOR_VOICE=Ryan
   ```

## ⚡ Usage

### CLI Pipeline
```bash
# Full pipeline
python main.py --epub "data/examples/book.epub"

# Single chapter
python main.py --epub "book.epub" --chapter 1

# Resume from a stage
python main.py --epub "book.epub" --from-stage audio_generator

# Interactive mode (pause between stages)
python main.py --epub "book.epub" --interactive
```

### Web UI
```bash
python main.py --web-ui
# Open http://127.0.0.1:4200 in your browser
```

## ⚙️ Pipeline Stages

| # | Stage | LLM Pass | Description |
|---|-------|----------|-------------|
| 1 | Ingestor | — | Parse EPUB structure |
| 2 | Normalizer | — | HTML → clean text |
| 3 | Scene Extractor | Pass 1 | Split into visual scenes |
| 4 | Entity Resolver | — | Canonicalize names |
| 5 | Speaker Annotator | Pass 2 | Speaker labels + TTS directions |
| 6 | Script Reviewer | Pass 3 | Fix annotation errors |
| 7 | Prompt Builder | Pass 4 | Visual + voice prompts |
| 8 | Image Generator | — | Wan2GP AI images |
| 9 | Audio Generator | — | Qwen3-TTS voiceover |
| 10 | Composer | — | FFmpeg video output |

## 🎤 Voice Types

| Type | Description | Best For |
|------|-------------|----------|
| **Custom** | 9 pre-trained voices (Ryan, Aiden, Serena, etc.) | Narrator, main characters |
| **Design** | Create voice from text description | Unique character voices |
| **Clone** | Clone from 5-15s reference audio | Specific voice matching |
| **LoRA** | Fine-tuned voice adapters | Persistent voice identities |

## 📋 Requirements

- **Python** 3.10+
- **GPU**: 8 GB VRAM minimum (16 GB+ recommended)
- **Wan2GP**: For image generation
- **FFmpeg**: For video composition
- **LLM API**: OpenRouter, LM Studio, Ollama, or any OpenAI-compatible API
