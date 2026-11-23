====================================================================
MANUAL DE ARQUITECTURA: HunterZero (GPi CASE 2W + RASPBERRY PI ZERO W V1.1)
====================================================================

OBJETIVO
Crear una herramienta de ciberseguridad ética y automatización modular, con una 
interfaz gráfica (GUI) de estilo retro, operable al 100% con el gamepad de 
la GPi Case y configurable de forma remota y segura por SSH.

REGLA DE ORO
"El núcleo controla la interfaz y los procesos; los módulos hacen tareas 
aisladas; los archivos de configuración y logs permiten reutilizar y depurar."

--------------------------------------------------------------------
1. ESTRUCTURA GENERAL DEL PROYECTO
--------------------------------------------------------------------
mi-app/
├── main.py                  # Punto de entrada de la aplicación
├── core/                    # Núcleo del sistema (Intocable por módulos)
│   ├── app.py               # Bucle principal de Pygame
│   ├── menu.py              # Lógica de navegación de menús
│   ├── input.py             # Mapeo del gamepad (GPi Case) y teclado
│   ├── screen.py            # Gestión del framebuffer/KMS
│   ├── theme.py             # Colores y fuentes (Press Start 2P)
│   ├── process_manager.py   # Lanzador y monitor de subprocesos
│   ├── system_stats.py      # Lectura real de CPU, RAM, Temp, Batería
│   ├── state.py             # Estado en memoria (recientes, favoritos)
│   └── logger.py            # Sistema centralizado de logs
├── modules/                 # Plugins independientes
│   ├── network_tools/
│   ├── system_control/
│   ├── file_manager/
│   ├── custom_scripts/
│   ├── system_monitor/
│   └── terminal/
├── data/                    # Archivos compartidos (generados por módulos)
│   ├── scans/               # Salidas de Nmap (.xml, .txt)
│   ├── captures/            # Capturas de Bettercap/Handshakes
│   ├── reports/             # Informes consolidados
│   └── targets/             # Listas de IPs/Dominios (favoritos.txt, recientes.txt)
├── state/                   # Estado persistente entre reinicios
│   ├── heartbeats/          # Archivos temporales de vida de los módulos
│   └── ui_state.json        # Último menú visitado
├── config/                  # Configuraciones editables por SSH
│   ├── settings.example.json # Valores iniciales documentados
│   └── settings.json        # Opcional/local; no se versiona
├── logs/                    # Registro histórico (app.log, actions.log)
└── assets/                  # Fuentes (.ttf), iconos, sonidos

--------------------------------------------------------------------
2. CONTRATO DE MÓDULOS (Plugins)
--------------------------------------------------------------------
Cada módulo es una carpeta independiente dentro de modules/ y DEBE tener:

modules/<nombre_modulo>/
├── manifest.yaml      # Metadatos (obligatorio)
├── main.py            # Punto de entrada (obligatorio)
└── module.py          # Lógica de menú y acciones (opcional)

--- Ejemplo de manifest.yaml ---
id: network_tools            # Debe coincidir con la carpeta del plugin
name: "Herramientas de Red"
description: "Diagnósticos de redes propias o autorizadas"
icon: network
version: "0.1.0"
entry_point: main.py
timeout_seconds: 30

--- Ejemplo de main.py ---
import sys
import json

def main():
    # Validar argumentos explícitos y limitar toda acción a usos autorizados.
    # Los procesos largos actualizan la ruta HUNTERZERO_HEARTBEAT.
    # Escribir resultados únicamente en las carpetas de datos acordadas.
    # Retornar código 0 en éxito y un código distinto de cero ante errores.
    pass

if __name__ == "__main__":
    main()

--------------------------------------------------------------------
3. GESTIÓN DE PROCESOS (Process Manager)
--------------------------------------------------------------------
La interfaz gráfica NUNCA se bloquea. Cada módulo se lanza usando 
subprocess.Popen y el núcleo se encarga de vigilarlo.

Flujo:
1. El usuario pulsa 'A' en un menú.
2. El núcleo lee el manifest.yaml del módulo.
3. La GUI no ejecuta como root ni eleva permisos de un módulo.
4. Se lanza el proceso con argumentos separados y `shell=False`.
5. El núcleo muestra una pantalla de "Ejecutando..." (con spinner animado).
6. El módulo escribe en la ruta recibida en `HUNTERZERO_HEARTBEAT`.
7. El núcleo lee el heartbeat; su antigüedad límite se configura localmente.
8. Si el tiempo supera timeout_seconds, el núcleo mata el proceso.
9. Al terminar, el núcleo lee el stdout/stderr y muestra un resumen de 2 líneas.
10. El usuario pulsa 'A' y vuelve al menú.

--------------------------------------------------------------------
4. SEGURIDAD Y PERMISOS (Modelo de mínimo privilegio)
--------------------------------------------------------------------
La aplicación de Pygame corre SIEMPRE como el usuario estándar (ej: 'hunter').
NUNCA se ejecuta como root.

Operaciones sin privilegios: (usuario normal)
- Leer el gamepad (añadido al grupo input).
- Leer métricas locales expuestas por procfs y sysfs.
- Consultas de diagnóstico únicamente en redes propias o con autorización.

La versión inicial no define acciones root ni módulos ofensivos. No añadir
reglas sudo NOPASSWD genéricas, comodines o ejecutores arbitrarios. Si una
operación futura requiere privilegios, debe diseñarse y revisarse por separado,
con mínimo privilegio y una lista permitida explícita; la interfaz nunca corre
como root.

--------------------------------------------------------------------
5. INTERFAZ GRÁFICA (UI) Y EXPERIENCIA DE USUARIO
--------------------------------------------------------------------
Estilo visual: 
- Fondo: Negro (#0F0F0F)
- Texto: Naranja (#FF8C00)
- Fuente: Press Start 2P (Bitmap/8-bit)
- Resolución: 640x480 (nativa de la GPi Case 2W)

Componentes visuales:
- HUD Superior: CPU, RAM, Temp, Hora (actualizados cada 2s, no cada frame).
- Menú Central: Lista seleccionable. El ítem seleccionado se pinta con 
  fondo naranja y texto negro.
- Footer: Indicaciones de botones (D-Pad: Navegar, A: Abrir, B: Volver).

Navegación del Gamepad (GPi Case 2W):
- D-Pad (Arriba/Abajo): Mover selección en el menú.
- D-Pad (Izquierda/Derecha): Cambiar de octeto (al introducir IPs).
- Botón A: Seleccionar / Confirmar / Abrir.
- Botón B: Volver al menú anterior / Cancelar.
- Botón START: Ejecutar acción directa.

--------------------------------------------------------------------
6. ENTRADA DE DATOS SIN TECLADO
--------------------------------------------------------------------
Dado que el dispositivo carece de teclado, se usan tres métodos:
1. Favoritos y Recientes: Archivos JSON en data/targets/. El usuario 
   elige de una lista predefinida con el D-Pad (máximo 2-3 pulsaciones).
2. Selector de IPs: Para IPs nuevas, se usa un selector de 4 octetos 
   (ej: [192].[168].[001].[100]). El D-Pad cambia de octeto y arriba/abajo 
   cambia el valor. Mucho más rápido que un teclado virtual.
3. Teclado Virtual (Dominios): Rejilla alfabética simple, navegable con 
   D-Pad. Solo aparece si el usuario elige "Introducir nuevo dominio".

--------------------------------------------------------------------
7. FLUJO DE ARRANQUE Y EJECUCIÓN (Systemd)
--------------------------------------------------------------------
El dispositivo arranca directo a la interfaz (modo Kiosco) sin login.

- La unidad deploy/hunterzero.service corre como usuario estándar en tty1.
- SDL_VIDEODRIVER=kmsdrm y pantalla completa se configuran en systemd, solo
  después de probar el modo gráfico en la instalación concreta.
- deploy/install.sh instala paquetes Trixie y crea un venv con
  --system-site-packages; no usar pip para depender de wheels ARMv6.
- Reinicio automático ante fallo; logs disponibles vía journalctl y logs/app.log.
- No habilitar el kiosco antes de validar pantalla, permisos de input/video y
  gamepad localmente.

--------------------------------------------------------------------
8. COMUNICACIÓN Y DATOS COMPARTIDOS
--------------------------------------------------------------------
- stdout/stderr: el proceso se redirige a logs/modules/<id>.log y el núcleo
  muestra su estado/error en pantalla.
- Archivos en data/: Un módulo de escaneo guarda un JSON. Un módulo de 
  diagnóstico autorizado puede consumir resultados locales validados.
- Heartbeats: Archivos JSON en state/heartbeats/ que se actualizan cada 
  pocos segundos para indicar que el módulo sigue vivo.

====================================================================
9. IMPLEMENTACIÓN BASE Y MEJORAS DE MANTENIBILIDAD
====================================================================
La implementación inicial se mantiene en módulos independientes:
- core/ controla el bucle Pygame, entradas, estado, métricas, logs y procesos.
- core/ui/ contiene componentes reutilizables; MenuLayout recibe límites y
  tamaño de fila para que los menús compartan geometría.
- modules/<id>/ contiene un plugin aislado, con manifest.yaml validado con
  yaml.safe_load y main.py. El id coincide con el nombre de la carpeta.
- assets/fonts/ conserva Press Start 2P y su licencia OFL. Los iconos son
  trazos vectoriales originales y no requieren paquetes de iconos externos.

Requisitos de despliegue objetivo:
- Raspberry Pi OS Lite Trixie de 32 bits en Pi Zero W (ARMv6), Python 3.13.
- Usar python3-pygame y python3-yaml de APT dentro de un venv creado con
  --system-site-packages. No depender de wheels de PyPI que no estén
  publicados para ARMv6.
- SDL_VIDEODRIVER=kmsdrm solo si está disponible en la imagen; probar
  pantalla y gamepad desde la consola antes de habilitar systemd.
- La interfaz y sus procesos se ejecutan como usuario normal, nunca como root.

Reglas de operación segura y confiable:
- Los módulos de ejemplo son informativos; no escanean redes ni modifican
  servicios. Las funciones de red futuras se limitan a sistemas propios o
  con autorización explícita.
- Lanzar procesos con argumentos separados, shell=False, timeout y logs;
  no aceptar comandos arbitrarios ni conceder sudo global.
- Heartbeat atómico de la app cada 5 segundos en state/heartbeats/app.json.
  Los procesos largos pueden actualizar la ruta recibida en
  HUNTERZERO_HEARTBEAT; el supervisor controla timeout y antigüedad.
- Escribir JSON/estado mediante archivo temporal y rename, validar
  manifiestos y parámetros, y registrar fallos en logs/app.log sin ocultarlos.
- config/settings.example.json documenta la configuración; settings.json es
  local/no versionado y permite ajustar refresco de métricas y heartbeats.
- Mantener en Git solo código, documentación, licencia y recursos libres.
  Excluir datos, logs, estado, secretos y configuración local.
- Las actualizaciones remotas usan git pull --ff-only y reinicio explícito de
  systemd; conservar la configuración local fuera de los archivos versionados.

Distribución y organización:
- README.md documenta dependencias, instalación, gamepad y actualización SSH.
- deploy/install.sh prepara paquetes de Trixie, entorno virtual y unidad
  systemd; deploy/update.sh actualiza desde Git sin sobrescribir datos locales.
- La unidad systemd corre en tty1 y reinicia solo ante fallo; no usar inicio
  automático hasta validar KMS/DRM en la pantalla GPi.
- El código usa licencia MIT y la fuente Press Start 2P conserva OFL.txt.
- Mejoras siguientes: validar SDL/gamepad en hardware real; agregar pruebas
  en la Pi; implementar pantallas útiles por plugin; y diseñar permisos
  privilegiados caso por caso con wrapper root-owned y lista permitida.
- El selector de octetos, favoritos/recientes y teclado virtual descritos arriba
  son objetivos futuros, no capacidades implementadas en la GUI inicial.