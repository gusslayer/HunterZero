"""Summarize running processes with a compact, top-style snapshot."""

import os
from dataclasses import dataclass
from pathlib import Path

PROC_ROOT = Path("/proc")

try:
    CLK_TCK = float(os.sysconf("SC_CLK_TCK"))
except (AttributeError, OSError, ValueError):
    CLK_TCK = 100.0

try:
    PAGE_SIZE = float(os.sysconf("SC_PAGE_SIZE"))
except (AttributeError, OSError, ValueError):
    PAGE_SIZE = 4096.0


@dataclass(frozen=True)
class ProcessSnapshot:
    """One summarized running process row for the process-monitor screen."""

    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    elapsed: str


def snapshot_processes(limit: int = 10) -> tuple[ProcessSnapshot, ...]:
    """Return up to `limit` processes sorted by CPU use, highest first."""
    uptime = _read_uptime()
    total_memory = _read_total_memory()
    snapshots = []
    for entry in _process_entries():
        snapshot = _read_process(entry, uptime, total_memory)
        if snapshot is not None:
            snapshots.append(snapshot)
    snapshots.sort(key=lambda snap: (-snap.cpu_percent, snap.pid))
    return tuple(snapshots[:limit])


def _read_uptime() -> float:
    """Return the system uptime in seconds from procfs."""
    try:
        with (PROC_ROOT / "uptime").open(encoding="utf-8") as file:
            return float(file.read().split()[0])
    except (OSError, ValueError, IndexError):
        return 0.0


def _read_total_memory() -> float:
    """Return the total system memory in bytes from /proc/meminfo."""
    try:
        for line in (PROC_ROOT / "meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return float(line.split()[1]) * 1024.0
    except (OSError, ValueError, IndexError):
        pass
    return 0.0


def _process_entries() -> list[Path]:
    """Return the numeric PID directories under /proc, sorted by name."""
    try:
        entries = [entry for entry in PROC_ROOT.iterdir() if entry.name.isdigit()]
    except OSError:
        return []
    return sorted(entries, key=lambda entry: int(entry.name))


def _read_process(entry: Path, uptime: float, total_memory: float) -> ProcessSnapshot | None:
    """Read one /proc/<pid>/stat and turn it into a summarized snapshot."""
    try:
        raw = (entry / "stat").read_text(encoding="utf-8")
    except OSError:
        return None
    open_index = raw.find("(")
    close_index = raw.rfind(")")
    if open_index < 0 or close_index <= open_index:
        return None
    try:
        fields = raw[close_index + 1:].split()
        utime = float(fields[11])
        stime = float(fields[12])
        starttime = float(fields[19])
        rss_pages = float(fields[21])
    except (IndexError, ValueError):
        return None
    pid = int(entry.name)
    cpu_seconds = (utime + stime) / CLK_TCK
    cpu_percent = cpu_seconds / uptime * 100 if uptime > 0 else 0.0
    memory_percent = rss_pages * PAGE_SIZE / total_memory * 100 if total_memory > 0 else 0.0
    elapsed = max(0.0, uptime - starttime / CLK_TCK)
    return ProcessSnapshot(
        pid=pid,
        name=raw[open_index + 1:close_index] or f"pid{pid}",
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        elapsed=_format_elapsed(elapsed),
    )


def _format_elapsed(seconds: float) -> str:
    """Format an elapsed time in seconds as a compact human-readable string."""
    total = max(0, int(seconds))
    if total < 60:
        return f"{total}s"
    minutes, remainder = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}m {remainder:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"
