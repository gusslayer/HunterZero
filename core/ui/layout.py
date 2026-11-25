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

    @property
    def capacity(self) -> int:
        """Return how many complete rows fit inside the visible bounds."""
        return max(1, self.bounds.height // (self.row_height + self.padding))

    def row_rect(self, position: int) -> pygame.Rect:
        """Return the rectangle for a row at a position inside the visible window."""
        return pygame.Rect(
            self.bounds.x,
            self.bounds.y + position * (self.row_height + self.padding),
            self.bounds.width,
            self.row_height,
        )

    def visible_range(self, count: int, selection: int) -> tuple[int, int]:
        """Calculate the index range needed to keep the selection visible."""
        capacity = self.capacity
        first = max(0, min(selection - capacity // 2, count - capacity))
        return first, min(count, first + capacity)
