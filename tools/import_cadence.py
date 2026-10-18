"""Turn downloaded military cadence clips (video or audio) into player tracks.

Reads  staging/cadence/manifest.json  (written by the search step)
Writes public/cadence/<name>.mp3 and tools/cadence-tracks.json

For each clip: decode the audio, find stretches with a steady running
cadence (see steady_segments), and save each as a normalized 96 kbps MP3.

Usage:  python tools/import_cadence.py
Needs:  pip install numpy av lameenc
"""
import json
import pathlib
import sys

import av
import lameenc
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import detect_bpm  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
STAGING = ROOT / "staging" / "cadence"
OUT = ROOT / "public" / "cadence"
META = ROOT / "tools" / "cadence-tracks.json"
SR = 44100


def decode_all(path):
    with av.open(str(path)) as f:
        if not f.streams.audio:
            return np.zeros(0)
        res = av.AudioResampler(format="flt", layout="mono", rate=SR)
        parts = [r.to_ndarray().reshape(-1)
                 for frame in f.decode(f.streams.audio[0]) for r in res.resample(frame)]
    return np.concatenate(parts) if parts else np.zeros(0)


def normalize(x):
    """Scale so loud passages sit near full level without clipping spikes."""
    peak = np.percentile(np.abs(x), 99.9) or 1.0
    return np.clip(x / peak * 0.9, -1, 1)


def encode(x, path):
    enc = lameenc.Encoder()
    enc.set_bit_rate(96)
    enc.set_in_sample_rate(SR)
    enc.set_channels(1)
    enc.set_quality(2)
    pcm = (x * 32767).astype(np.int16)
    path.write_bytes(enc.encode(pcm.tobytes()) + enc.flush())


WIN, HOP = 12, 4          # seconds: analysis window and step
MIN_WINDOWS = 4           # 4 agreeing windows = at least 24 s of steady cadence
TOLERANCE = 4             # spm a window may differ from the segment's median


def steady_segments(x):
    """Find stretches with a steady running cadence.

    Each 12 s window gets a tempo folded into 150-189 spm (or None). Runs of
    consecutive windows that agree within TOLERANCE become segments; speech,
    interviews and edits don't hold a steady beat, so they drop out.
    Returns [(start_s, end_s, spm)].
    """
    a = x[::2]                                      # 22.05 kHz for analysis
    sr = detect_bpm.SR
    reads = []
    for s in range(0, max(1, len(a) - WIN * sr + 1), HOP * sr):
        bpm, _ = detect_bpm.tempo(a[s:s + WIN * sr])
        reads.append(detect_bpm.to_cadence(bpm))

    segments, run = [], []
    for i, c in enumerate(reads + [None]):
        if c is not None and (not run or abs(c - np.median([r for _, r in run])) <= TOLERANCE):
            run.append((i, c))
            continue
        if len(run) >= MIN_WINDOWS:
            first, last = run[0][0], run[-1][0]
            segments.append((first * HOP, last * HOP + WIN, int(round(np.median([r for _, r in run])))))
        run = [(i, c)] if c is not None else []

    # A slight tempo drift splits one run into overlapping pieces; join them back.
    merged = []
    for s in segments:
        if merged and s[0] <= merged[-1][1] and abs(s[2] - merged[-1][2]) <= TOLERANCE:
            p = merged[-1]
            w0, w1 = p[1] - p[0], s[1] - s[0]
            merged[-1] = (p[0], s[1], int(round((p[2] * w0 + s[2] * w1) / (w0 + w1))))
        else:
            merged.append(s)
    return merged


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((STAGING / "manifest.json").read_text(encoding="utf-8"))
    existing = ({t["file"] or f"none:{t['from']}": t for t in json.loads(META.read_text())}
                if META.exists() else {})
    done = {t["from"] for t in existing.values()}
    for m in manifest:
        if m["file"] in done:
            continue
        try:
            x = decode_all(STAGING / m["file"])
        except Exception as e:  # damaged or unsupported file
            print(f"SKIP {m['file']}: {e}", flush=True)
            continue
        segs = steady_segments(x) if len(x) >= SR * WIN else []
        print(f"{m['file'][:60]:60} {len(x)/SR:5.0f}s  segments {[(a, b, c) for a, b, c in segs]}", flush=True)
        stem = pathlib.Path(m["file"]).stem
        for n, (start, end, spm) in enumerate(segs, 1):
            name = f"{stem}-{n}.mp3"
            encode(normalize(x[start * SR:end * SR]), OUT / name)
            title = m.get("title") or stem
            existing[name] = {
                "file": name, "from": m["file"],
                "title": title + (f" (part {n})" if len(segs) > 1 else ""),
                "artist": m.get("credit") or "U.S. military",
                "license": m.get("license", "Public domain (US Gov)"),
                "license_url": "https://www.usa.gov/government-copyright",
                "source_url": m.get("source_url"), "kind": m.get("kind"),
                "start": start, "seconds": end - start, "bpm": spm,
            }
        if not segs:                                 # remember it was checked
            existing[f"none:{m['file']}"] = {"file": None, "from": m["file"], "bpm": None}
        META.write_text(json.dumps(list(existing.values()), indent=1))


if __name__ == "__main__":
    main()
