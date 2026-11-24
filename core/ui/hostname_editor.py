"""Gamepad editor for DNS hostnames using only glyphs the pixel font has."""

import pygame

from core import theme
from core.hostname import normalize_hostname
from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP
from core.ui.text_cache import render_cached
from core.ui.widgets import plain_text


class HostnameEditor:
    """Edit a hostname one character at a time with the D-pad."""

    SLOTS = 28
    ALPHABET = " abcdefghijklmnopqrstuvwxyz0123456789-."

    def __init__(self, hostname: str = "example.com") -> None:
        """Initialize a padded character buffer from a valid default hostname."""
        try:
            initial = normalize_hostname(hostname)
        except ValueError:
            initial = "example.com"
        self.slots = list(initial.ljust(self.SLOTS, " "))
        self._saved = self.slots.copy()
        self.position = 0
        self.notice = ""

    @property
    def value(self) -> str:
        """Return the trimmed hostname currently held in the editor buffer."""
        return "".join(self.slots).strip()

    def begin(self) -> None:
        """Remember the current buffer so B can restore it before saving."""
        self._saved = self.slots.copy()
        self.notice = ""

    def handle(self, action) -> str | None:
        """Apply one D-pad/button action and report save or cancel when finished."""
        if action == LEFT:
            self.position = max(0, self.position - 1)
            self.notice = ""
        elif action == RIGHT:
            self.position = min(self.SLOTS - 1, self.position + 1)
            self.notice = ""
        elif action in (UP, DOWN):
            step = 1 if action == UP else -1
            index = self.ALPHABET.index(self.slots[self.position])
            self.slots[self.position] = self.ALPHABET[(index + step) % len(self.ALPHABET)]
            self.notice = ""
        elif action == OPEN:
            try:
                normalize_hostname(self.value)
            except ValueError as error:
                self.notice = str(error)[:34]
            else:
                self._saved = self.slots.copy()
                return "saved"
        elif action == BACK:
            self.slots = self._saved.copy()
            self.notice = ""
            return "cancelled"
        return None

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        """Render the two-row character grid with the active cell highlighted."""
        columns = self.SLOTS // 2
        for index, character in enumerate(self.slots):
            x = 18 + (index % columns) * 17
            y = 62 + (index // columns) * 24
            if index == self.position:
                pygame.draw.rect(surface, theme.ACCENT_COLOR, (x - 2, y - 2, 14, 15))
                color = theme.BG_COLOR
            else:
                color = theme.TEXT_COLOR if character != " " else theme.MUTED_COLOR
            if character != " ":
                surface.blit(render_cached(font, character, color), (x, y))
        surface.blit(
            render_cached(small_font, f"HOST: {self.value or '-'}", theme.TEXT_COLOR), (18, 118)
        )
        surface.blit(
            render_cached(
                small_font,
                f"POS {self.position + 1:02d}/{self.SLOTS}  LEN {len(self.value):02d}",
                theme.MUTED_COLOR,
            ),
            (18, 134),
        )
        if self.notice:
            surface.blit(
                render_cached(small_font, plain_text(self.notice)[:34], theme.ACCENT_COLOR),
                (18, 152),
            )
