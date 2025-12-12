"""Test simplified image generation."""
from src.image.generator import ImageGenerator
from pathlib import Path

print("Testing SIMPLIFIED image generation...")
g = ImageGenerator()
success = g.generate("test sunset", Path("test_simple.png"))
print(f"Result: {'SUCCESS ✅' if success else 'FAILED ❌'}")
