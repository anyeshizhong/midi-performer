from enum import Enum
from typing import Callable, Optional, Tuple, Dict, List
import pygame

class ButtonState(Enum):
    """按钮状态枚举"""
    NORMAL = "normal"
    HOVERED = "hovered"
    PRESSED = "pressed"
    ACTIVE = "active"


class Button:
    """按钮容器 - 状态机和事件处理"""
    
    def __init__(self, x: int, y: int, width: int, height: int,
                 on_click: Optional[Callable] = None, midi_note: Optional[int] = None):
        self.rect = pygame.Rect(x, y, width, height)
        self.state = ButtonState.NORMAL
        self.prev_state = ButtonState.NORMAL
        self.on_click = on_click
        self.midi_note = midi_note
        
        self.key_pressed = False
        self.playback_pressed = False
        self.is_toggle = False
        self.is_active = False
        
        self.appearances: Dict[ButtonState, Callable] = {
            ButtonState.NORMAL: self._default_render,
            ButtonState.HOVERED: self._default_render,
            ButtonState.PRESSED: self._default_render,
            ButtonState.ACTIVE: self._default_render,
        }
        self.default_colors = {
            ButtonState.NORMAL: (70, 130, 180),
            ButtonState.HOVERED: (100, 150, 200),
            ButtonState.PRESSED: (50, 100, 150),
            ButtonState.ACTIVE: (200, 50, 50),
        }
    
    def _default_render(self, surface: pygame.Surface):
        color = self.default_colors.get(self.state, (70, 130, 180))
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, (100, 100, 100), self.rect, 2)
    
    def set_appearance(self, state: ButtonState, render_func: Callable) -> 'Button':
        self.appearances[state] = render_func
        return self
    
    def set_appearances(self, appearances: Dict[ButtonState, Callable]) -> 'Button':
        self.appearances.update(appearances)
        return self
    
    def update(self, mouse_pos: Tuple[int, int], mouse_pressed: bool):
        """更新按钮状态"""
        self.prev_state = self.state
        
        is_hovered = self.rect.collidepoint(mouse_pos)
        is_mouse_pressed = is_hovered and mouse_pressed
        # 优先显示按下状态（包括键盘触发和回放视觉触发），
        # 以便 toggle（is_active）按钮仍能在再次点击时被识别为按下/释放。
        if self.playback_pressed or self.key_pressed or is_mouse_pressed:
            self.state = ButtonState.PRESSED
        elif self.is_active:
            self.state = ButtonState.ACTIVE
        elif is_hovered:
            self.state = ButtonState.HOVERED
        else:
            self.state = ButtonState.NORMAL
    
    def draw(self, surface: pygame.Surface):
        """绘制按钮"""
        render_func = self.appearances.get(self.state, self._default_render)
        render_func(surface)
    
    def handle_click(self):
        """处理点击事件"""
        if self.is_toggle:
            self.is_active = not self.is_active
        
        if self.on_click:
            self.on_click(self.is_active)
    
    def set_active(self, active: bool):
        """直接设置激活状态（不触发点击）"""
        self.is_active = active 
    
    def is_clicked(self) -> bool:
        """检查按钮是否在这一帧被点击"""
        return self.prev_state != ButtonState.PRESSED and self.state == ButtonState.PRESSED
    
    def is_released(self) -> bool:
        """检查按钮是否在这一帧被释放（鼠标从按下变为正常或悬停）"""
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = self.rect.collidepoint(mouse_pos)
        mouse_pressed = pygame.mouse.get_pressed()[0]
        
        # 前一帧是按下状态，这一帧不再是按下状态
        was_pressed = self.prev_state == ButtonState.PRESSED
        is_no_longer_pressed = not mouse_pressed
        
        return was_pressed and is_no_longer_pressed and is_hovered