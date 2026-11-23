"""Validate private IPv4 targets and build bounded Linux ping commands."""

import ipaddress


PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)
PACKET_COUNTS = (1, 2, 3, 4)


def validate_target(target: str) -> str:
    """Return a normalized private IPv4 address or raise a clear validation error."""
    try:
        address = ipaddress.ip_address(target)
    except ValueError as error:
        raise ValueError("Ingresa una dirección IPv4 privada válida.") from error
    if not isinstance(address, ipaddress.IPv4Address) or not any(
        address in network for network in PRIVATE_NETWORKS
    ):
        raise ValueError("Solo se permiten direcciones privadas de la red local.")
    return str(address)


def build_ping_command(target: str, packet_count: int = 2) -> list[str]:
    """Build a bounded ping command for one manually entered private IPv4 address."""
    normalized_target = validate_target(target)
    if packet_count not in PACKET_COUNTS:
        raise ValueError(f"El número de paquetes debe ser uno de {PACKET_COUNTS}.")
    return ["ping", "-n", "-c", str(packet_count), "-W", "2", normalized_target]
