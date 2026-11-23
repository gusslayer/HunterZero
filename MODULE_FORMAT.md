# Formato obligatorio de módulos HunterZero

Cada módulo futuro debe ser una carpeta independiente dentro de `modules/`.
No se deben crear manifiestos para funciones simuladas, marcadores vacíos o
carpetas sin implementación.

## Estructura mínima

```text
modules/<id>/
  __init__.py
  manifest.yaml
  main.py       # Solo si el módulo inicia procesos externos
  screen.py
  tests/        # Opcional; pruebas específicas del módulo
```

El identificador `<id>` debe contener letras minúsculas, números y guiones
bajos. Debe coincidir exactamente con el nombre de carpeta y con `id` del
manifiesto.

## manifest.yaml

```yaml
id: ejemplo
name: Ejemplo
description: Explica brevemente qué hace el módulo.
icon: chart
version: "0.1.0"
screen: screen.py
```

Campos:

- `id`: identificador único y nombre exacto de carpeta.
- `name`: texto visible en el menú.
- `description`: descripción breve.
- `icon`: nombre admitido de Lucide y archivo `assets/icons/<icon>.png`.
  Entre los disponibles están `network`, `gauge`, `folder`, `code-xml`,
  `chart-no-axes-combined`, `terminal`, `radar`, `wifi`, `cpu`, `database`,
  `shield-check`, `search`, `settings`, `lock`, `upload`, `download`,
  `play`, `power`, `activity` y otros catalogados en `core/plugins.py`.
- `version`: versión textual del módulo.
- `screen`: siempre `screen.py`.

El catálogo valida los manifiestos con `yaml.safe_load`. Los módulos inválidos
se omiten y el error se registra en `logs/app.log`.

## screen.py

La clase debe implementar como mínimo:

```python
class EjemploScreen:
    def __init__(self) -> None:
        """Initialize module state."""

    def handle(self, action, processes) -> bool:
        """Return True only when B exits to the module menu."""

    def sync(self, processes) -> None:
        """Synchronize process or local state each application tick."""

    def draw(self, surface, title_font, body_font, small_font, processes, stats) -> None:
        """Render this module's screen."""

    def footer_hints(self) -> list[tuple[str, int]]:
        """Return footer labels and horizontal positions."""
```

Debe incluir docstrings en todas las clases y funciones. Si usa acciones nuevas,
mapéalas primero en `core/input.py` y pruébalas sin teclado ni tráfico real.

## Procesos externos

- Construye el argv en `main.py` y valida todos los argumentos.
- Solo se permiten direcciones privadas o datos ya validados.
- Registra el ejecutable explícitamente en `ALLOWED_COMMANDS`.
- Usa `shell=False`, `stdin=DEVNULL` y timeout acotado.
- No agregues reglas `sudo` ni ejecutes Pygame como root.
- No aceptes comandos escritos libremente desde la interfaz.

## Icono

Coloca un PNG cuadrado transparente de 34x34, 64x64 o 128x128 en
`assets/icons/<icon>.png`. El nombre debe coincidir con `icon` del manifiesto.
También puede permanecer el trazado vectorial de respaldo en `core/ui/icons.py`
mientras se migra el recurso gráfico.

## Registro

Después de crear el módulo, agrega su clase explícitamente a `screen_types`
en `core/app.py`. El manifiesto nunca cargará clases o ejecutará código Python
de forma dinámica.

## Pruebas

- Añade pruebas unitarias que no envíen red ni dependan de hardware.
- Añade una prueba del manifiesto y una de la navegación del screen.
- Ejecuta:
  `python -m unittest discover -s tests -v`
