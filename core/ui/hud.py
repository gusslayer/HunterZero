import pygame

from core import theme
from core.system_stats import SystemStats


def _text(surface: pygame.Surface, font: pygame.font.Font, value: str, x: int, y: int) -> None:
    """Render one orange HUD label at the specified pixel position."""
    surface.blit(font.render(value, True, theme.ORANGE), (x, y))


def draw_hud(surface: pygame.Surface, font: pygame.font.Font, stats: SystemStats) -> None:
    """Draw system metrics, hardware symbols, Wi-Fi, battery, and clock."""
    pygame.draw.rect(surface, theme.BLACK, (0, 0, theme.WIDTH, 52))
    pygame.draw.line(surface, theme.ORANGE, (20, 51), (620, 51), 2)
    _draw_chip(surface, 12, 18, 16)
    _draw_memory(surface, 148, 19)
    _draw_thermometer(surface, 282, 16)
    _text(surface, font, f"CPU:{stats.cpu_percent:02d}", 34, 20)
    _text(surface, font, f"RAM:{stats.memory_percent:02d}", 170, 20)
    temperature = f"{stats.temperature_c}C" if stats.temperature_c is not None else "--C"
    _text(surface, font, f"TEMP:{temperature}", 300, 20)
    draw_wifi(surface, 442, 28, stats.wifi_connected)
    _draw_battery(surface, 462, 19, stats.battery_percent is not None)
    battery = f"{stats.battery_percent}%" if stats.battery_percent is not None else "--%"
    _text(surface, font, battery, 490, 20)
    _text(surface, font, stats.clock, 552, 20)
    for x in (140, 274, 432, 546):
        pygame.draw.line(surface, theme.ORANGE, (x, 12), (x, 42), 2)


def _draw_chip(surface: pygame.Surface, x: int, y: int, size: int) -> None:
    """Draw the chip glyph used beside CPU utilization."""
    pygame.draw.rect(surface, theme.ORANGE, (x, y, size, size), 2)
    pygame.draw.rect(surface, theme.ORANGE, (x + 5, y + 5, size - 10, size - 10), 1)
    for offset in (3, 8, 13):
        pygame.draw.line(surface, theme.ORANGE, (x - 3, y + offset), (x, y + offset), 2)
        pygame.draw.line(surface, theme.ORANGE, (x + size, y + offset), (x + size + 3, y + offset), 2)


def _draw_memory(surface: pygame.Surface, x: int, y: int) -> None:
    """Draw the memory-module glyph used beside RAM utilization."""
    pygame.draw.rect(surface, theme.ORANGE, (x, y, 18, 14), 2)
    for offset in (4, 9, 14):
        pygame.draw.line(surface, theme.ORANGE, (x + offset, y + 4), (x + offset, y + 10), 2)
        pygame.draw.line(surface, theme.ORANGE, (x + offset, y + 14), (x + offset, y + 17), 1)


def _draw_thermometer(surface: pygame.Surface, x: int, y: int) -> None:
    """Draw the temperature glyph used beside the thermal reading."""
    pygame.draw.rect(surface, theme.ORANGE, (x + 5, y, 7, 17), 2, border_radius=3)
    pygame.draw.circle(surface, theme.ORANGE, (x + 8, y + 18), 5, 2)
    pygame.draw.line(surface, theme.ORANGE, (x + 8, y + 5), (x + 8, y + 18), 2)


def _draw_battery(surface: pygame.Surface, x: int, y: int, available: bool) -> None:
    """Draw the battery glyph with enabled/disabled styling."""
    color = theme.ORANGE if available else theme.DIM_ORANGE
    pygame.draw.rect(surface, color, (x, y + 2, 20, 13), 2, border_radius=2)
    pygame.draw.rect(surface, color, (x + 20, y + 6, 3, 5))
    pygame.draw.rect(surface, color, (x + 3, y + 5, 12, 7))


def draw_wifi(surface: pygame.Surface, x: int, y: int, connected: bool) -> None:
    """Draw the Wi-Fi glyph in orange when connected and dim orange otherwise."""
    color = theme.ORANGE if connected else theme.DIM_ORANGE
    pygame.draw.arc(surface, color, (x - 11, y - 10, 22, 18), 0.65, 2.5, 2)
    pygame.draw.arc(surface, color, (x - 7, y - 6, 14, 12), 0.65, 2.5, 2)
    pygame.draw.circle(surface, color, (x, y + 4), 2)
