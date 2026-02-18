"""Flask backend for Novel Video Generator WebUI.

Exposes REST + SSE endpoints for pipeline control, character/scene management.
"""

import asyncio
import hashlib
import json
import logging
import os
import queue
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

from flask import Flask, Response, jsonify, request, send_from_directory

from dotenv import load_dotenv
load_dotenv()

# Add FFMPEG_PATH to system PATH if configured
_ffmpeg_path = os.getenv("FFMPEG_PATH", "")
if _ffmpeg_path and Path(_ffmpeg_path).exists():
    os.environ["PATH"] = _ffmpeg_path + os.pathsep + os.environ.get("PATH", "")
    logging.info("Added FFmpeg to PATH: %s", _ffmpeg_path)

from ..consistency.store import ConsistencyStore
from ..consistency.voice_assigner import assign_voices_with_llm, AVAILABLE_VOICES
from ..parser.openrouter_parser import SceneExtractor
from ..common import ensure_output_dir

logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static",
)

DATA_DIR = Path("data")
UPLOAD_DIR = DATA_DIR / "uploads"
WEB_RUN_DIR = DATA_DIR / "web_runs"

# Global state for SSE progress
_progress_queues: dict[str, queue.Queue] = {}

# Scene cache: chapter_path -> { job_id, scenes_count, chapter_id }
_scene_cache: dict[str, dict] = {}


def _send_progress(job_id: str, step: str, pct: int, detail: str = ""):
    """Push progress event to SSE queue."""
    q = _progress_queues.get(job_id)
    if q:
        q.put({"step": step, "percent": pct, "detail": detail})


def _chapter_key(chapter_path: str) -> str:
    """Stable key for a chapter path to use in caching."""
    return hashlib.md5(Path(chapter_path).resolve().as_posix().encode()).hexdigest()[:12]


def _get_cached_job(chapter_path: str) -> Optional[dict]:
    """Return cached extraction result for a chapter, if scenes.json still exists."""
    key = _chapter_key(chapter_path)
    cached = _scene_cache.get(key)
    if cached:
        scenes_path = WEB_RUN_DIR / cached["job_id"] / "scenes.json"
        if scenes_path.exists():
            return cached
        # Cache stale, remove
        del _scene_cache[key]
    return None


# ── Static & Pages ────────────────────────────────────────────


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ── Chapter Management ────────────────────────────────────────


@app.route("/api/chapters", methods=["GET"])
def list_chapters():
    """List available chapter JSON files."""
    chapters = []
    for pattern in ["data/*/chapters/*.json", "data/chapters/*.json"]:
        for p in Path(".").glob(pattern):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ch_num = data.get("chapter_number", data.get("id", 0))
                title = data.get("title", p.stem)
                para_count = len(data.get("paragraphs", data.get("content", [])))
                # Check if already extracted
                cached = _get_cached_job(str(p))
                chapters.append({
                    "path": str(p),
                    "chapter_number": ch_num,
                    "title": title,
                    "paragraph_count": para_count,
                    "extracted": cached is not None,
                    "job_id": cached["job_id"] if cached else None,
                })
            except Exception:
                continue
    chapters.sort(key=lambda c: c["chapter_number"])
    return jsonify(chapters)


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Upload a chapter JSON file."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    save_path = UPLOAD_DIR / f.filename
    f.save(str(save_path))

    try:
        with open(save_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        ch_num = data.get("chapter_number", data.get("id", 0))
        para_count = len(data.get("paragraphs", data.get("content", [])))
        return jsonify({
            "path": str(save_path),
            "chapter_number": ch_num,
            "title": data.get("title", save_path.stem),
            "paragraph_count": para_count,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ── Scene Extraction ──────────────────────────────────────────


@app.route("/api/extract", methods=["POST"])
def extract_scenes():
    """Extract scenes from a chapter with enrichment + voice assignment."""
    body = request.json or {}
    chapter_path = body.get("chapter_path")
    force = body.get("force", False)

    if not chapter_path or not Path(chapter_path).exists():
        return jsonify({"error": "Invalid chapter_path"}), 400

    # Check cache first
    if not force:
        cached = _get_cached_job(chapter_path)
        if cached:
            return jsonify({
                "job_id": cached["job_id"],
                "status": "cached",
                "scenes_count": cached.get("scenes_count", 0),
                "message": f"Scenes already extracted ({cached.get('scenes_count', '?')} scenes). Use force=true to re-extract.",
            })

    job_id = f"extract_{int(time.time())}"
    _progress_queues[job_id] = queue.Queue()

    def _run():
        try:
            _send_progress(job_id, "loading", 5, "Loading chapter...")
            with open(chapter_path, "r", encoding="utf-8") as f:
                chapter_data = json.load(f)

            if "id" in chapter_data and "chapter_number" not in chapter_data:
                chapter_data["chapter_number"] = chapter_data["id"]
            if "paragraphs" in chapter_data and "content" not in chapter_data:
                chapter_data["content"] = chapter_data["paragraphs"]

            chapter_id = f"ch{chapter_data['chapter_number']:04d}"
            chapter_text = "\n".join(chapter_data["content"])

            _send_progress(job_id, "extracting", 20, "LLM extracting scenes & characters...")

            extractor = SceneExtractor()
            response = extractor.extract_scenes(chapter_text, chapter_id=chapter_id)
            scenes = response.get("scenes", [])

            _send_progress(job_id, "voices", 60, "Assigning voices...")
            store = extractor.store
            assign_voices_with_llm(store)

            _send_progress(job_id, "enriching", 80, "Enriching scene prompts...")
            scenes = extractor.enrich_scene_prompts(scenes, chapter_id=chapter_id)

            # Save results
            run_dir = WEB_RUN_DIR / job_id
            run_dir.mkdir(parents=True, exist_ok=True)
            with open(run_dir / "scenes.json", "w", encoding="utf-8") as f:
                json.dump(scenes, f, indent=2, ensure_ascii=False)

            # Cache this extraction
            key = _chapter_key(chapter_path)
            _scene_cache[key] = {
                "job_id": job_id,
                "scenes_count": len(scenes),
                "chapter_id": chapter_id,
                "chapter_path": chapter_path,
            }

            char_count = len(store.list_characters())
            _send_progress(job_id, "done", 100, f"Extracted {len(scenes)} scenes, {char_count} characters")
            _progress_queues[job_id].put({
                "step": "complete", "percent": 100,
                "scenes_count": len(scenes), "job_id": job_id,
            })
        except Exception as e:
            logger.error("Extraction failed: %s", e, exc_info=True)
            _progress_queues[job_id].put({"step": "error", "percent": -1, "detail": str(e)})

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({"job_id": job_id, "status": "started"})


@app.route("/api/progress/<job_id>")
def stream_progress(job_id: str):
    """SSE endpoint for job progress."""
    q = _progress_queues.get(job_id)
    if not q:
        return jsonify({"error": "Unknown job"}), 404

    def generate():
        while True:
            try:
                msg = q.get(timeout=60)
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get("step") in ("complete", "error"):
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'step': 'heartbeat', 'percent': -1})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


# ── Character & Location Data ─────────────────────────────────


@app.route("/api/characters", methods=["GET"])
def get_characters():
    store = ConsistencyStore()
    return jsonify(store.list_characters())


@app.route("/api/characters/<name>", methods=["PUT"])
def update_character(name: str):
    """Update a character's voice or appearance."""
    store = ConsistencyStore()
    chars = store.list_characters()
    if name not in chars:
        return jsonify({"error": "Character not found"}), 404

    updates = request.json or {}
    char = chars[name]
    for k, v in updates.items():
        if k in char:
            char[k] = v
    store.upsert_characters([char])
    return jsonify(store.get_character(name))


@app.route("/api/locations", methods=["GET"])
def get_locations():
    store = ConsistencyStore()
    return jsonify(store.list_locations())


# ── Scenes ────────────────────────────────────────────────────


@app.route("/api/scenes/<job_id>", methods=["GET"])
def get_scenes(job_id: str):
    """Get scenes for a job."""
    scenes_path = WEB_RUN_DIR / job_id / "scenes.json"
    if not scenes_path.exists():
        return jsonify({"error": "No scenes found"}), 404
    with open(scenes_path, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/api/scenes/<job_id>/<int:scene_idx>", methods=["PUT"])
def update_scene(job_id: str, scene_idx: int):
    """Update a scene's description/narration/dialogues."""
    scenes_path = WEB_RUN_DIR / job_id / "scenes.json"
    if not scenes_path.exists():
        return jsonify({"error": "No scenes found"}), 404

    with open(scenes_path, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    if scene_idx < 0 or scene_idx >= len(scenes):
        return jsonify({"error": "Invalid scene index"}), 400

    updates = request.json or {}
    for k, v in updates.items():
        scenes[scene_idx][k] = v

    with open(scenes_path, "w", encoding="utf-8") as f:
        json.dump(scenes, f, indent=2, ensure_ascii=False)

    return jsonify(scenes[scene_idx])


# ── Service Health ────────────────────────────────────────────


@app.route("/api/health", methods=["GET"])
def check_services():
    """Check availability of external services (WanGP, Kokoro, FFmpeg)."""
    import os
    import subprocess

    status = {}

    # WanGP
    wangp_path = os.getenv("WANGP_PATH", r"D:\GeneAI\Wan2GP")
    wgp_script = Path(wangp_path) / "wgp.py"
    status["wangp"] = {
        "available": wgp_script.exists(),
        "path": wangp_path,
        "detail": "Found" if wgp_script.exists() else f"wgp.py not found at {wangp_path}",
    }

    # Kokoro TTS
    import requests as req
    kokoro_url = os.getenv("KOKORO_BASE_URL", "http://localhost:8000")
    try:
        r = req.get(f"{kokoro_url}/health", timeout=3)
        data = r.json() if r.status_code == 200 else {}
        status["kokoro"] = {
            "available": r.status_code == 200,
            "url": kokoro_url,
            "detail": f"Online — {data.get('model', '?')} v{data.get('version', '?')}" if r.status_code == 200 else f"Error ({r.status_code})",
        }
    except Exception as e:
        status["kokoro"] = {"available": False, "url": kokoro_url, "detail": str(e)}

    # FFmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        version_line = result.stdout.split("\n")[0] if result.returncode == 0 else "?"
        status["ffmpeg"] = {"available": result.returncode == 0, "detail": version_line}
    except Exception:
        status["ffmpeg"] = {"available": False, "detail": "FFmpeg not found in PATH"}

    return jsonify(status)


# ── Pipeline ──────────────────────────────────────────────────


@app.route("/api/pipeline", methods=["POST"])
def run_pipeline():
    """Run full pipeline (extract → images → audio → video).

    Reuses cached scenes if already extracted for this chapter.
    """
    body = request.json or {}
    chapter_path = body.get("chapter_path")
    force_extract = body.get("force_extract", False)
    if not chapter_path or not Path(chapter_path).exists():
        return jsonify({"error": "Invalid chapter_path"}), 400

    job_id = f"pipeline_{int(time.time())}"
    _progress_queues[job_id] = queue.Queue()

    def _run():
        try:
            import os

            # Step 1: Extract (or reuse cache)
            cached = None if force_extract else _get_cached_job(chapter_path)
            if cached:
                _send_progress(job_id, "extracting", 25,
                    f"Reusing cached scenes ({cached['scenes_count']} scenes from {cached['job_id']})")

                scenes_path = WEB_RUN_DIR / cached["job_id"] / "scenes.json"
                with open(scenes_path, "r", encoding="utf-8") as f:
                    scenes = json.load(f)

                chapter_id = cached.get("chapter_id", "ch0001")
                store = ConsistencyStore()
            else:
                _send_progress(job_id, "extracting", 5, "Loading & extracting scenes...")
                with open(chapter_path, "r", encoding="utf-8") as f:
                    chapter_data = json.load(f)

                if "id" in chapter_data and "chapter_number" not in chapter_data:
                    chapter_data["chapter_number"] = chapter_data["id"]
                if "paragraphs" in chapter_data and "content" not in chapter_data:
                    chapter_data["content"] = chapter_data["paragraphs"]

                chapter_id = f"ch{chapter_data['chapter_number']:04d}"
                chapter_text = "\n".join(chapter_data["content"])

                extractor = SceneExtractor()
                response = extractor.extract_scenes(chapter_text, chapter_id=chapter_id)
                scenes = response.get("scenes", [])

                _send_progress(job_id, "voices", 20, f"Extracted {len(scenes)} scenes, assigning voices...")
                store = extractor.store
                assign_voices_with_llm(store)

                _send_progress(job_id, "enriching", 30, "Enriching prompts...")
                scenes = extractor.enrich_scene_prompts(scenes, chapter_id=chapter_id)

                # Cache extracted scenes under a stable directory name
                extract_dir = WEB_RUN_DIR / f"extract_{_chapter_key(chapter_path)}"
                extract_dir.mkdir(parents=True, exist_ok=True)
                with open(extract_dir / "scenes.json", "w", encoding="utf-8") as f:
                    json.dump(scenes, f, indent=2, ensure_ascii=False)

                cache_key = _chapter_key(chapter_path)
                _scene_cache[cache_key] = {
                    "job_id": extract_dir.name,
                    "scenes_count": len(scenes),
                    "chapter_id": chapter_id,
                    "chapter_path": chapter_path,
                }

            # Use a stable output dir based on chapter
            run_dir = WEB_RUN_DIR / chapter_id
            run_dir.mkdir(parents=True, exist_ok=True)

            # Save scenes in chapter output dir too
            scenes_out = run_dir / "scenes.json"
            with open(scenes_out, "w", encoding="utf-8") as f:
                json.dump(scenes, f, indent=2, ensure_ascii=False)

            # Step 2: Images
            images_dir = run_dir / "images"
            images_dir.mkdir(exist_ok=True)
            wangp_path = os.getenv("WANGP_PATH", r"D:\GeneAI\Wan2GP")
            wgp_exists = (Path(wangp_path) / "wgp.py").exists()

            if not wgp_exists:
                _send_progress(job_id, "images_skip", 60,
                    f"Image generation skipped: WanGP not found at {wangp_path}. Set WANGP_PATH in .env")
            else:
                try:
                    from ..image.generator import ImageGenerator
                    generator = ImageGenerator()
                    for i, scene in enumerate(scenes):
                        pct = 35 + int((i / max(len(scenes), 1)) * 25)
                        _send_progress(job_id, "images", pct, f"Generating image {i+1}/{len(scenes)}...")
                        out_file = images_dir / f"scene_{i:03d}.png"
                        generator.generate_for_scene(scene, out_file, store=store)
                        logger.info("Image saved: %s (%s bytes)", out_file, out_file.stat().st_size if out_file.exists() else "missing")
                except Exception as e:
                    _send_progress(job_id, "images_skip", 60, f"Image generation error: {e}")
                    logger.error("Image generation failed:\n%s", traceback.format_exc())

            # Step 3: Audio
            audio_dir = run_dir / "audio"
            audio_dir.mkdir(exist_ok=True)
            kokoro_url = os.getenv("KOKORO_BASE_URL", "http://localhost:8000")
            kokoro_ok = False
            try:
                import requests as req
                r = req.get(f"{kokoro_url}/health", timeout=3)
                kokoro_ok = r.status_code == 200
            except Exception:
                pass

            if not kokoro_ok:
                _send_progress(job_id, "audio_skip", 85,
                    f"Audio generation skipped: Kokoro TTS not running at {kokoro_url}")
            else:
                try:
                    from ..tts.manager import TTSManager
                    tts = TTSManager()
                    _send_progress(job_id, "audio", 65, "Generating audio...")

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(
                        tts.generate_batch_audio(scenes, audio_dir, max_concurrent=2)
                    )
                    loop.close()

                    ok_count = sum(1 for r in results if r)
                    _send_progress(job_id, "audio_done", 85, f"Audio: {ok_count}/{len(scenes)} generated")
                except Exception as e:
                    _send_progress(job_id, "audio_skip", 85, f"Audio generation error: {e}")
                    logger.error("Audio generation failed:\n%s", traceback.format_exc())

            # Step 4: Video
            has_images = any(images_dir.glob("*.png")) or any(images_dir.glob("*.jpg"))
            has_audio = any(audio_dir.glob("*.wav")) or any(audio_dir.glob("*.mp3"))

            if not has_images or not has_audio:
                missing = []
                if not has_images: missing.append("images")
                if not has_audio: missing.append("audio")
                _send_progress(job_id, "video_skip", 95,
                    f"Video composition skipped: missing {' and '.join(missing)}")
            else:
                try:
                    from ..video.composer import VideoComposer
                    _send_progress(job_id, "video", 90, "Composing video...")
                    composer = VideoComposer()
                    video_path = run_dir / f"{chapter_id}.mp4"
                    composer.create_video(scenes, str(images_dir), str(audio_dir), str(video_path))
                    _send_progress(job_id, "done", 100, f"Video saved: {video_path}")
                except Exception as e:
                    _send_progress(job_id, "video_skip", 95, f"Video composition error: {e}")
                    logger.error("Video composition failed:\n%s", traceback.format_exc())

            # Summary of what was produced
            img_count = len(list(images_dir.glob("*.*")))
            aud_count = len(list(audio_dir.glob("*.*")))
            video_exists = any(run_dir.glob("*.mp4"))
            summary = f"Scenes: {len(scenes)}, Images: {img_count}, Audio: {aud_count}, Video: {'yes' if video_exists else 'no'}"
            summary += f" | Output: {run_dir.resolve()}"

            _progress_queues[job_id].put({
                "step": "complete", "percent": 100,
                "job_id": job_id, "scenes_count": len(scenes),
                "detail": summary,
                "output_dir": str(run_dir.resolve()),
            })
        except Exception as e:
            logger.error("Pipeline failed: %s", e, exc_info=True)
            _progress_queues[job_id].put({"step": "error", "percent": -1, "detail": str(e)})

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return jsonify({"job_id": job_id, "status": "started"})


# ── Output Files ──────────────────────────────────────────────


@app.route("/api/outputs/<chapter_id>", methods=["GET"])
def list_outputs(chapter_id: str):
    """List output files for a chapter."""
    run_dir = WEB_RUN_DIR / chapter_id
    if not run_dir.exists():
        return jsonify({"error": "No output directory found"}), 404

    outputs = {
        "chapter_id": chapter_id,
        "directory": str(run_dir.resolve()),
        "scenes": None,
        "images": [],
        "audio": [],
        "video": [],
    }

    scenes_path = run_dir / "scenes.json"
    if scenes_path.exists():
        outputs["scenes"] = str(scenes_path.resolve())

    for ext in ["png", "jpg", "jpeg"]:
        for f in sorted((run_dir / "images").glob(f"*.{ext}")):
            outputs["images"].append({"name": f.name, "path": str(f.resolve()), "size": f.stat().st_size})

    for ext in ["wav", "mp3"]:
        for f in sorted((run_dir / "audio").glob(f"*.{ext}")):
            outputs["audio"].append({"name": f.name, "path": str(f.resolve()), "size": f.stat().st_size})

    for f in sorted(run_dir.glob("*.mp4")):
        outputs["video"].append({"name": f.name, "path": str(f.resolve()), "size": f.stat().st_size})

    return jsonify(outputs)


# ── Voice Catalog ─────────────────────────────────────────────


@app.route("/api/voices", methods=["GET"])
def get_voices():
    return jsonify(AVAILABLE_VOICES)


# ── Run Server ────────────────────────────────────────────────


def run_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    logging.basicConfig(level=logging.INFO)
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    run_server(debug=True)
