"""Build a safe nslookup argv and extract the resolved addresses from its output."""

import ipaddress

from core.hostname import normalize_hostname


RECORD_TYPES = ("A", "AAAA")
MAX_LOOKUP_TIMEOUT_SECONDS = 20


def build_nslookup_command(hostname: str, record_type: str) -> list[str]:
    """Return a bounded nslookup argv for a validated hostname and record type."""
    target = normalize_hostname(hostname)
    if record_type not in RECORD_TYPES:
        raise ValueError("Tipo de registro no admitido.")
    return ["nslookup", f"-type={record_type}", target]


def parse_addresses(output: str) -> list[str]:
    """Collect unique IP addresses from the answer section of nslookup output."""
    addresses: list[str] = []
    in_answer = False
    for raw_line in output.splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        if lowered.startswith("name:") or "answer:" in lowered:
            in_answer = True
            continue
        if not in_answer or not lowered.startswith("address:"):
            continue
        candidate = line.split(":", 1)[1].strip().split("#", 1)[0]
        try:
            address = str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
        if address not in addresses:
            addresses.append(address)
    return addresses
