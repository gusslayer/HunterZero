import pygame

from core import theme
from core.system_stats import SystemStats


def _text(surface: pygame.Surface, font: pygame.font.Font, value: str, x: int, y: int) -> None:
    surface.blit(font.render(value, True, theme.ORANGE), (x, y))


def draw_hud(surface: pygame.Surface, font: pygame.font.Font, stats: SystemStats) -> None:
    pygame.draw.rect(surface, theme.BLACK, (0, 0, theme.WIDTH, 54))
    pygame.draw.line(surface, theme.ORANGE, (20, 53), (620, 53), 2)
    _draw_chip(surface, 29, 19, 17)
    _draw_memory(surface, 175, 20)
    _draw_thermometer(surface, 354, 18)
    _draw_battery(surface, 486, 20, stats.battery_percent is not None)
    _text(surface, font, f"CPU:{stats.cpu_percent:02d}%", 54, 22)
    _text(surface, font, f"RAM:{stats.memory_percent:02d}%", 201, 22)
    temperature = f"{stats.temperature_c}C" if stats.temperature_c is not None else "--C"
    _text(surface, font, f"TEMP:{temperature}", 377, 22)
    draw_wifi(surface, 462, 28, stats.wifi_connected)
    battery = f"{stats.battery_percent}%" if stats.battery_percent is not None else "--%"
    _text(surface, font, battery, 512, 22)
    _text(surface, font, stats.clock, 572, 22)
    for x in (154, 339, 445, 565):
        pygame.draw.line(surface, theme.ORANGE, (x, 13), (x, 43), 2)


def _draw_chip(surface: pygame.Surface, x: int, y: int, size: int) -> None:
    pygame.draw.rect(surface, theme.ORANGE, (x, y, size, size), 2)
    pygame.draw.rect(surface, theme.ORANGE, (x + 5, y + 5, size - 10, size - 10), 1)
    for offset in (3, 8, 13):
        pygame.draw.line(surface, theme.ORANGE, (x - 3, y + offset), (x, y + offset), 2)
        pygame.draw.line(surface, theme.ORANGE, (x + size, y + offset), (x + size + 3, y + offset), 2)


def _draw_memory(surface: pygame.Surface, x: int, y: int) -> None:
    pygame.draw.rect(surface, theme.ORANGE, (x, y, 18, 14), 2)
    for offset in (4, 9, 14):
        pygame.draw.line(surface, theme.ORANGE, (x + offset, y + 4), (x + offset, y + 10), 2)
        pygame.draw.line(surface, theme.ORANGE, (x + offset, y + 14), (x + offset, y + 17), 1)


def _draw_thermometer(surface: pygame.Surface, x: int, y: int) -> None:
    pygame.draw.rect(surface, theme.ORANGE, (x + 5, y, 7, 17), 2, border_radius=3)
    pygame.draw.circle(surface, theme.ORANGE, (x + 8, y + 18), 5, 2)
    pygame.draw.line(surface, theme.ORANGE, (x + 8, y + 5), (x + 8, y + 18), 2)


def _draw_battery(surface: pygame.Surface, x: int, y: int, available: bool) -> None:
    color = theme.ORANGE if available else theme.DIM_ORANGE
    pygame.draw.rect(surface, color, (x, y + 2, 20, 13), 2, border_radius=2)
    pygame.draw.rect(surface, color, (x + 20, y + 6, 3, 5))
    pygame.draw.rect(surface, color, (x + 3, y + 5, 12, 7))


def draw_wifi(surface: pygame.Surface, x: int, y: int, connected: bool) -> None:
    color = theme.ORANGE if connected else theme.DIM_ORANGE
    pygame.draw.arc(surface, color, (x - 11, y - 10, 22, 18), 0.65, 2.5, 2)
    pygame.draw.arc(surface, color, (x - 7, y - 6, 14, 12), 0.65, 2.5, 2)
    pygame.draw.circle(surface, color, (x, y + 4), 2)
