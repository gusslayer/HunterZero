from pathlib import Path


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


def load_font(size: int):
    """Load the stored 8x8 bitmap font, scaled to the requested grid multiple."""
    from core.ui.pixel_font import PixelFont

    if size <= 0 or size % 8:
        raise ValueError("El tamaño de fuente debe ser un múltiplo positivo de 8.")
    return PixelFont(scale=size // 8)
