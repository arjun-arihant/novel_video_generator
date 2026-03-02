import json
from pathlib import Path

# Check the queue
q_path = Path(r"d:\repos\novel_video_generator\data\novels\i_have_a_cultivation_world\queues\image_queue_ch1.json")
q = json.loads(q_path.read_text(encoding="utf-8"))
print(f"Queue: {len(q)} tasks")
for i, task in enumerate(q):
    print(f"  Task {i}: {json.dumps(task, indent=2, default=str)[:300]}")
    print()

# Check all image files in the data directory
print("\n--- Image files found in data/ ---")
data = Path(r"d:\repos\novel_video_generator\data")
for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
    for f in data.rglob(ext):
        print(f"  {f} ({f.stat().st_size} bytes)")

# Check Wan2GP output for recent files
print("\n--- Recent files in Wan2GP/output ---")
wan2gp_out = Path(r"D:\GeneAI\Wan2GP\output")
if wan2gp_out.exists():
    files = sorted(wan2gp_out.rglob("*.*"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[:10]:
        print(f"  {f} ({f.stat().st_size} bytes)")
else:
    # Try to find any output directory
    for d in Path(r"D:\GeneAI\Wan2GP").iterdir():
        if d.is_dir() and ("output" in d.name.lower() or "result" in d.name.lower()):
            print(f"  Found dir: {d}")
