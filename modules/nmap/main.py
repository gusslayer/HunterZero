"""Validate IPv4 targets and build conservative Nmap commands."""

# Este archivo solo genera argumentos: la ejecución pasa por ProcessManager.
import ipaddress


PORT_COUNTS = (20, 50, 100)


def validate_target(target: str) -> str:
    """Return a normalized IPv4 address or raise a clear validation error."""
    try:
        address = ipaddress.ip_address(target)
    except ValueError as error:
        raise ValueError("Ingresa una dirección IPv4 válida.") from error
    if not isinstance(address, ipaddress.IPv4Address):
        raise ValueError("Solo se permiten direcciones IPv4.")
    return str(address)


def build_nmap_command(target: str, port_count: int = 20) -> list[str]:
    """Build a slow, unprivileged TCP-connect scan with NSE vuln scripts."""
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
        "--script",
        "vuln",
        normalized_target,
    ]
