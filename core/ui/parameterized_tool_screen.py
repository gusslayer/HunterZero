"""Reusable settings, confirmation, help, and result flow for one tool module."""

from collections.abc import Callable

import pygame

from core import theme
from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP
from core.process_manager import ProcessManager
from core.system_stats import SystemStats
from core.ui.help_view import draw_help_view
from core.ui.scroll import ScrollState
from core.ui.target_editor import IPv4Editor
from core.ui.text_cache import render_cached
from core.ui.widgets import draw_frame, draw_row, plain_text, wrap_text


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
        command_builder: Callable[[str, int, str | None], list[str]],
        timeout_seconds: Callable[[int], int],
        *,
        option_label: str = "",
        option_values: tuple[str, ...] = (),
        initial_option: int = 0,
    ) -> None:
        """Initialize a tool screen from the module's validated options and help."""
        if not parameter_values or initial_parameter not in parameter_values:
            raise ValueError("El parámetro inicial debe pertenecer a sus opciones permitidas.")
        if option_values and not (0 <= initial_option < len(option_values)):
            raise ValueError("La opción inicial debe pertenecer a sus opciones permitidas.")
        self.title = title
        self.parameter_label = parameter_label
        self.parameter_values = parameter_values
        self.parameter = initial_parameter
        self.operation_label = operation_label
        self.help_sections = help_sections
        self.command_builder = command_builder
        self.timeout_for_parameter = timeout_seconds
        self.option_label = option_label
        self.option_values = option_values
        self.option = initial_option
        self.target = IPv4Editor()
        self.phase = "settings"
        self.selected = 0
        self.help_scroll = ScrollState()
        if option_values:
            self.rows = ("IP DESTINO", parameter_label, operation_label, option_label, "AYUDA", "VOLVER")
        else:
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
            if action == UP:
                self.help_scroll.move(-1)
            elif action == DOWN:
                self.help_scroll.move(1)
            elif action == OPEN:
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
            self.target.draw(surface, body_font, body_font, small_font)
            return
        if self.phase == "help":
            total, capacity = draw_help_view(
                surface,
                title_font,
                body_font,
                small_font,
                f"AYUDA {self.title}",
                self.help_sections,
                self.help_scroll.offset,
            )
            self.help_scroll.update(total, capacity)
            return
        pygame.draw.rect(surface, theme.BG_COLOR, (0, 28, theme.WIDTH, 184))
        if self.phase == "settings":
            self._draw_settings(surface, body_font)
            self._draw_settings_tip(surface, small_font)
        elif self.phase == "confirm":
            self._draw_confirmation(surface, small_font)
        elif self.phase == "running":
            label = plain_text(f"{self.operation_label} EN CURSO")
            surface.blit(render_cached(body_font, label, theme.TEXT_COLOR), (16, 38))
            surface.blit(
                render_cached(small_font, f"OBJETIVO: {self.target.address}", theme.ACCENT_COLOR),
                (16, 58),
            )
        else:
            self._draw_result(surface, small_font, processes)

    def footer_hints(self) -> list[tuple[str, int]]:
        """Return button labels for the current tool screen state."""
        if self.phase == "edit_target":
            return [("UP/DOWN DIGITO", 8), ("LEFT/RIGHT IP", 126), ("A GUARDAR", 234)]
        if self.phase == "confirm":
            return [("A CONFIRMAR", 12), ("B CANCELAR", 168)]
        if self.phase == "running":
            return [("B CANCELAR", 12)]
        if self.phase == "help":
            return [("ARR/ABA TEXTO", 8), ("A VOLVER", 168), ("B SALIR", 240)]
        if self.phase == "result":
            return [("A OPCIONES", 12), ("B VOLVER", 168)]
        return [("UP/DOWN MOVER", 8), ("IZQ/DER AJUSTAR", 118), ("A ABRIR", 250)]

    def _handle_settings(self, action) -> bool:
        """Navigate target, parameter, option, operation, help, and exit rows."""
        if action == UP:
            self.selected = (self.selected - 1) % len(self.rows)
        elif action == DOWN:
            self.selected = (self.selected + 1) % len(self.rows)
        elif action in (LEFT, RIGHT) and self.selected == 1:
            step = 1 if action == RIGHT else -1
            index = self.parameter_values.index(self.parameter)
            self.parameter = self.parameter_values[(index + step) % len(self.parameter_values)]
        elif action in (LEFT, RIGHT) and self.option_values and self.selected == 3:
            step = 1 if action == RIGHT else -1
            self.option = (self.option + step) % len(self.option_values)
        elif action == OPEN:
            if self.selected == 0:
                self.target.begin()
                self.phase = "edit_target"
            elif self.selected == 2:
                self.phase = "confirm"
            elif self.selected == self._help_row():
                self.phase = "help"
            elif self.selected == self._back_row():
                return True
        elif action == BACK:
            return True
        return False

    def _option_value(self) -> str | None:
        """Return the selected extra option value, or None when there is no option row."""
        if not self.option_values:
            return None
        return self.option_values[self.option]

    def _help_row(self) -> int:
        """Return the help row index for the current rows layout."""
        return len(self.rows) - 2

    def _back_row(self) -> int:
        """Return the exit row index for the current rows layout."""
        return len(self.rows) - 1

    def _start_command(self, processes: ProcessManager) -> None:
        """Build the module-provided safe argv and start it through the allowlist."""
        try:
            command = self.command_builder(self.target.address, self.parameter, self._option_value())
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
        """Draw selectable settings and expose the current parameter and option."""
        values = [self.target.address, str(self.parameter)]
        if self.option_values:
            values.append(self._option_value())
        values.extend(("",) * (len(self.rows) - len(values)))
        for index, label in enumerate(self.rows):
            row = pygame.Rect(12, 32 + index * 19, 296, 17)
            draw_row(surface, row, label, values[index], index == self.selected, font)

    def _draw_settings_tip(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Fill the lower panel with a short, module-specific operating tip."""
        draw_frame(surface, pygame.Rect(10, 150, 300, 59), theme.GRID_COLOR, theme.PANEL_COLOR)
        surface.blit(render_cached(font, "AYUDA RAPIDA", theme.ACCENT_COLOR), (16, 154))
        tip = self.help_sections[0][1][0] if self.help_sections else ""
        for line_index, line in enumerate(wrap_text(tip, 34)[:2]):
            surface.blit(render_cached(font, line, theme.TEXT_COLOR), (16, 165 + line_index * 11))

    def _draw_confirmation(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Show target and selected parameter before requiring explicit approval."""
        lines = [
            f"Destino: {self.target.address}",
            f"{self.parameter_label}: {self.parameter}",
        ]
        if self.option_values:
            lines.append(f"{self.option_label}: {self._option_value()}")
        lines.extend(
            (
                "Solo equipos propios o autorizados.",
                "A: ejecutar    B: cancelar",
            )
        )
        for index, line in enumerate(lines):
            color = theme.ACCENT_COLOR if index == len(lines) - 1 else theme.TEXT_COLOR
            surface.blit(
                render_cached(font, plain_text(line)[:36], color), (16, 36 + index * 16)
            )

    def _draw_result(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        processes: ProcessManager,
    ) -> None:
        """Show bounded process status and captured output in the result view."""
        surface.blit(
            render_cached(font, plain_text(processes.message)[:36], theme.ACCENT_COLOR), (16, 62)
        )
        for index, line in enumerate(processes.output.splitlines()[-6:]):
            surface.blit(
                render_cached(font, plain_text(line)[:36], theme.TEXT_COLOR), (16, 54 + index * 14)
            )
