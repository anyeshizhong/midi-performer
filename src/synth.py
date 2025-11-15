import sys
import pygame

try :
    import numpy as np
except ImportError:
    print("错误：未找到 'numpy' 库。")
    print("请使用 'pip install numpy' 来安装它。")
    sys.exit()
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
    