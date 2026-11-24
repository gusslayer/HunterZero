"""Print raw SDL input events to diagnose gamepad buttons on the GPi.

Run from SSH with the same user as the service:

    cd ~/HunterZero
    SDL_VIDEODRIVER=dummy .venv/bin/python tools/input_probe.py

Press D-pad/A/B/START for a few seconds. If lines appear only as JOYBUTTONDOWN
or JOYHATMOTION, the legacy fallback in core/input.py is the one that must work.
"""

import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402  (the driver must be selected before importing)


def main() -> int:
    """Report detected devices and raw events for twenty seconds."""
    pygame.init()
    try:
        from pygame._sdl2 import controller

        controller.init()
        has_controller_api = True
    except (ImportError, pygame.error):
        has_controller_api = False

    print(f"SDL {pygame.version.SDL}, joysticks: {pygame.joystick.get_count()}")
    for index in range(pygame.joystick.get_count()):
        stick = pygame.joystick.Joystick(index)
        stick.init()
        mapped = has_controller_api and controller.is_controller(index)
        print(f"  [{index}] {stick.get_name()} mapped={mapped}")

    deadline = time.monotonic() + 20
    print("Pulsa botones del mando durante 20 segundos...")
    while time.monotonic() < deadline:
        for event in pygame.event.get():
            if event.type in (
                pygame.CONTROLLERBUTTONDOWN,
                pygame.JOYBUTTONDOWN,
                pygame.JOYHATMOTION,
                pygame.JOYAXISMOTION,
            ):
                print(
                    f"type={event.type} button={getattr(event, 'button', None)} "
                    f"axis={getattr(event, 'axis', None)} value={getattr(event, 'value', None)}",
                    flush=True,
                )
        time.sleep(0.05)
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
