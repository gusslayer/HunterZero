from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parents[2]
ICON_ROOT = ROOT / "assets" / "icons"
_icon_cache: dict[str, pygame.Surface] = {}
_scaled_icon_cache: dict[tuple[str, int, int, tuple[int, int, int]], pygame.Surface] = {}


def load_icon(name: str) -> pygame.Surface | None:
    """Load an optional menu icon PNG and cache it for the event loop."""
    if name in _icon_cache:
        return _icon_cache[name]
    path = ICON_ROOT / f"{name}.png"
    if not path.is_file():
        return None
    try:
        loaded = pygame.image.load(str(path))
        icon = loaded.convert_alpha() if pygame.display.get_surface() else loaded.copy()
    except (pygame.error, OSError):
        return None
    for y in range(icon.get_height()):
        for x in range(icon.get_width()):
            pixel = icon.get_at((x, y))
            icon.set_at((x, y), (*pixel[:3], 255 if pixel.a >= 128 else 0))
    _icon_cache[name] = icon
    return icon


def draw_icon(surface: pygame.Surface, name: str, rect: pygame.Rect, color: tuple[int, int, int]) -> None:
    """Draw a cached icon, clipped so it never overflows the surface."""
    icon = load_icon(name)
    if icon is None:
        pygame.draw.rect(surface, color, rect, 1)
        return
    visible = surface.get_rect().clip(rect)
    if not visible.w or not visible.h:
        return
    key = (name, visible.w, visible.h, color)
    tinted = _scaled_icon_cache.get(key)
    if tinted is None:
        # transform.scale es el escalado sin suavizado: un píxel por píxel.
        tinted = pygame.transform.scale(icon, (visible.w, visible.h))
        tinted.fill(color, special_flags=pygame.BLEND_RGB_MULT)
        _scaled_icon_cache[key] = tinted
    surface.blit(tinted, visible)
