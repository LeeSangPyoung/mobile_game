from __future__ import annotations

from pathlib import Path
import math
import wave

import numpy as np
import soundfile as sf


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "audio" / "battle.ogg"
OUT_DIR = ROOT / "assets" / "audio"
APP_OUT_DIR = ROOT / "app" / "www" / "assets" / "audio"


def wrap_take(src: np.ndarray, start: int, length: int) -> np.ndarray:
    idx = (np.arange(length) + start) % len(src)
    out = src[idx].copy()
    fade = min(int(0.8 * SR), length // 12)
    if fade > 1:
      ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)[:, None]
      tail = src[(np.arange(fade) + start + length - fade) % len(src)]
      out[:fade] = out[:fade] * ramp + tail * (1.0 - ramp)
    return out


def add_hit(buf: np.ndarray, pos: int, mono: np.ndarray, pan: float, gain: float) -> None:
    if pos >= len(buf):
        return
    n = min(len(mono), len(buf) - pos)
    left = math.cos((pan + 1.0) * math.pi / 4.0)
    right = math.sin((pan + 1.0) * math.pi / 4.0)
    buf[pos:pos + n, 0] += mono[:n] * gain * left
    buf[pos:pos + n, 1] += mono[:n] * gain * right


def kick(sr: int) -> np.ndarray:
    n = int(sr * 0.34)
    t = np.arange(n, dtype=np.float32) / sr
    freq = 86.0 * np.exp(-t * 17.0) + 38.0
    phase = 2.0 * np.pi * np.cumsum(freq) / sr
    env = np.exp(-t * 9.0)
    click = np.exp(-t * 95.0) * np.sin(2.0 * np.pi * 1450.0 * t)
    return (np.sin(phase) * env + click * 0.18).astype(np.float32)


def snare(sr: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(sr * 0.24)
    t = np.arange(n, dtype=np.float32) / sr
    noise = rng.normal(0.0, 1.0, n).astype(np.float32)
    body = np.sin(2.0 * np.pi * 182.0 * t) * np.exp(-t * 18.0)
    env = np.exp(-t * 15.0)
    return (noise * env * 0.55 + body * 0.35).astype(np.float32)


def metal(sr: int, seed: int, dur: float = 0.42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(sr * dur)
    t = np.arange(n, dtype=np.float32) / sr
    freqs = [780.0, 1120.0, 1490.0, 2330.0]
    tone = sum(np.sin(2.0 * np.pi * f * t + rng.random() * 6.28) for f in freqs)
    tone = tone.astype(np.float32) / len(freqs)
    noise = rng.normal(0.0, 1.0, n).astype(np.float32) * 0.22
    env = np.exp(-t * 7.5)
    return (tone + noise) * env


def hat(sr: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(sr * 0.055)
    t = np.arange(n, dtype=np.float32) / sr
    noise = rng.normal(0.0, 1.0, n).astype(np.float32)
    env = np.exp(-t * 55.0)
    return noise * env


def low_pulse(sr: int, dur: float, freq: float) -> np.ndarray:
    n = int(sr * dur)
    t = np.arange(n, dtype=np.float32) / sr
    env = np.minimum(1.0, t / 0.025) * np.exp(-t * 5.5)
    return (np.sin(2.0 * np.pi * freq * t) * env).astype(np.float32)


def build_variant(src: np.ndarray, sr: int, idx: int, offset_sec: float, bpm: float, intensity: float) -> np.ndarray:
    length = int(78.0 * sr)
    base = wrap_take(src, int(offset_sec * sr), length)
    if base.shape[1] == 1:
        base = np.repeat(base, 2, axis=1)

    mix = base * (0.76 - intensity * 0.08)
    drums = np.zeros_like(mix, dtype=np.float32)
    beat = 60.0 / bpm
    step = int(beat * sr)

    k = kick(sr)
    s = snare(sr, 100 + idx)
    h = hat(sr, 200 + idx)
    m = metal(sr, 300 + idx)
    lp_a = low_pulse(sr, beat * 0.72, 55.0)
    lp_b = low_pulse(sr, beat * 0.72, 73.4)

    total_beats = int(length / step) + 2
    for b in range(total_beats):
        pos = b * step
        if b % 4 in (0, 3):
            add_hit(drums, pos, k, -0.06, 0.42 + intensity * 0.2)
        if b % 4 == 2:
            add_hit(drums, pos, s, 0.08, 0.26 + intensity * 0.16)
        if b % 2 == 1 and intensity > 0.3:
            add_hit(drums, pos, k, -0.14, 0.16 * intensity)
        if b % 8 in (0, 6):
            add_hit(drums, pos, m, 0.22, 0.12 + intensity * 0.12)
        pulse = lp_a if (b // 4) % 2 == 0 else lp_b
        if b % 2 == 0:
            add_hit(drums, pos, pulse, 0.0, 0.10 + intensity * 0.05)
        if intensity > 0.45:
            add_hit(drums, pos + step // 2, h, 0.5 if b % 2 else -0.5, 0.035 + intensity * 0.035)

    out = mix + drums
    out += np.tanh(base * (1.6 + intensity * 0.8)) * (0.05 + intensity * 0.04)
    out = np.tanh(out * (1.12 + intensity * 0.18))
    peak = float(np.max(np.abs(out))) or 1.0
    return (out / peak * 0.9).astype(np.float32)


def write_mobile_wav(path: Path, data: np.ndarray, sr: int) -> None:
    mono = np.mean(np.clip(data, -1.0, 1.0), axis=1)
    if sr == 44100:
        mono = mono[::2]
        out_sr = 22050
    else:
        out_sr = sr
    pcm16 = (mono * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(out_sr)
        wf.writeframes(pcm16.tobytes())


data, SR = sf.read(SRC, dtype="float32", always_2d=True)
if data.shape[1] > 2:
    data = data[:, :2]
peak = float(np.max(np.abs(data))) or 1.0
data = data / peak * 0.84

configs = [
    (1, 0.0, 140.0, 0.25),
    (2, 12.0, 146.0, 0.42),
    (3, 27.0, 150.0, 0.55),
    (4, 43.0, 144.0, 0.48),
    (5, 58.0, 154.0, 0.68),
]

for idx, offset, bpm, intensity in configs:
    out = build_variant(data, SR, idx, offset, bpm, intensity)
    name = f"battle{idx}.wav"
    target = OUT_DIR / name
    write_mobile_wav(target, out, SR)
    APP_OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_mobile_wav(APP_OUT_DIR / name, out, SR)
    print(f"{name}: source=battle.ogg offset={offset}s bpm={bpm} intensity={intensity}")
