from dataclasses import dataclass

import pygame


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
    pygame.K_SPACE: OPEN,
    pygame.K_ESCAPE: BACK,
    pygame.K_BACKSPACE: BACK,
    pygame.K_TAB: RUN,
    pygame.K_q: QUIT,
}


def action_from_event(event: pygame.event.Event) -> Action | None:
    if event.type == pygame.KEYDOWN:
        return KEY_ACTIONS.get(event.key)
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
        if event.axis == 0:
            return LEFT if event.value < 0 else RIGHT
        if event.axis == 1:
            return UP if event.value < 0 else DOWN
    if event.type == pygame.JOYBUTTONDOWN:
        if event.button == 0:
            return OPEN
        if event.button == 1:
            return BACK
        if event.button == 7:
            return RUN
    if event.type == pygame.QUIT:
        return QUIT
    return None


def initialize_joysticks(logger) -> list[pygame.joystick.Joystick]:
    devices = []
    try:
        pygame.joystick.init()
        for index in range(pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(index)
            joystick.init()
            devices.append(joystick)
            logger.info("Gamepad detectado: %s", joystick.get_name())
    except pygame.error:
        logger.exception("No se pudo inicializar el gamepad")
    return devices
