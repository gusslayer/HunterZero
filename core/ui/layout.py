from dataclasses import dataclass

import pygame


@dataclass(frozen=True)
class MenuItem:
    label: str
    icon: str


class MenuLayout:
    def __init__(self, bounds: pygame.Rect, row_height: int, padding: int = 4) -> None:
        """Store dimensions shared by menu rows and their visible window."""
        self.bounds = bounds
        self.row_height = row_height
        self.padding = padding

    def row_rect(self, index: int) -> pygame.Rect:
        """Return the pixel rectangle for a menu item at the given index."""
        return pygame.Rect(
            self.bounds.x,
            self.bounds.y + index * (self.row_height + self.padding),
            self.bounds.width,
            self.row_height,
        )

    def visible_range(self, count: int, selection: int) -> tuple[int, int]:
        """Calculate the index range needed to keep the selection visible."""
        capacity = max(1, (self.bounds.height + self.padding) // (self.row_height + self.padding))
        first = max(0, min(selection - capacity // 2, count - capacity))
        return first, min(count, first + capacity)
