"""Reusable D-pad editor for a manually entered private IPv4 address."""

import ipaddress

import pygame

from core import theme
from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP


PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)


class PrivateIPv4Editor:
    """Edit one IPv4 octet at a time without requiring a keyboard."""

    def __init__(self, address: str = "192.168.1.1") -> None:
        """Initialize the current private address and selection backup."""
        self.octets = [int(octet) for octet in address.split(".")]
        self._saved_octets = self.octets.copy()
        self.selected_octet = 0

    @property
    def address(self) -> str:
        """Return the currently edited address in dotted-decimal notation."""
        return ".".join(str(octet) for octet in self.octets)

    @property
    def is_private(self) -> bool:
        """Check that the edited address belongs to an RFC1918 network."""
        address = ipaddress.ip_address(self.address)
        return any(address in network for network in PRIVATE_NETWORKS)

    def begin(self) -> None:
        """Save the current address so the user can cancel editing."""
        self._saved_octets = self.octets.copy()

    def handle(self, action) -> str | None:
        """Apply one D-pad/button action and return save or cancel when finished."""
        if action == LEFT:
            self.selected_octet = (self.selected_octet - 1) % 4
        elif action == RIGHT:
            self.selected_octet = (self.selected_octet + 1) % 4
        elif action == UP:
            self.octets[self.selected_octet] = (self.octets[self.selected_octet] + 1) % 256
        elif action == DOWN:
            self.octets[self.selected_octet] = (self.octets[self.selected_octet] - 1) % 256
        elif action == OPEN:
            if self.is_private:
                self._saved_octets = self.octets.copy()
                return "saved"
        elif action == BACK:
            self.octets = self._saved_octets.copy()
            return "cancelled"
        return None

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        """Draw four selectable IP octets and instructions for the D-pad."""
        pygame.draw.rect(surface, theme.BLACK, (0, 55, theme.WIDTH, 370))
        surface.blit(font.render("EDITAR IP PRIVADA", True, theme.ORANGE), (30, 95))
        x = 70
        for index, octet in enumerate(self.octets):
            color = theme.AMBER if index == self.selected_octet else theme.ORANGE
            surface.blit(font.render(f"{octet:03d}", True, color), (x, 180))
            if index < 3:
                surface.blit(font.render(".", True, theme.ORANGE), (x + 42, 180))
            x += 125
        hint = "A: guardar" if self.is_private else "Solo se acepta IP privada RFC1918"
        surface.blit(small_font.render(hint, True, theme.WHITE), (30, 275))
        surface.blit(
            small_font.render("UP/DOWN: valor  LEFT/RIGHT: octeto", True, theme.WHITE),
            (30, 310),
        )
