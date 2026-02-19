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
from ..consistency.voice_assigner import assign_voices_with_llm
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

# Serve generated files
@app.route("/runs/<path:filename>")
def serve_runs(filename):
    return send_from_directory(WEB_RUN_DIR, filename)

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



from ..core.library_manager import LibraryManager

# ── Library Management ────────────────────────────────────────


@app.route("/api/library", methods=["GET"])
def list_library():
    """List all novels in the library."""
    manager = LibraryManager()
    return jsonify(manager.get_library())


@app.route("/api/library/upload", methods=["POST"])
def upload_novel():
    """Upload and ingest an EPUB file."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    # Save to temp
    temp_dir = UPLOAD_DIR / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    save_path = temp_dir / f.filename
    f.save(str(save_path))

    try:
        manager = LibraryManager()
        metadata = manager.create_novel_from_epub(str(save_path))
        # Cleanup temp
        if os.path.exists(save_path):
            os.remove(save_path)
        return jsonify(metadata)
    except Exception as e:
        logger.error("Upload failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/library/<novel_id>", methods=["GET"])
def get_novel_details(novel_id):
    """Get metadata for a specific novel."""
    manager = LibraryManager()
    novel = manager.get_novel(novel_id)
    if not novel:
        return jsonify({"error": "Novel not found"}), 404
    return jsonify(novel)


@app.route("/api/library/<novel_id>/chapters", methods=["GET"])
def list_novel_chapters(novel_id):
    """List chapters for a novel."""
    manager = LibraryManager()
    chapters = manager.get_chapters(novel_id)
    return jsonify(chapters)


@app.route("/api/library/<novel_id>/chapters/<chapter_id>", methods=["GET"])
def get_novel_chapter(novel_id, chapter_id):
    """Get content of a specific chapter."""
    manager = LibraryManager()
    content = manager.get_chapter_content(novel_id, chapter_id)
    if not content:
        return jsonify({"error": "Chapter not found"}), 404
    return jsonify(content)


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
    raw_text = body.get("text")
    force = body.get("force", False)

    # Handle raw text input by saving it as a temporary chapter file
    if raw_text:
        timestamp = int(time.time())
        filename = f"raw_input_{timestamp}.json"
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        chapter_path = str(UPLOAD_DIR / filename)
        
        chapter_data = {
            "id": timestamp,
            "chapter_number": 1,
            "title": "Raw Input",
            "content": [raw_text], # Treat whole text as one block for now, or split by newlines
            "paragraphs": [p for p in raw_text.split('\n') if p.strip()]
        }
        
        with open(chapter_path, "w", encoding="utf-8") as f:
            json.dump(chapter_data, f, indent=2)

    if not chapter_path or not Path(chapter_path).exists():
        return jsonify({"error": "Invalid chapter_path or missing text"}), 400

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

    # Kokoro TTS (Removed)
    # status["kokoro"] = {"available": True, "detail": "Using Qwen3 Engine (internal)"}


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

            # Step 3: Audio (Qwen3)
            audio_dir = run_dir / "audio"
            audio_dir.mkdir(exist_ok=True)
            
            try:
                from ..tts.manager import TTSManager
                tts = TTSManager()
                _send_progress(job_id, "audio", 65, "Generating audio (Qwen3)...")

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # Use Qwen3 3-pass strategy
                results = loop.run_until_complete(
                    tts.generate_chapter_audio(scenes, audio_dir, default_voice="narrator")
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
    # Only expose Qwen3 as capable engine? 
    # Or just return empty list as we don't have presets anymore
    return jsonify({})

# ── Generation Endpoints ──────────────────────────────────────
@app.route("/api/generate/audio", methods=["POST"])
def regenerate_audio():
    """Regenerate audio for specific scenes."""
    body = request.json or {}
    job_id = body.get("job_id")
    indices = body.get("scene_indices", []) # List of integers

    if not job_id:
        return jsonify({"error": "Missing job_id"}), 400

    scenes_path = WEB_RUN_DIR / job_id / "scenes.json"
    if not scenes_path.exists():
        return jsonify({"error": "Job not found"}), 404

    with open(scenes_path, "r", encoding="utf-8") as f:
        all_scenes = json.load(f)

    # Filter scenes
    if not indices:
        target_scenes = all_scenes # Regen all
        target_indices = range(len(all_scenes))
    else:
        target_scenes = []
        target_indices = []
        for idx in indices:
            if 0 <= idx < len(all_scenes):
                target_scenes.append(all_scenes[idx])
                target_indices.append(idx)
    
    if not target_scenes:
        return jsonify({"error": "No valid scenes selected"}), 400

    regen_job_id = f"regen_audio_{int(time.time())}"
    _progress_queues[regen_job_id] = queue.Queue()

    def _run():
        try:
            _send_progress(regen_job_id, "start", 0, f"Regenerating audio for {len(target_scenes)} scenes...")
            
            run_dir = WEB_RUN_DIR / job_id
            audio_dir = run_dir / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)

            from ..tts.manager import TTSManager
            tts = TTSManager()
            
            # Since we need to update specific files (scene_XXX.wav),
            # generate_chapter_audio returns a list matching input scenes.
            # We map the results back to the original indices?
            # Actually, generate_chapter_audio saves files to output_dir names as scene_000.wav based on index in `scenes` list.
            # NO, it uses `s_idx` from built-in enumeration.
            # If we pass a subset [scene 5, scene 8], it will save as scene_000.wav, scene_001.wav?
            # YES. This is a problem.
            # We need to preserve the original filenames (scene_005.wav).
            # I need to modify `generate_chapter_audio` to accept explicit output filenames or indices?
            # OR, I temporarily patch the `s_idx` logic in `generate_chapter_audio`.
            # OR, I just rename the files after generation?
            # Renaming is easier.
            
            # Create a temp dir for this partial generation
            with tempfile.TemporaryDirectory() as tmp_gen_dir:
                tmp_path = Path(tmp_gen_dir)
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # This will generate scene_000.wav ... scene_N.wav in tmp_path
                results = loop.run_until_complete(
                    tts.generate_chapter_audio(target_scenes, tmp_path)
                )
                loop.close()
                
                # Move files to real audio_dir with correct names
                success_count = 0
                for i, result_path in enumerate(results):
                    real_idx = target_indices[i]
                    if result_path and os.path.exists(result_path):
                        src = Path(result_path)
                        dst = audio_dir / f"scene_{real_idx:03d}.wav"
                        import shutil
                        shutil.copy2(src, dst)
                        success_count += 1
                        
            _send_progress(regen_job_id, "complete", 100, f"Regenerated {success_count}/{len(target_scenes)} audio clips")
             
        except Exception as e:
            logger.error("Audio regen failed: %s", e, exc_info=True)
            _progress_queues[regen_job_id].put({"step": "error", "percent": -1, "detail": str(e)})

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({"job_id": regen_job_id, "status": "started"})


@app.route("/api/generate/image", methods=["POST"])
def regenerate_image():
    """Regenerate images for specific scenes."""
    body = request.json or {}
    job_id = body.get("job_id")
    indices = body.get("scene_indices", [])

    if not job_id:
        return jsonify({"error": "Missing job_id"}), 400

    scenes_path = WEB_RUN_DIR / job_id / "scenes.json"
    if not scenes_path.exists():
        return jsonify({"error": "Job not found"}), 404

    with open(scenes_path, "r", encoding="utf-8") as f:
        all_scenes = json.load(f)

    # Filter scenes
    target_tasks = [] # (index, scene)
    for idx in indices:
        if 0 <= idx < len(all_scenes):
            target_tasks.append((idx, all_scenes[idx]))
    
    if not target_tasks:
        return jsonify({"error": "No valid scenes selected"}), 400

    regen_job_id = f"regen_image_{int(time.time())}"
    _progress_queues[regen_job_id] = queue.Queue()

    def _run():
        try:
            _send_progress(regen_job_id, "start", 0, f"Regenerating images for {len(target_tasks)} scenes...")
            
            run_dir = WEB_RUN_DIR / job_id
            images_dir = run_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            
            from ..consistency.store import ConsistencyStore
            store = ConsistencyStore()
            
            # Check for Image Generator
            wangp_path = os.getenv("WANGP_PATH", r"D:\GeneAI\Wan2GP")
            wgp_exists = (Path(wangp_path) / "wgp.py").exists()
            if not wgp_exists:
                 # Try import anyway?
                 pass

            from ..image.generator import ImageGenerator
            generator = ImageGenerator()

            for i, (real_idx, scene) in enumerate(target_tasks):
                out_file = images_dir / f"scene_{real_idx:03d}.png"
                _send_progress(regen_job_id, "generating", int((i / len(target_tasks)) * 100), f"Scene {real_idx}...")
                generator.generate_for_scene(scene, out_file, store=store)
            
            _send_progress(regen_job_id, "complete", 100, f"Regenerated {len(target_tasks)} images")

        except Exception as e:
            logger.error("Image regen failed: %s", e, exc_info=True)
            _progress_queues[regen_job_id].put({"step": "error", "percent": -1, "detail": str(e)})

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({"job_id": regen_job_id, "status": "started"})


# ── Run Server ────────────────────────────────────────────────


def run_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    logging.basicConfig(level=logging.INFO)
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    run_server(debug=True)
