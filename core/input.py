from dataclasses import dataclass

import pygame


_CONTROLLER_INSTANCE_IDS: set[int] = set()
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

def action_from_event(event: pygame.event.Event) -> Action | None:
    """Translate only GPi/joystick controls and the SDL window-close event."""
    if event.type == pygame.CONTROLLERBUTTONDOWN:
        controller_actions = {
            pygame.CONTROLLER_BUTTON_DPAD_UP: UP,
            pygame.CONTROLLER_BUTTON_DPAD_DOWN: DOWN,
            pygame.CONTROLLER_BUTTON_DPAD_LEFT: LEFT,
            pygame.CONTROLLER_BUTTON_DPAD_RIGHT: RIGHT,
            pygame.CONTROLLER_BUTTON_A: OPEN,
            pygame.CONTROLLER_BUTTON_B: BACK,
            pygame.CONTROLLER_BUTTON_START: RUN,
        }
        return controller_actions.get(event.button)
    if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION, pygame.JOYAXISMOTION):
        if getattr(event, "instance_id", -1) in _CONTROLLER_INSTANCE_IDS:
            return None
    if event.type == pygame.JOYHATMOTION:
        x, y = event.value
        if y > 0:
            return UP
        if y < 0:
            return DOWN
        if x < 0:
            return LEFT
        if x > 0:
            return RIGHT
    if event.type == pygame.JOYAXISMOTION and abs(event.value) >= 0.6:
        instance_id = getattr(event, "instance_id", -1)
        axis_key = (instance_id, event.axis)
        direction = -1 if event.value < 0 else 1
        if _ACTIVE_AXES.get(axis_key) == direction:
            return None
        _ACTIVE_AXES[axis_key] = direction
        if event.axis == 0:
            return LEFT if event.value < 0 else RIGHT
        if event.axis == 1:
            return UP if event.value < 0 else DOWN
    elif event.type == pygame.JOYAXISMOTION and abs(event.value) <= 0.3:
        _ACTIVE_AXES.pop((getattr(event, "instance_id", -1), event.axis), None)
    if event.type == pygame.JOYBUTTONDOWN:
        if event.button == 0:
            return OPEN
        if event.button == 1:
            return BACK
        if event.button == 6:
            return RUN
    if event.type == pygame.QUIT:
        return QUIT
    return None


def initialize_joysticks(logger) -> list[object]:
    """Initialize available gamepads and log each detected device."""
    devices = []
    _CONTROLLER_INSTANCE_IDS.clear()
    _ACTIVE_AXES.clear()
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
                        "No se pudo mapear el gamepad %s; se usará el mapeo legacy.",
                        joystick.get_name(),
                    )
            if mapped_controller:
                devices.append(mapped_controller)
                _CONTROLLER_INSTANCE_IDS.add(joystick.get_instance_id())
                logger.info("Gamepad SDL mapeado: %s", mapped_controller.name)
            else:
                logger.info(
                    "Gamepad sin mapeo SDL: %s; se usarán los botones físicos estándar.",
                    joystick.get_name(),
                )
    except pygame.error:
        logger.exception("No se pudo inicializar el gamepad")
    return devices
