import pygame


def draw_icon(surface: pygame.Surface, name: str, rect: pygame.Rect, color: tuple[int, int, int]) -> None:
    x, y, w, h = rect
    center = (x + w // 2, y + h // 2)
    if name == "network":
        pygame.draw.circle(surface, color, center, 5, 2)
        pygame.draw.arc(surface, color, pygame.Rect(x + 2, y + 3, w - 4, h - 6), 0.3, 2.8, 2)
        pygame.draw.arc(surface, color, pygame.Rect(x + 8, y + 8, w - 16, h - 16), 0.3, 2.8, 2)
    elif name == "system":
        pygame.draw.circle(surface, color, center, 7, 3)
        for angle in range(0, 360, 45):
            vector = pygame.Vector2(1, 0).rotate(angle)
            start = pygame.Vector2(center) + vector * 9
            end = pygame.Vector2(center) + vector * 13
            pygame.draw.line(surface, color, start, end, 3)
    elif name == "folder":
        pygame.draw.rect(surface, color, (x + 2, y + 8, w - 4, h - 12), 2, border_radius=2)
        pygame.draw.line(surface, color, (x + 3, y + 8), (x + 12, y + 8), 3)
        pygame.draw.line(surface, color, (x + 12, y + 8), (x + 16, y + 12), 3)
    elif name == "code":
        pygame.draw.rect(surface, color, (x + 2, y + 4, w - 4, h - 8), 2, border_radius=3)
        pygame.draw.lines(surface, color, False, [(x + 14, y + 12), (x + 8, y + 17), (x + 14, y + 22)], 2)
        pygame.draw.line(surface, color, (x + 18, y + 22), (x + 22, y + 12), 2)
        pygame.draw.lines(surface, color, False, [(x + 26, y + 12), (x + 32, y + 17), (x + 26, y + 22)], 2)
    elif name == "chart":
        for i, height in enumerate((8, 15, 22, 29)):
            pygame.draw.rect(surface, color, (x + 3 + i * 7, y + h - height, 4, height))
        pygame.draw.line(surface, color, (x + 1, y + h - 1), (x + w - 1, y + h - 1), 2)
    elif name == "terminal":
        pygame.draw.circle(surface, color, center, 13, 3)
        pygame.draw.line(surface, color, (center[0], y + 1), (center[0], y + 13), 3)
    else:
        pygame.draw.circle(surface, color, center, 4)
