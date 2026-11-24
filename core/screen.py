"""Creación de la pantalla 640x480 con degradación controlada de drivers SDL."""

import glob
import logging
import os

import pygame

from core import theme

LOGGER = logging.getLogger("hunterzero")


def _video_device_diagnostics(errors: dict[str, str]) -> str:
    """Describe available display nodes and likely causes after SDL fails."""
    drm_cards = sorted(glob.glob("/dev/dri/card*"))
    render_nodes = sorted(glob.glob("/dev/dri/renderD*"))
    framebuffers = sorted(glob.glob("/dev/fb*"))
    nodes = [*drm_cards, *render_nodes, *framebuffers]
    if nodes:
        access = [
            f"{path}={'rw' if os.access(path, os.R_OK | os.W_OK) else 'sin acceso rw'}"
            for path in nodes
        ]
        node_summary = ", ".join(access)
    else:
        node_summary = "no se detectan /dev/dri/* ni /dev/fb*"

    if "kmsdrm" in errors and not drm_cards:
        hint = (
            "el kernel no expuso /dev/dri/card*: comprueba los overlays KMS/DPI "
            "de /boot/firmware/config.txt y los mensajes vc4/drm del arranque"
        )
    elif "kmsdrm" in errors and not any(
        os.access(path, os.R_OK | os.W_OK) for path in drm_cards
    ):
        hint = (
            "el usuario del servicio no puede leer/escribir los dispositivos DRM; "
            "revisa sus grupos video/render y reinicia la sesión o el servicio"
        )
    elif "kmsdrm" in errors and any("EGL" in error.upper() for error in errors.values()):
        hint = (
            "DRM está presente pero EGL no inicializa; verifica el driver Mesa/GBM "
            "y el modo DPI. fbcon solo sirve si existe /dev/fb0"
        )
    else:
        hint = "revisa los dispositivos, permisos y errores del kernel para KMS/DRM"

    return (
        f"Dispositivos: {node_summary}. Diagnóstico: {hint}. "
        "Comprueba con: ls -l /dev/dri /dev/fb0; id; "
        "dmesg | grep -Ei 'vc4|drm|egl'."
    )


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
            surface = pygame.display.set_mode(
                (theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT),
                flags,
            )
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
    diagnostics = _video_device_diagnostics(errors)
    raise pygame.error(
        f"No se pudo inicializar ningún driver de vídeo: {errors}. {diagnostics}"
    )
