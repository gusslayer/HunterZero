"""Check the new pixelarticons PNGs rasterize to non-empty shapes and load via the app API."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

CHARS = " .:-=+*#%@"
for name in ("cpu", "battery-charging", "settings", "wifi", "memory-stick"):
    path = Path("assets/icons") / f"{name}.png"
    im = Image.open(path).convert("RGBA")
    print(f"=== {name}.png {im.size} ===")
    for y in range(im.size[1]):
        row = ""
        for x in range(im.size[0]):
            alpha = im.getpixel((x, y))[3]
            row += CHARS[min(9, alpha * 10 // 256)]
        print(" ", row)

import pygame

pygame.init()
from core.ui import icons

missing = []
for name in (
    "activity", "battery-charging", "bell", "chart", "chart-no-axes-combined",
    "code", "code-xml", "cpu", "crosshair", "database", "download", "eye",
    "folder", "gauge", "hard-drive", "lock", "map-pin", "memory-stick",
    "network", "play", "power", "radar", "radio", "rotate-cw", "scan-line",
    "search", "server", "settings", "shield-check", "system", "terminal",
    "upload", "wifi",
):
    icon = icons.load_icon(name)
    if icon is None or icon.get_width() == 0:
        missing.append(name)
print("icons missing after swap:", missing or "(none)")
pygame.quit()
