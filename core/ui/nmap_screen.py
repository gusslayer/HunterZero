"""Standalone gamepad UI for configuring and running Nmap."""

import pygame

from core import theme
from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP
from core.process_manager import ProcessManager
from core.ui.target_editor import PrivateIPv4Editor
from modules.nmap.main import PORT_COUNTS, build_nmap_command


class NmapScreen:
    """Control Nmap target entry, scan size, confirmation, and results."""

    ROWS = ("IP OBJETIVO", "PUERTOS TCP", "INICIAR NMAP", "VOLVER")

    def __init__(self) -> None:
        """Initialize a private target and a conservative top-20 port scan."""
        self.target = PrivateIPv4Editor()
        self.phase = "settings"
        self.selected = 0
        self.port_count = 20

    def handle(self, action, processes: ProcessManager) -> bool:
        """Handle gamepad commands and return true when the user leaves Nmap."""
        if self.phase == "edit_target":
            result = self.target.handle(action)
            if result in ("saved", "cancelled"):
                self.phase = "settings"
            return False
        if self.phase == "confirm":
            if action == BACK:
                self.phase = "settings"
            elif action == OPEN:
                self._start_scan(processes)
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
        """Move to the result view when the Nmap process exits."""
        if self.phase == "running" and processes.running is None:
            self.phase = "result"

    def draw(self, surface, title_font, body_font, small_font, processes) -> None:
        """Render the independent Nmap options, target editor, or scan results."""
        if self.phase == "edit_target":
            self.target.draw(surface, body_font, small_font)
            return
        surface.fill(theme.BLACK)
        surface.blit(title_font.render("NMAP TCP", True, theme.ORANGE), (30, 75))
        if self.phase == "settings":
            self._draw_settings(surface, body_font)
        elif self.phase == "confirm":
            self._draw_confirmation(surface, small_font)
        elif self.phase == "running":
            surface.blit(body_font.render("Escaneo TCP en curso...", True, theme.WHITE), (30, 140))
            surface.blit(small_font.render(f"Destino: {self.target.address}", True, theme.ORANGE), (30, 195))
        else:
            self._draw_result(surface, small_font, processes)

    def footer_hints(self):
        """Return controls for the active Nmap state."""
        if self.phase == "edit_target":
            return [("UP/DOWN VALOR", 24), ("LEFT/RIGHT IP", 260), ("A GUARDAR", 485)]
        if self.phase == "confirm":
            return [("A ESCANEAR", 24), ("B CANCELAR", 335)]
        if self.phase == "running":
            return [("B CANCELAR NMAP", 24)]
        if self.phase == "result":
            return [("A OPCIONES", 24), ("B MENU", 335)]
        return [("UP/DOWN MOVER", 24), ("LEFT/RIGHT AJUSTAR", 230), ("A SELECCIONAR", 485)]

    def _handle_settings(self, action) -> bool:
        """Navigate Nmap options, adjust common port count, and request confirmation."""
        if action == UP:
            self.selected = (self.selected - 1) % len(self.ROWS)
        elif action == DOWN:
            self.selected = (self.selected + 1) % len(self.ROWS)
        elif action in (LEFT, RIGHT) and self.selected == 1:
            step = 1 if action == RIGHT else -1
            current_index = PORT_COUNTS.index(self.port_count)
            self.port_count = PORT_COUNTS[(current_index + step) % len(PORT_COUNTS)]
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

    def _start_scan(self, processes: ProcessManager) -> None:
        """Build the fixed safe TCP-connect command and start it in the background."""
        try:
            command = build_nmap_command(self.target.address, self.port_count)
        except ValueError as error:
            processes.message = str(error)
            self.phase = "result"
            return
        self.phase = (
            "running"
            if processes.start_command(f"NMAP {self.target.address}", command, 100)
            else "result"
        )

    def _draw_settings(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Draw target address, top-port count, scan action, and return rows."""
        values = (self.target.address, str(self.port_count), "", "")
        for index, label in enumerate(self.ROWS):
            row = pygame.Rect(28, 132 + index * 54, 584, 44)
            selected = index == self.selected
            pygame.draw.rect(surface, theme.ORANGE if selected else theme.BLACK, row, border_radius=4)
            color = theme.BLACK if selected else theme.ORANGE
            surface.blit(font.render(f"{label}  {values[index]}".rstrip(), True, color), (row.x + 12, row.y + 13))

    def _draw_confirmation(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Show Nmap scope and authorization warning before the user starts."""
        for index, text in enumerate((
            f"Destino privado: {self.target.address}",
            f"TCP Connect, top {self.port_count} puertos, lento.",
            "Solo equipos propios o autorizados.",
            "A: escanear   B: cancelar",
        )):
            surface.blit(font.render(text, True, theme.AMBER if index == 3 else theme.WHITE), (30, 135 + index * 48))

    def _draw_result(self, surface: pygame.Surface, font: pygame.font.Font, processes) -> None:
        """Show Nmap completion status and a bounded set of output lines."""
        surface.blit(font.render(processes.message[:64], True, theme.AMBER), (30, 125))
        for index, line in enumerate(processes.output.splitlines()[-6:]):
            surface.blit(font.render(line[:64], True, theme.WHITE), (30, 170 + index * 32))
