"""Quick test of image generation fix."""
from src.image.generator import ImageGenerator
from pathlib import Path

print("Testing image generation with fixed Pollinations.ai API...")
g = ImageGenerator()
success = g.generate(
    "A beautiful sunset over mountains",
    Path("test_image.png")
)
print(f"Result: {'SUCCESS ✅' if success else 'FAILED ❌'}")
if success:
    print("Image saved to: test_image.png")
