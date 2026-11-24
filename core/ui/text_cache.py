"""Cache rendered text surfaces so repeated screens reuse pixels, not re-renders."""

import pygame

_CACHE_LIMIT = 256
_cache: dict[tuple[pygame.font.Font, str, tuple[int, int, int]], pygame.Surface] = {}


def render_cached(font: pygame.font.Font, text: str, color: tuple[int, int, int]) -> pygame.Surface:
    """Return a cached render of text in color, re-rendering only when inputs change."""
    key = (font, text, color)
    surface = _cache.get(key)
    if surface is None:
        surface = font.render(text, False, color)
        if len(_cache) >= _CACHE_LIMIT:
            _cache.clear()
        _cache[key] = surface
    return surface
