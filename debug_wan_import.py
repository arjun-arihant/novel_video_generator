import sys
import os

# Add WanGP to path and switch context
WANGP_ROOT = "D:/GeneAI/Wan2GP"
sys.path.insert(0, WANGP_ROOT)
os.chdir(WANGP_ROOT)

try:
    import wgp
    print(f"Base wgp file: {wgp.__file__}")
    
    if hasattr(wgp, 'process_tasks_cli'):
        print(f"process_tasks_cli found in: {wgp.process_tasks_cli.__code__.co_filename}")
        print(f"process_tasks_cli line: {wgp.process_tasks_cli.__code__.co_firstlineno}")
        import inspect
        print("Source of process_tasks_cli:")
        print(inspect.getsource(wgp.process_tasks_cli))
    else:
        print("process_tasks_cli NOT found in wgp module")
        
    if hasattr(wgp, '_parse_settings_json'):
        print(f"_parse_settings_json found.")
    else:
        print("_parse_settings_json NOT found.")

except ImportError as e:
    print(f"Failed to import wgp: {e}")
except Exception as e:
    print(f"Error: {e}")
