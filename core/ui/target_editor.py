"""D-pad editor that can enter any IPv4 address one digit at a time."""

import ipaddress

import pygame

from core import theme
from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP


class IPv4Editor:
    """Edit four octets by moving between their three digits with the D-pad."""

    def __init__(self, address: str = "192.168.1.1") -> None:
        """Initialize the current address, digit cursor, and cancellation backup."""
        try:
            parsed = ipaddress.IPv4Address(address)
        except ValueError:
            parsed = ipaddress.IPv4Address("192.168.1.1")
        self.octets = [int(part) for part in str(parsed).split(".")]
        self._saved_octets = self.octets.copy()
        self.selected_octet = 0
        self.selected_digit = 0
        self.notice = ""

    @property
    def address(self) -> str:
        """Return the currently edited address in dotted-decimal notation."""
        return ".".join(str(octet) for octet in self.octets)

    @property
    def is_valid(self) -> bool:
        """Check that every octet is inside the 0-255 IPv4 range."""
        return all(0 <= octet <= 255 for octet in self.octets)

    def begin(self) -> None:
        """Save the current address so the user can cancel editing."""
        self._saved_octets = self.octets.copy()
        self.notice = ""

    def handle(self, action) -> str | None:
        """Apply one D-pad/button action and return save or cancel when finished."""
        if action == LEFT:
            if self.selected_digit > 0:
                self.selected_digit -= 1
            else:
                self.selected_octet = (self.selected_octet - 1) % 4
                self.selected_digit = 2
            self.notice = ""
        elif action == RIGHT:
            if self.selected_digit < 2:
                self.selected_digit += 1
            else:
                self.selected_octet = (self.selected_octet + 1) % 4
                self.selected_digit = 0
            self.notice = ""
        elif action in (UP, DOWN):
            self._change_digit(1 if action == UP else -1)
        elif action == OPEN:
            if self.is_valid:
                self._saved_octets = self.octets.copy()
                return "saved"
            self.notice = "OCTETO INVALIDO: DEBE SER 0-255"
        elif action == BACK:
            self.octets = self._saved_octets.copy()
            self.notice = ""
            return "cancelled"
        return None

    def _change_digit(self, step: int) -> None:
        """Increment or decrement the selected digit, wrapping from 9 to 0."""
        digits = list(f"{self.octets[self.selected_octet]:03d}")
        index = self.selected_digit
        digits[index] = str((int(digits[index]) + step) % 10)
        self.octets[self.selected_octet] = int("".join(digits))
        self.notice = "" if self.is_valid else "OCTETO INVALIDO: DEBE SER 0-255"

    def draw(
        self,
        surface: pygame.Surface,
        octet_font: pygame.font.Font,
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
    ) -> None:
        """Draw four editable octets with the active digit highlighted."""
        pygame.draw.rect(surface, theme.BLACK, (0, 55, theme.WIDTH, 370))
        surface.blit(body_font.render("EDITAR IP", True, theme.ORANGE), (30, 88))
        for index in range(4):
            group_x = 36 + index * 146
            label = f"OCTETO {index + 1}"
            color = theme.AMBER if index == self.selected_octet else theme.DIM_ORANGE
            surface.blit(small_font.render(label, True, color), (group_x, 136))
            digits = f"{self.octets[index]:03d}"
            for digit_index, digit in enumerate(digits):
                digit_x = group_x + digit_index * 24
                selected = index == self.selected_octet and digit_index == self.selected_digit
                if selected:
                    pygame.draw.rect(surface, theme.ORANGE, (digit_x - 2, 168, 26, 31))
                surface.blit(
                    octet_font.render(digit, True, theme.BLACK if selected else theme.ORANGE),
                    (digit_x, 170),
                )
            if index < 3:
                surface.blit(octet_font.render(".", True, theme.AMBER), (group_x + 76, 170))
        surface.blit(body_font.render(f"IP: {self.address}", True, theme.WHITE), (30, 250))
        lines = (
            f"OCTETO {self.selected_octet + 1}/4   DIGITO {self.selected_digit + 1}/3",
            "UP/DOWN digito   LEFT/RIGHT mover",
            "A guardar   B cancelar   0-255",
        )
        for row, line in enumerate(lines):
            surface.blit(small_font.render(line, True, theme.WHITE), (30, 292 + row * 28))
        if self.notice:
            surface.blit(small_font.render(self.notice, True, theme.AMBER), (30, 382))


# Nombre anterior conservado para no romper importaciones existentes.
PrivateIPv4Editor = IPv4Editor
