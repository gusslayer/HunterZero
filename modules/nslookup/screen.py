"""DNS lookup screen with a gamepad hostname editor and an IP result view."""

import pygame

from core import theme
from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP
from core.ui.help_view import draw_help_view
from core.ui.hostname_editor import HostnameEditor
from core.ui.scroll import ScrollState
from core.ui.text_cache import render_cached
from core.ui.widgets import draw_frame, draw_row, plain_text, wrap_text
from modules.nslookup.main import (
    MAX_LOOKUP_TIMEOUT_SECONDS,
    RECORD_TYPES,
    build_nslookup_command,
    parse_addresses,
)


class NsLookupScreen:
    """Resolve an entered domain name and display the returned IP addresses."""

    def __init__(self) -> None:
        """Start on the settings screen with a valid default hostname."""
        self.title = "NSLOOKUP"
        self.editor = HostnameEditor()
        self.record_type = 0
        self.rows = ("HOST", "TIPO REGISTRO", "CONSULTAR DNS", "AYUDA", "VOLVER")
        self.selected = 0
        self.phase = "settings"
        self.addresses: list[str] = []
        self.help_scroll = ScrollState()

    def handle(self, action, processes) -> bool:
        """Route D-pad actions through editing, confirmation, and result views."""
        if self.phase == "edit_host":
            result = self.editor.handle(action)
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

    def sync(self, processes) -> None:
        """Parse the finished lookup output and switch to the result view."""
        if self.phase == "running" and processes.running is None:
            self.addresses = parse_addresses(processes.output)
            self.phase = "result"

    def draw(
        self,
        surface: pygame.Surface,
        title_font: pygame.font.Font,
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
        processes,
        stats,
    ) -> None:
        """Render the active editor, settings, confirmation, progress, or result view."""
        del stats
        pygame.draw.rect(surface, theme.BG_COLOR, (0, 28, theme.WIDTH, 184))
        if self.phase == "edit_host":
            self.editor.draw(surface, body_font, small_font)
            return
        if self.phase == "help":
            total, capacity = draw_help_view(
                surface,
                title_font,
                body_font,
                small_font,
                f"AYUDA {self.title}",
                (
                    (
                        "CONFIGURAR",
                        (
                            "HOST: izquierda/derecha mueve el cursor.",
                            "Arriba/abajo cambia el caracter; el espacio lo borra.",
                        ),
                    ),
                    (
                        "CONSULTAR",
                        (
                            "TIPO REGISTRO elige A (IPv4) o AAAA (IPv6).",
                            "Confirma con A; B cancela la consulta en curso.",
                        ),
                    ),
                ),
                self.help_scroll.offset,
            )
            self.help_scroll.update(total, capacity)
            return
        if self.phase == "settings":
            self._draw_settings(surface, body_font)
            self._draw_tip(surface, small_font)
        elif self.phase == "confirm":
            self._draw_confirmation(surface, small_font)
        elif self.phase == "running":
            self._draw_running(surface, body_font, small_font)
        else:
            self._draw_result(surface, small_font, processes)

    def footer_hints(self) -> list[tuple[str, int]]:
        """Return button labels for the current lookup screen state."""
        if self.phase == "edit_host":
            return [("UP/DOWN LETRA", 8), ("IZQ/DER CURSOR", 118), ("A GUARDAR", 240)]
        if self.phase == "confirm":
            return [("A CONSULTAR", 8), ("B CANCELAR", 168)]
        if self.phase == "running":
            return [("B CANCELAR", 8)]
        if self.phase == "help":
            return [("ARR/ABA TEXTO", 8), ("A VOLVER", 168), ("B SALIR", 240)]
        if self.phase == "result":
            return [("A OPCIONES", 8), ("B VOLVER", 168)]
        return [("UP/DOWN MOVER", 8), ("IZQ/DER TIPO", 118), ("A ABRIR", 250)]

    def _handle_settings(self, action) -> bool:
        """Navigate host, record type, lookup, help, and exit rows."""
        if action == UP:
            self.selected = (self.selected - 1) % len(self.rows)
        elif action == DOWN:
            self.selected = (self.selected + 1) % len(self.rows)
        elif action in (LEFT, RIGHT) and self.selected == 1:
            step = 1 if action == RIGHT else -1
            self.record_type = (self.record_type + step) % len(RECORD_TYPES)
        elif action == OPEN:
            if self.selected == 0:
                self.editor.begin()
                self.phase = "edit_host"
            elif self.selected == 2:
                self.phase = "confirm"
            elif self.selected == 3:
                self.phase = "help"
            elif self.selected == 4:
                return True
        elif action == BACK:
            return True
        return False

    def _start_command(self, processes) -> None:
        """Build the validated nslookup argv and start it through the allowlist."""
        try:
            command = build_nslookup_command(self.editor.value, RECORD_TYPES[self.record_type])
        except ValueError as error:
            processes.message = str(error)
            self.addresses = []
            self.phase = "result"
            return
        label = f"NSLOOKUP {self.editor.value}"
        started = processes.start_command(label, command, MAX_LOOKUP_TIMEOUT_SECONDS)
        self.phase = "running" if started else "result"

    def _draw_settings(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Draw the editable host, record type, and action rows."""
        values = [self.editor.value, RECORD_TYPES[self.record_type], "", "", ""]
        for index, label in enumerate(self.rows):
            row = pygame.Rect(12, 32 + index * 19, 296, 17)
            draw_row(surface, row, label, values[index], index == self.selected, font)

    def _draw_tip(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Fill the lower panel with a short operating tip."""
        draw_frame(surface, pygame.Rect(10, 150, 300, 59), theme.GRID_COLOR, theme.PANEL_COLOR)
        surface.blit(render_cached(font, "AYUDA RAPIDA", theme.ACCENT_COLOR), (16, 154))
        for index, line in enumerate(wrap_text("ESCRIBE EL DOMINIO Y PULSA A PARA RESOLVER.", 34)):
            surface.blit(render_cached(font, line, theme.TEXT_COLOR), (16, 165 + index * 11))

    def _draw_confirmation(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Show the host and record type before requiring explicit approval."""
        lines = (
            f"HOST: {self.editor.value}",
            f"TIPO: {RECORD_TYPES[self.record_type]}",
            "A: EJECUTAR  B: CANCELAR",
        )
        for index, line in enumerate(lines):
            color = theme.ACCENT_COLOR if index == len(lines) - 1 else theme.TEXT_COLOR
            surface.blit(render_cached(font, plain_text(line)[:34], color), (16, 36 + index * 16))

    def _draw_running(self, surface: pygame.Surface, font, small_font) -> None:
        """Show progress while the bounded DNS query is running."""
        surface.blit(render_cached(font, "CONSULTANDO DNS...", theme.TEXT_COLOR), (16, 38))
        surface.blit(
            render_cached(small_font, f"HOST: {self.editor.value}", theme.ACCENT_COLOR), (16, 60)
        )
        surface.blit(
            render_cached(small_font, f"TIPO: {RECORD_TYPES[self.record_type]}", theme.MUTED_COLOR),
            (16, 77),
        )

    def _draw_result(self, surface: pygame.Surface, font: pygame.font.Font, processes) -> None:
        """Show the parsed IP addresses and the tail of the captured output."""
        surface.blit(
            render_cached(font, plain_text(processes.message)[:34], theme.ACCENT_COLOR), (16, 34)
        )
        if self.addresses:
            surface.blit(render_cached(font, "IP ENCONTRADA", theme.ACCENT_COLOR), (16, 54))
            for index, address in enumerate(self.addresses[:4]):
                surface.blit(render_cached(font, address[:20], theme.TEXT_COLOR), (16, 68 + index * 14))
            output_y = 68 + min(len(self.addresses), 4) * 14 + 6
        else:
            surface.blit(render_cached(font, "SIN IP EN LA RESPUESTA", theme.MUTED_COLOR), (16, 54))
            output_y = 74
        for index, line in enumerate(processes.output.splitlines()[-3:]):
            if output_y + index * 14 > 190:
                break
            surface.blit(
                render_cached(font, plain_text(line)[:34], theme.MUTED_COLOR),
                (16, output_y + index * 14),
            )
