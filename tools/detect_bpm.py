"""Estimate the tempo of audio files and fold it into running cadence.

How it works:
  1. Decode ~90 s from the middle of the track to mono.
  2. Onset strength: how much the spectrum *jumps up* from one frame to the
     next (drum hits, note attacks). This gives a pulse-train-like signal.
  3. Autocorrelation of that signal: it peaks at lags equal to the beat
     period. Each candidate BPM is scored at its lag and at 2x lag.
  4. Fold into the running range: 75-95 BPM doubles to 150-190 spm
     (one step per half-beat).

Usage:
  python tools/detect_bpm.py FILE...       print BPM for each file
  python tools/detect_bpm.py --music       fill tools/bpm-cache.json for public/music/
Needs:  pip install numpy av
"""
import json
import pathlib
import sys
import numpy as np
import av

SR = 22050
HOP = 256
FPS = SR / HOP
LOW, HIGH = 150, 190          # target cadence range (spm)
ROOT = pathlib.Path(__file__).resolve().parent.parent


def decode(path, seconds=90):
    """Return mono float32 samples from the middle of the file."""
    with av.open(str(path)) as f:
        stream = f.streams.audio[0]
        dur = float(stream.duration * stream.time_base) if stream.duration else (f.duration or 0) / 1e6
        start = max(0.0, dur / 2 - seconds / 2)
        if start > 0:
            f.seek(int(start / stream.time_base), stream=stream)
        res = av.AudioResampler(format="flt", layout="mono", rate=SR)
        chunks, total = [], 0
        for frame in f.decode(stream):
            for r in res.resample(frame):
                a = r.to_ndarray().reshape(-1)
                chunks.append(a)
                total += len(a)
            if total >= seconds * SR:
                break
    return np.concatenate(chunks)[: seconds * SR] if chunks else np.zeros(0)


def onset_strength(x):
    n_fft = 1024
    frames = 1 + (len(x) - n_fft) // HOP
    idx = np.arange(n_fft)[None, :] + HOP * np.arange(frames)[:, None]
    spec = np.abs(np.fft.rfft(x[idx] * np.hanning(n_fft), axis=1))
    spec = np.log1p(100 * spec)
    flux = np.maximum(0, np.diff(spec, axis=0)).sum(axis=1)
    k = int(FPS)                               # remove slow loudness trend
    flux = flux - np.convolve(flux, np.ones(k) / k, mode="same")
    return np.maximum(flux, 0)


def tempo(x):
    """Return (bpm, confidence) for the dominant beat between 60 and 200 BPM."""
    o = onset_strength(x)
    o = o - o.mean()
    ac = np.fft.irfft(np.abs(np.fft.rfft(o, 2 * len(o))) ** 2)[: len(o)]
    ac /= ac[0] or 1
    lag_at = lambda lag: np.interp(lag, np.arange(len(ac)), ac)

    bpms = np.arange(60, 200.01, 0.1)
    lags = 60 * FPS / bpms
    score = lag_at(lags) + 0.5 * lag_at(2 * lags)
    best = bpms[np.argmax(score)]
    conf = float((score.max() - score.mean()) / (score.std() + 1e-9))   # peak height in std devs

    # Refine: a small tempo error grows with each beat, so lining up 8 beats
    # in a row pins the tempo down far more precisely than 1 or 2.
    fine = np.arange(best - 1.5, best + 1.5, 0.01)
    fine_lags = 60 * FPS / fine
    fine_score = sum(lag_at(k * fine_lags) for k in range(1, 9))
    return float(fine[np.argmax(fine_score)]), conf


def to_cadence(bpm):
    """Fold a song tempo into LOW..HIGH spm, or None if it doesn't fit."""
    for mult in (1, 2, 0.5):
        v = round(bpm * mult)
        if LOW <= v < HIGH:
            return v
    return None


def analyze(path):
    bpm, conf = tempo(decode(path))
    return {"tempo": round(bpm, 1), "cadence": to_cadence(bpm), "confidence": round(conf, 2)}


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--music"]:
        cache_path = ROOT / "tools" / "bpm-cache.json"
        cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        for p in sorted((ROOT / "public" / "music").glob("*")):
            key = f"music/{p.name}"
            if p.suffix.lower() in (".mp3", ".m4a", ".aac", ".wav") and key not in cache:
                r = analyze(p)
                cache[key] = r["cadence"]
                print(key, r, flush=True)
        cache_path.write_text(json.dumps(cache, indent=1))
    else:
        for a in args:
            print(pathlib.Path(a).name, analyze(a), flush=True)
