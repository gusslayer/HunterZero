"""Arcade-style name entry: move over a character matrix and stamp letters into a field."""

import pygame

from core import theme
from core.hostname import normalize_hostname
from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP
from core.ui.text_cache import render_cached
from core.ui.widgets import plain_text


class HostnameEditor:
    """Enter a DNS hostname with a retro console-style character grid."""

    GRID = (
        ("A", "B", "C", "D", "E", "F", "G", "H"),
        ("I", "J", "K", "L", "M", "N", "O", "P"),
        ("Q", "R", "S", "T", "U", "V", "W", "X"),
        ("Y", "Z", "0", "1", "2", "3", "4", "5"),
        ("6", "7", "8", "9", "-", ".", "DEL", "OK"),
    )
    MAX_LENGTH = 24

    def __init__(self, hostname: str = "example.com") -> None:
        """Initialize the text field and place the cursor on the first cell."""
        try:
            initial = normalize_hostname(hostname)
        except ValueError:
            initial = "example.com"
        self.characters = list(initial)
        self._saved = self.characters.copy()
        self.row = 0
        self.column = 0
        self.notice = ""

    @property
    def value(self) -> str:
        """Return the hostname currently shown in the entry field."""
        return "".join(self.characters)

    def begin(self) -> None:
        """Remember the field content so B can restore it before saving."""
        self._saved = self.characters.copy()
        self.notice = ""

    def handle(self, action) -> str | None:
        """Move the grid cursor, stamp a character, delete, save, or cancel."""
        if action == UP:
            self.row = (self.row - 1) % len(self.GRID)
            self.notice = ""
        elif action == DOWN:
            self.row = (self.row + 1) % len(self.GRID)
            self.notice = ""
        elif action == LEFT:
            self.column = (self.column - 1) % len(self.GRID[0])
            self.notice = ""
        elif action == RIGHT:
            self.column = (self.column + 1) % len(self.GRID[0])
            self.notice = ""
        elif action == OPEN:
            return self._stamp()
        elif action == BACK:
            self.characters = self._saved.copy()
            self.notice = ""
            return "cancelled"
        return None

    def _stamp(self) -> str | None:
        """Apply the selected grid cell and report a saved hostname when accepted."""
        choice = self.GRID[self.row][self.column]
        if choice == "DEL":
            if self.characters:
                self.characters.pop()
            self.notice = ""
        elif choice == "OK":
            try:
                normalize_hostname(self.value)
            except ValueError as error:
                self.notice = str(error)[:34]
            else:
                self._saved = self.characters.copy()
                return "saved"
        elif len(self.characters) < self.MAX_LENGTH:
            self.characters.append(choice.lower())
            self.notice = ""
        return None

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        """Render the entry field and the selectable character matrix."""
        pygame.draw.rect(surface, theme.PANEL_COLOR, (10, 32, 300, 30))
        pygame.draw.rect(surface, theme.GRID_COLOR, (10, 32, 300, 30), 1)
        surface.blit(render_cached(small_font, "HOST", theme.MUTED_COLOR), (16, 36))
        surface.blit(render_cached(font, plain_text(self.value)[:34], theme.TEXT_COLOR), (16, 48))
        cursor_x = 16 + min(len(self.value), 34) * 8
        pygame.draw.rect(surface, theme.ACCENT_COLOR, (cursor_x, 48, 8, 8))

        cell_width = 26
        cell_height = 20
        grid_x = (theme.WIDTH - cell_width * len(self.GRID[0])) // 2
        for row_index, row in enumerate(self.GRID):
            for column_index, choice in enumerate(row):
                x = grid_x + column_index * cell_width
                y = 72 + row_index * 22
                active = (row_index, column_index) == (self.row, self.column)
                if active:
                    pygame.draw.rect(surface, theme.ACCENT_COLOR, (x, y, cell_width - 2, cell_height))
                    color = theme.BG_COLOR
                else:
                    pygame.draw.rect(surface, theme.GRID_COLOR, (x, y, cell_width - 2, cell_height), 1)
                    color = theme.TEXT_COLOR if choice not in ("DEL", "OK") else theme.ACCENT_COLOR
                label = "<-" if choice == "DEL" else choice
                rendered = render_cached(font, label, color)
                surface.blit(rendered, (x + (cell_width - 2 - rendered.get_width()) // 2, y + 6))
        if self.notice:
            surface.blit(
                render_cached(small_font, plain_text(self.notice)[:34], theme.ACCENT_COLOR),
                (16, 192),
            )
