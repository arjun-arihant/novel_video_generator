\# 📘 Novel Video Generator  

\*\*End-to-end pipeline that converts EPUB webnovel chapters into narrated YouTube videos with AI-generated images.\*\*



This project runs \*\*entirely on your local desktop (CPU)\*\* and uses cloud APIs only for image generation and optional TTS acceleration.



---



\# 🚀 Features



\### \*\*✔ EPUB → Clean Text\*\*

\- Extract chapters from EPUB  

\- Clean HTML → paragraphs  

\- Remove boilerplate (translator notes, ads)  

\- Normalize Unicode, quotes, whitespace  



\### \*\*✔ Scene + Character Extraction\*\*

\- Use LLM to extract:  

&nbsp; - 2–4 major scenes per chapter  

&nbsp; - Character descriptions  

&nbsp; - Dialogue and emotion cues  

\- Generate 1-line image prompts  



\### \*\*✔ Image Generation\*\*

\- 2–4 AI images per chapter  

\- Supports:  

&nbsp; - OpenAI Images  

&nbsp; - Stability/SDXL  

&nbsp; - Replicate/Flux  



\### \*\*✔ Narration (TTS)\*\*

\- Local Maya-1 inference for testing (CPU)  

\- Cloud GPU TTS for full chapters  



\### \*\*✔ Video Assembly\*\*

\- ffmpeg/moviepy  

\- Ken Burns effect on stills  

\- Background music  

\- Subtitles (SRT)  

\- Intro/outro cards  



\### \*\*✔ YouTube Upload\*\*

\- Auto upload  

\- Auto thumbnail  

\- Auto title, tags, and description  



---



\# 📁 Project Structure



novel\_video\_generator/

│

├── src/

│ ├── epub/ # EPUB loading + cleaning

│ ├── parser/ # scene + character extraction

│ ├── tts/ # Maya-1 TTS

│ ├── image/ # image generation

│ ├── video/ # video assembly

│ ├── publishing/ # YouTube uploading

│ ├── core/ # config, utils, logger, pipeline

│ └── api/ # optional FastAPI interface

│

├── data/ # raw + processed novel data

├── assets/ # images, audio, music

├── outputs/ # final videos + logs

├── configs/ # YAML configs for style/voices/etc.

├── scripts/ # CLI scripts for each pipeline step

├── tests/ # unit tests

├── models/ # (optional) local model weights

├── .env # API keys (not committed)

├── requirements.txt

├── requirements.lock

└── README.md



yaml

Copy code



---



\# 🔧 Installation



\### \*\*1. Clone the repo\*\*

```bash

git clone https://github.com/yourusername/novel\_video\_generator.git

cd novel\_video\_generator

2\. Create a virtual environment

bash

Copy code

python -m venv .venv

3\. Activate it

Windows:



powershell

Copy code

.\\.venv\\Scripts\\Activate.ps1

Linux / macOS:



bash

Copy code

source .venv/bin/activate

4\. Install dependencies

bash

Copy code

pip install -r requirements.txt

5\. Add API keys to .env

Create .env:



ini

Copy code

OPENAI\_API\_KEY=...

YOUTUBE\_CLIENT\_SECRET=...

YOUTUBE\_REFRESH\_TOKEN=...

🧪 Quick Start

1\. Put your EPUB into:

bash

Copy code

data/raw\_epubs/

2\. Run EPUB → Clean JSON

bash

Copy code

python src/epub/epub\_cleaner.py data/raw\_epubs/mybook.epub --out data/chapters\_clean

3\. Run Scene Extraction

bash

Copy code

python scripts/run\_scene\_extraction.py --chapter 1

4\. Generate Images

bash

Copy code

python scripts/run\_image\_generation.py --chapter 1

5\. Generate Narration

bash

Copy code

python scripts/run\_tts.py --chapter 1

6\. Build the Video

bash

Copy code

python scripts/run\_video\_build.py --chapter 1

7\. Upload to YouTube

bash

Copy code

python scripts/run\_pipeline.py --upload --chapter 1

⚙️ Config Files

configs/style\_prompts.yaml

Art direction for image generation.



configs/voices.yaml

Voice presets for narrator and characters.



configs/pipeline\_settings.yaml

Batch size, concurrency, retry settings, CPU/GPU flags.



🧱 Technologies Used

Python 3.10+



ebooklib, bs4, lxml for EPUB parsing



ffmpeg / moviepy for video



OpenAI / Stability / Replicate for image generation



Maya-1 TTS local \& cloud inference



YouTube Data API for uploading



🧩 Roadmap

Character-specific voice cloning



Character-consistent image generation (LoRA)



Full novel batch processing



Web UI



GPT-powered script editing



📝 License

MIT / Apache-2.0 (choose one).

