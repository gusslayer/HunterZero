"""Draw the top HUD as a compact six-cell dashboard with live readings."""

import pygame

from core import theme
from core.system_stats import SystemStats
from core.ui import icons
from core.ui.text_cache import render_cached
from core.ui.widgets import draw_meter, plain_text


def draw_hud(surface: pygame.Surface, font: pygame.font.Font, stats: SystemStats) -> None:
    """Draw aligned icon/value cells for CPU, RAM, temperature, Wi-Fi, battery, and clock."""
    pygame.draw.rect(surface, theme.PANEL_COLOR, (0, 0, theme.WIDTH, 27))
    pygame.draw.line(surface, theme.ACCENT_COLOR, (0, 26), (theme.WIDTH, 26), 1)
    temperature = f"{stats.temperature_c}C" if stats.temperature_c is not None else "--C"
    battery = f"{stats.battery_percent}%" if stats.battery_percent is not None else "--"
    cells = [
        ("cpu", f"{stats.cpu_percent}%", stats.cpu_percent, theme.TEXT_COLOR),
        ("memory-stick", f"{stats.memory_percent}%", stats.memory_percent, theme.TEXT_COLOR),
        ("gauge", temperature, None, theme.TEXT_COLOR),
        (
            "wifi",
            "ON" if stats.wifi_connected else "OFF",
            None,
            theme.ACCENT_COLOR if stats.wifi_connected else theme.MUTED_COLOR,
        ),
        (
            "battery-charging",
            battery,
            stats.battery_percent,
            theme.ACCENT_COLOR if stats.battery_charging else theme.TEXT_COLOR,
        ),
        (None, stats.clock, None, theme.ACCENT_COLOR),
    ]
    cell_width = theme.WIDTH // len(cells)
    for index, (icon_name, value, percent, color) in enumerate(cells):
        cell_x = index * cell_width
        if icon_name:
            icons.draw_icon(
                surface,
                icon_name,
                pygame.Rect(cell_x + (cell_width - 14) // 2, 0, 14, 14),
                color,
            )
        rendered = render_cached(font, plain_text(value), color)
        text_y = 14 if icon_name else 9
        surface.blit(rendered, (cell_x + (cell_width - rendered.get_width()) // 2, text_y))
        if percent is not None:
            draw_meter(surface, pygame.Rect(cell_x + 6, 23, cell_width - 12, 2), percent, color)
