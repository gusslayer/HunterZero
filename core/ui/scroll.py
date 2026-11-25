"""Estado de desplazamiento compartido por listas y vistas con muchas líneas."""

from dataclasses import dataclass


@dataclass
class ScrollState:
    """Mantener una selección y una ventana visible dentro de una lista larga."""

    count: int = 0
    capacity: int = 1
    selected: int = 0
    offset: int = 0

    def update(self, count: int, capacity: int | None = None) -> None:
        """Actualizar el tamaño de la lista y conservar una vista válida."""
        self.count = max(0, count)
        if capacity is not None:
            self.capacity = max(1, capacity)
        self.clamp()

    def reset(self, count: int) -> None:
        """Volver al inicio cuando se carga una lista nueva."""
        self.selected = 0
        self.offset = 0
        self.update(count)

    def clamp(self) -> None:
        """Forzar límites válidos y dejar visible la fila seleccionada."""
        self.selected = max(0, min(self.selected, max(0, self.count - 1)))
        max_offset = max(0, self.count - self.capacity)
        self.offset = max(0, min(self.offset, max_offset))
        if self.selected < self.offset:
            self.offset = self.selected
        elif self.selected >= self.offset + self.capacity:
            self.offset = self.selected - self.capacity + 1

    def move(self, step: int) -> None:
        """Mover la selección una fila y desplazar la ventana si hace falta."""
        if not self.count:
            return
        self.selected = (self.selected + step) % self.count
        self.clamp()

    @property
    def first(self) -> int:
        """Devolver el índice de la primera fila visible."""
        return self.offset

    @property
    def last(self) -> int:
        """Devolver el índice exclusivo de la última fila visible."""
        return min(self.count, self.offset + self.capacity)

    @property
    def has_above(self) -> bool:
        """Indicar si hay filas ocultas por encima de la ventana."""
        return self.offset > 0

    @property
    def has_below(self) -> bool:
        """Indicar si hay filas ocultas por debajo de la ventana."""
        return self.last < self.count

    @property
    def can_scroll(self) -> bool:
        """Indicar si la lista completa cabe en la pantalla."""
        return self.has_above or self.has_below
