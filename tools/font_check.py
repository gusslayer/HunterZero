"""Measure the HackerNoon font metrics used by theme.load_font for sizes 8 and 16."""
import sys
from pathlib import Path

from PIL import ImageFont

for name in ("HackerNoonV2-Regular.ttf", "HackerNoonV1-Regular.ttf"):
    path = Path(r"C:\Users\david.martinez\AppData\Local\Temp\opencode\hackernoon-font") / name
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
