# Running Cadence

Personal cadence player: https://cadence.matmerten.com

Home screen lists 5-spm buckets (150–154 … 185–189). Tap one for a screen with
just those tracks: Play/Pause and Shuffle. Once something is playing, a
Play/Pause bar stays pinned to the bottom of every screen (tap its text to jump
back to that cadence). Plays with the iPhone screen locked.

## Music sources
- **Generated beats** – `tools/make_cadence_tracks.py` (drumline / rock / electro, kick on every step)
- **Free music** – Kevin MacLeod (incompetech.com), CC BY 4.0; list in `tools/free-tracks.json`
  (stated BPM, cross-checked with `tools/detect_bpm.py`)
- **Military cadence** – public-domain US military video from DVIDS / Wikimedia Commons.
  `tools/import_cadence.py` pulls the audio, keeps only stretches with a steady
  150–189 spm cadence, and writes `tools/cadence-tracks.json`
- **Your music** – drop files in `public/music/`

Audio files are not in git (see `.gitignore`).

## Add your own music
1. Copy MP3/M4A files (DRM-free) into `public/music/`.
2. Either name them `180 - Song Title.mp3`, or detect tempo automatically:
   `pip install numpy av` then `python tools/detect_bpm.py --music`
3. `npm run deploy`

Copyrighted music on a public URL: turn on Cloudflare Access for cadence.matmerten.com first.

## Regenerate beat tracks
`pip install numpy lameenc`, then `python tools/make_cadence_tracks.py` and `npm run deploy`.

## How it fits together
- `public/index.html` – the whole player
- `tools/build-tracklist.mjs` – writes `public/tracks.json` (runs on every deploy)
- `src/worker.js` – byte-range support so iPhone Safari can stream and seek audio
- `wrangler.jsonc` – Cloudflare Workers config (custom domain cadence.matmerten.com)
