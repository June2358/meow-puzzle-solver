"""Small pygame components shared by the input and playback screens."""

from __future__ import annotations

import pygame

from .ui_style import BLACK, WHITE, Color

_BUTTON_BORDER_RADIUS = 10
_BUTTON_SHADOW_OFFSET = 2
_BUTTON_SHADOW_ALPHA = 24
_BUTTON_HOVER_BRIGHTNESS = 12
_BUTTON_BORDER_DARKEN = 22


class Button:
    """A rounded button with deterministic hover and hit-test behavior."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        color: Color,
        font: pygame.font.Font,
        *,
        text_color: Color = WHITE,
        hover_color: Color | None = None,
        border_color: Color | None = None,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.text = text
        self.base_color = color
        self.hover_color = hover_color
        self.border_color = border_color
        self.font = font
        self.text_color = text_color
        self.is_hovered = False
        self._shadow_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            self._shadow_surface,
            (*BLACK, _BUTTON_SHADOW_ALPHA),
            self._shadow_surface.get_rect(),
            border_radius=_BUTTON_BORDER_RADIUS,
        )

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(mouse_pos)

    def draw(self, screen: pygame.Surface) -> None:
        color = self._get_color()
        border_color = self.border_color or self._darken(color)

        shadow_rect = self.rect.move(_BUTTON_SHADOW_OFFSET, _BUTTON_SHADOW_OFFSET)
        screen.blit(self._shadow_surface, shadow_rect.topleft)

        self._draw_rect(screen, color, self.rect)
        self._draw_rect(screen, border_color, self.rect, width=1)

        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def _get_color(self) -> Color:
        if self.is_hovered:
            if self.hover_color is not None:
                return self.hover_color
            return tuple(
                min(255, c + _BUTTON_HOVER_BRIGHTNESS) for c in self.base_color
            )
        return self.base_color

    @staticmethod
    def _darken(color: Color) -> Color:
        return tuple(max(0, channel - _BUTTON_BORDER_DARKEN) for channel in color)

    @staticmethod
    def _draw_rect(
        screen: pygame.Surface,
        color: Color,
        rect: pygame.Rect,
        width: int = 0,
    ) -> None:
        pygame.draw.rect(
            screen,
            color,
            rect,
            width=width,
            border_radius=_BUTTON_BORDER_RADIUS,
        )
