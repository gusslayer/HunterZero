"""Offline tests for the BLEeding module: validation, jobs, and GUI navigation."""

import time
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame
import yaml

from core import theme
from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP
from core.system_stats import StatsReader
from modules.bleeding.engine import (
    KIND_DEAUTH,
    KIND_ENUM,
    KIND_SCAN,
    MAC_PATTERN,
    BluetoothEngine,
    JobState,
    normalize_target,
    random_mac,
    validate_deauth_parameters,
)
from modules.bleeding.screen import BleedingScreen


ROOT = Path(__file__).resolve().parents[1]
ADDRESS = "FC:FC:48:AA:BB:CC"


class FakeProcesses:
    """Capture status messages without launching any process."""

    def __init__(self) -> None:
        """Start with an empty HUD message."""
        self.message = ""


class FakeEngine:
    """Record requested jobs and expose a controlled job snapshot."""

    def __init__(self) -> None:
        """Advertise both stacks and start with no active job."""
        self.ble_available = True
        self.bredr_available = True
        self.bredr_discovery_available = True
        self.state = JobState()
        self.calls = []
        self.cancelled = 0

    def snapshot(self) -> JobState:
        """Return the current fake job state."""
        return self.state

    def start_scan(self, mode: str) -> None:
        """Record a scan request as a running fake job."""
        self.calls.append(("scan", mode))
        self.state = JobState(kind=KIND_SCAN, running=True, message="Escaneando")

    def start_enumeration(self, address: str, mode: str) -> None:
        """Record an enumeration request as a running fake job."""
        self.calls.append(("enum", address, mode))
        self.state = JobState(kind=KIND_ENUM, running=True, message="Enumerando")

    def start_deauth(self, address: str, mode: str, protocol: str, port: int, packet: int, workers: int, duration: int) -> None:
        """Record a validated DeAuth request as a running fake job."""
        self.calls.append(("deauth", address, mode, protocol, port, packet, workers, duration))
        self.state = JobState(kind=KIND_DEAUTH, running=True, message="Atacando")

    def cancel(self) -> None:
        """Count cancellation requests and clear the fake job."""
        self.cancelled += 1
        self.state = JobState(message="Cancelado")


class FakeCharacteristic:
    """Expose one writable GATT characteristic to the engine."""

    def __init__(self) -> None:
        """Use a short UUID and write permission by default."""
        self.uuid = "0000-TEST-ABCD"
        self.properties = ["write"]
        self.description = "Escritura"


class FakeService:
    """Expose one GATT service with a single characteristic."""

    def __init__(self) -> None:
        """Populate the service with a fake writable characteristic."""
        self.uuid = "0000-SVC-0001"
        self.description = "Servicio de prueba"
        self.characteristics = [FakeCharacteristic()]


class FakeClient:
    """Async context manager mimicking a Bleak BLE client."""

    writes = []

    def __init__(self, address: str, timeout: float = 10.0) -> None:
        """Remember the target address and the offered services."""
        del timeout
        self.address = address
        self.services = [FakeService()]
        self.is_connected = False

    async def __aenter__(self):
        """Simulate a successful connection."""
        self.is_connected = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Simulate a clean disconnection."""
        del exc_type, exc_value, traceback
        self.is_connected = False

    async def write_gatt_char(self, uuid: str, payload: bytes, response: bool = False) -> None:
        """Record a GATT write and its response flag without touching hardware."""
        FakeClient.writes.append((uuid, payload, response))


class LimitedCharacteristic:
    """Describe a GATT characteristic with a specific write permission."""

    def __init__(self, uuid: str, properties: list[str], maximum: int | None) -> None:
        """Store the UUID, properties, and optional write size limit."""
        self.uuid = uuid
        self.properties = properties
        self.max_write_without_response_size = maximum


class MtuClient(FakeClient):
    """Bleak client with one write-without-response and one request-only char."""

    def __init__(self, address: str, timeout: float = 10.0) -> None:
        """Replace the default service with two realistic characteristics."""
        super().__init__(address, timeout)
        service = FakeService()
        service.characteristics = [
            LimitedCharacteristic("0000-NORESP-0001", ["write-without-response"], 20),
            LimitedCharacteristic("0000-RESP-0002", ["write"], None),
        ]
        self.services = [service]


class FakeAdvertisement:
    """Provide a received signal strength for a fake BLE device."""

    rssi = -60


class FakeDevice:
    """Provide the address and name of a fake BLE device."""

    address = ADDRESS.lower()
    name = "Prueba"


class FakeScanner:
    """Provide a deterministic BLE advertisement dictionary."""

    @staticmethod
    async def discover(timeout: float = 5.0, return_adv: bool = True):
        """Return one advertisement after the requested timeout."""
        del timeout, return_adv
        return {FakeDevice(): FakeAdvertisement()}


class FakeBleak:
    """Namespace with the two Bleak classes used by the engine."""

    BleakScanner = FakeScanner
    BleakClient = FakeClient


class MtuBleak(FakeBleak):
    """Bleak namespace that serves the two-permission fake client."""

    BleakClient = MtuClient


class SmallMtuClient(MtuClient):
    """Bleak client stuck with the default 23-byte ATT MTU."""

    mtu_size = 23


class SmallMtuBleak(FakeBleak):
    """Bleak namespace that serves the low-MTU fake client."""

    BleakClient = SmallMtuClient


class FakeSocket:
    """Record connections and packets sent by the BR/EDR worker."""

    def __init__(self, protocol: int, hub) -> None:
        """Store the protocol constant and the owning fake stack."""
        self.protocol = protocol
        self.hub = hub

    def connect(self, target) -> None:
        """Record a successful connection to a target tuple."""
        self.hub.events.append("connect")
        self.hub.connections.append(target)

    def settimeout(self, seconds: float) -> None:
        """Record that the timeout was set before connecting."""
        del seconds
        self.hub.events.append("timeout")

    def send(self, payload: bytes) -> None:
        """Record the payload length instead of sending data."""
        self.hub.sent.append(len(payload))

    def close(self) -> None:
        """Accept a socket close without doing anything."""


class FlakySocket(FakeSocket):
    """Fail the first connection attempt and accept the next one."""

    def connect(self, target) -> None:
        """Raise once to check that the worker retries within its deadline."""
        self.hub.failures += 1
        if self.hub.failures == 1:
            raise OSError("rechazado")
        super().connect(target)


class FakeBluetooth:
    """Minimal PyBluez substitute for offline engine tests."""

    L2CAP = 101
    RFCOMM = 3

    def __init__(self) -> None:
        """Initialize empty connection, payload, and socket event logs."""
        self.connections = []
        self.sent = []
        self.events = []
        self.failures = 0

    def discover_devices(self, **kwargs):
        """Return one classic Bluetooth device."""
        del kwargs
        return [(ADDRESS.lower(), "Prueba", 0)]

    def find_service(self, address: str):
        """Return one SDP service record."""
        return [
            {
                "name": "Serial",
                "description": "Puerto serie",
                "protocol": "RFCOMM",
                "port": 1,
                "service-id": "uuid-1",
            }
        ]

    def BluetoothSocket(self, protocol: int) -> FakeSocket:
        """Create a socket recorder for the selected protocol."""
        return FakeSocket(protocol, self)


class FlakyBluetooth(FakeBluetooth):
    """PyBluez substitute whose first socket connection is rejected."""

    def BluetoothSocket(self, protocol: int) -> FlakySocket:
        """Create a socket that fails once before connecting."""
        return FlakySocket(protocol, self)


def wait_for(engine: BluetoothEngine) -> JobState:
    """Poll a fake-library job until it finishes or the test times out."""
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        state = engine.snapshot()
        if not state.running:
            return state
        time.sleep(0.01)
    raise AssertionError("La tarea Bluetooth no terminó a tiempo")


class BleedingValidationTests(unittest.TestCase):
    """Check pure validation and address helpers without Bluetooth hardware."""

    def test_manifest_declares_both_stacks(self):
        """Require an implemented screen, an icon, and system dependencies."""
        path = ROOT / "modules" / "bleeding" / "manifest.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "bleeding")
        self.assertEqual(data["screen"], "screen.py")
        self.assertIn("bluez", data["deps"])
        self.assertIn("libbluetooth-dev", data["deps"])
        self.assertTrue((ROOT / "assets" / "icons" / f"{data['icon']}.png").is_file())

    def test_target_and_random_addresses_are_valid(self):
        """Normalize MAC input and generate only well-formed random addresses."""
        self.assertEqual(normalize_target(f" {ADDRESS.lower()} "), ADDRESS)
        self.assertTrue(MAC_PATTERN.fullmatch(random_mac()))
        for bad in ("", "FC:FC:48:AA:BB", "FC:FC:48:AA:BB:GG", "host.local"):
            with self.assertRaises(ValueError):
                normalize_target(bad)

    def test_deauth_options_reject_out_of_range_values(self):
        """Bound every attack option and block L2CAP on Windows."""
        self.assertEqual(
            validate_deauth_parameters(ADDRESS, "BLE", "RFCOMM", 1, 512, 2, 30, is_windows=False),
            ADDRESS,
        )
        with self.assertRaises(ValueError):
            validate_deauth_parameters(ADDRESS, "OTRO", "RFCOMM", 1, 512, 2, 30)
        with self.assertRaises(ValueError):
            validate_deauth_parameters(ADDRESS, "BR/EDR", "OTRO", 1, 512, 2, 30)
        with self.assertRaises(ValueError):
            validate_deauth_parameters(ADDRESS, "BR/EDR", "L2CAP", 1, 512, 2, 30, is_windows=True)
        with self.assertRaises(ValueError):
            validate_deauth_parameters(ADDRESS, "BR/EDR", "RFCOMM", 0, 512, 2, 30)
        with self.assertRaises(ValueError):
            validate_deauth_parameters(ADDRESS, "BR/EDR", "RFCOMM", 1, 2048, 2, 30)
        with self.assertRaises(ValueError):
            validate_deauth_parameters(ADDRESS, "BR/EDR", "RFCOMM", 1, 512, 3, 30)
        with self.assertRaises(ValueError):
            validate_deauth_parameters(ADDRESS, "BR/EDR", "RFCOMM", 1, 512, 2, 200)


class BleedingEngineTests(unittest.TestCase):
    """Exercise scans, enumeration, and DeAuth with injected fake libraries."""

    def setUp(self) -> None:
        """Reset the fake GATT write log before each engine test."""
        FakeClient.writes = []

    def test_ble_scan_and_enumeration_use_injected_libraries(self):
        """Discover a BLE device and enumerate its GATT service offline."""
        engine = BluetoothEngine(bleak_module=FakeBleak, bluetooth_module=FakeBluetooth())
        engine.start_scan("BLE")
        state = wait_for(engine)
        self.assertEqual(state.devices[0]["address"], ADDRESS)
        self.assertEqual(state.devices[0]["rssi"], -60)
        engine.start_enumeration(ADDRESS, "BLE")
        state = wait_for(engine)
        self.assertEqual(state.services[0]["protocol"], "GATT")
        self.assertEqual(state.services[0]["characteristics"][0]["uuid"], "0000-TEST-ABCD")

    def test_bredr_scan_and_enumeration_use_injected_libraries(self):
        """Discover a classic device and enumerate its SDP service offline."""
        bluetooth = FakeBluetooth()
        engine = BluetoothEngine(bleak_module=FakeBleak, bluetooth_module=bluetooth)
        engine.start_scan("BR/EDR")
        state = wait_for(engine)
        self.assertEqual(state.devices[0]["type"], "BR/EDR")
        engine.start_enumeration(ADDRESS, "BR/EDR")
        state = wait_for(engine)
        self.assertEqual(state.services[0]["port"], 1)

    def test_ble_deauth_writes_only_to_writable_characteristics(self):
        """Send one bounded GATT write and stop at the requested deadline."""
        engine = BluetoothEngine(bleak_module=FakeBleak, bluetooth_module=FakeBluetooth())
        engine.start_deauth(ADDRESS, "BLE", "RFCOMM", 1, 128, 1, 1)
        state = wait_for(engine)
        self.assertTrue(FakeClient.writes)
        self.assertEqual(FakeClient.writes[0][1], b"\xff" * 128)
        self.assertFalse(state.running)

    def test_bredr_deauth_sends_bounded_payloads(self):
        """Open a classic socket and send the configured payload size."""
        bluetooth = FakeBluetooth()
        engine = BluetoothEngine(bleak_module=FakeBleak, bluetooth_module=bluetooth)
        engine.start_deauth(ADDRESS, "BR/EDR", "RFCOMM", 1, 256, 1, 1)
        state = wait_for(engine)
        self.assertTrue(bluetooth.sent)
        self.assertEqual(bluetooth.sent[0], 256)
        self.assertEqual(bluetooth.connections[0], (ADDRESS, 1))
        self.assertFalse(state.running)

    def test_cancel_stops_a_running_job(self):
        """Cancel a long attack without waiting for its full duration."""
        engine = BluetoothEngine(bleak_module=FakeBleak, bluetooth_module=FakeBluetooth())
        engine.start_deauth(ADDRESS, "BLE", "RFCOMM", 1, 128, 1, 180)
        engine.cancel()
        state = engine.snapshot()
        self.assertFalse(state.running)
        self.assertEqual(state.message, "Cancelado")

    def test_missing_libraries_are_reported_before_starting(self):
        """Fail fast when the selected Bluetooth stack is unavailable."""
        engine = BluetoothEngine(bleak_module=None, bluetooth_module=None)
        with self.assertRaises(RuntimeError):
            engine.start_scan("BLE")
        with self.assertRaises(RuntimeError):
            engine.start_scan("BR/EDR")

    def test_a_cancelled_job_cannot_overwrite_a_new_job(self):
        """Give every job its own state and stop event to avoid stale writes."""
        engine = BluetoothEngine(bleak_module=FakeBleak, bluetooth_module=FakeBluetooth())
        engine.start_deauth(ADDRESS, "BLE", "RFCOMM", 1, 128, 1, 180)
        old_state = engine.snapshot()
        old_stop = engine._stop
        engine.cancel()
        engine.start_scan("BLE")
        self.assertIsNot(engine.snapshot(), old_state)
        self.assertIsNot(engine._stop, old_stop)
        state = wait_for(engine)
        self.assertEqual(state.kind, KIND_SCAN)
        self.assertEqual(len(state.devices), 1)

    def test_successful_jobs_keep_their_detailed_message(self):
        """Preserve result counts instead of replacing them with a generic text."""
        engine = BluetoothEngine(bleak_module=FakeBleak, bluetooth_module=FakeBluetooth())
        engine.start_scan("BLE")
        state = wait_for(engine)
        self.assertEqual(state.message, "1 dispositivos")
        engine.start_enumeration(ADDRESS, "BLE")
        self.assertEqual(wait_for(engine).message, "1 servicios")

    def test_ble_writes_respect_permissions_and_mtu(self):
        """Use requests for write-only chars and clamp command payloads to the MTU."""
        engine = BluetoothEngine(bleak_module=MtuBleak, bluetooth_module=FakeBluetooth())
        engine.start_deauth(ADDRESS, "BLE", "RFCOMM", 1, 512, 1, 1)
        self.assertFalse(wait_for(engine).running)
        writes = {uuid: (len(payload), response) for uuid, payload, response in FakeClient.writes}
        self.assertEqual(writes["0000-NORESP-0001"], (20, False))
        self.assertEqual(writes["0000-RESP-0002"], (512, True))

    def test_ble_request_writes_respect_the_negotiated_mtu(self):
        """Shrink request payloads when the link only negotiates the default MTU."""
        engine = BluetoothEngine(bleak_module=SmallMtuBleak, bluetooth_module=FakeBluetooth())
        engine.start_deauth(ADDRESS, "BLE", "RFCOMM", 1, 512, 1, 1)
        self.assertFalse(wait_for(engine).running)
        writes = {uuid: (len(payload), response) for uuid, payload, response in FakeClient.writes}
        self.assertEqual(writes["0000-RESP-0002"], (20, True))

    def test_bredr_sets_timeout_before_connecting_and_retries(self):
        """Bound connect() and keep trying until the attack deadline."""
        bluetooth = FlakyBluetooth()
        engine = BluetoothEngine(bleak_module=FakeBleak, bluetooth_module=bluetooth)
        engine.start_deauth(ADDRESS, "BR/EDR", "RFCOMM", 1, 128, 1, 2)
        self.assertFalse(wait_for(engine).running)
        self.assertEqual(bluetooth.events[0], "timeout")
        self.assertGreater(bluetooth.events.index("connect"), 0)
        self.assertGreaterEqual(bluetooth.failures, 1)
        self.assertTrue(bluetooth.connections)
        self.assertTrue(bluetooth.sent)

    def test_bredr_deauth_works_without_pybluez(self):
        """Fall back to standard-library AF_BLUETOOTH sockets for DeAuth."""
        hub = FakeBluetooth()
        with patch("modules.bleeding.engine.socket.socket", return_value=FakeSocket(3, hub)):
            engine = BluetoothEngine(bleak_module=None, bluetooth_module=None)
            self.assertTrue(engine.bredr_available)
            self.assertFalse(engine.bredr_discovery_available)
            with self.assertRaises(RuntimeError):
                engine.start_scan("BR/EDR")
            engine.start_deauth(ADDRESS, "BR/EDR", "RFCOMM", 1, 128, 1, 1)
            self.assertFalse(wait_for(engine).running)
        self.assertEqual(hub.sent[0], 128)


class BleedingScreenTests(unittest.TestCase):
    """Check gamepad navigation, confirmations, and rendering without hardware."""

    def test_scan_selects_a_target_and_enumeration_shows_services(self):
        """Pick a scanned MAC and display the simulated service list."""
        engine = FakeEngine()
        screen = BleedingScreen(engine)
        processes = FakeProcesses()
        for _ in range(2):
            screen.handle(DOWN, processes)
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "running")
        engine.state = JobState(
            kind=KIND_SCAN,
            devices=[{"address": ADDRESS, "name": "Prueba", "type": "BLE", "rssi": -60}],
        )
        screen.sync(processes)
        self.assertEqual(screen.phase, "devices")
        screen.handle(OPEN, processes)
        self.assertEqual(screen.editor.value, ADDRESS)
        for _ in range(2):
            screen.handle(DOWN, processes)
        screen.handle(OPEN, processes)
        engine.state = JobState(
            kind=KIND_ENUM,
            services=[{"name": "Servicio", "uuid": "0000-SVC-0001"}],
        )
        screen.sync(processes)
        self.assertEqual(screen.phase, "services")
        screen.handle(BACK, processes)
        self.assertEqual(screen.phase, "settings")

    def test_deauth_requires_confirmation_and_can_be_cancelled(self):
        """Adjust parameters, confirm once, and cancel the running attack."""
        engine = FakeEngine()
        screen = BleedingScreen(engine)
        processes = FakeProcesses()
        for _ in range(4):
            screen.handle(DOWN, processes)
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "prepare")
        screen.handle(RIGHT, processes)
        self.assertEqual(screen.packet_index, 3)
        for _ in range(4):
            screen.handle(DOWN, processes)
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "confirm")
        screen.handle(BACK, processes)
        self.assertEqual(screen.phase, "prepare")
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "confirm")
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "running")
        self.assertEqual(engine.calls[0][0], "deauth")
        self.assertEqual(engine.calls[0][1], screen.editor.value)
        engine.state = JobState(kind=KIND_DEAUTH, message="Ataque finalizado")
        screen.sync(processes)
        self.assertEqual(screen.phase, "result")
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "settings")
        self.assertTrue(screen.handle(BACK, processes))
        self.assertGreaterEqual(engine.cancelled, 1)

    def test_editor_and_mode_are_editable_with_the_dpad(self):
        """Change mode, edit a MAC, and restore it when B cancels."""
        engine = FakeEngine()
        screen = BleedingScreen(engine)
        processes = FakeProcesses()
        screen.handle(RIGHT, processes)
        self.assertEqual(screen.mode, 1)
        screen.handle(DOWN, processes)
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "edit_target")
        original = screen.editor.value
        screen.handle(UP, processes)
        self.assertNotEqual(screen.editor.value, original)
        screen.handle(BACK, processes)
        self.assertEqual(screen.editor.value, original)
        self.assertEqual(screen.phase, "settings")

    def test_missing_library_is_shown_as_a_result(self):
        """Report an unavailable stack in the GUI instead of starting a job."""
        engine = BluetoothEngine(bleak_module=None, bluetooth_module=None)
        screen = BleedingScreen(engine)
        processes = FakeProcesses()
        for _ in range(2):
            screen.handle(DOWN, processes)
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "result")
        self.assertIn("bleak", screen.result_message)

    def test_close_cancels_any_background_work(self):
        """Let the app stop the engine when returning to the module menu."""
        engine = FakeEngine()
        screen = BleedingScreen(engine)
        screen.close()
        self.assertEqual(engine.cancelled, 1)

    def test_failed_scan_shows_the_error_instead_of_an_empty_list(self):
        """Surface worker errors in the result view instead of 'SIN RESULTADOS'."""
        engine = FakeEngine()
        screen = BleedingScreen(engine)
        processes = FakeProcesses()
        for _ in range(2):
            screen.handle(DOWN, processes)
        screen.handle(OPEN, processes)
        engine.state = JobState(kind=KIND_SCAN, message="Fallo: D-Bus no disponible")
        screen.sync(processes)
        self.assertEqual(screen.phase, "result")
        self.assertIn("Fallo", screen.result_message)

    def test_screen_renders_every_phase_in_memory(self):
        """Draw all views without opening a window or using Bluetooth."""
        pygame.init()
        surface = pygame.Surface((theme.WIDTH, theme.HEIGHT))
        screen = BleedingScreen(FakeEngine())
        processes = FakeProcesses()
        font = theme.load_font(8)
        title_font = theme.load_font(16)
        stats = StatsReader().read()
        for phase in (
            "settings",
            "edit_target",
            "prepare",
            "confirm",
            "running",
            "result",
            "devices",
            "services",
            "help",
        ):
            screen.phase = phase
            screen.draw(surface, title_font, font, font, processes, stats)
            self.assertTrue(screen.footer_hints())
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
