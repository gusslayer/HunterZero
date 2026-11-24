# HunterZero: contexto funcional y técnico

## Objetivo

Interfaz modular Pygame de 640×480 para GPi Case 2W con Raspberry Pi Zero W,
orientada a Raspberry Pi OS Lite Trixie de 32 bits. La aplicación se opera
desde la GPi mediante D-pad, A, B y START; no se necesita teclado para navegar,
introducir direcciones IPv4 o ejecutar las funciones disponibles.

La app se ejecuta como usuario estándar. Cada herramienta tiene su propia
carpeta, pantalla, manifiesto, validación y pruebas. El núcleo proporciona
widgets compartidos, entrada, estado, supervisión de procesos y logs; no mezcla
las opciones de herramientas distintas.

## Funciones implementadas

### Ping (`modules/ping/`)

- Menú y pantalla independientes con destino IPv4 manual y paquetes ICMP.
- El destino se edita octeto por octeto con D-pad; A guarda y B cancela.
- Se permiten 1, 2, 3 o 4 paquetes y timeout corto.
- Solo acepta una dirección IPv4 RFC1918 (`10/8`, `172.16/12`,
  `192.168/16`); rechaza dominios, rangos, IPv6 y direcciones públicas.
- Muestra confirmación explícita antes de enviar paquetes; B cancela.
- Presenta el resultado capturado y permite regresar con botones.

### Nmap (`modules/nmap/`)

- Menú, manifiesto, comandos y pantalla independientes de Ping.
- Destino manual con el mismo editor D-pad de IPv4 privada.
- Solo escaneo `-sT` de TCP connect y ritmo `-T2`, top 20/50/100 puertos,
  `--script vuln` (scripts NSE de la categoría vuln) y límite de tiempo;
  sin ejecución como root.
- Requiere confirmación explícita; B cancela el escaneo en curso.
- Presenta el resultado del comando y permite regresar con A/B.
- Utilizar solamente en equipos propios o con autorización.

### Monitor del sistema

Lee CPU, RAM, temperatura, Wi-Fi y batería cuando los expone procfs/sysfs.
Las métricas también aparecen en el HUD y se actualizan de forma periódica.
La disponibilidad de batería/temperatura depende del hardware/kernel.

El Monitor del Sistema es una pantalla implementada en su propia carpeta.
No se deben crear manifests para módulos sin pantalla funcional; no hay
marcadores vacíos ni una terminal genérica en el menú.

## Controles de la GPi

| Entrada | Función |
|---|---|
| D-pad arriba/abajo | Cambiar fila o valor |
| D-pad izquierda/derecha | Cambiar octeto o una opción |
| A | Abrir, guardar o confirmar |
| B | Cancelar/volver; en el menú principal no cierra la interfaz para no dejar el framebuffer en blanco |
| START | Abrir el módulo seleccionado; dentro de uno equivale a A |

El menú principal lista los módulos; su última fila es **ACTUALIZAR HUNTERZERO**
(icono `rotate-cw`). Abrirla muestra la pantalla de actualización: A ejecuta
`deploy/update.sh`, B desde la fase de confirmación vuelve al menú y durante
la ejecución lo cancela.

La app es de quiosco: `pygame.QUIT` (SDL lo emite al cambiar de VT/consola) se
traduce como "volver al menú", nunca como salida del proceso; `self.running`
solo lo detiene una señal externa. Al arrancar se llama a `pygame.event.clear()`
para descartar pulsaciones mantenidas durante el boot. `create_display()` llama
a `pygame.mouse.set_visible(False)` tras cada `set_mode()`: KMSDRM dibuja el
cursor en un plane DRM fuera del surface y en tty1 no hay compositor que lo
oculte. Las fuentes son 24/18/14 px y los textos se recortan al ancho útil de
640 px, ajustando también posiciones y separadores del HUD para que no se
solapen.

Se aceptan las tres familias de entrada que puede emitir la GPi Case 2W:
teclas GPIO (D-pad, A, B, START), `JOYBUTTONDOWN`/`JOYHATMOTION`/`JOYAXISMOTION`
y eventos normalizados de SDL GameController. Ignorar las familias legacy o las
teclas dejaba **todos los botones sin respuesta**; ahora solo se suprime la
repetición de la misma pulsación entre familias durante 150 ms. Ninguna tecla
del teclado cierra la app: solo `SDL_QUIT` vuelve al menú. Con
`HUNTERZERO_INPUT_DEBUG=1` se registran los eventos SDL crudos; la sonda
`tools/input_probe.py` los muestra desde SSH.

Flujo de Ping/Nmap:
1. Abrir la herramienta usando D-pad y A.
2. Elegir destino, editar cualquier IPv4 dígito a dígito con D-pad y guardar con A.
3. Ajustar paquetes o cantidad de puertos con izquierda/derecha.
4. Seleccionar la acción y revisar la pantalla de confirmación.
5. A ejecuta; B cancela. La UI presenta estado/resultado sin bloquear el loop.

## Arquitectura y contrato de módulos

```text
main.py
core/                     # App, control de entrada, métricas y procesos
core/ui/                  # HUD, widgets, layouts, ayuda y vistas reusables
modules/
  ping/                   # manifiesto, builder, validación y pantalla Ping
  nmap/                   # manifiesto, builder, validación y pantalla Nmap
  system_monitor/         # pantalla y ayuda de métricas locales
  proc_monitor/           # lista de procesos activos, estilo top resumido
assets/fonts/             # Press Start 2P y licencia OFL
assets/icons/             # PNG originales de los iconos del menú
config/                   # ejemplo versionado, configuración local ignorada
state/heartbeats/         # estado runtime; no se sube a Git
logs/                     # logs de aplicación y comandos
deploy/                   # instalador, config.txt de pantalla, deps, actualizador y unidad systemd
tests/                    # pruebas sin operaciones reales sobre la red
```

Cada `modules/<id>/` funcional contiene `manifest.yaml` y `screen.py`; las
herramientas que ejecutan procesos también definen sus builders y validación en
su propio módulo. El `id` del manifiesto debe coincidir con la carpeta y su
pantalla debe existir. El núcleo descubre manifiestos usando `yaml.safe_load`,
pero la clase de pantalla se registra explícitamente en `core/app.py`; el
manifiesto no ejecuta código Python. Vistas compartidas como el editor IPv4,
las opciones parametrizadas y la ayuda permanecen en `core/ui/`.

El lanzador acepta únicamente ejecutables incluidos en su allowlist (`ping`,
`nmap`), argv construido por funciones tipadas, `shell=False`, entrada estándar
cerrada, timeout, salida limitada y cancelación. No interpolar comandos de
texto ni añadir una terminal genérica. No ejecutar Pygame como root ni agregar
reglas sudo sin contraseña. El botón de actualización del menú ejecuta
`deploy/update.sh` mediante `ProcessManager.start_update`, compartiendo
esos controles y rechazando el comando si `bash` no está disponible. Se pasa
`HUNTERZERO_UPDATE_GUI=1` para que solo haga `git pull --ff-only --progress`:
sin tty `sudo` no puede pedir contraseña y reiniciar el servicio mataría la
interfaz antes de mostrar el resultado. Se desactiva `GIT_TERMINAL_PROMPT` para
no colgar esperando credenciales. La pantalla muestra tiempo, log en vivo y una
barra de actividad indeterminada (nunca un porcentaje falso); los pasos con root
se indican al terminar para ejecutarlos por SSH.

## Trazabilidad de UI y errores

- Los eventos de teclado GPIO, joystick y gamepad se normalizan a acciones
  UP/DOWN/LEFT/RIGHT/OPEN/BACK y START antes de llegar a pantallas. START
  equivale a OPEN dentro de un módulo para que ningún botón quede muerto. El
  timeout máximo es
  `MAX_COMMAND_TIMEOUT_SECONDS` (180 s) y Nmap usa ese valor: un timeout mayor
  hacía que `ProcessManager` rechazara el escaneo sin lanzarlo.
- Ping y Nmap mantienen estado propio de ajustes, edición, confirmación,
  ejecución y resultado usando el layout parametrizado compartido. El Monitor
  del Sistema tiene pantalla y ayuda propias.
- Los procesos escriben stdout/stderr a `logs/commands/latest.log`; la pantalla
  enseña un fragmento acotado y un estado explícito.
- El timeout/cancelación terminan el proceso. Fallos de sistema y validación
  deben mostrarse y registrarse, no ocultarse ni presentarse como éxito.
- `state/heartbeats/app.json` indica vida de la aplicación; no se exige
  heartbeat de fichero para comandos breves de una sola ejecución.
- Cada función/clase no trivial debe tener docstring en español o inglés
  describiendo su responsabilidad; mantener docstrings y pruebas al ampliar
  cualquier módulo.

## Requisitos para Raspberry Pi OS Trixie

- Pi Zero W, imagen armhf de 32 bits, Python 3.13 de Trixie.
- Paquetes APT: `python3`, `python3-venv`, `python3-pygame`,
  `python3-yaml`, `iputils-ping`, `nmap`, `git`, `gpiod` (señales GPIO del
  botón físico), y para SDL `kmsdrm`:
  `libegl1`, `libegl-mesa0`, `libgles2`, `libgbm1`, `libgl1-mesa-dri`, `libdrm2`
  y `libegl-dev` (verificado: sin él `pygame` termina con `EGL not initialized`).
  Sin EGL/GBM/Mesa, `pygame.display.set_mode` falla con `EGL not initialized`.
- El venv se crea con `--system-site-packages` para reutilizar los bindings de
  Pygame/YAML compilados para ARMv6; no depender de wheels PyPI ARMv6.
- Usuario estándar agregado a los grupos `input`, `video` y `render` (este último
  para `/dev/dri/renderD128`). La unidad systemd no fija `SupplementaryGroups`
  y hereda los grupos del usuario.
- `deploy/install.sh` instala `deploy/config.txt` en `/boot/firmware/config.txt`
  mediante `deploy/display-config.sh`: timings DPI 640×480, `vc4-kms-v3d` +
  `vc4-kms-dpi-generic` y audio PWM. Respaldar el original como
  `config.txt.hunterzero.bak` y reiniciar para aplicarlo. `update.sh` no lo
  sobrescribe en cada actualización.
- El apagado físico usa `hunterzero-poweroff.service` (root): mantiene GPIO 27
  en alto con `gpioset` y programa `shutdown -h now` al flanco descendente de
  GPIO 26 con `gpiomon`, según el esquema oficial de RetroFlag. No se usan los
  overlays `gpio-shutdown` ni `gpio-led` porque reclamarían esas líneas. El
  servicio se instala en `/usr/local/bin` y funciona aunque la app no esté
  arrancada; no añade reglas sudoers.
- `core/screen.py` intenta `kmsdrm` y, si EGL falla, `fbcon` (framebuffer del
  kernel); solo usa `dummy` cuando no se forzó ningún driver. Cada degradación
  se registra con un aviso en `logs/app.log`.
- Probar driver SDL, pantalla y gamepad desde la consola antes de habilitar
  `hunterzero.service` en tty1. El modo KMS/DRM depende de la imagen GPi.
- `deploy/update.sh` realiza `git pull --ff-only --progress` con salida
  progresiva visible, instala los paquetes APT nuevos declarados por los
  módulos con `deploy/deps.sh` y reinicia el servicio. Desde la GUI solo se
  descarga el código; el resto se termina por SSH con sudo.

## Licencias y calidad

- Código: MIT.
- Press Start 2P: SIL Open Font License, con `assets/fonts/OFL.txt`.
- Iconos: librería Lucide distribuida como PNG transparentes en
  `assets/icons/`, con licencia y atribución originales.
- Ejecutar `python -m unittest discover -s tests -v`. Las pruebas de comandos
  solo verifican argumentos; no envían ping ni inician Nmap.
- La validación en pantalla/gamepad físicos debe completarse en la GPi real.
