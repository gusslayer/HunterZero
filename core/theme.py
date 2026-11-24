from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parents[1]
WIDTH = 320
HEIGHT = 240
WINDOW_WIDTH = 640
WINDOW_HEIGHT = 480
FPS = 15

BG_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (255, 85, 0)
MUTED_COLOR = (102, 102, 102)
PANEL_COLOR = (12, 12, 12)
SELECTED_BG = (58, 20, 0)
GRID_COLOR = (38, 38, 38)

FONT_PATH = ROOT / "assets" / "fonts" / "PressStart2P-Regular.ttf"


def load_font(size: int) -> pygame.font.Font:
    """Load the bundled pixel font, keeping every glyph sharp on the 2x grid."""
    if size <= 0 or size % 8:
        raise ValueError("El tamaño de fuente debe ser un múltiplo positivo de 8.")
    if not FONT_PATH.is_file():
        raise FileNotFoundError(f"Falta la fuente requerida: {FONT_PATH}")
    return pygame.font.Font(str(FONT_PATH), size)
