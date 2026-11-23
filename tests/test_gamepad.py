"""Verify semantic SDL button events map to the expected UI actions."""

import unittest

import pygame

from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, RUN, UP, action_from_event


class GamepadMappingTests(unittest.TestCase):
    """Ensure the GPi D-pad and face buttons can navigate every tool screen."""

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

    def test_keyboard_events_cannot_trigger_an_action(self):
        """Ensure tool commands cannot be invoked through a keyboard event."""
        self.assertIsNone(
            action_from_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        )

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
