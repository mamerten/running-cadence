"""Generate royalty-free running-cadence beat tracks as MP3s.

One beat = one footstep: there is a kick on every step. Three styles
(drumline, rock, electro) are spread across each 5-spm bucket so every
bucket has a few different-sounding options.

Usage:  python tools/make_cadence_tracks.py
Needs:  pip install numpy lameenc
"""
import pathlib
import numpy as np
import lameenc

SR = 44100
MINUTES = 10
BUCKETS = range(150, 190, 5)          # 150-154, 155-159, ... 185-189
STYLES = ["drumline", "rock", "electro"]
OUT = pathlib.Path(__file__).resolve().parent.parent / "public" / "generated"
rng = np.random.default_rng(7)


# ---------- instruments ----------

def env(n, decay):
    return np.exp(-np.arange(n) / (SR * decay))


def kick(depth=110):
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    freq = 45 + depth * np.exp(-t * 30)        # pitch drop = punch
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * env(n, 0.12)


def snare(tone_hz=190, decay=0.07):
    n = int(SR * 0.25)
    t = np.arange(n) / SR
    noise = rng.uniform(-1, 1, n)
    noise = noise - np.concatenate(([0], noise[:-1])) * 0.6
    return 0.7 * noise * env(n, decay) + 0.5 * np.sin(2 * np.pi * tone_hz * t) * env(n, 0.04)


def clap():
    n = int(SR * 0.2)
    noise = np.diff(rng.uniform(-1, 1, n), prepend=0)
    bursts = sum(np.roll(env(n, 0.006), int(SR * d)) for d in (0, 0.01, 0.02))
    return noise * (bursts * 0.5 + env(n, 0.05))


def hat(length=0.04, decay=0.012):
    n = int(SR * length)
    return np.diff(rng.uniform(-1, 1, n), prepend=0) * env(n, decay)


def crash():
    n = int(SR * 1.5)
    return np.diff(rng.uniform(-1, 1, n), prepend=0) * env(n, 0.5)


def bass(freq, dur, drive=1.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    wave = sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, 7))
    a = np.minimum(1, np.arange(n) / (SR * 0.005))
    out = wave * a * env(n, dur * 0.6)
    return np.tanh(out * drive) if drive > 1 else out


def pluck(freq, dur):
    n = int(SR * dur)
    t = np.arange(n) / SR
    wave = sum(np.sin(2 * np.pi * freq * k * t) / k for k in (1, 3, 5))   # square-ish
    return wave * env(n, dur * 0.4)


def place(buf, sample, start, gain):
    end = min(len(buf), start + len(sample))
    if start < len(buf):
        buf[start:end] += gain * sample[: end - start]


# ---------- styles ----------
# Root notes in Hz, one chord per bar.
PROG = {
    "drumline": [55.0, 43.65, 65.41, 49.0],     # Am F C G
    "rock":     [41.2, 65.41, 73.42, 55.0],     # E  C D A
    "electro":  [73.42, 58.27, 87.31, 65.41],   # Dm Bb F C
}


def render(bpm, style):
    beat = 60.0 / bpm
    bars = int(MINUTES * 60 / (beat * 4))      # whole bars -> clean loop
    buf = np.zeros(int(round(bars * 4 * beat * SR)))
    K = kick(140 if style == "rock" else 110)
    S = snare(220, 0.09) if style == "rock" else snare()
    C, H, HO, CR = clap(), hat(), hat(0.12, 0.05), crash()
    prog = PROG[style]

    for bar in range(bars):
        section = (bar // 16) % 4               # change feel every 16 bars
        intro = bar < 4 and style != "electro"  # electro starts full-on
        root = prog[bar % 4]
        for b in range(4):
            t0 = (bar * 4 + b) * beat
            i = int(t0 * SR)
            place(buf, K, i, 1.0)               # footstep, every beat

            if style == "drumline":
                if b in (1, 3) and not intro:
                    place(buf, S, i, 0.55)
                for e in range(2):
                    j = int((t0 + e * beat / 2) * SR)
                    place(buf, HO if (e == 1 and section == 2) else H, j, 0.25 if e else 0.15)
                    if not intro and section != 3:
                        note = root * (2 if (e == 1 and section == 1) else 1)
                        place(buf, bass(note, beat / 2), j, 0.35)
                if section == 3 and not intro and b in (0, 2):
                    place(buf, bass(root, beat * 2), i, 0.4)

            elif style == "rock":
                if b in (1, 3) and not intro:
                    place(buf, S, i, 0.6)
                for e in range(2):
                    j = int((t0 + e * beat / 2) * SR)
                    place(buf, H, j, 0.2 if section != 2 else 0.3)
                    if not intro:
                        place(buf, bass(root * (1.5 if section == 1 and e else 1), beat / 2, 3.0), j, 0.3)
                if b == 0 and bar % 8 == 0 and not intro:
                    place(buf, CR, i, 0.25)

            else:  # electro
                if b in (1, 3) and not intro:
                    place(buf, C, i, 0.45)
                j = int((t0 + beat / 2) * SR)
                place(buf, HO, j, 0.22)         # offbeat open hat
                if not intro:
                    place(buf, bass(root, beat / 2), j, 0.45)   # pumping offbeat bass
                if section != 3:                # arpeggio in 3 of every 4 sections
                    arp = ([1, 2, 1.5, 2], [1, 1.5, 2, 3], [2, 1.5, 1.189, 1.5])[section]
                    for s in range(4):
                        place(buf, pluck(root * 4 * arp[s], beat / 4),
                              int((t0 + s * beat / 4) * SR), 0.08)

        if bar % 8 == 7 and not intro and style != "electro":   # fill into next phrase
            for k in range(4):
                j = int(((bar * 4 + 3) * beat + k * beat / 4) * SR)
                place(buf, S, j, 0.3 + 0.1 * k)

    buf = np.tanh(buf * 1.2)                    # glue + loudness
    buf /= np.max(np.abs(buf)) * 1.05
    return (buf * 32767).astype(np.int16)


def encode(pcm, path):
    enc = lameenc.Encoder()
    enc.set_bit_rate(96)
    enc.set_in_sample_rate(SR)
    enc.set_channels(1)
    enc.set_quality(2)
    path.write_bytes(enc.encode(pcm.tobytes()) + enc.flush())


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for b in BUCKETS:
        # three tracks per bucket at b, b+2, b+4, rotating which style gets which tempo
        for k, offset in enumerate((0, 2, 4)):
            style = STYLES[(k + b // 5) % len(STYLES)]
            bpm = b + offset
            p = OUT / f"cadence-{bpm}-{style}.mp3"
            if p.exists():
                continue
            encode(render(bpm, style), p)
            print(f"{p.name}  {p.stat().st_size / 1e6:.1f} MB", flush=True)
