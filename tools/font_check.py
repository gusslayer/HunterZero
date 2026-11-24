"""Measure the bundled pixel font metrics used by theme.load_font for sizes 8 and 16."""
from pathlib import Path

from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[1]
for name in ("PressStart2P-Regular.ttf",):
    path = ROOT / "assets" / "fonts" / name
    for size in (8, 16):
        try:
            font = ImageFont.truetype(str(path), size)
            text = "CPU:95"
            print(
                f"{name} size={size} height={font.getbbox('Agy')[3] - font.getbbox('Agy')[1]} "
                f"ascent={font.getmetrics()[0]} descent={font.getmetrics()[1]} "
                f"{text!r} width={font.getlength(text)}"
            )
        except (OSError, ValueError) as error:
            print(f"{name} size={size} error: {error}")
