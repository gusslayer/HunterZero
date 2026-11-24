"""Nmap-specific parameters and guidance for the shared tool-screen layout."""

# Mantiene toda la configuración visual y de ayuda dentro del módulo Nmap.
from core.process_manager import MAX_COMMAND_TIMEOUT_SECONDS
from core.ui.parameterized_tool_screen import ParameterizedToolScreen
from modules.nmap.main import PORT_COUNTS, build_nmap_command


class NmapScreen(ParameterizedToolScreen):
    """Configure and run a conservative TCP-connect scan with NSE vulnerability scripts."""

    def __init__(self) -> None:
        """Set Nmap's port-count range, timeout, and in-app instructions."""
        super().__init__(
            title="NMAP TCP",
            parameter_label="PUERTOS TCP",
            parameter_values=PORT_COUNTS,
            initial_parameter=20,
            operation_label="INICIAR NMAP",
            help_sections=(
                (
                    "CONFIGURAR",
                    (
                        "Selecciona IP DESTINO y edita los octetos con el D-pad.",
                        "En PUERTOS TCP elige 20, 50 o 100 puertos comunes.",
                    ),
                ),
                (
                    "EJECUTAR",
                    (
                        "Selecciona INICIAR NMAP y confirma con A; B cancela.",
                        "Usa TCP connect lento y scripts NSE de la categoría vuln; solo IPv4 privadas autorizadas.",
                    ),
                ),
            ),
            command_builder=build_nmap_command,
            timeout_seconds=lambda _count: MAX_COMMAND_TIMEOUT_SECONDS,
        )
