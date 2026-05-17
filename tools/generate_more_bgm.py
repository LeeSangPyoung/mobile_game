from __future__ import annotations

import math
import random
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "audio"
SR = 22050


def env_pulse(t: float, start: float, dur: float, attack: float = 0.03, release: float = 0.18) -> float:
    x = t - start
    if x < 0 or x >= dur:
        return 0.0
    if x < attack:
        return x / attack
    if x > dur - release:
        return max(0.0, (dur - x) / release)
    return 1.0


def tone(freq: float, t: float, kind: str = "soft") -> float:
    if kind == "bell":
        return (
            math.sin(2 * math.pi * freq * t)
            + 0.42 * math.sin(2 * math.pi * freq * 2.01 * t)
            + 0.18 * math.sin(2 * math.pi * freq * 3.02 * t)
        ) / 1.6
    if kind == "reed":
        return math.tanh(1.7 * (math.sin(2 * math.pi * freq * t) + 0.35 * math.sin(2 * math.pi * freq * 2 * t)))
    return math.sin(2 * math.pi * freq * t) * 0.78 + math.sin(2 * math.pi * freq * 2 * t) * 0.14


def write_wav(name: str, seconds: float, render) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    n = int(seconds * SR)
    fade = int(0.45 * SR)
    data: list[int] = []
    for i in range(n):
        t = i / SR
        v = render(t)
        if i < fade:
            v *= i / fade
        elif i > n - fade:
            v *= (n - i) / fade
        v = max(-0.98, min(0.98, v))
        data.append(int(v * 32767))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        frames = bytearray()
        for s in data:
            frames.extend(int(s).to_bytes(2, "little", signed=True))
        w.writeframes(frames)
    print(path.relative_to(ROOT), f"{path.stat().st_size:,} bytes")


def calm_track(seed: int, name: str, root_freq: float, seconds: float = 52.0) -> None:
    rng = random.Random(seed)
    scale = [0, 2, 4, 7, 9, 12]
    phrase = [rng.choice(scale) for _ in range(24)]
    bass = [0, -5, -3, -7]

    def render(t: float) -> float:
        beat = t * 1.55
        step = int(beat) % len(phrase)
        note = root_freq * (2 ** (phrase[step] / 12))
        local = beat - int(beat)
        v = 0.0
        v += 0.12 * tone(root_freq * 0.5 * (2 ** (bass[int(beat / 8) % len(bass)] / 12)), t, "soft")
        v += 0.18 * env_pulse(beat, int(beat), 0.82, 0.04, 0.34) * tone(note, t, "bell")
        if step % 4 == 2:
            v += 0.08 * env_pulse(beat, int(beat), 0.65, 0.03, 0.28) * tone(note * 1.5, t, "bell")
        v += 0.018 * math.sin(2 * math.pi * 0.08 * t)
        return v

    write_wav(name, seconds, render)


def battle_track(seed: int, name: str, root_freq: float, seconds: float = 58.0) -> None:
    rng = random.Random(seed)
    scale = [0, 2, 3, 5, 7, 10, 12]
    riff = [0, 0, 7, 5, 3, 5, 10, 7, 0, 0, 12, 10, 7, 5, 3, 2]
    lead = [riff[i % len(riff)] + rng.choice([0, 0, 0, 12]) for i in range(64)]
    drum_noise = [rng.uniform(-1, 1) for _ in range(int(seconds * 64) + 64)]

    def noise_at(t: float) -> float:
        idx = int(t * 64)
        return drum_noise[idx % len(drum_noise)]

    def render(t: float) -> float:
        beat = t * 3.15
        whole = int(beat)
        frac = beat - whole
        note = root_freq * (2 ** (lead[whole % len(lead)] / 12))
        v = 0.0
        # Marching low engine.
        v += 0.23 * tone(root_freq * 0.5, t, "reed")
        v += 0.12 * tone(root_freq * 0.25, t, "soft")

        # Aggressive ostinato: short brass-like stabs.
        v += 0.26 * env_pulse(beat, whole, 0.50, 0.012, 0.13) * tone(note, t, "reed")
        if whole % 2 == 0:
            v += 0.16 * env_pulse(beat, whole, 0.44, 0.01, 0.11) * tone(note * 2, t, "reed")

        # Kick on 1 and 3, snare/noise on off beats, quick hats every half beat.
        if whole % 4 in (0, 2):
            v += 0.30 * env_pulse(frac, 0, 0.22, 0.003, 0.14) * (tone(58, t, "soft") + 0.35 * noise_at(t))
        if whole % 4 in (1, 3):
            v += 0.17 * env_pulse(frac, 0, 0.15, 0.003, 0.10) * noise_at(t)
        half = (beat * 2) - int(beat * 2)
        v += 0.035 * env_pulse(half, 0, 0.07, 0.002, 0.05) * noise_at(t)

        # Periodic alarm hits.
        if whole % 16 in (14, 15):
            alarm = root_freq * (2 ** (scale[(whole + seed) % len(scale)] / 12)) * 2
            v += 0.15 * env_pulse(beat, whole, 0.72, 0.02, 0.24) * tone(alarm, t, "bell")
        return v

    write_wav(name, seconds, render)


def main() -> None:
    calm_track(41, "calm4.wav", 196.0)
    calm_track(73, "calm5.wav", 174.6)
    battle_track(101, "battle1.wav", 146.8)
    battle_track(202, "battle2.wav", 164.8)
    battle_track(303, "battle3.wav", 130.8)
    battle_track(404, "battle4.wav", 185.0)
    battle_track(505, "battle5.wav", 155.6)


if __name__ == "__main__":
    main()
