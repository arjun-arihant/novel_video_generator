import os
import shutil
import subprocess
import sys
import json
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
SAMPLE_CHAPTER = PROJECT_ROOT / "tests" / "sample_chapter.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "verify_run"

def run_command(cmd, cwd=PROJECT_ROOT):
    """Run a shell command and print output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Error:")
        print(result.stderr)
        return False
    # print(result.stdout)
    return True

def verify_pipeline():
    print("=== Starting Pipeline Verification ===")
    
    # 1. Environment Check
    wangp_path = os.getenv("WANGP_PATH", r"D:\GeneAI\Wan2GP")
    if not Path(wangp_path).exists():
        print(f"[WARN] WanGP not found at {wangp_path}. Image generation might be skipped.")
    else:
        print("[OK] WanGP found.")

    # Clean previous run
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    
    # 2. Run CLI Pipeline
    cli_script = PROJECT_ROOT / "cli.py"
    
    # We use fewer concurrent tasks to be gentle
    cmd = [
        sys.executable, str(cli_script), 
        "pipeline", str(SAMPLE_CHAPTER), 
        "--output", str(OUTPUT_DIR),
        "--max-scenes", "2"
    ]
    
    success = run_command(cmd)
    if not success:
        print("[FAIL] Pipeline execution failed.")
        return

    # 3. Verify Outputs
    print("\n=== Verifying Outputs ===")
    
    scenes_file = OUTPUT_DIR / "scenes.json"
    if scenes_file.exists():
        print(f"[OK] Scenes extracted: {scenes_file}")
        with open(scenes_file, "r", encoding="utf-8") as f:
            scenes = json.load(f)
            print(f"     Count: {len(scenes)}")
    else:
        print("[FAIL] scenes.json missing!")
    
    images_dir = OUTPUT_DIR / "images"
    if images_dir.exists():
        images = list(images_dir.glob("*.png"))
        if images:
            print(f"[OK] Images generated: {len(images)}")
        else:
            print("[WARN] No images generated (WanGP might be missing/failed).")
    else:
        print("[FAIL] images directory missing!")

    audio_dir = OUTPUT_DIR / "audio"
    if audio_dir.exists():
        audio_files = list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.mp3"))
        if audio_files:
            print(f"[OK] Audio generated: {len(audio_files)}")
            # Check size
            for af in audio_files:
                if af.stat().st_size < 1000:
                    print(f"     [WARN] Audio file {af.name} is very small ({af.stat().st_size} bytes)")
        else:
            print("[WARN] No audio generated (TTS failure?).")
    else:
        print("[FAIL] audio directory missing!")

    video_file = OUTPUT_DIR / "chapter_0999.mp4"
    if video_file.exists():
        print(f"[OK] Video generated: {video_file}")
        print(f"     Size: {video_file.stat().st_size / 1024 / 1024:.2f} MB")
    else:
        print("[WARN] Video not generated (likely due to missing images/audio).")

    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    verify_pipeline()
