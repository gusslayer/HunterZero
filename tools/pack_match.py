"""List pixelarticons SVG names that could substitute the app's missing icon names."""
import sys
from pathlib import Path

SRC = Path(r"C:\Users\david.martinez\AppData\Local\Temp\opencode\pixelarticons\svg")
MISSING = [
    "activity", "battery-charging", "chart-no-axes-combined", "code-xml",
    "crosshair", "gauge", "hard-drive", "network", "radar", "rotate-cw",
    "scan-line", "settings", "shield-check", "system",
]
KEYWORDS = [
    "activ", "battery", "chart", "code", "crosshair", "gauge", "hard", "disk",
    "network", "radar", "rotate", "scan", "settings", "shield", "system",
    "stats", "analytics",
]

names = sorted(p.stem for p in SRC.glob("*.svg"))
print(f"total pack icons: {len(names)}")
print("names containing missing keywords:")
for name in names:
    if any(keyword in name for keyword in KEYWORDS):
        print(" ", name)
print("missing app icons:", MISSING)
