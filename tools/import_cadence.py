"""Turn downloaded military cadence clips (video or audio) into player tracks.

Reads  staging/cadence/manifest.json  (written by the search step)
Writes public/cadence/<name>.mp3 and tools/cadence-tracks.json

For each clip: decode the audio track, mix to mono, normalize loudness,
measure the cadence with detect_bpm, and encode a 96 kbps MP3.

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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((STAGING / "manifest.json").read_text(encoding="utf-8"))
    existing = {t["file"]: t for t in json.loads(META.read_text())} if META.exists() else {}
    for m in manifest:
        name = pathlib.Path(m["file"]).stem + ".mp3"
        if name in existing:
            continue
        try:
            x = decode_all(STAGING / m["file"])
        except Exception as e:  # damaged or unsupported file
            print(f"SKIP {m['file']}: {e}")
            continue
        if len(x) < SR * 20:
            print(f"SKIP {m['file']}: under 20 s of audio")
            continue
        x = normalize(x)
        encode(x, OUT / name)
        r = detect_bpm.analyze(OUT / name)
        existing[name] = {
            "file": name, "title": m.get("title") or name, "artist": m.get("credit") or "U.S. military",
            "license": m.get("license", "Public domain (US Gov)"),
            "license_url": "https://www.usa.gov/government-copyright",
            "source_url": m.get("source_url"), "kind": m.get("kind"),
            "seconds": round(len(x) / SR), "tempo": r["tempo"], "confidence": r["confidence"],
            "bpm": r["cadence"],            # None = outside 150-189, not listed in the player
        }
        print(f"{name:60} {len(x)/SR:6.0f}s  tempo {r['tempo']:6}  -> {r['cadence']}  conf {r['confidence']}",
              flush=True)
    META.write_text(json.dumps(list(existing.values()), indent=1))


if __name__ == "__main__":
    main()
