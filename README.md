# 📖 Novel Video Generator

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()

Turn any EPUB ebook into an immersive, narrated video experience. **Novel Video Generator** is an automated pipeline that ingest ebooks, uses LLMs to break chapters into visually compelling scenes, generates voiceovers, creates images with **Wan2GP**, and composites everything into chapter-by-chapter videos.

---

## 🚀 Features

- **📖 EPUB Ingestion**: Automatically parses structural chapter data from raw `.epub` files.
- **🧠 Intelligent Scene Extraction**: Uses advanced LLMs (via OpenRouter) to semantically split chapters into vivid, descriptive scenes.
- **🗣️ Dynamic TTS & Voices**: Assigns consistent character voice identities and generates high-quality narrations.
- **🎨 Image Generation**: Plugs into **Wan2GP** for headless, batch image generation using text-to-image AI pipelines.
- **🎞️ Video Compositing**: Combines audio and images with smooth transitions, creating ready-to-watch videos.
- **💾 State Manager**: Full resumption support! If the pipeline fails, it resumes exactly where it left off.

## 📁 Repository Structure

```plaintext
novel_video_generator/
├── epub_pipeline/       # Core python application code
│   ├── pipeline/        # Distinct pipeline stages (ingestor, extractor, etc)
│   └── main.py          # Entrypoint script
├── config/              # Configuration files (TTS, queues)
├── data/                # Generated assets, staging areas, and processing data
├── docs/                # Project documentation and setup guides
└── requirements.txt     # Python dependencies
```

## 🛠️ Setup & Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/arjun-arihant/novel_video_generator.git
   cd novel_video_generator
   ```

2. **Set up a Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Create a `.env` file at the root of the project with:
   ```env
   OPENROUTER_API_KEY="your_api_key_here"
   WANGP_PATH="C:\path\to\your\Wan2GP"
   ```

## ⚡ Usage

Run the core pipeline from the repository root:

```bash
python epub_pipeline/main.py --epub "data/examples/my_book.epub"
```

**Optional Arguments:**
- `--chapter <no>`: Process only a specific chapter (great for testing).
- `--interactive`: Pauses after major phases to await user confirmation.
- `--from-stage <stage>`: Resume pipeline from a specific stage (e.g., `extractor`, `image_queue`).

## ⚙️ How It Works

The generator operates through a strictly mapped sequence of states:
1. **Ingestor & Normalizer**: Reads the EPUB, standardizing HTML into clean text.
2. **Extractor**: LLM splits chapter text into logical scenes.
3. **Entity Resolver**: Tracks character appearances across scenes for voice consistency.
4. **Prompt Builder**: Translates scene descriptions into visual prompts.
5. **Image & Audio Queues**: Dispatches background generation jobs for TTS and images.
6. **Generator**: Waits for generation completion and verifies assets.
7. **Composer**: Stitches everything into a `.mp4` video.
