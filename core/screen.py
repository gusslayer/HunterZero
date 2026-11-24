"""Creación de la pantalla 640x480 con degradación controlada de drivers SDL."""

import logging
import os

import pygame

from core import theme

LOGGER = logging.getLogger("hunterzero")


def _candidate_drivers(forced: str | None) -> list[str]:
    """Devuelve los drivers a intentar, probando KMS antes que el framebuffer."""
    if forced == "dummy":
        return ["dummy"]
    if forced:
        # kmsdrm es el preferido en la GPi; fbcon es el respaldo cuando EGL falla.
        return [forced] if forced != "kmsdrm" else ["kmsdrm", "fbcon"]
    return ["kmsdrm", "fbcon", "dummy"]


def create_display() -> pygame.Surface:
    """Create the 640x480 SDL display, falling back to fbcon when EGL fails."""
    flags = pygame.FULLSCREEN if os.environ.get("HUNTERZERO_FULLSCREEN") == "1" else 0
    errors: dict[str, str] = {}
    for driver in _candidate_drivers(os.environ.get("SDL_VIDEODRIVER")):
        os.environ["SDL_VIDEODRIVER"] = driver
        pygame.display.quit()
        try:
            pygame.display.init()
            surface = pygame.display.set_mode((theme.WIDTH, theme.HEIGHT), flags)
            try:
                # KMSDRM muestra el cursor en un plane DRM ajeno al surface.
                pygame.mouse.set_visible(False)
            except pygame.error as exc:
                LOGGER.warning("No se pudo ocultar el cursor SDL: %s", exc)
            pygame.display.set_caption("HunterZero")
            if errors:
                LOGGER.warning("Pantalla inicializada con %s tras fallar %s", driver, errors)
            return surface
        except pygame.error as exc:
            errors[driver] = str(exc)
            LOGGER.warning("Driver SDL %s no disponible: %s", driver, exc)
    raise pygame.error(f"No se pudo inicializar ningún driver de vídeo: {errors}")
