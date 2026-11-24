"""Rasterize the downloaded pixelarticons SVGs into the app's assets/icons directory."""
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(r"C:\Users\david.martinez\AppData\Local\Temp\opencode\pixelarticons\svg")
DEST = ROOT / "assets" / "icons"

APP_ICONS = [
    "activity", "battery-charging", "bell", "chart", "chart-no-axes-combined",
    "code", "code-xml", "cpu", "crosshair", "database", "download", "eye",
    "folder", "gauge", "hard-drive", "lock", "map-pin", "memory-stick",
    "network", "play", "power", "radar", "radio", "rotate-cw", "scan-line",
    "search", "server", "settings", "shield-check", "system", "terminal",
    "upload", "wifi",
]

FILL = (255, 255, 255, 255)

#Iconos que usan un pack sin nombre igual: sustituye el que existe en pixelarticons.
SUBSTITUTIONS = {
    "battery-charging": "battery",
    "settings": "settings-2",
    "shield-check": "shield",
    "code-xml": "code",
}


def parse_path(d):
    """Return a list of closed polygons from an SVG path string."""
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.?\d+)", d)
    pos = (0.0, 0.0)
    start = (0.0, 0.0)
    sub = []
    polygons = []
    i = 0

    def flush():
        if len(sub) >= 3:
            polygons.append(sub.copy())
        sub.clear()

    while i < len(tokens):
        token = tokens[i]
        if not re.fullmatch(r"[A-Za-z]", token):
            i += 1
            continue
        cmd = token
        i += 1
        if cmd in "Mm":
            x, y = float(tokens[i]), float(tokens[i + 1])
            i += 2
            if cmd == "m":
                x += pos[0]
                y += pos[1]
            flush()
            pos = (x, y)
            start = pos
            sub.append(pos)
        elif cmd in "Ll":
            x, y = float(tokens[i]), float(tokens[i + 1])
            i += 2
            if cmd == "l":
                x += pos[0]
                y += pos[1]
            pos = (x, y)
            sub.append(pos)
        elif cmd in "Hh":
            x = float(tokens[i])
            i += 1
            if cmd == "h":
                x += pos[0]
            pos = (x, pos[1])
            sub.append(pos)
        elif cmd in "Vv":
            y = float(tokens[i])
            i += 1
            if cmd == "v":
                y += pos[1]
            pos = (pos[0], y)
            sub.append(pos)
        elif cmd in "Zz":
            flush()
            pos = start
        else:
            i += 1
    flush()
    return polygons


def rasterize_icon(svg_text, size=24):
    """Draw the SVG paths into a white-on-transparent square PNG."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    match = re.search(r'd="([^"]*)"', svg_text)
    if match is None:
        return img
    for polygon in parse_path(match.group(1)):
        points = [(int(round(x)), int(round(y))) for x, y in polygon]
        draw.polygon(points, fill=FILL)
    return img


def main() -> None:
    """Rasterize every app icon that exists in the pixelarticons pack."""
    available = {p.stem for p in SRC.glob("*.svg")}
    missing = [
        name
        for name in APP_ICONS
        if SUBSTITUTIONS.get(name, name) not in available
    ]
    written = []
    for name in APP_ICONS:
        source_name = SUBSTITUTIONS.get(name, name)
        if source_name not in available:
            continue
        svg = (SRC / f"{source_name}.svg").read_text(encoding="utf-8")
        png = rasterize_icon(svg)
        png.save(DEST / f"{name}.png", format="PNG")
        written.append(f"{name}<-{source_name}")
    print("rasterized:", ", ".join(written))
    print("app icons without pixelarticons asset:", ", ".join(missing) or "(none)")


if __name__ == "__main__":
    sys.exit(main())
