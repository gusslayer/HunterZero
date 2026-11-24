"""Reusable settings, confirmation, help, and result flow for one tool module."""

from collections.abc import Callable

import pygame

from core import theme
from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP
from core.process_manager import ProcessManager
from core.system_stats import SystemStats
from core.ui.help_view import draw_help_view
from core.ui.target_editor import IPv4Editor


class ParameterizedToolScreen:
    """Provide shared GPi navigation while each module owns its command spec."""

    def __init__(
        self,
        title: str,
        parameter_label: str,
        parameter_values: tuple[int, ...],
        initial_parameter: int,
        operation_label: str,
        help_sections: tuple[tuple[str, tuple[str, ...]], ...],
        command_builder: Callable[[str, int], list[str]],
        timeout_seconds: Callable[[int], int],
    ) -> None:
        """Initialize a tool screen from the module's validated options and help."""
        if not parameter_values or initial_parameter not in parameter_values:
            raise ValueError("El parámetro inicial debe pertenecer a sus opciones permitidas.")
        self.title = title
        self.parameter_label = parameter_label
        self.parameter_values = parameter_values
        self.parameter = initial_parameter
        self.operation_label = operation_label
        self.help_sections = help_sections
        self.command_builder = command_builder
        self.timeout_for_parameter = timeout_seconds
        self.target = IPv4Editor()
        self.phase = "settings"
        self.selected = 0
        self.rows = ("IP DESTINO", parameter_label, operation_label, "AYUDA", "VOLVER")

    def handle(self, action, processes: ProcessManager) -> bool:
        """Handle D-pad/A/B input and return true when the user exits the tool."""
        if self.phase == "edit_target":
            result = self.target.handle(action)
            if result in ("saved", "cancelled"):
                self.phase = "settings"
            return False
        if self.phase == "confirm":
            if action == BACK:
                self.phase = "settings"
            elif action == OPEN:
                self._start_command(processes)
            return False
        if self.phase == "running":
            if action == BACK:
                processes.stop()
                self.phase = "result"
            return False
        if self.phase == "result":
            if action == OPEN:
                self.phase = "settings"
            elif action == BACK:
                return True
            return False
        if self.phase == "help":
            if action == OPEN:
                self.phase = "settings"
            elif action == BACK:
                return True
            return False
        return self._handle_settings(action)

    def sync(self, processes: ProcessManager) -> None:
        """Switch to the result view once the command manager has finished."""
        if self.phase == "running" and processes.running is None:
            self.phase = "result"

    def draw(
        self,
        surface: pygame.Surface,
        title_font: pygame.font.Font,
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
        processes: ProcessManager,
        stats: SystemStats,
    ) -> None:
        """Render the active parameter, help, confirmation, progress, or result view."""
        del stats
        if self.phase == "edit_target":
            self.target.draw(surface, title_font, body_font, small_font)
            return
        if self.phase == "help":
            draw_help_view(
                surface,
                title_font,
                body_font,
                small_font,
                f"AYUDA {self.title}",
                self.help_sections,
            )
            return
        pygame.draw.rect(surface, theme.BLACK, (0, 55, theme.WIDTH, 370))
        surface.blit(title_font.render(self.title[:24], True, theme.ORANGE), (30, 72))
        if self.phase == "settings":
            self._draw_settings(surface, body_font)
        elif self.phase == "confirm":
            self._draw_confirmation(surface, small_font)
        elif self.phase == "running":
            surface.blit(body_font.render(f"{self.operation_label} EN CURSO", True, theme.WHITE), (30, 138))
            surface.blit(small_font.render(f"Objetivo: {self.target.address}", True, theme.ORANGE), (30, 184))
        else:
            self._draw_result(surface, small_font, processes)

    def footer_hints(self) -> list[tuple[str, int]]:
        """Return button labels for the current tool screen state."""
        if self.phase == "edit_target":
            return [("UP/DOWN DIGITO", 24), ("LEFT/RIGHT IP", 260), ("A GUARDAR", 480)]
        if self.phase == "confirm":
            return [("A CONFIRMAR", 24), ("B CANCELAR", 335)]
        if self.phase == "running":
            return [("B CANCELAR", 24)]
        if self.phase in ("result", "help"):
            return [("A OPCIONES", 24), ("B VOLVER", 335)]
        return [("UP/DOWN MOVER", 24), ("LEFT/RIGHT AJUSTAR", 230), ("A ABRIR", 500)]

    def _handle_settings(self, action) -> bool:
        """Navigate target, parameter, operation, help, and exit rows."""
        if action == UP:
            self.selected = (self.selected - 1) % len(self.rows)
        elif action == DOWN:
            self.selected = (self.selected + 1) % len(self.rows)
        elif action in (LEFT, RIGHT) and self.selected == 1:
            step = 1 if action == RIGHT else -1
            index = self.parameter_values.index(self.parameter)
            self.parameter = self.parameter_values[(index + step) % len(self.parameter_values)]
        elif action == OPEN:
            if self.selected == 0:
                self.target.begin()
                self.phase = "edit_target"
            elif self.selected == 2:
                self.phase = "confirm"
            elif self.selected == 3:
                self.phase = "help"
            elif self.selected == 4:
                return True
        elif action == BACK:
            return True
        return False

    def _start_command(self, processes: ProcessManager) -> None:
        """Build the module-provided safe argv and start it through the allowlist."""
        try:
            command = self.command_builder(self.target.address, self.parameter)
            timeout = self.timeout_for_parameter(self.parameter)
        except ValueError as error:
            processes.message = str(error)
            self.phase = "result"
            return
        label = f"{self.operation_label} {self.target.address}"
        self.phase = (
            "running"
            if processes.start_command(label, command, timeout)
            else "result"
        )

    def _draw_settings(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Draw selectable settings and expose the current parameter value."""
        values = (self.target.address, str(self.parameter), "", "", "")
        for index, label in enumerate(self.rows):
            row = pygame.Rect(28, 118 + index * 54, 584, 46)
            selected = index == self.selected
            pygame.draw.rect(surface, theme.ORANGE if selected else theme.BLACK, row, border_radius=4)
            color = theme.BLACK if selected else theme.ORANGE
            surface.blit(
                font.render(f"{label}  {values[index]}".rstrip()[:31], True, color),
                (row.x + 12, row.y + 12),
            )

    def _draw_confirmation(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Show target and selected parameter before requiring explicit approval."""
        lines = (
            f"Destino: {self.target.address}",
            f"{self.parameter_label}: {self.parameter}",
            "Solo equipos propios o autorizados.",
            "A: ejecutar    B: cancelar",
        )
        for index, line in enumerate(lines):
            color = theme.AMBER if index == len(lines) - 1 else theme.WHITE
            surface.blit(font.render(line[:40], True, color), (30, 134 + index * 50))

    def _draw_result(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        processes: ProcessManager,
    ) -> None:
        """Show bounded process status and captured output in the result view."""
        surface.blit(font.render(processes.message[:40], True, theme.AMBER), (30, 124))
        for index, line in enumerate(processes.output.splitlines()[-7:]):
            surface.blit(font.render(line[:40], True, theme.WHITE), (30, 166 + index * 30))
