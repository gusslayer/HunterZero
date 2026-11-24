import pygame

from core import theme
from core.system_stats import SystemStats
from core.ui import icons
from core.ui.text_cache import render_cached


def _text(surface: pygame.Surface, font: pygame.font.Font, value: str, x: int, y: int) -> None:
    """Render one white HUD reading at the specified logical pixel position."""
    surface.blit(render_cached(font, value, theme.TEXT_COLOR), (x, y))


def draw_hud(surface: pygame.Surface, font: pygame.font.Font, stats: SystemStats) -> None:
    """Draw system metrics, hardware symbols, Wi-Fi, battery, and clock."""
    pygame.draw.rect(surface, theme.BG_COLOR, (0, 0, theme.WIDTH, 27))
    pygame.draw.line(surface, theme.MUTED_COLOR, (10, 26), (310, 26), 1)
    temperature = f"{stats.temperature_c}C" if stats.temperature_c is not None else "--C"
    battery = f"{stats.battery_percent}%" if stats.battery_percent is not None else "--%"
    _text(surface, font, f"CPU:{stats.cpu_percent:02d}", 6, 9)
    _text(surface, font, f"RAM:{stats.memory_percent:02d}", 66, 9)
    _text(surface, font, f"T:{temperature}", 126, 9)
    draw_battery(surface, font, 176, 5, battery)
    draw_wifi(surface, 244, 13, stats.wifi_connected)
    _text(surface, font, stats.clock, 270, 9)


def draw_battery(surface: pygame.Surface, font: pygame.font.Font, x: int, y: int, value: str) -> None:
    """Draw the battery icon at x,y and its percentage text after the icon."""
    icons.draw_icon(surface, "battery-charging", pygame.Rect(x, y, 17, 17), theme.TEXT_COLOR)
    _text(surface, font, value, x + 20, y + 4)


def draw_wifi(surface: pygame.Surface, x: int, y: int, connected: bool) -> None:
    """Draw a hard-edged Wi-Fi glyph using only short horizontal pixels."""
    color = theme.ACCENT_COLOR if connected else theme.MUTED_COLOR
    pygame.draw.rect(surface, color, (x - 5, y - 3, 10, 1))
    pygame.draw.rect(surface, color, (x - 3, y - 1, 6, 1))
    pygame.draw.rect(surface, color, (x - 1, y + 1, 2, 2))
