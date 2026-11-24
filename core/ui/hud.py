"""Draw the top HUD header with one icon per metric and live readings."""

import pygame

from core import theme
from core.system_stats import SystemStats
from core.ui import icons
from core.ui.text_cache import render_cached


def _text(surface: pygame.Surface, font: pygame.font.Font, value: str, x: int, y: int) -> None:
    """Render one HUD reading at the specified logical pixel position."""
    surface.blit(render_cached(font, value, theme.TEXT_COLOR), (x, y))


def draw_hud(surface: pygame.Surface, font: pygame.font.Font, stats: SystemStats) -> None:
    """Draw icons and values for CPU, RAM, temperature, battery, Wi-Fi, and clock."""
    pygame.draw.rect(surface, theme.BG_COLOR, (0, 0, theme.WIDTH, 27))
    pygame.draw.line(surface, theme.MUTED_COLOR, (10, 26), (310, 26), 1)
    temperature = f"{stats.temperature_c}C" if stats.temperature_c is not None else "--C"
    icons.draw_icon(surface, "cpu", pygame.Rect(6, 5, 17, 17), theme.TEXT_COLOR)
    _text(surface, font, f"CPU:{stats.cpu_percent:02d}", 26, 9)
    icons.draw_icon(surface, "memory-stick", pygame.Rect(84, 5, 17, 17), theme.TEXT_COLOR)
    _text(surface, font, f"RAM:{stats.memory_percent:02d}", 103, 9)
    icons.draw_icon(surface, "gauge", pygame.Rect(160, 5, 17, 17), theme.TEXT_COLOR)
    _text(surface, font, f"T:{temperature}", 179, 9)
    battery_color = theme.ACCENT_COLOR if stats.battery_charging else theme.TEXT_COLOR
    icons.draw_icon(surface, "battery-charging", pygame.Rect(228, 5, 17, 17), battery_color)
    draw_wifi(surface, 246, 5, stats.wifi_connected)
    _text(surface, font, stats.clock, 270, 9)


def draw_wifi(surface: pygame.Surface, x: int, y: int, connected: bool) -> None:
    """Draw the Wi-Fi icon at x,y tinted by the connection state."""
    color = theme.ACCENT_COLOR if connected else theme.MUTED_COLOR
    icons.draw_icon(surface, "wifi", pygame.Rect(x, y, 17, 17), color)
