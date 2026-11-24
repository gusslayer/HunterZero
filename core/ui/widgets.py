"""Shared pixel-art widgets used by the HUD, menus, and tool screens."""

import unicodedata

import pygame

from core import theme
from core.ui import icons


def plain_text(text: str) -> str:
    """Strip diacritics that the bundled 8x8 pixel font cannot represent."""
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(character)
    )


def draw_title(surface: pygame.Surface, font: pygame.font.Font, title: str, color=None) -> int:
    """Draw the shared title band and return the first content row's y coordinate."""
    tint = color if color is not None else theme.TEXT_COLOR
    pygame.draw.rect(surface, theme.PANEL_COLOR, (0, 28, theme.WIDTH, 20))
    pygame.draw.line(surface, theme.MUTED_COLOR, (10, 48), (310, 48), 1)
    rendered = font.render(plain_text(title)[:18], False, tint)
    surface.blit(rendered, (12, 32))
    pygame.draw.rect(surface, theme.ACCENT_COLOR, (12 + rendered.get_width() + 6, 35, 4, 10))
    return 52


def draw_frame(surface: pygame.Surface, rect: pygame.Rect, color, fill=None) -> None:
    """Draw a crisp one-pixel frame with small corner ticks around a panel."""
    if fill is not None:
        pygame.draw.rect(surface, fill, rect)
    pygame.draw.rect(surface, color, rect, 1)
    pygame.draw.line(surface, color, (rect.x, rect.y + 4), (rect.x + 4, rect.y), 1)
    pygame.draw.line(
        surface, color, (rect.right - 5, rect.bottom - 1), (rect.right - 1, rect.bottom - 5), 1
    )


def draw_chevron(surface: pygame.Surface, rect: pygame.Rect, color) -> None:
    """Draw a small right-pointing chevron inside the given rectangle."""
    middle = rect.y + rect.height // 2
    pygame.draw.lines(
        surface,
        color,
        False,
        [(rect.x, rect.y), (rect.right - 2, middle), (rect.x, rect.bottom - 1)],
        2,
    )


def draw_keycap(surface: pygame.Surface, font: pygame.font.Font, label: str, x: int, y: int, color) -> int:
    """Draw a boxed action key and return its width so the caption can follow."""
    rendered = font.render(plain_text(label), False, color)
    width = rendered.get_width() + 6
    pygame.draw.rect(surface, color, (x, y, width, 12), 1)
    surface.blit(rendered, (x + 3, y + 2))
    return width


def draw_meter(surface: pygame.Surface, rect: pygame.Rect, percent: int, color) -> None:
    """Draw a segmented bar representing a clamped 0..100 percentage."""
    clamped = max(0, min(100, percent))
    filled_segments = round(4 * clamped / 100)
    for index in range(4):
        segment = pygame.Rect(rect.x + index * 5, rect.y, 4, rect.height)
        pygame.draw.rect(surface, color if index < filled_segments else theme.GRID_COLOR, segment)


def wrap_text(text: str, max_chars: int) -> list[str]:
    """Wrap plain text into lines no longer than max_chars characters."""
    lines: list[str] = []
    current = ""
    for word in plain_text(text).split():
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            if len(word) > max_chars:
                lines.extend(word[start : start + max_chars] for start in range(0, len(word), max_chars))
                current = ""
            else:
                current = word
    if current:
        lines.append(current)
    return lines


def draw_row(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    value: str,
    selected: bool,
    font: pygame.font.Font,
    icon: str | None = None,
) -> None:
    """Render one selectable row with a consistent, readable pixel-art style."""
    if selected:
        pygame.draw.rect(surface, theme.SELECTED_BG, rect)
        pygame.draw.rect(surface, theme.ACCENT_COLOR, rect, 1)
        pygame.draw.rect(surface, theme.ACCENT_COLOR, (rect.x, rect.y, 3, rect.height))
    text_y = rect.y + (rect.height - font.get_height()) // 2
    text_x = rect.x + 7
    if icon:
        icons.draw_icon(
            surface,
            icon,
            pygame.Rect(rect.x + 5, rect.y + (rect.height - 14) // 2, 14, 14),
            theme.ACCENT_COLOR if selected else theme.TEXT_COLOR,
        )
        text_x = rect.x + 24
    caption = plain_text(label).upper()[:34]
    surface.blit(font.render(caption, False, theme.TEXT_COLOR), (text_x, text_y))
    if value:
        rendered_value = font.render(plain_text(value)[:12], False, theme.ACCENT_COLOR)
        right_margin = 20 if selected else 10
        surface.blit(rendered_value, (rect.right - right_margin - rendered_value.get_width(), text_y))
    if selected:
        draw_chevron(surface, pygame.Rect(rect.right - 13, rect.y + 3, 9, rect.height - 6), theme.ACCENT_COLOR)
