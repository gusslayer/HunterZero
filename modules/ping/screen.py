"""Ping-specific parameters and guidance for the shared tool-screen layout."""

# Mantiene toda la configuración visual y de ayuda dentro del módulo Ping.
from core.ui.parameterized_tool_screen import ParameterizedToolScreen
from modules.ping.main import PACKET_COUNTS, build_ping_command


class PingScreen(ParameterizedToolScreen):
    """Configure and run manually addressed ICMP Echo requests."""

    def __init__(self) -> None:
        """Set Ping's packet-count range, timeout, and in-app instructions."""
        super().__init__(
            title="PING MANUAL",
            parameter_label="PAQUETES ICMP",
            parameter_values=PACKET_COUNTS,
            initial_parameter=2,
            operation_label="ENVIAR PING",
            help_sections=(
                (
                    "CONFIGURAR",
                    (
                        "Selecciona IP DESTINO y edita los octetos con el D-pad.",
                        "En PAQUETES ICMP usa izquierda/derecha para elegir de 1 a 4.",
                    ),
                ),
                (
                    "EJECUTAR",
                    (
                        "Selecciona ENVIAR PING y confirma con A; B cancela.",
                        "Solo se admiten direcciones IPv4 privadas RFC1918.",
                    ),
                ),
            ),
            command_builder=build_ping_command,
            timeout_seconds=lambda count: 3 + count * 2,
        )
