"""Validate IPv4 targets and build bounded Linux ping commands."""

# Este archivo solo genera argumentos: la ejecución pasa por ProcessManager.
import ipaddress


PACKET_COUNTS = (1, 2, 3, 4)


def validate_target(target: str) -> str:
    """Return a normalized IPv4 address or raise a clear validation error."""
    try:
        address = ipaddress.ip_address(target)
    except ValueError as error:
        raise ValueError("Ingresa una dirección IPv4 válida.") from error
    if not isinstance(address, ipaddress.IPv4Address):
        raise ValueError("Solo se permiten direcciones IPv4.")
    return str(address)


def build_ping_command(target: str, packet_count: int = 2, script: str | None = None) -> list[str]:
    """Build a bounded ping command; the script option is unused by this module."""
    del script
    address = validate_target(target)
    if packet_count not in PACKET_COUNTS:
        raise ValueError(f"El número de paquetes debe ser uno de {PACKET_COUNTS}.")
    return ["ping", "-n", "-c", str(packet_count), "-W", "2", address]
