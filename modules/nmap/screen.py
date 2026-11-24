"""Nmap-specific parameters and guidance for the shared tool-screen layout."""

# Mantiene toda la configuración visual y de ayuda dentro del módulo Nmap.
from core.process_manager import MAX_COMMAND_TIMEOUT_SECONDS
from core.ui.parameterized_tool_screen import ParameterizedToolScreen
from modules.nmap.main import PORT_COUNTS, SCRIPT_OPTIONS, build_nmap_command


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
            option_label="SCRIPTS NSE",
            option_values=SCRIPT_OPTIONS,
            initial_option=0,
            help_sections=(
                (
                    "CONFIGURAR",
                    (
                        "IP DESTINO: D-pad mueve entre digitos y cambia su valor.",
                        "En PUERTOS TCP elige 20, 50 o 100 puertos comunes.",
                    ),
                ),
                (
                    "EJECUTAR",
                    (
                        "Selecciona INICIAR NMAP y confirma con A; B cancela.",
                        "TCP connect lento y scripts NSE vuln; usa solo equipos autorizados.",
                    ),
                ),
            ),
            command_builder=build_nmap_command,
            timeout_seconds=lambda _count: MAX_COMMAND_TIMEOUT_SECONDS,
        )
