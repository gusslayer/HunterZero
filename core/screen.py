import os

import pygame

from core import theme


def create_display() -> pygame.Surface:
    driver = os.environ.get("SDL_VIDEODRIVER")
    flags = pygame.FULLSCREEN if os.environ.get("HUNTERZERO_FULLSCREEN") == "1" else 0
    try:
        return pygame.display.set_mode((theme.WIDTH, theme.HEIGHT), flags)
    except pygame.error:
        if driver:
            raise
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.display.quit()
        pygame.display.init()
        return pygame.display.set_mode((theme.WIDTH, theme.HEIGHT))
