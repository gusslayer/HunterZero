"""Map every supported SDL input family to the gamepad actions used by the UI."""

import logging
import os
import time
from dataclasses import dataclass

import pygame


LOGGER = logging.getLogger("hunterzero")

# Una misma pulsación puede llegar como CONTROLLERBUTTONDOWN, JOYBUTTONDOWN o
# KEYDOWN (la GPi Case 2W expone los controles como teclas GPIO). Se aceptan las
# tres familias y solo se descarta la repetición muy cercana en el tiempo;
# bloquear las familias legacy dejaba el menú completamente sin respuesta.
_DUPLICATE_WINDOW_SECONDS = 0.15
_LAST_EMITTED: tuple[object, str, float] | None = None
_ACTIVE_AXES: dict[tuple[int, int], int] = {}


@dataclass(frozen=True)
class Action:
    name: str


UP = Action("up")
DOWN = Action("down")
LEFT = Action("left")
RIGHT = Action("right")
OPEN = Action("open")
BACK = Action("back")
RUN = Action("run")
QUIT = Action("quit")

# La GPi Case 2W presenta D-pad/A/B/START como eventos de teclado GPIO. Estas
# teclas son navegación, no atajos de salida: la app es un quiosco sin teclado.
KEY_ACTIONS = {
    pygame.K_UP: UP,
    pygame.K_w: UP,
    pygame.K_DOWN: DOWN,
    pygame.K_s: DOWN,
    pygame.K_LEFT: LEFT,
    pygame.K_a: LEFT,
    pygame.K_RIGHT: RIGHT,
    pygame.K_d: RIGHT,
    pygame.K_RETURN: OPEN,
    pygame.K_KP_ENTER: OPEN,
    pygame.K_SPACE: OPEN,
    pygame.K_ESCAPE: BACK,
    pygame.K_BACKSPACE: BACK,
    pygame.K_TAB: RUN,
    pygame.K_LCTRL: RUN,
    pygame.K_RCTRL: RUN,
}


def reset_input_state() -> None:
    """Forget debounce state so held buttons at boot do not leak into the menu."""
    global _LAST_EMITTED
    _LAST_EMITTED = None
    _ACTIVE_AXES.clear()


def _emit(action: object, family: str) -> object | None:
    """Suppress the same action arriving from another SDL family at once."""
    global _LAST_EMITTED
    now = time.monotonic()
    if _LAST_EMITTED is not None:
        last_action, last_family, last_time = _LAST_EMITTED
        if last_action == action and last_family != family and now - last_time < _DUPLICATE_WINDOW_SECONDS:
            return None
    _LAST_EMITTED = (action, family, now)
    return action


def _log_raw_event(event: pygame.event.Event, action: object | None) -> None:
    """Log incoming SDL input when HUNTERZERO_INPUT_DEBUG=1 for field diagnosis."""
    if os.environ.get("HUNTERZERO_INPUT_DEBUG") != "1":
        return
    detail = {
        "type": event.type,
        "button": getattr(event, "button", None),
        "key": getattr(event, "key", None),
        "axis": getattr(event, "axis", None),
        "value": getattr(event, "value", None),
        "instance_id": getattr(event, "instance_id", None),
        "action": getattr(action, "name", None),
    }
    LOGGER.info("SDL input: %s", detail)


def action_from_event(event: pygame.event.Event) -> Action | None:
    """Translate keyboard, gamepad, hat, axis, and SDL close events into actions."""
    action: Action | None = None
    family = ""

    if event.type == pygame.CONTROLLERBUTTONDOWN:
        family = "controller"
        action = {
            pygame.CONTROLLER_BUTTON_DPAD_UP: UP,
            pygame.CONTROLLER_BUTTON_DPAD_DOWN: DOWN,
            pygame.CONTROLLER_BUTTON_DPAD_LEFT: LEFT,
            pygame.CONTROLLER_BUTTON_DPAD_RIGHT: RIGHT,
            pygame.CONTROLLER_BUTTON_A: OPEN,
            pygame.CONTROLLER_BUTTON_B: BACK,
            pygame.CONTROLLER_BUTTON_START: RUN,
        }.get(event.button)
    elif event.type == pygame.JOYHATMOTION:
        family = "legacy"
        x, y = event.value
        if y > 0:
            action = UP
        elif y < 0:
            action = DOWN
        elif x < 0:
            action = LEFT
        elif x > 0:
            action = RIGHT
    elif event.type == pygame.JOYAXISMOTION:
        family = "legacy"
        instance_id = getattr(event, "instance_id", -1)
        axis_key = (instance_id, event.axis)
        if abs(event.value) >= 0.6:
            direction = -1 if event.value < 0 else 1
            if _ACTIVE_AXES.get(axis_key) != direction:
                _ACTIVE_AXES[axis_key] = direction
                if event.axis == 0:
                    action = LEFT if event.value < 0 else RIGHT
                elif event.axis == 1:
                    action = UP if event.value < 0 else DOWN
        else:
            _ACTIVE_AXES.pop(axis_key, None)
    elif event.type == pygame.JOYBUTTONDOWN:
        family = "legacy"
        if event.button == 0:
            action = OPEN
        elif event.button == 1:
            action = BACK
        elif event.button in (6, 7):
            action = RUN
    elif event.type == pygame.KEYDOWN:
        family = "keyboard"
        action = KEY_ACTIONS.get(event.key)
    elif event.type == pygame.QUIT:
        family = "window"
        action = QUIT

    if action is None:
        _log_raw_event(event, None)
        return None
    emitted = _emit(action, family)
    _log_raw_event(event, emitted)
    return emitted  # type: ignore[return-value]


def initialize_joysticks(logger) -> list[object]:
    """Initialize every gamepad and keep controller objects alive for SDL events."""
    devices = []
    reset_input_state()
    try:
        pygame.joystick.init()
        try:
            from pygame._sdl2 import controller

            controller.init()
        except (ImportError, pygame.error) as error:
            controller = None
            logger.warning(
                "No está disponible SDL GameController; se usará el mapeo legacy: %s",
                error,
            )
        for index in range(pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(index)
            joystick.init()
            devices.append(joystick)
            mapped_controller = None
            if controller and controller.is_controller(index):
                try:
                    mapped_controller = controller.Controller.from_joystick(joystick)
                    mapped_controller.init()
                except pygame.error:
                    logger.exception(
                        "No se pudo mapear el gamepad %s; se usarán también los eventos legacy.",
                        joystick.get_name(),
                    )
            if mapped_controller:
                devices.append(mapped_controller)
                logger.info("Gamepad SDL mapeado: %s", mapped_controller.name)
            else:
                logger.info(
                    "Gamepad sin mapeo SDL: %s; se usarán los botones físicos estándar.",
                    joystick.get_name(),
                )
    except pygame.error:
        logger.exception("No se pudo inicializar el gamepad")
    return devices
