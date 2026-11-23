"""Launch the small, explicitly allowlisted set of background diagnostics."""

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


ALLOWED_COMMANDS = frozenset({"ping", "nmap"})
MAX_DISPLAY_OUTPUT = 4096


@dataclass
class RunningCommand:
    """Track one child process and its bounded execution deadline."""

    label: str
    process: subprocess.Popen
    started_at: float
    timeout_seconds: int
    output_path: Path


class ProcessManager:
    """Run allowlisted commands without blocking the Pygame event loop."""

    def __init__(self, root: Path, logger) -> None:
        """Store application paths and initialize the empty process state."""
        self.root = root
        self.logger = logger
        self.running: RunningCommand | None = None
        self.message = ""
        self.output = ""

    def start_command(self, label: str, command: list[str], timeout_seconds: int) -> bool:
        """Start a validated ping or Nmap argv list with captured output."""
        if self.running and self.running.process.poll() is None:
            self.message = "Ya hay una herramienta en ejecución."
            return False
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.message = "Por seguridad, no ejecutes HunterZero como root."
            return False
        if not command or command[0] not in ALLOWED_COMMANDS:
            self.message = "Comando no permitido."
            self.logger.error("Se bloqueó el intento de lanzar un comando no permitido.")
            return False
        if not 1 <= timeout_seconds <= 180:
            self.message = "Tiempo límite fuera del rango permitido."
            return False
        if any(not isinstance(argument, str) or "\x00" in argument for argument in command):
            self.message = "Argumentos de comando inválidos."
            return False
        executable = shutil.which(command[0])
        if executable is None:
            self.message = f"No está instalado {command[0]}; instala ping y nmap."
            self.logger.error("No se encontró el ejecutable permitido %s.", command[0])
            return False

        output_path = self.root / "logs" / "commands" / "latest.log"
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_file = output_path.open("wb")
            try:
                process = subprocess.Popen(
                    [executable, *command[1:]],
                    stdin=subprocess.DEVNULL,
                    stdout=output_file,
                    stderr=subprocess.STDOUT,
                    shell=False,
                    close_fds=True,
                )
            finally:
                output_file.close()
        except OSError as error:
            self.message = f"No se pudo iniciar {label}: {error}"
            self.logger.exception("No se pudo iniciar %s.", label)
            return False

        self.output = ""
        self.message = f"Ejecutando {label}..."
        self.running = RunningCommand(
            label=label,
            process=process,
            started_at=time.monotonic(),
            timeout_seconds=timeout_seconds,
            output_path=output_path,
        )
        self.logger.info("Se inició %s (pid %d).", label, process.pid)
        return True

    def update(self) -> None:
        """Collect completed output or stop the command when its deadline expires."""
        task = self.running
        if task is None:
            return

        if time.monotonic() - task.started_at >= task.timeout_seconds:
            self._stop_process(task.process)
            self.output = self._read_output(task.output_path)
            self.message = f"Tiempo agotado: {task.label}."
            self.logger.error("Se agotó el tiempo de %s.", task.label)
            self.running = None
            return

        return_code = task.process.poll()
        if return_code is None:
            return

        self.output = self._read_output(task.output_path)
        if return_code == 0:
            self.message = f"{task.label}: finalizado correctamente."
            self.logger.info("%s finalizó correctamente.", task.label)
        else:
            self.message = f"{task.label}: terminó con error ({return_code})."
            self.logger.error("%s terminó con código %d.", task.label, return_code)
        self.running = None

    def stop(self) -> None:
        """Terminate the active command when the user leaves or cancels its screen."""
        if self.running is None:
            return
        task = self.running
        self._stop_process(task.process)
        self.output = self._read_output(task.output_path)
        self.message = f"Cancelado: {task.label}."
        self.running = None

    @staticmethod
    def _stop_process(process: subprocess.Popen) -> None:
        """Ask the child to exit, then force-stop it if it ignores termination."""
        if process.poll() is not None:
            return
        try:
            process.terminate()
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except ProcessLookupError:
                return
            process.wait()

    @staticmethod
    def _read_output(path: Path) -> str:
        """Read only the final few kilobytes of a command log for the screen."""
        try:
            with path.open("rb") as output_file:
                output_file.seek(0, os.SEEK_END)
                size = output_file.tell()
                output_file.seek(max(0, size - MAX_DISPLAY_OUTPUT), os.SEEK_SET)
                text = output_file.read(MAX_DISPLAY_OUTPUT).decode("utf-8", errors="replace")
        except OSError as error:
            return f"No se pudo leer el resultado: {error}"
        return "\n".join(line.rstrip() for line in text.splitlines()[-8:])
