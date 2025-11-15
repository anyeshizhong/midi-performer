import pygame
import sys
import os
from typing import Callable, Optional, Tuple, Dict, List
from enum import Enum
import time

# ==================== 库导入 ====================
try:
    import numpy as np
except ImportError:
    print("错误：未找到 'numpy' 库。")
    print("请使用 'pip install numpy' 来安装它。")
    sys.exit()

try:
    from mido import Message, MidiFile, MidiTrack, MetaMessage
except ImportError:
    print("错误：未找到 'mido' 库。")
    print("请使用 'pip install mido' 来安装它。")
    sys.exit()

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except ImportError:
    print("错误：未找到 'tkinter' 库。")
    sys.exit()

# ==================== 状态枚举 ====================
class ButtonState(Enum):
    """按钮状态枚举"""
    NORMAL = "normal"
    HOVERED = "hovered"
    PRESSED = "pressed"
    ACTIVE = "active"


# ==================== WordProcess 类 ====================
class WordProcess:
    """文字处理类"""
    
    def __init__(self, text: str = "", font_size: int = 24, 
                 color: Tuple = (255, 255, 255), font_name: Optional[str] = None):
        self.text = text
        self.base_font_size = font_size
        self.current_font_size = font_size
        self.base_color = color
        self.current_color = color
        self.font_name = font_name
        
        self.bold = False
        self.italic = False
        self.underline = False
        self.brightness = 0
    
    def size(self, scale: float) -> 'WordProcess':
        if scale <= 0:
            raise ValueError("缩放倍数必须为正数")
        self.current_font_size = int(self.base_font_size * scale)
        return self
    
    def color(self, r: int, g: int, b: int) -> 'WordProcess':
        self.current_color = (max(0, min(255, r)), 
                              max(0, min(255, g)), 
                              max(0, min(255, b)))
        return self
    
    def light(self, amount: int) -> 'WordProcess':
        self.brightness = min(255, self.brightness + amount)
        self._apply_brightness()
        return self
    
    def dark(self, amount: int) -> 'WordProcess':
        self.brightness = max(-255, self.brightness - amount)
        self._apply_brightness()
        return self
    
    def _apply_brightness(self):
        r = max(0, min(255, self.base_color[0] + self.brightness))
        g = max(0, min(255, self.base_color[1] + self.brightness))
        b = max(0, min(255, self.base_color[2] + self.brightness))
        self.current_color = (r, g, b)
        return self
    
    def bold(self, enabled: bool = True) -> 'WordProcess':
        self.bold = enabled
        return self
    
    def italic(self, enabled: bool = True) -> 'WordProcess':
        self.italic = enabled
        return self
    
    def reset(self) -> 'WordProcess':
        self.current_font_size = self.base_font_size
        self.current_color = self.base_color
        self.bold = False
        self.italic = False
        self.underline = False
        self.brightness = 0
        return self

    def _get_font(self) -> pygame.font.Font:
        font = pygame.font.Font(self.font_name, self.current_font_size)
        font.set_bold(self.bold)
        font.set_italic(self.italic)
        font.set_underline(self.underline)
        return font

    def render(self) -> pygame.Surface:
        font = self._get_font()
        return font.render(self.text, True, self.current_color)
    
    def get_size(self) -> Tuple[int, int]:
        font = self._get_font()
        return font.size(self.text)


# ==================== 音频生成器 (改进版本) ====================
class SynthGenerator:
    """改进的正弦波合成器 - 更真实的音色"""
    
    MIDI_NOTE_NAMES = {
        60: "C4", 61: "C#4", 62: "D4", 63: "D#4", 64: "E4", 65: "F4",
        66: "F#4", 67: "G4", 68: "G#4", 69: "A4", 70: "A#4", 71: "B4",
        72: "C5", 73: "C#5", 74: "D5", 75: "D#5", 76: "E5", 77: "F5",
        78: "F#5", 79: "G5", 80: "G#5", 81: "A5", 82: "A#5", 83: "B5", 84: "C6"
    }
    
    A4_FREQ = 440.0
    A4_MIDI = 69
    
    @staticmethod
    def midi_to_frequency(midi_note: int) -> float:
        """MIDI 音符号到频率的转换"""
        return SynthGenerator.A4_FREQ * (2.0 ** ((midi_note - SynthGenerator.A4_MIDI) / 12.0))
    
    @staticmethod
    def generate_tone(frequency: float, duration_ms: int, 
                      sample_rate: int = 44100, volume: float = 0.3) -> pygame.mixer.Sound:
        """
        生成改进的音色：
        - 主波形（正弦波）+ 谐音添加
        - 更平滑的 ADSR 包络
        - 更自然的衰减
        """
        num_samples = int(sample_rate * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, num_samples, False)
        
        # 主波形（带谐音）
        fundamental = np.sin(2 * np.pi * frequency * t)
        # 添加第二泛音（1/4 振幅）
        harmonic2 = 0.25 * np.sin(2 * np.pi * frequency * 2 * t)
        # 添加第三泛音（1/8 振幅）
        harmonic3 = 0.125 * np.sin(2 * np.pi * frequency * 3 * t)
        
        wave = fundamental + harmonic2 + harmonic3
        
        # 改进的 ADSR 包络
        attack_time = 0.02  # 20ms
        decay_time = 0.05   # 50ms
        sustain_level = 0.7
        release_time = 0.5  # 500ms
        
        attack_samples = int(sample_rate * attack_time)
        decay_samples = int(sample_rate * decay_time)
        release_samples = int(sample_rate * release_time)
        sustain_samples = num_samples - attack_samples - decay_samples - release_samples
        
        envelope = np.ones(num_samples)
        
        # Attack: 0 -> 1
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Decay: 1 -> sustain_level
        if decay_samples > 0:
            envelope[attack_samples:attack_samples + decay_samples] = \
                np.linspace(1, sustain_level, decay_samples)
        
        # Sustain: 保持在 sustain_level
        sustain_start = attack_samples + decay_samples
        sustain_end = sustain_start + sustain_samples
        if sustain_end > sustain_start:
            envelope[sustain_start:sustain_end] = sustain_level
        
        # Release: sustain_level -> 0
        if release_samples > 0:
            envelope[-release_samples:] = np.linspace(sustain_level, 0, release_samples)
        
        wave = wave * envelope * volume
        
        # 转换为 16 位 PCM
        wave_int16 = np.clip(wave * 32767, -32768, 32767).astype(np.int16)
        
        # 创建立体声
        stereo = np.zeros((len(wave_int16), 2), dtype=np.int16)
        stereo[:, 0] = wave_int16
        stereo[:, 1] = wave_int16
        
        sound = pygame.mixer.Sound(buffer=stereo.tobytes())
        return sound


# ==================== 按钮类 ====================
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


# ==================== MIDI 演奏器应用 ====================
class MidiPerformer:
    """MIDI 演奏器 - 支持录制、回放、保存、加载"""
    
    def __init__(self, screen_width: int = 1200, screen_height: int = 550):
        pygame.display.set_caption("MIDI 演奏器 (带录制、保存、加载)")
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        self.clock = pygame.time.Clock()
        
        pygame.mixer.init(frequency=44100, size=-16, channels=16, buffer=256)
        
        self.font_title = pygame.font.Font(None, 32)
        self.font_label = pygame.font.Font(None, 18)
        self.font_status = pygame.font.Font(None, 28)
        
        # sound_cache keyed by (midi_note, duration_ms)
        self.sound_cache: Dict[Tuple[int, int], pygame.mixer.Sound] = {}
        
        self.buttons: List[Button] = []
        self.key_to_button: Dict[int, Button] = {}
        self.note_to_button: Dict[int, Button] = {}
        
        self.start_midi = 60
        self.end_midi = 84
        
        self.is_recording = False
        self.is_playing_back = False
        self.recorded_track: List[Tuple[int, int]] = []
        self.recording_start_time = 0
        self.playback_start_time = 0
        self.playback_note_index = 0
        
        self.current_file_name = "未命名.mid"
        
        self.PLAYBACK_NOTE_OFF_EVENT = pygame.USEREVENT + 1

        # 播放设置
        self.master_volume = 0.8
        self.note_duration_ms = 1000  # 每个生成音的时长（可由 sustain 控制）
        self.volume_rect: Optional[pygame.Rect] = None
        self.volume_dragging = False

        self._create_buttons()
    
    def _create_standard_renderer(
        self, 
        button: Button, 
        text_getter: Callable[[], str],
        colors: Dict[ButtonState, Tuple[int, int, int]],
        font_size: int = 18
    ) -> Callable:
        """渲染器工厂"""
        def render(surface: pygame.Surface):
            state = button.state
            rect = button.rect
            
            color = colors.get(state, colors[ButtonState.NORMAL])
            pygame.draw.rect(surface, color, rect, border_radius=5)
            pygame.draw.rect(surface, (100, 100, 100), rect, 2, border_radius=5)
            
            text = text_getter()
            word = WordProcess(text, font_size, (255, 255, 255))
            
            if state == ButtonState.HOVERED:
                word.size(1.1)
            
            text_surf = word.render()
            text_rect = text_surf.get_rect(center=rect.center)
            surface.blit(text_surf, text_rect)
            
        return render

    def _create_buttons(self):
        """创建所有按钮"""
        
        # --- 控制按钮（居中排列） ---
        control_y = 70
        btn_width, btn_height = 110, 48
        margin = 14
        center_x = self.screen.get_width() / 2
        # 我们会放 6 个控制按钮：Record, Play, Stop, Save, Load, Sustain
        num_controls = 6
        total_controls_width = num_controls * btn_width + (num_controls - 1) * margin
        start_x = center_x - total_controls_width / 2
        
        # 录制按钮
        btn_record = Button(start_x, control_y, btn_width, btn_height, 
                            on_click=self._on_record_click)
        btn_record.is_toggle = True
        
        rec_colors = {
            ButtonState.NORMAL: (180, 50, 50),
            ButtonState.HOVERED: (220, 70, 70),
            ButtonState.PRESSED: (150, 30, 30),
            ButtonState.ACTIVE: (255, 0, 0),
        }
        rec_renderer = self._create_standard_renderer(
            btn_record,
            lambda: "Recording" if btn_record.is_active else "Record",
            rec_colors
        )
        btn_record.set_appearances({s: rec_renderer for s in ButtonState})
        self.buttons.append(btn_record)

        # 播放按钮
        btn_play = Button(start_x + btn_width + margin, control_y, btn_width, btn_height,
                          on_click=self._on_play_click)
        btn_play.is_toggle = True
        
        play_colors = {
            ButtonState.NORMAL: (50, 150, 100),
            ButtonState.HOVERED: (70, 180, 120),
            ButtonState.PRESSED: (30, 120, 80),
            ButtonState.ACTIVE: (0, 255, 0),
        }
        play_renderer = self._create_standard_renderer(
            btn_play,
            lambda: "Playing" if btn_play.is_active else "Play",
            play_colors
        )
        btn_play.set_appearances({s: play_renderer for s in ButtonState})
        self.buttons.append(btn_play)

        # 停止按钮
        btn_stop = Button(start_x + (btn_width + margin) * 2, control_y, btn_width, btn_height,
                          on_click=self._on_stop_click)
        
        stop_colors = {
            ButtonState.NORMAL: (70, 130, 180),
            ButtonState.HOVERED: (100, 150, 200),
            ButtonState.PRESSED: (50, 100, 150),
            ButtonState.ACTIVE: (70, 130, 180),
        }
        stop_renderer = self._create_standard_renderer(
            btn_stop, lambda: "Stop", stop_colors
        )
        btn_stop.set_appearances({s: stop_renderer for s in ButtonState})
        self.buttons.append(btn_stop)
        
        # 保存按钮
        btn_save = Button(start_x + (btn_width + margin) * 3, control_y, btn_width, btn_height,
                          on_click=self._on_save_click)
        
        save_colors = {
            ButtonState.NORMAL: (100, 100, 180),
            ButtonState.HOVERED: (130, 130, 210),
            ButtonState.PRESSED: (80, 80, 150),
            ButtonState.ACTIVE: (100, 100, 180),
        }
        save_renderer = self._create_standard_renderer(
            btn_save, lambda: "Save", save_colors
        )
        btn_save.set_appearances({s: save_renderer for s in ButtonState})
        self.buttons.append(btn_save)
        
        # 加载按钮
        btn_load = Button(start_x + (btn_width + margin) * 4, control_y, btn_width, btn_height,
                          on_click=self._on_load_click)
        
        load_colors = {
            ButtonState.NORMAL: (150, 100, 180),
            ButtonState.HOVERED: (180, 130, 210),
            ButtonState.PRESSED: (120, 80, 150),
            ButtonState.ACTIVE: (150, 100, 180),
        }
        load_renderer = self._create_standard_renderer(
            btn_load, lambda: "Load", load_colors
        )
        btn_load.set_appearances({s: load_renderer for s in ButtonState})
        self.buttons.append(btn_load)
        
        # Sustain 按钮（延长音符时长）
        btn_sustain = Button(start_x + (btn_width + margin) * 5, control_y, btn_width, btn_height,
                             on_click=self._on_sustain_click)
        btn_sustain.is_toggle = True
        sustain_colors = {
            ButtonState.NORMAL: (140, 115, 60),
            ButtonState.HOVERED: (170, 140, 80),
            ButtonState.PRESSED: (120, 90, 40),
            ButtonState.ACTIVE: (200, 170, 80),
        }
        sustain_renderer = self._create_standard_renderer(
            btn_sustain, lambda: "Sustain" if btn_sustain.is_active else "Sustain", sustain_colors
        )
        btn_sustain.set_appearances({s: sustain_renderer for s in ButtonState})
        self.buttons.append(btn_sustain)

        # 设置音量滑块位置（紧随控制按钮下方）
        self.volume_rect = pygame.Rect(int(center_x - 150), int(control_y + btn_height + 12), 300, 12)
        
        # --- 琴键按钮 ---
        key_width = 38
        key_height = 140
        key_margin = 2
        
        total_keys = (self.end_midi - self.start_midi + 1)
        total_key_width = (total_keys * key_width) + ((total_keys - 1) * key_margin)
        key_start_x = (self.screen.get_width() - total_key_width) / 2
        key_start_y = 260
        
        keyboard_map = {
            pygame.K_z: 60, pygame.K_s: 61, pygame.K_x: 62, pygame.K_d: 63,
            pygame.K_c: 64, pygame.K_v: 65, pygame.K_g: 66, pygame.K_b: 67,
            pygame.K_h: 68, pygame.K_n: 69, pygame.K_j: 70, pygame.K_m: 71,
            pygame.K_q: 72, pygame.K_2: 73, pygame.K_w: 74, pygame.K_3: 75,
            pygame.K_e: 76, pygame.K_r: 77, pygame.K_5: 78, pygame.K_t: 79,
            pygame.K_6: 80, pygame.K_y: 81, pygame.K_7: 82, pygame.K_u: 83,
            pygame.K_i: 84
        }
        
        note_idx = 0
        for midi_note in range(self.start_midi, self.end_midi + 1):
            is_black_key = SynthGenerator.MIDI_NOTE_NAMES.get(midi_note, "").endswith("#")
            
            x = key_start_x + note_idx * (key_width + key_margin)
            y = key_start_y
            
            current_width = key_width
            current_height = key_height
            if is_black_key:
                current_width = key_width * 0.7
                current_height = key_height * 0.6
                x -= (key_width + key_margin) * 0.15
                y -= key_height * 0.05
            
            button = Button(x, y, current_width, current_height,
                            on_click=lambda active, note=midi_note: self._play_note(note),
                            midi_note=midi_note)
            
            self._setup_key_appearance(button, is_black_key)
            
            self.buttons.append(button)
            self.note_to_button[midi_note] = button
            note_idx += 1
            
            for key, note in keyboard_map.items():
                if note == midi_note:
                    self.key_to_button[key] = button

    def _setup_key_appearance(self, button: Button, is_black_key: bool):
        """设置琴键外观"""
        
        normal_color = (20, 20, 20) if is_black_key else (245, 245, 245)
        hover_color = (60, 60, 60) if is_black_key else (220, 220, 255)
        pressed_color = (50, 150, 100)
        
        text_color = (200, 200, 200) if is_black_key else (50, 50, 50)
        
        def make_renderer(btn):
            def render(surface: pygame.Surface):
                state = btn.state
                rect = btn.rect
                
                if state == ButtonState.PRESSED or state == ButtonState.ACTIVE:
                    color = pressed_color
                elif state == ButtonState.HOVERED:
                    color = hover_color
                else:
                    color = normal_color
                
                pygame.draw.rect(surface, color, rect, border_radius=3)
                pygame.draw.rect(surface, (100, 100, 100), rect, 1, border_radius=3)
                
                if btn.midi_note is not None:
                    note_name = SynthGenerator.MIDI_NOTE_NAMES.get(btn.midi_note, "")
                    word = WordProcess(note_name, 12, text_color)
                    text_surf = word.render()
                    text_rect = text_surf.get_rect(centerx=rect.centerx, bottom=rect.bottom - 5)
                    surface.blit(text_surf, text_rect)
            
            return render
        
        renderer = make_renderer(button)
        button.set_appearances({s: renderer for s in ButtonState})

    # --- 控制器回调 ---

    def _on_record_click(self, is_active: bool):
        """处理录制按钮点击"""
        if is_active:
            self.is_recording = True
            self.is_playing_back = False
            for btn in self.buttons:
                if btn.on_click == self._on_play_click:
                    btn.set_active(False)
            
            self.recorded_track = []
            self.recording_start_time = pygame.time.get_ticks()
            print("--- 开始录制 ---")
        else:
            self.is_recording = False
            print(f"--- 停止录制. 录制了 {len(self.recorded_track)} 个音符 ---")

    def _on_play_click(self, is_active: bool):
        """处理播放按钮点击"""
        if is_active:
            if not self.recorded_track:
                print("没有录制内容可播放")
                for btn in self.buttons:
                    if btn.on_click == self._on_play_click:
                        btn.set_active(False)
                return

            self.is_playing_back = True
            self.is_recording = False
            for btn in self.buttons:
                if btn.on_click == self._on_record_click:
                    btn.set_active(False)
            
            self.playback_start_time = pygame.time.get_ticks()
            self.playback_note_index = 0
            print("--- 开始播放 ---")
        else:
            self.is_playing_back = False
            print("--- 停止播放 ---")

    def _on_stop_click(self, is_active: bool):
        """处理停止按钮点击"""
        print("--- 全部停止 ---")
        self.is_recording = False
        self.is_playing_back = False
        
        for btn in self.buttons:
            if btn.on_click == self._on_record_click or btn.on_click == self._on_play_click:
                btn.set_active(False)
        
        pygame.mixer.stop()

    def _on_save_click(self, is_active: bool):
        """处理保存按钮点击"""
        if not self.recorded_track:
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning("警告", "没有录制内容可保存")
            root.destroy()
            return
        
        root = tk.Tk()
        root.withdraw()
        
        file_path = filedialog.asksaveasfilename(
            title="保存 MIDI 文件",
            defaultextension=".mid",
            filetypes=[("MIDI 文件", "*.mid"), ("所有文件", "*.*")],
            initialfile=self.current_file_name
        )
        root.destroy()
        
        if file_path:
            self._save_midi_file(file_path)

    def _on_load_click(self, is_active: bool):
        """处理加载按钮点击"""
        root = tk.Tk()
        root.withdraw()
        
        file_path = filedialog.askopenfilename(
            title="打开 MIDI 文件",
            filetypes=[("MIDI 文件", "*.mid *.midi"), ("所有文件", "*.*")]
        )
        root.destroy()
        
        if file_path:
            self._load_midi_file(file_path)

    def _save_midi_file(self, file_path: str):
        """保存为 MIDI 文件"""
        try:
            mid = MidiFile()
            track = MidiTrack()
            mid.tracks.append(track)
            
            # 转换录制的时间戳为 MIDI 时间（使用 ticks_per_beat）
            ticks_per_beat = 480
            bpm = 120
            microseconds_per_beat = 60 * 1000000 // bpm
            
            # 添加速度元事件
            track.append(MetaMessage('set_tempo', tempo=microseconds_per_beat))
            
            # 转换毫秒为 MIDI tick
            # 1 beat = microseconds_per_beat microseconds
            # 1 ms = 1000 microseconds
            # tick = (ms / 1000) * (bpm / 60) * ticks_per_beat
            
            current_time_ticks = 0
            
            for timestamp_ms, midi_note in self.recorded_track:
                # 转换毫秒到 tick
                time_ticks = int((timestamp_ms / 1000.0) * (bpm / 60.0) * ticks_per_beat)
                delta_ticks = time_ticks - current_time_ticks
                
                # Note On
                track.append(Message('note_on', note=midi_note, velocity=100, time=delta_ticks))
                current_time_ticks = time_ticks
            
            # 在所有音符之后添加 Note Off 消息
            for midi_note in set(note for _, note in self.recorded_track):
                track.append(Message('note_off', note=midi_note, velocity=0, time=0))
            
            mid.save(file_path)
            self.current_file_name = os.path.basename(file_path)
            
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("成功", f"已保存到: {os.path.basename(file_path)}")
            root.destroy()
            
            print(f"✓ 已保存 MIDI 文件: {file_path}")
        
        except Exception as e:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("错误", f"保存失败: {str(e)}")
            root.destroy()
            print(f"✗ 保存失败: {e}")

    def _load_midi_file(self, file_path: str):
        """加载 MIDI 文件"""
        try:
            mid = MidiFile(file_path)
            
            # 清空旧数据
            self._on_stop_click(True)
            self.recorded_track = []
            
            # 提取事件
            bpm = 120
            microseconds_per_beat = 60 * 1000000 // bpm
            ticks_per_beat = 480
            
            current_time_ms = 0
            
            for msg in mid.tracks[0]:
                if msg.type == 'set_tempo':
                    microseconds_per_beat = msg.tempo
                
                elif msg.type == 'note_on' and msg.velocity > 0:
                    # 转换 tick 到毫秒
                    # ms = (tick / ticks_per_beat) * (microseconds_per_beat / 1000000) * 1000
                    time_ms = int((msg.time / ticks_per_beat) * (microseconds_per_beat / 1000000) * 1000)
                    current_time_ms += time_ms
                    
                    self.recorded_track.append((current_time_ms, msg.note))
            
            self.current_file_name = os.path.basename(file_path)
            
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("成功", f"已加载: {os.path.basename(file_path)}\n音符数: {len(self.recorded_track)}")
            root.destroy()
            
            print(f"✓ 已加载 MIDI 文件: {file_path} ({len(self.recorded_track)} 个音符)")
        
        except Exception as e:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("错误", f"加载失败: {str(e)}")
            root.destroy()
            print(f"✗ 加载失败: {e}")

    def _on_sustain_click(self, is_active: bool):
        """处理 Sustain 按钮：切换音符生成时长"""
        if is_active:
            self.note_duration_ms = 2000
            print("Sustain ON: 音符时长延长")
        else:
            self.note_duration_ms = 1000
            print("Sustain OFF: 使用默认音符时长")

    def _play_note(self, midi_note: int):
        """播放音符，并处理录制"""
        
        # 录制
        if self.is_recording:
            current_time = pygame.time.get_ticks()
            timestamp = current_time - self.recording_start_time
            self.recorded_track.append((timestamp, midi_note))
            print(f"录制: Note {midi_note} @ {timestamp}ms")

        # 生成或获取缓存的音频
        duration_ms = int(self.note_duration_ms)
        cache_key = (midi_note, duration_ms)

        if cache_key not in self.sound_cache:
            frequency = SynthGenerator.midi_to_frequency(midi_note)
            snd = SynthGenerator.generate_tone(frequency, duration_ms=duration_ms, volume=0.3)
            self.sound_cache[cache_key] = snd

        # 播放音频（设置主音量）
        sound = self.sound_cache[cache_key]
        try:
            sound.set_volume(self.master_volume)
        except Exception:
            pass
        sound.play()
    
    def _trigger_playback_press(self, midi_note: int):
        """用于视觉回放，触发按钮按下"""
        if midi_note in self.note_to_button:
            button = self.note_to_button[midi_note]
            button.playback_pressed = True
            
            event = pygame.event.Event(self.PLAYBACK_NOTE_OFF_EVENT, note=midi_note)
            pygame.time.set_timer(event, 200, 1)

    def handle_events(self):
        """处理事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == self.PLAYBACK_NOTE_OFF_EVENT:
                if event.note in self.note_to_button:
                    self.note_to_button[event.note].playback_pressed = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key in self.key_to_button:
                    button = self.key_to_button[event.key]
                    if not button.key_pressed:
                        button.key_pressed = True
                        button.handle_click()
                        print(f"键盘: {SynthGenerator.MIDI_NOTE_NAMES.get(button.midi_note, '')}")
            
            elif event.type == pygame.KEYUP:
                if event.key in self.key_to_button:
                    button = self.key_to_button[event.key]
                    button.key_pressed = False
            
            # 音量滑块交互
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and self.volume_rect is not None:
                    if self.volume_rect.collidepoint(event.pos):
                        self.volume_dragging = True
                        # 立刻更新音量
                        rel_x = event.pos[0] - self.volume_rect.x
                        self.master_volume = max(0.0, min(1.0, rel_x / self.volume_rect.width))
                        print(f"音量: {int(self.master_volume*100)}%")

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and self.volume_dragging:
                    self.volume_dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if self.volume_dragging and self.volume_rect is not None:
                    rel_x = event.pos[0] - self.volume_rect.x
                    self.master_volume = max(0.0, min(1.0, rel_x / self.volume_rect.width))
                    # 这里不打印太多信息，直接设置音量
        
        return True
    
    def update(self):
        """更新状态"""
        
        # 处理回放
        if self.is_playing_back:
            if self.playback_note_index >= len(self.recorded_track):
                # 等待最后一个音的自然尾声结束后再结束播放（避免最后一个音被立即 stop 中断）
                if self.recorded_track:
                    last_ts = self.recorded_track[-1][0]
                else:
                    last_ts = 0

                current_time = pygame.time.get_ticks()
                playback_elapsed = current_time - self.playback_start_time

                if playback_elapsed >= last_ts + int(self.note_duration_ms):
                    # 播放真正结束：只关闭播放状态，不强制停止混音器
                    self.is_playing_back = False
                    for btn in self.buttons:
                        if btn.on_click == self._on_play_click:
                            btn.set_active(False)
                    print("--- 播放结束（自然收尾） ---")
                # else: 等待音频自然结束
            else:
                current_time = pygame.time.get_ticks()
                playback_time = current_time - self.playback_start_time
                
                note_timestamp, note_midi = self.recorded_track[self.playback_note_index]
                
                if playback_time >= note_timestamp:
                    print(f"回放: Note {note_midi}")
                    self._play_note(note_midi)
                    self._trigger_playback_press(note_midi)
                    
                    self.playback_note_index += 1

        # 更新所有按钮
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]
        
        for button in self.buttons:
            button.update(mouse_pos, mouse_pressed)
            
            # [修复] 只在鼠标真正释放时才触发点击（is_released）
            if button.is_released() and not button.key_pressed and not button.playback_pressed:
                note_name = SynthGenerator.MIDI_NOTE_NAMES.get(button.midi_note, 'UI Button')
                if note_name:
                    print(f"鼠标: {note_name}")
                button.handle_click()
    
    def draw(self):
        """绘制演奏器"""
        self.screen.fill((40, 40, 40))
        
        # 标题
        title = self.font_title.render("MIDI 演奏器 (录制、保存、加载)", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.screen.get_width() / 2, 30))
        self.screen.blit(title, title_rect)
        
        # 提示文本
        hint = self.font_label.render("键盘: Z-M (白键) S/D/G/H/J (黑键) | Q-I (上排)", True, (200, 200, 200))
        hint_rect = hint.get_rect(center=(self.screen.get_width() / 2, 50))
        self.screen.blit(hint, hint_rect)
        
        # 文件名
        file_text = f"当前文件: {self.current_file_name}"
        file_surf = self.font_label.render(file_text, True, (180, 180, 180))
        file_rect = file_surf.get_rect(center=(self.screen.get_width() / 2, 155))
        self.screen.blit(file_surf, file_rect)
        
        # 状态
        status_text = ""
        status_color = (255, 255, 255)
        if self.is_recording:
            status_text = "● 录制中"
            status_color = (255, 0, 0)
        elif self.is_playing_back:
            status_text = "▶ 播放中"
            status_color = (0, 255, 0)
        else:
            status_text = "■ 已停止"
            status_color = (200, 200, 200)
            
        status_surf = self.font_status.render(status_text, True, status_color)
        status_rect = status_surf.get_rect(center=(self.screen.get_width() / 2, 190))
        self.screen.blit(status_surf, status_rect)
        
        # 音量滑块
        if self.volume_rect is not None:
            # 背景轨道
            pygame.draw.rect(self.screen, (120, 120, 120), self.volume_rect, border_radius=6)
            # 已填充部分
            filled_width = int(self.volume_rect.width * self.master_volume)
            filled_rect = pygame.Rect(self.volume_rect.x, self.volume_rect.y, filled_width, self.volume_rect.height)
            pygame.draw.rect(self.screen, (70, 200, 120), filled_rect, border_radius=6)
            # 拖动手柄
            handle_x = int(self.volume_rect.x + filled_width)
            handle_y = int(self.volume_rect.y + self.volume_rect.height / 2)
            pygame.draw.circle(self.screen, (230, 230, 230), (handle_x, handle_y), 8)
            # 标签
            vol_label = self.font_label.render(f"Volume: {int(self.master_volume*100)}%", True, (200, 200, 200))
            vol_label_rect = vol_label.get_rect(center=(self.volume_rect.centerx, self.volume_rect.y - 12))
            self.screen.blit(vol_label, vol_label_rect)
        
        # 绘制所有按钮
        for button in self.buttons:
            button.draw(self.screen)
        
        pygame.display.flip()
    
    def run(self):
        """运行演奏器"""
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()


# ==================== 主程序 ====================
if __name__ == "__main__":
    pygame.init()
    performer = MidiPerformer()
    performer.run()