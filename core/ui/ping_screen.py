"""Standalone gamepad UI for manually configuring and running Ping."""

import pygame

from core import theme
from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP
from core.process_manager import ProcessManager
from core.ui.target_editor import PrivateIPv4Editor
from modules.ping.main import PACKET_COUNTS, build_ping_command


class PingScreen:
    """Control target entry, packet count, confirmation, and ping results."""

    ROWS = ("IP DESTINO", "PAQUETES", "ENVIAR PING", "VOLVER")

    def __init__(self) -> None:
        """Set a private-network default and initialize Ping screen state."""
        self.target = PrivateIPv4Editor()
        self.phase = "settings"
        self.selected = 0
        self.packet_count = 2

    def handle(self, action, processes: ProcessManager) -> bool:
        """Handle D-pad and A/B button actions; return true to leave this module."""
        if self.phase == "edit_target":
            result = self.target.handle(action)
            if result in ("saved", "cancelled"):
                self.phase = "settings"
            return False
        if self.phase == "confirm":
            if action == BACK:
                self.phase = "settings"
            elif action == OPEN:
                self._start_ping(processes)
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
        return self._handle_settings(action)

    def sync(self, processes: ProcessManager) -> None:
        """Move to the result view when the current Ping process finishes."""
        if self.phase == "running" and processes.running is None:
            self.phase = "result"

    def draw(self, surface, title_font, body_font, small_font, processes) -> None:
        """Render the independent Ping settings, IP editor, or result screen."""
        if self.phase == "edit_target":
            self.target.draw(surface, body_font, small_font)
            return
        surface.fill(theme.BLACK)
        surface.blit(title_font.render("PING MANUAL", True, theme.ORANGE), (30, 75))
        if self.phase == "settings":
            self._draw_settings(surface, body_font)
        elif self.phase == "confirm":
            self._draw_confirmation(surface, small_font)
        elif self.phase == "running":
            surface.blit(body_font.render("Enviando paquetes...", True, theme.WHITE), (30, 140))
            surface.blit(small_font.render(f"Destino: {self.target.address}", True, theme.ORANGE), (30, 195))
        else:
            self._draw_result(surface, small_font, processes)

    def footer_hints(self):
        """Return button labels for the current Ping view."""
        if self.phase == "edit_target":
            return [("UP/DOWN VALOR", 24), ("LEFT/RIGHT IP", 260), ("A GUARDAR", 485)]
        if self.phase == "confirm":
            return [("A ENVIAR", 24), ("B CANCELAR", 335)]
        if self.phase == "running":
            return [("B CANCELAR PING", 24)]
        if self.phase == "result":
            return [("A OPCIONES", 24), ("B MENU", 335)]
        return [("UP/DOWN MOVER", 24), ("LEFT/RIGHT AJUSTAR", 230), ("A SELECCIONAR", 485)]

    def _handle_settings(self, action) -> bool:
        """Navigate Ping options, edit packet count, or start confirmation."""
        if action == UP:
            self.selected = (self.selected - 1) % len(self.ROWS)
        elif action == DOWN:
            self.selected = (self.selected + 1) % len(self.ROWS)
        elif action in (LEFT, RIGHT) and self.selected == 1:
            step = 1 if action == RIGHT else -1
            current_index = PACKET_COUNTS.index(self.packet_count)
            self.packet_count = PACKET_COUNTS[(current_index + step) % len(PACKET_COUNTS)]
        elif action == OPEN:
            if self.selected == 0:
                self.target.begin()
                self.phase = "edit_target"
            elif self.selected == 2:
                self.phase = "confirm"
            elif self.selected == 3:
                return True
        elif action == BACK:
            return True
        return False

    def _start_ping(self, processes: ProcessManager) -> None:
        """Build the safe Ping argv and launch it through the allowlisted runner."""
        try:
            command = build_ping_command(self.target.address, self.packet_count)
        except ValueError as error:
            processes.message = str(error)
            self.phase = "result"
            return
        timeout = 3 + self.packet_count * 2
        self.phase = (
            "running"
            if processes.start_command(f"PING {self.target.address}", command, timeout)
            else "result"
        )

    def _draw_settings(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Draw Ping target, packet count, send, and return rows."""
        values = (self.target.address, str(self.packet_count), "", "")
        for index, label in enumerate(self.ROWS):
            row = pygame.Rect(28, 132 + index * 54, 584, 44)
            selected = index == self.selected
            pygame.draw.rect(surface, theme.ORANGE if selected else theme.BLACK, row, border_radius=4)
            color = theme.BLACK if selected else theme.ORANGE
            surface.blit(font.render(f"{label}  {values[index]}".rstrip(), True, color), (row.x + 12, row.y + 13))

    def _draw_confirmation(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Display the manual Ping target and packet count before authorization."""
        for index, text in enumerate((
            f"Destino privado: {self.target.address}",
            f"Paquetes ICMP: {self.packet_count}",
            "Solo tu red o un equipo autorizado.",
            "A: enviar   B: cancelar",
        )):
            surface.blit(font.render(text, True, theme.AMBER if index == 3 else theme.WHITE), (30, 135 + index * 48))

    def _draw_result(self, surface: pygame.Surface, font: pygame.font.Font, processes) -> None:
        """Show the command status and captured Ping output."""
        surface.blit(font.render(processes.message[:64], True, theme.AMBER), (30, 125))
        for index, line in enumerate(processes.output.splitlines()[-6:]):
            surface.blit(font.render(line[:64], True, theme.WHITE), (30, 170 + index * 32))
