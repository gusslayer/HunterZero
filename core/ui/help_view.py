"""Reusable gamepad help view shared by independently implemented modules."""

import pygame

from core import theme
from core.ui.text_cache import render_cached
from core.ui.widgets import plain_text


HELP_TOP = 36
HELP_BOTTOM = 178


def build_help_lines(
    sections: tuple[tuple[str, tuple[str, ...]], ...],
    body_font: pygame.font.Font,
    small_font: pygame.font.Font,
    max_width: int = 285,
) -> list[tuple[str, pygame.font.Font, bool]]:
    """Flatten wrapped help sections into drawable (text, font, heading) lines."""
    lines: list[tuple[str, pygame.font.Font, bool]] = []
    for heading, paragraphs in sections:
        lines.append((plain_text(heading)[:30], body_font, True))
        for paragraph in paragraphs:
            lines.extend(
                (line, small_font, False) for line in _wrap_text(paragraph, small_font, max_width)
            )
        lines.append(("", small_font, False))
    return lines


def help_capacity(small_font: pygame.font.Font) -> int:
    """Return how many help lines fit between the top margin and the footer."""
    return max(1, (HELP_BOTTOM - HELP_TOP) // (small_font.get_linesize() + 3))


def draw_help_view(
    surface: pygame.Surface,
    title_font: pygame.font.Font,
    body_font: pygame.font.Font,
    small_font: pygame.font.Font,
    title: str,
    sections: tuple[tuple[str, tuple[str, ...]], ...],
    scroll: int = 0,
) -> tuple[int, int]:
    """Render titled help sections, returning the line count and visible capacity."""
    del title_font, title
    pygame.draw.rect(surface, theme.BG_COLOR, (0, 28, theme.WIDTH, 184))
    lines = build_help_lines(sections, body_font, small_font)
    capacity = help_capacity(small_font)
    first = max(0, min(scroll, max(0, len(lines) - capacity)))
    y = HELP_TOP
    for text, font, is_heading in lines[first : first + capacity]:
        if text:
            color = theme.ACCENT_COLOR if is_heading else theme.TEXT_COLOR
            surface.blit(render_cached(font, text, color), (16, y))
        y += font.get_linesize() + 3
    surface.blit(
        render_cached(small_font, "A: VOLVER   B: SALIR", theme.ACCENT_COLOR), (16, 194)
    )
    return len(lines), capacity


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Wrap one help paragraph into lines that fit the GPi content area."""
    lines: list[str] = []
    current = ""
    for word in plain_text(text).split():
        candidate = f"{current} {word}".strip()
        if current and font.size(candidate)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]
