"""Validation shared by the DNS editor and the nslookup command builder."""

import re


MAX_HOSTNAME_LENGTH = 253
MAX_LABEL_LENGTH = 63
_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_HOSTNAME = re.compile(rf"{_LABEL}(?:\.{_LABEL})*")


def normalize_hostname(value: str) -> str:
    """Return a lowercase DNS hostname or raise ValueError when it is invalid."""
    if not isinstance(value, str):
        raise ValueError("El host debe ser texto.")
    candidate = value.strip().lower()
    if not candidate or len(candidate) > MAX_HOSTNAME_LENGTH:
        raise ValueError("El host debe tener entre 1 y 253 caracteres.")
    if not _HOSTNAME.fullmatch(candidate):
        raise ValueError("Host no valido: usa letras, digitos, guiones y puntos.")
    if any(len(label) > MAX_LABEL_LENGTH for label in candidate.split(".")):
        raise ValueError("Cada etiqueta del host puede tener hasta 63 caracteres.")
    return candidate
