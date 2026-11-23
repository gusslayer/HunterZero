import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from core.plugins import Plugin


@dataclass
class RunningModule:
    plugin: Plugin
    process: subprocess.Popen
    started_at: float
    output_path: Path
    heartbeat_path: Path


class ProcessManager:
    def __init__(self, root: Path, logger, heartbeat_timeout_seconds: int) -> None:
        self.root = root
        self.logger = logger
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self.running: RunningModule | None = None
        self.message = ""

    def start(self, plugin: Plugin) -> None:
        if self.running and self.running.process.poll() is None:
            self.message = "Ya hay un módulo en ejecución"
            return
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.message = "Por seguridad, no ejecutes HunterZero como root"
            return
        if not plugin.entry_point.is_file() or plugin.path not in plugin.entry_point.parents:
            self.message = "Punto de entrada inválido"
            return
        run_dir = self.root / "logs" / "modules"
        heartbeat_dir = self.root / "state" / "heartbeats"
        run_dir.mkdir(parents=True, exist_ok=True)
        heartbeat_dir.mkdir(parents=True, exist_ok=True)
        output_path = run_dir / f"{plugin.identifier}.log"
        heartbeat_path = heartbeat_dir / f"{plugin.identifier}.json"
        environment = os.environ.copy()
        environment["HUNTERZERO_HEARTBEAT"] = str(heartbeat_path)
        output = None
        try:
            heartbeat_path.unlink(missing_ok=True)
            output = output_path.open("ab")
            process = subprocess.Popen(
                [sys.executable, "-m", f"modules.{plugin.identifier}.main"],
                cwd=self.root,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                shell=False,
                close_fds=True,
                env=environment,
            )
        except OSError as error:
            self.message = f"No se pudo iniciar {plugin.name}: {error}"
            self.logger.exception("Error al iniciar el módulo %s", plugin.identifier)
            return
        finally:
            if output:
                output.close()
        self.running = RunningModule(plugin, process, time.monotonic(), output_path, heartbeat_path)
        self.message = f"Ejecutando {plugin.name}"
        self.logger.info("Módulo iniciado: %s (pid %d)", plugin.identifier, process.pid)

    def update(self) -> None:
        task = self.running
        if not task:
            return
        return_code = task.process.poll()
        elapsed = time.monotonic() - task.started_at
        if return_code is None and elapsed > task.plugin.timeout_seconds:
            self._stop_task(task, f"Tiempo agotado: {task.plugin.name}")
            self.logger.error("Tiempo agotado para el módulo %s", task.plugin.identifier)
            return
        if return_code is not None:
            self.message = (
                f"{task.plugin.name}: finalizó correctamente"
                if return_code == 0
                else f"{task.plugin.name}: error ({return_code})"
            )
            if return_code:
                self.logger.error("Módulo %s terminó con código %d", task.plugin.identifier, return_code)
            self.running = None
            return
        try:
            heartbeat_age = time.time() - task.heartbeat_path.stat().st_mtime
            if heartbeat_age > self.heartbeat_timeout_seconds:
                self._stop_task(task, f"Heartbeat caducado: {task.plugin.name}")
                self.logger.error("Heartbeat obsoleto para %s", task.plugin.identifier)
        except FileNotFoundError:
            if elapsed > self.heartbeat_timeout_seconds:
                self._stop_task(task, f"Sin heartbeat: {task.plugin.name}")
                self.logger.error("No se recibió heartbeat para %s", task.plugin.identifier)
            else:
                self.message = f"Esperando heartbeat: {task.plugin.name}"

    def stop(self) -> None:
        if self.running:
            self._stop_task(self.running, f"Cancelado: {self.running.plugin.name}")

    def _stop_task(self, task: RunningModule, message: str) -> None:
        if task.process.poll() is None:
            try:
                task.process.terminate()
            except ProcessLookupError:
                pass
            try:
                task.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    task.process.kill()
                except ProcessLookupError:
                    pass
                task.process.wait()
        self.message = message
        self.running = None
