from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parents[1]
WIDTH = 640
HEIGHT = 480
FPS = 30

BLACK = (8, 8, 8)
ORANGE = (255, 140, 0)
AMBER = (255, 166, 35)
DIM_ORANGE = (150, 78, 0)
WHITE = (244, 230, 211)
PANEL = (18, 15, 11)


def load_font(size: int) -> pygame.font.Font:
    """Load the bundled, freely licensed Press Start 2P font."""
    font_path = ROOT / "assets" / "fonts" / "PressStart2P-Regular.ttf"
    if not font_path.is_file():
        raise FileNotFoundError(f"Falta la fuente requerida: {font_path}")
    return pygame.font.Font(str(font_path), size)
