"""Gamepad screen for BLEeding: discovery, enumeration, and bounded DeAuth."""

import time

import pygame

from core import theme
from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP
from core.ui.help_view import draw_help_view
from core.ui.scroll import ScrollState
from core.ui.text_cache import render_cached
from core.ui.widgets import draw_frame, draw_row, draw_scroll_indicator, plain_text, wrap_text
from modules.bleeding.engine import (
    ATTACK_DURATIONS,
    KIND_DEAUTH,
    KIND_ENUM,
    KIND_SCAN,
    MODES,
    PACKET_SIZES,
    PORT_BY_PROTOCOL,
    PROTOCOLS,
    THREAD_COUNTS,
    BluetoothEngine,
)


SETTINGS_ROWS = ("MODO", "OBJETIVO", "ESCANEAR", "ENUMERAR", "DEAUTH", "AYUDA", "VOLVER")
PREPARE_ROWS = ("PAQUETE", "HILOS", "DURACION", "PROTOCOLO", "INICIAR", "CANCELAR")
LIST_CAPACITY = 8
RESULT_TOP = 38
RESULT_BOTTOM = 208
RESULT_ROW = 16
RESULT_CAPACITY = (RESULT_BOTTOM - RESULT_TOP) // RESULT_ROW


class BleedingScreen:
    """Expose Bluetooth analysis and a confirmed, cancellable DeAuth attack."""

    def __init__(self, engine=None) -> None:
        """Initialize settings, an engine, and an empty result set."""
        self.title = "BLEEDING"
        self.engine = BluetoothEngine() if engine is None else engine
        self.editor = self._make_editor()
        self.mode = 0
        self.selected = 0
        self.phase = "settings"
        self.job_kind = ""
        self.result_message = ""
        self.devices: list[dict] = []
        self.services: list[dict] = []
        self.device_view = ScrollState(capacity=LIST_CAPACITY)
        self.service_view = ScrollState(capacity=LIST_CAPACITY)
        self.result_view = ScrollState(capacity=RESULT_CAPACITY)
        self.help_scroll = ScrollState()
        self.packet_index = PACKET_SIZES.index(512)
        self.thread_index = THREAD_COUNTS.index(2)
        self.duration_index = ATTACK_DURATIONS.index(30)
        self.protocol_index = 0
        self.prepare_selected = 0

    @staticmethod
    def _make_editor(address: str | None = None):
        """Create a MAC editor, importing it lazily to keep tests independent."""
        from modules.bleeding.target_editor import MacEditor

        return MacEditor() if address is None else MacEditor(address)

    def close(self) -> None:
        """Stop any background job when the app leaves this module."""
        self.engine.cancel()

    def handle(self, action, processes) -> bool:
        """Route gamepad actions through every phase of the Bluetooth module."""
        if self.phase == "edit_target":
            if self.editor.handle(action) in ("saved", "cancelled"):
                self.phase = "settings"
            return False
        if self.phase == "devices":
            return self._handle_devices(action)
        if self.phase == "services":
            return self._handle_services(action)
        if self.phase == "prepare":
            return self._handle_prepare(action)
        if self.phase == "confirm":
            if action == BACK:
                self.phase = "prepare"
            elif action == OPEN:
                self._start_deauth(processes)
            return False
        if self.phase == "running":
            if action == BACK:
                self.engine.cancel()
                self.result_message = (
                    "Ataque cancelado" if self.job_kind == KIND_DEAUTH else "Tarea cancelada"
                )
                self.phase = "result"
            return False
        if self.phase == "result":
            self.result_view.update(len(self._result_lines()))
            if action == UP:
                self.result_view.move(-1)
            elif action == DOWN:
                self.result_view.move(1)
            elif action == OPEN:
                self.phase = "settings"
            elif action == BACK:
                self.engine.cancel()
                return True
            return False
        if self.phase == "help":
            if action == UP:
                self.help_scroll.move(-1)
            elif action == DOWN:
                self.help_scroll.move(1)
            elif action == OPEN:
                self.phase = "settings"
            elif action == BACK:
                return True
            return False
        return self._handle_settings(action, processes)

    def sync(self, processes) -> None:
        """Poll the background engine and present completed results in the GUI."""
        state = self.engine.snapshot()
        if self.phase != "running":
            return
        processes.message = plain_text(state.message)[:34]
        if state.running:
            return
        if state.message.startswith("Fallo"):
            self.result_message = state.message
            self.phase = "result"
            return
        if state.kind == KIND_SCAN:
            self.devices = state.devices
            self.device_view.reset(len(self.devices))
            self.phase = "devices"
        elif state.kind == KIND_ENUM:
            self.services = state.services
            self.service_view.reset(len(self.services))
            self.phase = "services"
        else:
            self.result_message = state.message
            self.phase = "result"

    def draw(
        self,
        surface: pygame.Surface,
        title_font: pygame.font.Font,
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
        processes,
        stats,
    ) -> None:
        """Render the active configuration, progress, list, confirmation, or result view."""
        del title_font, processes, stats
        pygame.draw.rect(surface, theme.BG_COLOR, (0, 28, theme.WIDTH, 183))
        if self.phase == "edit_target":
            self.editor.draw(surface, body_font, small_font)
        elif self.phase == "help":
            self._draw_help(surface, body_font, small_font)
        elif self.phase == "settings":
            self._draw_settings(surface, body_font, small_font)
        elif self.phase == "prepare":
            self._draw_prepare(surface, body_font, small_font)
        elif self.phase == "confirm":
            self._draw_confirmation(surface, small_font)
        elif self.phase == "running":
            self._draw_running(surface, small_font)
        elif self.phase == "devices":
            self._draw_devices(surface, small_font)
        elif self.phase == "services":
            self._draw_services(surface, small_font)
        else:
            self._draw_result(surface, small_font)

    def footer_hints(self) -> list[tuple[str, int]]:
        """Return the button legend for the current phase."""
        if self.phase == "edit_target":
            return [("ARR/ABA HEX", 8), ("IZQ/DER POS", 118), ("A GUARDAR", 240)]
        if self.phase in ("devices", "services"):
            return [("ARR/ABA LISTA", 8), ("A SELECCIONAR", 150), ("B VOLVER", 240)]
        if self.phase == "prepare":
            return [("IZQ/DER VALOR", 8), ("A INICIAR", 168), ("B VOLVER", 240)]
        if self.phase == "confirm":
            return [("A ATACAR", 8), ("B CANCELAR", 120)]
        if self.phase == "running":
            return [("B CANCELAR", 8)]
        if self.phase == "result":
            return [("ARR/ABA TEXTO", 8), ("A OPCIONES", 150), ("B VOLVER", 240)]
        if self.phase == "help":
            return [("ARR/ABA TEXTO", 8), ("A OPCIONES", 168), ("B VOLVER", 240)]
        return [("ARR/ABA MOVER", 8), ("IZQ/DER MODO", 136), ("A ABRIR", 240)]

    def _handle_settings(self, action, processes) -> bool:
        """Navigate the main rows and start scans, enumeration, or DeAuth setup."""
        if action == UP:
            self.selected = (self.selected - 1) % len(SETTINGS_ROWS)
        elif action == DOWN:
            self.selected = (self.selected + 1) % len(SETTINGS_ROWS)
        elif action in (LEFT, RIGHT) and self.selected == 0:
            self.mode = (self.mode + (1 if action == RIGHT else -1)) % len(MODES)
        elif action == OPEN:
            if self.selected == 0:
                self.mode = (self.mode + 1) % len(MODES)
            elif self.selected == 1:
                self.editor.begin()
                self.phase = "edit_target"
            elif self.selected == 2:
                self._start_action(KIND_SCAN, lambda: self.engine.start_scan(MODES[self.mode]), processes)
            elif self.selected == 3:
                self._start_action(
                    KIND_ENUM,
                    lambda: self.engine.start_enumeration(self.editor.value, MODES[self.mode]),
                    processes,
                )
            elif self.selected == 4:
                self.prepare_selected = 0
                self.phase = "prepare"
            elif self.selected == 5:
                self.phase = "help"
            else:
                self.engine.cancel()
                return True
        elif action == BACK:
            self.engine.cancel()
            return True
        return False

    def _handle_devices(self, action) -> bool:
        """Scroll discovered devices and choose one as the new DeAuth target."""
        if self.devices:
            self.device_view.update(len(self.devices))
            if action == UP:
                self.device_view.move(-1)
            elif action == DOWN:
                self.device_view.move(1)
            elif action == OPEN:
                device = self.devices[self.device_view.selected]
                self.editor = self._make_editor(device["address"])
                self.selected = 1
                self.result_message = "OBJETIVO SELECCIONADO"
                self.phase = "settings"
                return False
        if action == BACK:
            self.phase = "settings"
        return False

    def _handle_services(self, action) -> bool:
        """Scroll enumerated services and return to the settings view."""
        if self.services:
            self.service_view.update(len(self.services))
            if action == UP:
                self.service_view.move(-1)
            elif action == DOWN:
                self.service_view.move(1)
        if action in (OPEN, BACK):
            self.phase = "settings"
        return False

    def _handle_prepare(self, action) -> bool:
        """Adjust DeAuth parameters, start the attack, or go back."""
        if action == UP:
            self.prepare_selected = (self.prepare_selected - 1) % len(PREPARE_ROWS)
        elif action == DOWN:
            self.prepare_selected = (self.prepare_selected + 1) % len(PREPARE_ROWS)
        elif action in (LEFT, RIGHT):
            self._change_parameter(1 if action == RIGHT else -1)
        elif action == OPEN:
            if self.prepare_selected == 4:
                self.phase = "confirm"
            elif self.prepare_selected == 5:
                self.phase = "settings"
        elif action == BACK:
            self.phase = "settings"
        return False

    def _change_parameter(self, step: int) -> None:
        """Cycle the selected DeAuth option within its allowed values."""
        if self.prepare_selected == 0:
            self.packet_index = (self.packet_index + step) % len(PACKET_SIZES)
        elif self.prepare_selected == 1:
            self.thread_index = (self.thread_index + step) % len(THREAD_COUNTS)
        elif self.prepare_selected == 2:
            self.duration_index = (self.duration_index + step) % len(ATTACK_DURATIONS)
        elif self.prepare_selected == 3 and MODES[self.mode] == "BR/EDR":
            self.protocol_index = (self.protocol_index + step) % len(PROTOCOLS)

    def _start_action(self, kind: str, starter, processes) -> None:
        """Start a GUI job, showing validation or library errors as a result."""
        try:
            starter()
        except (ValueError, RuntimeError) as error:
            self.result_message = str(error)
            self.phase = "result"
            processes.message = self.result_message
            return
        self.job_kind = kind
        self.phase = "running"
        processes.message = f"Bluetooth: {kind}"

    def _start_deauth(self, processes) -> None:
        """Start the confirmed DeAuth job with validated options and a fixed port."""
        protocol = PROTOCOLS[self.protocol_index]
        self._start_action(
            KIND_DEAUTH,
            lambda: self.engine.start_deauth(
                self.editor.value,
                MODES[self.mode],
                protocol,
                PORT_BY_PROTOCOL[protocol],
                PACKET_SIZES[self.packet_index],
                THREAD_COUNTS[self.thread_index],
                ATTACK_DURATIONS[self.duration_index],
            ),
            processes,
        )

    def _result_lines(self) -> list[str]:
        """Build the wrapped result message plus all recorded job events."""
        state = self.engine.snapshot()
        lines = wrap_text(self.result_message or state.message, 34)
        for event in state.events:
            lines.extend(wrap_text(event, 34))
        return lines

    def _draw_settings(self, surface, font, small_font) -> None:
        """Draw the main rows, selected mode, target, and availability status."""
        for index, label in enumerate(SETTINGS_ROWS):
            row = pygame.Rect(12, 30 + index * 18, 296, 16)
            draw_row(surface, row, label, "", index == self.selected, font)
        surface.blit(render_cached(small_font, MODES[self.mode], theme.ACCENT_COLOR), (240, 34))
        surface.blit(render_cached(small_font, self.editor.value, theme.ACCENT_COLOR), (152, 52))
        draw_frame(surface, pygame.Rect(10, 160, 300, 46), theme.GRID_COLOR, theme.PANEL_COLOR)
        state = self.engine.snapshot()
        bredr_status = (
            "ON"
            if self.engine.bredr_discovery_available
            else "ATK" if self.engine.bredr_available else "OFF"
        )
        lines = (
            wrap_text(plain_text(state.message) or "LISTO PARA ANALIZAR", 36)[:2]
            + [f"BLE {'ON' if self.engine.ble_available else 'OFF'}  BR/EDR {bredr_status}"]
        )
        for index, line in enumerate(lines[:3]):
            color = theme.ACCENT_COLOR if index == 0 else theme.MUTED_COLOR
            surface.blit(render_cached(small_font, line[:36], color), (16, 164 + index * 13))

    def _draw_prepare(self, surface, font, small_font) -> None:
        """Draw the packet size, worker count, duration, and protocol options."""
        values = (
            f"{PACKET_SIZES[self.packet_index]}B",
            str(THREAD_COUNTS[self.thread_index]),
            f"{ATTACK_DURATIONS[self.duration_index]}S",
            "GATT" if MODES[self.mode] == "BLE" else PROTOCOLS[self.protocol_index],
            "",
            "",
        )
        for index, label in enumerate(PREPARE_ROWS):
            row = pygame.Rect(12, 30 + index * 18, 296, 16)
            draw_row(surface, row, label, values[index], index == self.prepare_selected, font)
        surface.blit(
            render_cached(small_font, f"OBJETIVO {self.editor.value}", theme.ACCENT_COLOR),
            (16, 168),
        )

    def _draw_confirmation(self, surface, font) -> None:
        """Show the exact target and limits before requiring explicit approval."""
        protocol = "GATT" if MODES[self.mode] == "BLE" else PROTOCOLS[self.protocol_index]
        lines = (
            f"OBJETIVO: {self.editor.value}",
            f"MODO: {MODES[self.mode]}  PROTOCOLO: {protocol}",
            f"PAQUETE: {PACKET_SIZES[self.packet_index]}B  HILOS: {THREAD_COUNTS[self.thread_index]}",
            f"DURACION: {ATTACK_DURATIONS[self.duration_index]}S",
            "SOLO EQUIPOS PROPIOS O AUTORIZADOS",
            "A INICIAR  B CANCELAR",
        )
        for index, line in enumerate(lines):
            color = theme.ACCENT_COLOR if index >= len(lines) - 2 else theme.TEXT_COLOR
            surface.blit(render_cached(font, plain_text(line)[:34], color), (16, 38 + index * 18))

    def _draw_running(self, surface, font) -> None:
        """Show the active job, target, elapsed time, and the latest events."""
        state = self.engine.snapshot()
        elapsed = max(0, int(time.monotonic() - state.started_at)) if state.started_at else 0
        lines = (
            f"{state.kind} EN CURSO  {elapsed}S",
            f"OBJETIVO: {self.editor.value}",
            *wrap_text(state.message, 34)[:2],
        )
        for index, line in enumerate(lines):
            surface.blit(render_cached(font, line, theme.ACCENT_COLOR), (16, 38 + index * 16))
        for index, event in enumerate(state.events[-3:]):
            surface.blit(
                render_cached(font, plain_text(event)[:34], theme.MUTED_COLOR),
                (16, 100 + index * 16),
            )

    def _draw_devices(self, surface, font) -> None:
        """List discovered addresses so one can be picked with A."""
        surface.blit(render_cached(font, "DISPOSITIVOS", theme.ACCENT_COLOR), (16, 34))
        if not self.devices:
            surface.blit(render_cached(font, "SIN RESULTADOS", theme.MUTED_COLOR), (16, 60))
            return
        self.device_view.update(len(self.devices))
        for position, index in enumerate(range(self.device_view.first, self.device_view.last)):
            device = self.devices[index]
            row = pygame.Rect(12, 52 + position * 17, 296, 15)
            draw_row(
                surface,
                row,
                str(device.get("name", ""))[:14],
                "",
                index == self.device_view.selected,
                font,
            )
            surface.blit(
                render_cached(font, str(device.get("address", ""))[:17], theme.ACCENT_COLOR),
                (150, row.y + 3),
            )
        draw_scroll_indicator(
            surface,
            pygame.Rect(12, 52, 296, LIST_CAPACITY * 17),
            self.device_view.has_above,
            self.device_view.has_below,
            theme.ACCENT_COLOR,
        )

    def _draw_services(self, surface, font) -> None:
        """List discovered services with a short UUID for reference."""
        surface.blit(render_cached(font, "SERVICIOS", theme.ACCENT_COLOR), (16, 34))
        if not self.services:
            surface.blit(render_cached(font, "SIN RESULTADOS", theme.MUTED_COLOR), (16, 60))
            return
        self.service_view.update(len(self.services))
        for position, index in enumerate(range(self.service_view.first, self.service_view.last)):
            service = self.services[index]
            row = pygame.Rect(12, 52 + position * 17, 296, 15)
            draw_row(
                surface,
                row,
                str(service.get("name", ""))[:18],
                str(service.get("uuid", ""))[-12:],
                index == self.service_view.selected,
                font,
            )
        draw_scroll_indicator(
            surface,
            pygame.Rect(12, 52, 296, LIST_CAPACITY * 17),
            self.service_view.has_above,
            self.service_view.has_below,
            theme.ACCENT_COLOR,
        )

    def _draw_result(self, surface, font) -> None:
        """Show the wrapped result message and scroll through all job events."""
        lines = self._result_lines()
        self.result_view.update(len(lines))
        for position, index in enumerate(range(self.result_view.first, self.result_view.last)):
            color = theme.ACCENT_COLOR if index == 0 else theme.MUTED_COLOR
            surface.blit(
                render_cached(font, lines[index], color),
                (16, RESULT_TOP + position * RESULT_ROW),
            )
        draw_scroll_indicator(
            surface,
            pygame.Rect(12, RESULT_TOP, 296, RESULT_BOTTOM - RESULT_TOP),
            self.result_view.has_above,
            self.result_view.has_below,
            theme.ACCENT_COLOR,
        )

    def _draw_help(self, surface, font, small_font) -> None:
        """Explain controls, limits, and the authorized-use requirement."""
        total, capacity = draw_help_view(
            surface,
            font,
            font,
            small_font,
            f"AYUDA {self.title}",
            (
                (
                    "ANALISIS",
                    (
                        "MODO alterna BLE y BR/EDR con izquierda/derecha.",
                        "ESCANEAR elige un dispositivo; ENUMERAR lee servicios.",
                    ),
                ),
                (
                    "DEAUTH",
                    (
                        "Requiere confirmacion; B cancela en cualquier momento.",
                        "Duracion maxima 180s. Usa solo equipos propios o autorizados.",
                    ),
                ),
            ),
            self.help_scroll.offset,
        )
        self.help_scroll.update(total, capacity)
