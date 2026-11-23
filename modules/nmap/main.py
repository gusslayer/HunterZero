"""Validate private IPv4 targets and build conservative Nmap commands."""

import ipaddress


PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)
PORT_COUNTS = (20, 50, 100)


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


def build_nmap_command(target: str, port_count: int = 20) -> list[str]:
    """Build a slow, unprivileged TCP-connect scan limited to common ports."""
    normalized_target = validate_target(target)
    if port_count not in PORT_COUNTS:
        raise ValueError(f"Los puertos deben ser uno de {PORT_COUNTS}.")
    return [
        "nmap",
        "-n",
        "-Pn",
        "-sT",
        "-T2",
        "--top-ports",
        str(port_count),
        "--open",
        "--host-timeout",
        "90s",
        normalized_target,
    ]
