import subprocess
import os

env = os.environ.copy()
env['PYTHONPATH'] = r'D:\GeneAI\Wan2GP'

proc = subprocess.run([
    r'C:\Users\Psyka\miniconda3\envs\wan2gp\python.exe',
    'wgp.py',
    '--process', r"d:\repos\novel_video_generator\data\novels\i_have_a_cultivation_world\queues\image_queue_ch1.zip",
    '--verbose', '1'
], cwd=r'D:\GeneAI\Wan2GP', capture_output=True, text=True, env=env)

with open(r'd:\repos\novel_video_generator\wan2gp_test.log', 'w', encoding='utf-8') as f:
    f.write(f"RC: {proc.returncode}\n")
    f.write(f"STDOUT:\n{proc.stdout}\n")
    f.write(f"STDERR:\n{proc.stderr}\n")
