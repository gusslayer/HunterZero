"""Launch the small, explicitly allowlisted set of background diagnostics."""

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


ALLOWED_COMMANDS = frozenset({"ping", "nmap"})
UPDATE_LABEL = "Actualización de HunterZero"
UPDATE_DEPENDENCY_HINT = (
    "Si falta una dependencia, instala los paquetes declarados en los manifiestos:"
    " sudo bash deploy/deps.sh."
)
MAX_DISPLAY_OUTPUT = 4096


@dataclass
class RunningCommand:
    """Track one child process and its bounded execution deadline."""

    label: str
    process: subprocess.Popen
    started_at: float
    timeout_seconds: int
    output_path: Path
    last_output_read: float = 0.0


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
        if not command or command[0] not in ALLOWED_COMMANDS:
            self.message = "Comando no permitido."
            self.logger.error("Se bloqueó el intento de lanzar un comando no permitido.")
            return False
        return self._launch(
            label,
            command,
            timeout_seconds,
            f"No está instalado {command[0]}; instala ping y nmap.",
        )

    def start_update(self, timeout_seconds: int = 180) -> bool:
        """Run deploy/update.sh with the same guarded launcher as tool commands."""
        command = ["bash", str(self.root / "deploy" / "update.sh")]
        environment = os.environ.copy()
        environment["HUNTERZERO_UPDATE_GUI"] = "1"
        return self._launch(
            UPDATE_LABEL,
            command,
            timeout_seconds,
            "No está instalado bash; no se puede actualizar ahora.",
            environment,
        )

    def _launch(
        self,
        label: str,
        command: list[str],
        timeout_seconds: int,
        missing_message: str,
        environment: dict[str, str] | None = None,
    ) -> bool:
        """Shared guards and subprocess launch for tool and update commands."""
        if self.running and self.running.process.poll() is None:
            self.message = "Ya hay una herramienta en ejecución."
            return False
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.message = "Por seguridad, no ejecutes HunterZero como root."
            return False
        if not 1 <= timeout_seconds <= 180:
            self.message = "Tiempo límite fuera del rango permitido."
            return False
        if any(not isinstance(argument, str) or "\x00" in argument for argument in command):
            self.message = "Argumentos de comando inválidos."
            return False
        executable = shutil.which(command[0])
        if executable is None:
            self.message = missing_message
            self.logger.error("No se encontró el ejecutable permitido %s.", command[0])
            return False

        output_path = self.root / "logs" / "commands" / "latest.log"
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_file = output_path.open("wb")
            popen_kwargs = {
                "stdin": subprocess.DEVNULL,
                "stdout": output_file,
                "stderr": subprocess.STDOUT,
                "shell": False,
                "close_fds": True,
            }
            if environment is not None:
                popen_kwargs["env"] = environment
            try:
                process = subprocess.Popen([executable, *command[1:]], **popen_kwargs)
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
            last_output_read=time.monotonic(),
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
            if task.label == UPDATE_LABEL:
                self.message += " " + UPDATE_DEPENDENCY_HINT
            self.logger.error("Se agotó el tiempo de %s.", task.label)
            self.running = None
            return

        return_code = task.process.poll()
        if return_code is None:
            # Muestra el log mientras corre para que la pantalla tenga progreso real.
            if time.monotonic() - task.last_output_read >= 0.25:
                self.output = self._read_output(task.output_path)
                task.last_output_read = time.monotonic()
            return

        self.output = self._read_output(task.output_path)
        if return_code == 0:
            self.message = f"{task.label}: finalizado correctamente."
            self.logger.info("%s finalizó correctamente.", task.label)
        else:
            self.message = f"{task.label}: terminó con error ({return_code})."
            if task.label == UPDATE_LABEL:
                self.message += " " + UPDATE_DEPENDENCY_HINT
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
