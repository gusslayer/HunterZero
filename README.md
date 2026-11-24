```text
  ___ ___               __                __________                    
 /   |   \ __ __  _____/  |_  ___________ \____    /___________  ____   
/    ~    \  |  \/    \   __\/ __ \_  __ \  /     // __ \_  __ \/  _ \  
\    Y    /  |  /   |  \  | \  ___/|  | \/ /     /\  ___/|  | \(  <_> ) 
 \___|_  /|____/|___|  /__|  \___  >__|   /_______ \___  >__|   \____/  
       \/            \/          \/               \/   \/               
```         

Interfaz modular para GPi Case 2W y Raspberry Pi Zero W, con Pygame, navegación por gamepad y estética pixel art de alto contraste. Toda la interfaz se dibuja en un lienzo virtual de 320x240 y se escala 2x con nearest-neighbor a 640x480; usa negro, blanco y naranja, sin suavizado de tipografía. El tipo de letra es Press Start 2P, incluido en `assets/fonts/PressStart2P-Regular.ttf` (fuente original: https://fonts.google.com/specimen/Press+Start+2P), porque sus glifos de 8x8 se leen nítidos tras el escalado entero 2x. Los iconos provienen del pack pixelarticons de halfmage (https://github.com/halfmage/pixelarticons).

> Ping, Nmap y NSLOOKUP son módulos independientes con opciones, validación y comandos propios. Ping y Nmap comparten la vista de configuración/ayuda y el editor IPv4 (octeto por octeto con el D-pad): Ping envía 1–4 paquetes y Nmap usa TCP Connect, 20/50/100 puertos comunes y scripts NSE de la categoría vuln. NSLOOKUP tiene su propio editor de dominio con matriz de caracteres estilo arcade y muestra las IP resueltas (A o AAAA). Toda ejecución solicita confirmación. El Monitor del Sistema muestra métricas locales. No se incluyen módulos vacíos ni una terminal de comandos.

## Requisitos

- Raspberry Pi Zero W (ARMv6) con Raspberry Pi OS Lite Trixie de 32 bits.
- Python 3.13 de Trixie (compatible con Python 3.11 o posterior).
- Paquetes del sistema: `python3-pygame`, `python3-yaml`, `python3-venv`, `iputils-ping`, `nmap`, `dnsutils` (proporciona `nslookup`), `git` y las bibliotecas de ejecución EGL/GBM/Mesa para KMS/DRM.
- GPi conectado como pantalla HDMI y gamepad detectable por SDL/pygame.
- Para ejecutar la unidad systemd: usuario local sin privilegios, incluido en los grupos `input` y `video`.

En Trixie se usan los paquetes Pygame y PyYAML de APT dentro de un entorno virtual con `--system-site-packages`. Esto evita depender de wheels de PyPI que pueden no estar disponibles para ARMv6. En otros equipos, instala `requirements.txt` con `pip`.
Paquetes verificados para Trixie `armhf`: [python3-pygame](https://packages.debian.org/trixie/armhf/python3-pygame) y [python3-yaml](https://packages.debian.org/trixie/armhf/python3-yaml).

## Instalación en la Raspberry Pi

Instala Git y clona el repositorio en la cuenta que ejecutará la interfaz:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/gusslayer/HunterZero.git ~/HunterZero
cd ~/HunterZero
sudo bash deploy/install.sh
```

Los scripts de `deploy/` se relanzan automáticamente con `bash` si se invocan con
`sh`, y comprueban privilegios con `id -u` para funcionar también con `dash`.

El instalador instala de APT todas las dependencias del sistema necesarias para una
Pi OS Lite limpia: Git, Python y venv, Pygame, PyYAML, SDL, fuentes, utilidades
de proceso/red, `ping`, `nmap`, `dnsutils` y soporte de dispositivos. También instala EGL,
GLES, GBM, Mesa y libdrm, necesarios para el driver `kmsdrm` de SDL2. Configura
el entorno virtual, agrega el usuario actual a `input`, `video` y `render`, e
instala la unidad systemd (que hereda esos grupos del usuario).

### Pantalla de la GPi Case 2W

`deploy/install.sh` copia `deploy/config.txt` a `/boot/firmware/config.txt`
(ruta de la partición de arranque en Trixie) con los timings DPI de 640×480, el
driver KMS, el apagado por GPIO 26 y el audio PWM. El archivo original se guarda
como `/boot/firmware/config.txt.hunterzero.bak`. Es necesario reiniciar para que
el cambio surta efecto:

```bash
sudo reboot
```

En una Pi ya instalada se puede aplicar solo la configuración de pantalla con
`sudo bash deploy/display-config.sh`. Para volver al archivo anterior:
`sudo cp /boot/firmware/config.txt.hunterzero.bak /boot/firmware/config.txt`.
`deploy/update.sh` no sobrescribe el `config.txt` en cada actualización.

Si `journalctl -u hunterzero.service -b` muestra `EGL not initialized` y luego
`fbcon not available`, SDL no pudo inicializar EGL sobre KMS/DRM y tampoco existe
un framebuffer legado utilizable. `core/screen.py` ahora añade al error los
dispositivos detectados y una pista según los permisos; no se fuerza `dummy`
porque mostraría una pantalla negra. Comprueba en la propia Pi:

```bash
ls -l /dev/dri /dev/fb0        # KMS: card0; fbcon solo funciona con /dev/fb0
id                             # el usuario del servicio necesita acceso a card0
sudo dmesg | grep -Ei 'vc4|drm|egl'
systemctl show hunterzero.service -p User -p SupplementaryGroups
```

Si falta `/dev/dri/card0`, revisa los overlays `vc4-kms-v3d` y
`vc4-kms-dpi-generic` de `config.txt` y reinicia. Si el dispositivo existe pero
no tiene acceso `rw`, corrige la pertenencia a `video` y reinicia el servicio.
Si `card0` es accesible y EGL sigue fallando, verifica que `libegl-mesa0`,
`libgbm1` y `libgl1-mesa-dri` estén instalados y que el kernel haya iniciado el
driver VC4 sin errores. `libegl-dev` por sí solo no proporciona un backend EGL
funcional. Comprueba primero desde la consola conectada a la GPi:

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

También se puede usar `bash deploy/update.sh`, que realiza `git pull --ff-only`, instala en APT los paquetes nuevos declarados por los módulos (`deploy/deps.sh`) y reinicia el servicio. Las preferencias, heartbeats, datos, logs y configuración local quedan fuera de Git.

Desde la interfaz elige **ACTUALIZAR HUNTERZERO** en el menú principal y pulsa A. La pantalla muestra el tiempo transcurrido, las últimas líneas del log y un indicador de actividad indeterminado (git no expone un porcentaje real); B cancela. Como la app no es root y no hay terminal para pedir la contraseña de `sudo`, este botón **solo descarga el código**: al terminar indica los pasos que faltan. Para completar la actualización, conecta por SSH y ejecuta `sudo bash deploy/update.sh` (instala dependencias y reinicia el servicio).

## Configuración

Opcionalmente copia `config/settings.example.json` a `config/settings.json` y edítalo por SSH. Se pueden ajustar los intervalos de métricas y heartbeat de la app; los valores se validan al arrancar. La configuración local no se sube a Git.
Comando: `cp config/settings.example.json config/settings.json`.

## Controles

| Acción | GPi/Gamepad |
|---|---|
| Navegar | D-pad arriba/abajo |
| Cambiar octeto u opción | D-pad izquierda/derecha |
| Abrir, guardar o confirmar | A |
| Cancelar/volver (en el menú principal no cierra la app) | B |
| Abrir módulo; dentro de uno equivale a A | START |

El menú muestra CPU, memoria, temperatura, estado de Wi-Fi, batería (si el kernel la expone) y hora. Las métricas se refrescan cada 5 segundos. La aplicación escribe `state/heartbeats/app.json` cada 5 segundos. El Monitor de Procesos calcula el %CPU entre lecturas sucesivas de `/proc` (no un promedio desde el arranque) y actualiza la lista una vez por segundo. Nmap usa el máximo de 180 s permitido por el lanzador y NSLOOKUP un límite de 20 s.

La interfaz es de quiosco: no se cierra con B ni con un evento `SDL_QUIT` del cambio de consola/VT; solo termina si systemd detiene el servicio. Los eventos de botones que estaban pulsados durante el arranque se descartan para no entrar en un módulo por accidente. `create_display()` oculta el cursor de SDL justo después de crear la ventana, porque KMSDRM lo dibuja en un plane ajeno al surface de Pygame. La tipografía Press Start 2P usa 16 px para títulos y 8 px para texto en el lienzo virtual; el escalado entero 2x produce píxeles nítidos en la pantalla de 640x480.

En Ping: selecciona **IP DESTINO**, edita sus octetos con el D-pad y pulsa A para guardar; ajusta paquetes y elige **ENVIAR PING**. Revisa la confirmación y pulsa A otra vez para ejecutar o B para cancelar. Nmap tiene su propio destino, cantidad de puertos y confirmación. En **NSLOOKUP** elige **HOST** para abrir la matriz de caracteres: el D-pad mueve el cursor por la rejilla, A estampa la letra elegida al final del dominio, `DEL` borra la última y `OK` valida y guarda; B cancela. **TIPO REGISTRO** alterna entre A (IPv4) y AAAA (IPv6) y **CONSULTAR DNS** pide confirmación. La pantalla de resultado muestra las IP encontradas y las últimas líneas de la salida. Los tres módulos permiten cancelar con B y enseñan el resultado dentro de la GUI. La opción **AYUDA** explica los controles y parámetros de cada pantalla.

## Estructura

```text
core/                  # Bucle Pygame, entrada, estado, procesos, métricas y widgets comunes
core/ui/               # Layout, HUD, ayuda y pantallas parametrizadas reutilizables
modules/ping/          # Especificación, validación, comando y pantalla de Ping
modules/nmap/          # Especificación, validación, comando y pantalla de Nmap
modules/nslookup/      # Editor de dominio, argv validado y resultado de DNS
modules/system_monitor/ # Pantalla independiente de métricas locales
modules/proc_monitor/   # Lista de procesos activos, estilo top resumido
assets/fonts/          # HackerNoon V2 de assets/fonts/HackerNoonV2-Regular.ttf
assets/icons/          # PNG de pixelarticons y iconos legacy para el menú
config/               # Ejemplo versionado y configuración local ignorada por Git
state/                # Estado UI y heartbeats locales
logs/                 # Registros locales
deploy/               # Instalación, configuración de pantalla, actualización y servicio systemd
```

## Crear un módulo

Consulta [MODULE_FORMAT.md](MODULE_FORMAT.md) para el formato completo y obligatorio.

1. Crea `modules/<id>/manifest.yaml` con `id` (igual al nombre de carpeta), `name`, `description`, `icon` y `screen: screen.py`.
2. Implementa la pantalla, parámetros y ayuda propios en `modules/<id>/screen.py`. Registra la clase en `core/app.py`; no cargues código arbitrario desde el manifiesto.
3. Si la función necesita un proceso, agrega un builder de argv validado en el módulo y añade el ejecutable a la allowlist de `core/process_manager.py` tras revisar sus límites de seguridad. Si el módulo necesita un ejecutable o paquete APT nuevo, decláralo con un campo `deps:` (lista de nombres de paquetes) en el manifiesto; `deploy/deps.sh` los instala durante `deploy/install.sh` y en cada actualización.
4. Reutiliza las vistas de destino, parámetros y ayuda de `core/ui/` cuando correspondan; una función sin comportamiento real no debe tener manifiesto ni mostrarse en el menú.
5. No uses `shell=True`, no eleves privilegios ni aceptes comandos de texto desde la pantalla.

Los manifiestos se leen con `yaml.safe_load`; los manifiestos inválidos o sin pantalla se registran en `logs/app.log` y no aparecen en el menú. El lanzador solo admite `ping`, `nmap` y `nslookup`, nunca usa shell, no acepta comandos de texto y termina procesos al vencer el timeout o cancelar desde la GUI. Ping y Nmap validan la IPv4 introducida; NSLOOKUP valida el nombre de dominio carácter a carácter y solo pasa al argv un host canónico. Ejecutar diagnósticos únicamente sobre equipos propios o autorizados.

Todos los métodos nuevos deben incluir docstrings que describan su propósito; las pruebas cubren argumentos, límites y navegación sin lanzar tráfico de red.

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
- Tipo de letra: Press Start 2P (original en https://fonts.google.com/specimen/Press+Start+2P),
  con licencia OFL incluida en `assets/fonts/OFL.txt`. HackerNoon V2 sigue
  disponible en `assets/fonts/` por si se quiere comparar, pero a 8 px no es legible.
- Iconos: pack [pixelarticons](https://github.com/halfmage/pixelarticons) de
  halfmage (MIT; texto en `assets/icons/PIXELARTICONS_LICENSE.txt`),
  rasterizados como PNG transparentes en `assets/icons/`;
  los iconos sin equivalente en el pack conservan los PNG originales de
  [Lucide](https://lucide.dev/) (licencia en `assets/icons/LUCIDE_LICENSE.txt`).
