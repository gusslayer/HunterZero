"""Verify every SDL input family maps to the actions used by the UI."""

import unittest

import pygame

from core.input import (
    BACK,
    DOWN,
    LEFT,
    OPEN,
    RIGHT,
    RUN,
    UP,
    action_from_event,
    reset_input_state,
)


class GamepadMappingTests(unittest.TestCase):
    """Ensure GPi controls navigate every screen, whichever SDL family they use."""

    def setUp(self) -> None:
        """Clear cross-family debounce state before each independent test."""
        reset_input_state()

    def test_sdl_controller_dpad_is_mapped_in_all_directions(self):
        """Map SDL GameController D-pad events to the four navigation actions."""
        expected = {
            pygame.CONTROLLER_BUTTON_DPAD_UP: UP,
            pygame.CONTROLLER_BUTTON_DPAD_DOWN: DOWN,
            pygame.CONTROLLER_BUTTON_DPAD_LEFT: LEFT,
            pygame.CONTROLLER_BUTTON_DPAD_RIGHT: RIGHT,
        }
        for button, action in expected.items():
            event = pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=button)
            self.assertEqual(action_from_event(event), action)

    def test_sdl_controller_buttons_open_back_and_start(self):
        """Map normalized SDL A, B, and Start button events."""
        self.assertEqual(
            action_from_event(
                pygame.event.Event(
                    pygame.CONTROLLERBUTTONDOWN,
                    button=pygame.CONTROLLER_BUTTON_A,
                )
            ),
            OPEN,
        )
        self.assertEqual(
            action_from_event(
                pygame.event.Event(
                    pygame.CONTROLLERBUTTONDOWN,
                    button=pygame.CONTROLLER_BUTTON_B,
                )
            ),
            BACK,
        )
        self.assertEqual(
            action_from_event(
                pygame.event.Event(
                    pygame.CONTROLLERBUTTONDOWN,
                    button=pygame.CONTROLLER_BUTTON_START,
                )
            ),
            RUN,
        )

    def test_gpio_keyboard_controls_are_mapped(self):
        """Restore the keyboard events exposed by the GPi Case 2W GPIO controls."""
        expected = {
            pygame.K_UP: UP,
            pygame.K_DOWN: DOWN,
            pygame.K_LEFT: LEFT,
            pygame.K_RIGHT: RIGHT,
            pygame.K_RETURN: OPEN,
            pygame.K_ESCAPE: BACK,
            pygame.K_TAB: RUN,
        }
        for key, action in expected.items():
            with self.subTest(key=key):
                reset_input_state()
                event = pygame.event.Event(pygame.KEYDOWN, key=key)
                self.assertEqual(action_from_event(event), action)

    def test_keyboard_has_no_exit_shortcut(self):
        """Keep the kiosk alive even if an external keyboard sends Q or Alt-F4."""
        for key in (pygame.K_q, pygame.K_F4):
            event = pygame.event.Event(pygame.KEYDOWN, key=key)
            self.assertIsNone(action_from_event(event))

    def test_legacy_joystick_buttons_are_not_ignored(self):
        """Accept physical button numbers when SDL reports JOYBUTTONDOWN only."""
        expected = {0: OPEN, 1: BACK, 6: RUN, 7: RUN}
        for button, action in expected.items():
            with self.subTest(button=button):
                reset_input_state()
                event = pygame.event.Event(pygame.JOYBUTTONDOWN, button=button)
                self.assertEqual(action_from_event(event), action)

    def test_duplicate_controller_and_legacy_button_is_suppressed(self):
        """Count a double-reported physical button as a single UI action."""
        controller = pygame.event.Event(
            pygame.CONTROLLERBUTTONDOWN,
            button=pygame.CONTROLLER_BUTTON_A,
        )
        legacy = pygame.event.Event(pygame.JOYBUTTONDOWN, button=0)
        self.assertEqual(action_from_event(controller), OPEN)
        self.assertIsNone(action_from_event(legacy))

    def test_analog_axis_movement_is_emitted_once_until_released(self):
        """Debounce held joystick axes to avoid skipping target octets."""
        event = pygame.event.Event(
            pygame.JOYAXISMOTION,
            axis=0,
            value=0.8,
            instance_id=999,
        )
        self.assertEqual(action_from_event(event), RIGHT)
        self.assertIsNone(action_from_event(event))
        release = pygame.event.Event(
            pygame.JOYAXISMOTION,
            axis=0,
            value=0.0,
            instance_id=999,
        )
        self.assertIsNone(action_from_event(release))
        self.assertEqual(action_from_event(event), RIGHT)


if __name__ == "__main__":
    unittest.main()
