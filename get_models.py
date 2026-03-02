import sys
import os
sys.path.insert(0, r"D:\GeneAI\Wan2GP")

try:
    from shared.models import list_models
    models = list_models()
    print("Registered models:")
    for m in models:
        print(" -", m)
except Exception as e:
    print("Error:", e)
