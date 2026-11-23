# HunterZero

Interfaz modular para GPi Case 2W y Raspberry Pi Zero W, con Pygame, navegación por gamepad y estética retro. La resolución base es 640x480; los iconos se dibujan localmente y la tipografía Press Start 2P se distribuye bajo SIL Open Font License.

> Estado inicial: la interfaz, el HUD, el catálogo de plugins, el heartbeat y el lanzador de procesos están preparados. Los seis módulos incluidos son plantillas informativas: no escanean redes, no modifican el sistema y no ejecutan comandos de terminal.

## Requisitos

- Raspberry Pi Zero W (ARMv6) con Raspberry Pi OS Lite Trixie de 32 bits.
- Python 3.13 de Trixie (compatible con Python 3.11 o posterior).
- Paquetes del sistema: `python3-pygame`, `python3-yaml`, `python3-venv` y `git`.
- GPi conectado como pantalla HDMI y gamepad detectable por SDL/pygame.
- Para ejecutar la unidad systemd: usuario local sin privilegios, incluido en los grupos `input` y `video`.

En Trixie se usan los paquetes Pygame y PyYAML de APT dentro de un entorno virtual con `--system-site-packages`. Esto evita depender de wheels de PyPI que pueden no estar disponibles para ARMv6. En otros equipos, instala `requirements.txt` con `pip`.
Paquetes verificados para Trixie `armhf`: [python3-pygame](https://packages.debian.org/trixie/armhf/python3-pygame) y [python3-yaml](https://packages.debian.org/trixie/armhf/python3-yaml).

## Instalación en la Raspberry Pi

Instala Git y clona el repositorio en la cuenta que ejecutará la interfaz:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/<usuario>/<repositorio>.git ~/HunterZero
cd ~/HunterZero
sudo bash deploy/install.sh
```

El instalador instala dependencias de Trixie, configura el entorno virtual, agrega el usuario actual a `input` y `video` e instala la unidad systemd. Cierra sesión y vuelve a entrar para que se apliquen los grupos. Comprueba primero la interfaz en la consola conectada a la GPi:

```bash
SDL_VIDEODRIVER=kmsdrm HUNTERZERO_FULLSCREEN=1 .venv/bin/python main.py
```

Cuando la pantalla y los controles funcionen, activa el inicio automático:

```bash
sudo systemctl enable --now hunterzero.service
systemctl status hunterzero.service
```

La app no debe ejecutarse como root. Si `kmsdrm` no está disponible en la imagen o el framebuffer no inicia, revisa `journalctl -u hunterzero.service -b` y prueba el driver SDL compatible con la configuración de esa Pi antes de activar el servicio.

## Actualización remota

Conecta por SSH y actualiza desde la copia clonada:

```bash
cd ~/HunterZero
git pull --ff-only
sudo systemctl restart hunterzero.service
```

También se puede usar `bash deploy/update.sh`, que realiza `git pull --ff-only` y reinicia el servicio. Las preferencias, heartbeats, datos, logs y configuración local quedan fuera de Git.

## Configuración

Opcionalmente copia `config/settings.example.json` a `config/settings.json` y edítalo por SSH. Se pueden ajustar los intervalos de métricas y heartbeat, y el umbral de heartbeat de módulos; los valores se validan al arrancar. La configuración local no se sube a Git.
Comando: `cp config/settings.example.json config/settings.json`.

## Controles

| Acción | Gamepad | Teclado |
|---|---|---|
| Navegar | D-pad arriba/abajo | Flechas o W/S |
| Abrir detalle | A | Enter o espacio |
| Volver / salir del menú raíz | B | Escape |
| Ejecutar plantilla seleccionada | A en detalle / START en menú | Enter / Tab |

El menú muestra CPU, memoria, temperatura, estado de Wi-Fi, batería (si el kernel la expone) y hora. Las métricas se refrescan cada 2 segundos. La aplicación escribe `state/heartbeats/app.json` cada 5 segundos.

## Estructura

```text
core/                 # Bucle Pygame, entrada, estado, procesos, métricas y widgets
core/ui/              # Layout, HUD, footer e iconos vectoriales reutilizables
modules/<modulo>/     # Plugin independiente: manifest.yaml y main.py
assets/fonts/         # Press Start 2P y licencia OFL
config/               # Ejemplo versionado y configuración local ignorada por Git
data/                 # Archivos de trabajo locales
state/                # Estado UI y heartbeats locales
logs/                 # Registros locales
deploy/               # Instalación, actualización y servicio systemd
```

## Crear un módulo

1. Crea `modules/<id>/manifest.yaml` con `id` (igual al nombre de carpeta), `name`, `description`, `icon`, `entry_point` y `timeout_seconds`.
2. Crea un paquete Python (`__init__.py`) y un `main.py` que exponga el contrato del módulo.
3. Usa argumentos de proceso, nunca `shell=True`; valida entradas y escribe solo en las carpetas de datos autorizadas.
4. Emite heartbeat en la ruta recibida por `HUNTERZERO_HEARTBEAT` para procesos largos.
5. No eleves privilegios desde la app. Cualquier operación privilegiada requiere una decisión de seguridad y un wrapper con lista permitida, independiente del proceso Pygame.

Los manifiestos se leen con `yaml.safe_load`; los módulos con manifiestos inválidos se registran en `logs/app.log`. Las plantillas incluidas sirven como punto de partida y no implementan operaciones de red o terminal.

## Desarrollo local

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Para un entorno sin pantalla se puede probar con `SDL_VIDEODRIVER=dummy`; la interfaz resultante no es representativa de la pantalla GPi.

Pruebas automatizadas: `python -m unittest discover -s tests -v`.

## Licencias

- Código: MIT (ver `LICENSE`).
- Press Start 2P: SIL Open Font License 1.1 (ver `assets/fonts/OFL.txt`).
- Iconos: trazados originales dibujados en Pygame; no requieren recursos gráficos externos.
