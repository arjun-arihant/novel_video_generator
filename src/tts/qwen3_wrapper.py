import sys
import os
import json
import argparse
import traceback

# 1. Setup Environment to look like we are inside WanGP
# Adjust this path if checking on a different machine, but based on analysis it is D:/GeneAI/Wan2GP
WANGP_ROOT = "D:/GeneAI/Wan2GP"
if WANGP_ROOT not in sys.path:
    old_sys_path = sys.path[:]
    sys.path.insert(0, WANGP_ROOT)

# Change CWD so WanGP can find its models/config relative to itself
original_cwd = os.getcwd()
os.chdir(WANGP_ROOT)

try:
    import wgp
except ImportError:
    print(f"[ERROR] Could not import 'wgp' from {WANGP_ROOT}. Check paths.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="WanGP Qwen3 Batch Wrapper")
    parser.add_argument("--batch", required=True, help="Path to JSON file containing list of tasks")
    parser.add_argument("--output-dir", help="Directory to save outputs")
    args = parser.parse_args()

    # Set Output Dir in WanGP config if provided
    if args.output_dir:
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir, exist_ok=True)
        # WanGP uses server_config global dict
        wgp.server_config["save_path"] = args.output_dir
        wgp.server_config["image_save_path"] = args.output_dir
        wgp.server_config["audio_save_path"] = args.output_dir
        # Also need to update module-level variables if any?
        # wgp.save_path seems to be used in some places, let's try to set it if it exists
        if hasattr(wgp, "save_path"):
            wgp.save_path = args.output_dir
            wgp.image_save_path = args.output_dir
            wgp.audio_save_path = args.output_dir
            
    # 2. Load the batch of tasks
    batch_path = args.batch
    if not os.path.exists(batch_path):
        print(f"[ERROR] Batch file not found: {batch_path}")
        sys.exit(1)

    try:
        with open(batch_path, 'r', encoding='utf-8') as f:
            tasks_data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load batch JSON: {e}")
        sys.exit(1)

    if not isinstance(tasks_data, list):
        print("[ERROR] Batch JSON must be a list of task objects")
        sys.exit(1)

    print(f"[Wrapper] Loaded {len(tasks_data)} tasks from {batch_path}")

    # 3. Construct Queue and State
    # WanGP expects a specific state structure based on analyzing wgp.py
    state = {
        "gen": {
            "queue": [],
            "in_progress": False,
            "processed": 0,
            # Required fields to avoid key errors in wgp
            "file_list": [],
            "file_settings_list": [],
            "audio_file_list": [],
            "audio_file_settings_list": [],
            "selected": 0,
            "audio_selected": 0,
            "prompt_no": 0,
            "prompts_max": len(tasks_data),
            "repeat_no": 0,
            "total_generation": 1,
            "window_no": 0,
            "total_windows": 0,
            "progress_status": "",
            "process_status": "process:main",
        },
        "loras": [],
    }

    # formatted_queue matches what _parse_settings_json or the UI would produce
    formatted_queue = []
    
    for i, item in enumerate(tasks_data):
        # We expect item to be { "id": ..., "params": {...} }
        # Or just params, in which case we wrap it.
        
        task_id = item.get("id", i + 1)
        
        # Ensure params are present
        if "params" in item:
            params = item["params"]
        else:
            params = item # Treat the whole item as params
            
        task = {
            "id": task_id,
            "prompt": params.get("prompt", ""),
            "params": params,
            "img_path": None, 
            "audio_path": None,
            "video_path": None
        }
        
        formatted_queue.append(task)

    state["gen"]["queue"] = formatted_queue

    # 4. Invoke WanGP Processing
    print("[Wrapper] Starting WanGP process_tasks_cli...")
    try:
        # This function processes the queue and prints progress to stdout
        # It does NOT exit, it returns True/False
        success = wgp.process_tasks_cli(formatted_queue, state)
        
        if success:
            print("[Wrapper] Batch processing completed successfully.")
            sys.exit(0)
        else:
            print("[Wrapper] Batch processing reported failure (some tasks may have failed).")
            # We don't exit with 1 because partial success is still useful?
            # But usually we want 1 if anything failed.
            sys.exit(1)
            
    except Exception as e:
        print(f"[Wrapper] Critical error during processing: {e}")
        # traceback.print_exc()
        sys.exit(1)
    finally:
        pass

if __name__ == "__main__":
    main()
