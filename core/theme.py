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


def load_font(size: int) -> pygame.font.Font:
    """Load the bundled, freely licensed Press Start 2P font."""
    if size <= 0 or size % 8:
        raise ValueError("El tamaño de fuente debe ser un múltiplo positivo de 8.")
    font_path = ROOT / "assets" / "fonts" / "PressStart2P-Regular.ttf"
    if not font_path.is_file():
        raise FileNotFoundError(f"Falta la fuente requerida: {font_path}")
    return pygame.font.Font(str(font_path), size)
