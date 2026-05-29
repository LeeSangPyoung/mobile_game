from __future__ import annotations

import math
import wave
from array import array
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "audio"
SR = 22050
TAU = math.tau


def clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def softclip(v: float) -> float:
    return math.tanh(v)


def note(root: float, semi: float) -> float:
    return root * (2.0 ** (semi / 12.0))


def frac(v: float) -> float:
    return v - math.floor(v)


def tri(freq: float, t: float) -> float:
    p = frac(freq * t)
    return 4.0 * abs(p - 0.5) - 1.0


def saw(freq: float, t: float) -> float:
    return 2.0 * frac(freq * t) - 1.0


def pulse(freq: float, t: float, width: float = 0.42) -> float:
    return 1.0 if frac(freq * t) < width else -1.0


def noise(i: int, seed: int) -> float:
    x = math.sin((i + 1) * 12.9898 + seed * 78.233) * 43758.5453
    return 2.0 * frac(x) - 1.0


def env(x: float, dur: float, attack: float, release: float, hold: float = 1.0) -> float:
    if x < 0.0 or x >= dur:
        return 0.0
    if x < attack:
        return x / max(attack, 0.0001)
    if x > dur - release:
        return max(0.0, (dur - x) / max(release, 0.0001))
    return hold


def pluck(freq: float, tt: float, brightness: float = 0.45) -> float:
    body = (
        math.sin(TAU * freq * tt)
        + brightness * tri(freq * 2.01, tt)
        + brightness * 0.35 * math.sin(TAU * freq * 3.0 * tt)
    )
    return body / (1.0 + brightness * 1.35)


def flute(freq: float, t: float, tt: float, vib: float = 0.012) -> float:
    drift = 1.0 + vib * math.sin(TAU * 5.1 * t)
    f = freq * drift
    return (
        math.sin(TAU * f * tt)
        + 0.22 * math.sin(TAU * f * 2.0 * tt)
        + 0.08 * tri(f * 3.0, tt)
    ) / 1.3


def erhu(freq: float, t: float, tt: float) -> float:
    drift = 1.0 + 0.009 * math.sin(TAU * 4.4 * t)
    f = freq * drift
    return 0.68 * tri(f, tt) + 0.22 * saw(f * 2.0, tt) + 0.10 * math.sin(TAU * f * 0.5 * tt)


def low_drum(tt: float, gain: float = 1.0) -> float:
    if tt < 0.0 or tt > 0.52:
        return 0.0
    e = math.exp(-tt * 8.5)
    f = 72.0 * math.exp(-tt * 14.0) + 42.0
    return gain * math.sin(TAU * f * tt) * e


def war_kick(tt: float, gain: float = 1.0) -> float:
    if tt < 0.0 or tt > 0.36:
        return 0.0
    e = math.exp(-tt * 10.5)
    f = 98.0 * math.exp(-tt * 20.0) + 38.0
    click = math.sin(TAU * 1500.0 * tt) * math.exp(-tt * 95.0)
    return gain * (math.sin(TAU * f * tt) * e + click * 0.16)


def snare(i: int, tt: float, seed: int, gain: float = 1.0) -> float:
    if tt < 0.0 or tt > 0.24:
        return 0.0
    n = noise(i, seed)
    body = math.sin(TAU * 178.0 * tt) * math.exp(-tt * 17.0)
    return gain * (n * math.exp(-tt * 18.0) * 0.55 + body * 0.35)


def hat(i: int, tt: float, seed: int, gain: float = 1.0) -> float:
    if tt < 0.0 or tt > 0.07:
        return 0.0
    return gain * noise(i, seed) * math.exp(-tt * 58.0)


def metal(i: int, tt: float, seed: int, gain: float = 1.0) -> float:
    if tt < 0.0 or tt > 0.65:
        return 0.0
    e = math.exp(-tt * 6.2)
    n = noise(i, seed) * 0.18
    ring = (
        math.sin(TAU * 740.0 * tt)
        + math.sin(TAU * 1090.0 * tt + 1.2)
        + math.sin(TAU * 1510.0 * tt + 2.4)
        + math.sin(TAU * 2320.0 * tt + 0.8)
    ) * 0.22
    return gain * (ring + n) * e


def gong(i: int, tt: float, seed: int, root: float = 72.0, gain: float = 1.0) -> float:
    if tt < 0.0 or tt > 2.2:
        return 0.0
    e = math.exp(-tt * 1.75)
    body = (
        math.sin(TAU * root * tt)
        + 0.55 * math.sin(TAU * root * 1.51 * tt + 0.4)
        + 0.27 * math.sin(TAU * root * 2.05 * tt + 1.3)
    )
    return gain * (body * 0.34 + noise(i, seed) * math.exp(-tt * 9.0) * 0.22) * e


def event_time(beat: float, every: float, offset: float = 0.0) -> float:
    return math.floor((beat - offset) / every) * every + offset


def write_wav(name: str, seconds: float, render) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    count = int(seconds * SR)
    fade_in = int(0.9 * SR)
    fade_out = int(1.2 * SR)
    samples = array("f")
    peak = 0.001
    for i in range(count):
        t = i / SR
        v = render(t, i)
        if i < fade_in:
            v *= i / max(1, fade_in)
        elif i > count - fade_out:
            v *= max(0.0, (count - i) / max(1, fade_out))
        v = softclip(v)
        peak = max(peak, abs(v))
        samples.append(v)

    scale = 0.88 / peak
    frames = bytearray()
    for v in samples:
        frames.extend(int(clamp(v * scale) * 32767.0).to_bytes(2, "little", signed=True))

    path = OUT / name
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(frames)
    print(f"{path.relative_to(ROOT)} {seconds:.1f}s {path.stat().st_size:,} bytes")


def prep_han_court(t: float, i: int) -> float:
    bpm = 68.0
    bps = bpm / 60.0
    beat = t * bps
    root = 146.83
    scale = [0, 2, 3, 7, 9, 12]
    melody = [0, 2, 3, 7, 9, 7, 3, 2, 0, -3, 0, 2, 7, 9, 12, 9]
    bass = [0, -5, -7, -3]
    v = 0.0

    chord_root = note(root * 0.5, bass[int(beat // 8) % len(bass)])
    v += 0.13 * math.sin(TAU * chord_root * t)
    v += 0.07 * tri(chord_root * 1.5, t + 0.1)

    step = int(beat * 2)
    local = beat * 2.0 - step
    start = step / (2.0 * bps)
    f = note(root, melody[step % len(melody)])
    v += 0.27 * env(local, 0.92, 0.025, 0.52) * pluck(f, t - start, 0.58)
    if step % 4 == 2:
        v += 0.14 * env(local, 0.84, 0.025, 0.45) * pluck(f * 1.5, t - start, 0.45)

    long_step = int(beat / 2)
    long_local = beat - long_step * 2
    long_start = long_step * 2 / bps
    lf = note(root, scale[(long_step * 2 + 1) % len(scale)] + 12)
    v += 0.20 * env(long_local, 1.72, 0.15, 0.42) * flute(lf, t, t - long_start)

    hit_beat = event_time(beat, 8.0)
    v += gong(i, t - hit_beat / bps, 11, 73.0, 0.25)
    drum_beat = event_time(beat, 4.0)
    v += low_drum(t - drum_beat / bps, 0.18)
    return v


def prep_war_council(t: float, i: int) -> float:
    bpm = 76.0
    bps = bpm / 60.0
    beat = t * bps
    root = 110.0
    riff = [0, 0, 3, 5, 7, 5, 3, 0, -2, 0, 3, 7, 10, 7, 5, 3]
    v = 0.0

    drone = root * 0.5
    v += 0.15 * tri(drone, t)
    v += 0.08 * math.sin(TAU * drone * 1.5 * t + 0.6)

    step = int(beat * 2.0)
    local = beat * 2.0 - step
    start = step / (2.0 * bps)
    f = note(root, riff[step % len(riff)] + 12)
    v += 0.20 * env(local, 0.82, 0.025, 0.38) * pluck(f, t - start, 0.7)
    if step % 6 in (0, 5):
        v += 0.13 * env(local, 0.55, 0.015, 0.25) * pluck(f * 2.0, t - start, 0.5)

    bow_step = int(beat / 3.0)
    bow_local = beat - bow_step * 3.0
    bow_start = bow_step * 3.0 / bps
    bow_notes = [0, 3, 7, 10, 7, 5, 3, 0]
    bf = note(root, bow_notes[bow_step % len(bow_notes)] + 12)
    v += 0.22 * env(bow_local, 2.45, 0.35, 0.7) * erhu(bf, t, t - bow_start)

    v += low_drum(t - event_time(beat, 4.0) / bps, 0.22)
    if int(beat) % 16 == 12:
        v += gong(i, t - int(beat) / bps, 21, 82.0, 0.20)
    return v


def prep_moonlit_camp(t: float, i: int) -> float:
    bpm = 60.0
    bps = bpm / 60.0
    beat = t * bps
    root = 130.81
    melody = [0, 2, 5, 7, 10, 7, 5, 2, 0, -5, 0, 2, 5, 7, 5, 2]
    v = 0.0

    pad_note = note(root * 0.5, [0, -5, -3, -7][int(beat // 8) % 4])
    v += 0.12 * math.sin(TAU * pad_note * t)
    v += 0.06 * math.sin(TAU * pad_note * 2.0 * t + math.sin(t * 0.2) * 0.15)

    step = int(beat)
    local = beat - step
    start = step / bps
    f = note(root, melody[step % len(melody)] + 12)
    v += 0.20 * env(local, 0.88, 0.12, 0.36) * flute(f, t, t - start, 0.018)
    if step % 2 == 1:
        v += 0.16 * env(local, 0.78, 0.025, 0.48) * pluck(f * 0.5, t - start, 0.38)

    bell_step = int(beat / 4)
    bell_local = beat - bell_step * 4
    bell_start = bell_step * 4 / bps
    bell_f = note(root, [12, 17, 19, 14][bell_step % 4])
    v += 0.12 * env(bell_local, 2.2, 0.04, 1.4) * pluck(bell_f, t - bell_start, 0.22)
    v += gong(i, t - event_time(beat, 16.0) / bps, 31, 65.0, 0.16)
    return v


def battle_iron_charge(t: float, i: int) -> float:
    bpm = 150.0
    bps = bpm / 60.0
    beat = t * bps
    root = 73.42
    bass = [0, 0, 7, 5, 3, 5, 10, 7, 0, 0, 12, 10, 7, 5, 3, 2]
    theme = [12, 15, 19, 19, 17, 19, 15, 12, 19, 22, 24, 24, 19, 17, 15, 12]
    v = 0.0

    v += 0.20 * pulse(root * 0.5, t, 0.48)
    v += 0.12 * saw(root * 0.25, t)

    beat_floor = math.floor(beat)
    local_sec = t - beat_floor / bps
    v += war_kick(local_sec, 0.50)
    if beat_floor % 2 == 1:
        v += snare(i, local_sec, 101, 0.36)
    if beat_floor % 4 == 3:
        v += snare(i, local_sec + 0.08, 102, 0.15)

    half = math.floor(beat * 2.0)
    half_local = t - half / (2.0 * bps)
    v += hat(i, half_local, 103, 0.08)

    step = int(beat * 2.0)
    local = beat * 2.0 - step
    start = step / (2.0 * bps)
    f = note(root, bass[step % len(bass)])
    v += 0.36 * env(local, 0.55, 0.012, 0.17) * (0.55 * saw(f, t - start) + 0.45 * pulse(f * 0.5, t - start))

    if step % 4 == 0:
        tf = note(root, theme[(step // 4) % len(theme)])
        v += 0.33 * env(local, 1.35, 0.04, 0.35) * (0.7 * saw(tf, t - start) + 0.3 * tri(tf * 0.5, t - start))

    if beat_floor % 16 == 0:
        v += gong(i, local_sec, 111, 73.0, 0.42)
        v += metal(i, local_sec, 112, 0.34)
    if beat_floor % 8 == 6:
        v += metal(i, local_sec, 113, 0.18)
    return v * 1.05


def battle_siege_breaker(t: float, i: int) -> float:
    bpm = 132.0
    bps = bpm / 60.0
    beat = t * bps
    root = 82.41
    bass = [0, -2, 0, 5, 7, 5, 3, 0, 10, 7, 5, 3, 0, -2, -5, -2]
    hornline = [0, 7, 10, 12, 10, 7, 5, 3, 0, 3, 5, 7, 12, 10, 7, 5]
    v = 0.0

    v += 0.22 * math.sin(TAU * root * 0.25 * t)
    v += 0.16 * pulse(root * 0.5, t, 0.36)

    beat_floor = math.floor(beat)
    local_sec = t - beat_floor / bps
    if beat_floor % 4 in (0, 3):
        v += war_kick(local_sec, 0.58)
    if beat_floor % 4 == 2:
        v += snare(i, local_sec, 201, 0.40)
    if beat_floor % 8 in (0, 6):
        v += metal(i, local_sec, 202, 0.23)

    half = math.floor(beat * 2.0)
    half_local = t - half / (2.0 * bps)
    if half % 2 == 1:
        v += war_kick(half_local, 0.19)
    v += hat(i, half_local, 203, 0.055)

    step = int(beat * 2.0)
    local = beat * 2.0 - step
    start = step / (2.0 * bps)
    f = note(root, bass[step % len(bass)])
    v += 0.34 * env(local, 0.62, 0.014, 0.2) * (0.62 * saw(f, t - start) + 0.38 * pulse(f * 0.5, t - start, 0.58))

    if step % 6 == 0:
        hf = note(root, hornline[(step // 2) % len(hornline)] + 12)
        v += 0.36 * env(local, 1.95, 0.05, 0.5) * (0.62 * saw(hf, t - start) + 0.38 * tri(hf * 0.5, t - start))

    if beat_floor % 16 == 8:
        v += gong(i, local_sec, 211, 55.0, 0.48)
    if beat_floor % 32 == 24:
        alarm = note(root, 24)
        v += 0.22 * env(local_sec, 1.1, 0.03, 0.4) * saw(alarm, local_sec)
    return v * 1.1


def main() -> None:
    tracks = [
        ("prep_han_court.wav", 96.0, prep_han_court),
        ("prep_war_council.wav", 96.0, prep_war_council),
        ("prep_moonlit_camp.wav", 96.0, prep_moonlit_camp),
        ("battle_iron_charge.wav", 92.0, battle_iron_charge),
        ("battle_siege_breaker.wav", 92.0, battle_siege_breaker),
    ]
    for name, seconds, render in tracks:
        write_wav(name, seconds, render)


if __name__ == "__main__":
    main()
