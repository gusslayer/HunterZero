"""Gamepad editor for Bluetooth MAC addresses used by the BLEeding module."""

import pygame

from core import theme
from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP
from core.ui.text_cache import render_cached
from core.ui.widgets import draw_frame, plain_text
from modules.bleeding.engine import normalize_target


class MacEditor:
    """Edit a six-byte Bluetooth address one hexadecimal nibble at a time."""

    HEX = "0123456789ABCDEF"
    DEFAULT = "FC:FC:48:11:22:33"

    def __init__(self, address: str = DEFAULT) -> None:
        """Start from a valid address and remember it for B cancellations."""
        try:
            value = normalize_target(address)
        except ValueError:
            value = self.DEFAULT
        self.pairs = value.split(":")
        self._saved = list(self.pairs)
        self.position = 0
        self.notice = ""

    @property
    def value(self) -> str:
        """Return the currently displayed Bluetooth address."""
        return ":".join(self.pairs)

    @property
    def current_digit(self) -> str:
        """Return the hexadecimal digit currently selected by the cursor."""
        return self.pairs[self.position // 2][self.position % 2]

    def begin(self) -> None:
        """Snapshot the address so B can restore it without saving."""
        self._saved = list(self.pairs)
        self.notice = ""

    def handle(self, action) -> str | None:
        """Move between nibbles, change digits, save, or cancel the edit."""
        if action == UP:
            self._change_digit(1)
        elif action == DOWN:
            self._change_digit(-1)
        elif action == LEFT:
            self.position = (self.position - 1) % 12
            self.notice = ""
        elif action == RIGHT:
            self.position = (self.position + 1) % 12
            self.notice = ""
        elif action == OPEN:
            try:
                value = normalize_target(self.value)
            except ValueError as error:
                self.notice = str(error)
            else:
                self.pairs = value.split(":")
                self._saved = list(self.pairs)
                self.notice = ""
                return "saved"
        elif action == BACK:
            self.pairs = list(self._saved)
            self.notice = ""
            return "cancelled"
        return None

    def _change_digit(self, step: int) -> None:
        """Increase or decrease the selected hexadecimal nibble."""
        pair_index = self.position // 2
        nibble_index = self.position % 2
        pair = self.pairs[pair_index]
        digit = self.HEX.index(pair[nibble_index])
        new_digit = (digit + step) % len(self.HEX)
        self.pairs[pair_index] = (
            self.HEX[new_digit] + pair[1] if nibble_index == 0 else pair[0] + self.HEX[new_digit]
        )
        self.notice = ""

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        """Render the current address, active nibble, hexadecimal legend, and notice."""
        draw_frame(surface, pygame.Rect(10, 32, 300, 30), theme.GRID_COLOR, theme.PANEL_COLOR)
        surface.blit(render_cached(small_font, "MAC", theme.MUTED_COLOR), (16, 36))
        selected_index = self.position + self.position // 2
        x = 16
        for index, character in enumerate(self.value):
            color = theme.ACCENT_COLOR if index == selected_index else theme.TEXT_COLOR
            if character == ":":
                color = theme.MUTED_COLOR
            surface.blit(render_cached(font, character, color), (x, 48))
            x += font.size("0")[0]
        cell_width = 34
        cell_height = 20
        grid_x = (theme.WIDTH - cell_width * 4) // 2
        for index, character in enumerate(self.HEX):
            column = index % 4
            row = index // 4
            rect = pygame.Rect(
                grid_x + column * cell_width,
                76 + row * (cell_height + 3),
                cell_width - 2,
                cell_height,
            )
            selected = character == self.current_digit
            pygame.draw.rect(
                surface,
                theme.ACCENT_COLOR if selected else theme.PANEL_COLOR,
                rect,
                0 if selected else 1,
            )
            color = theme.BG_COLOR if selected else theme.TEXT_COLOR
            rendered = render_cached(font, character, color)
            surface.blit(rendered, (rect.x + (rect.width - rendered.get_width()) // 2, rect.y + 5))
        if self.notice:
            surface.blit(
                render_cached(small_font, plain_text(self.notice)[:34], theme.ACCENT_COLOR),
                (16, 192),
            )
