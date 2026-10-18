# Running Cadence

Personal cadence player: https://cadence.matmerten.com

## Add your own music
1. Copy MP3/M4A files (DRM-free) into `public/music/`.
   Name them `180 - Song Title.mp3` to show the steps-per-minute.
2. Redeploy: `npm run deploy`

Keep Cloudflare Access turned on before uploading your own music, so the files aren't public.

## Regenerate the beat tracks
`pip install numpy lameenc`, then `python tools/make_cadence_tracks.py`.
Change `TEMPOS` / `MINUTES` at the top of the script, then `npm run deploy`.

## How it fits together
- `public/` – the site (index.html player, generated beats, your music, tracks.json)
- `tools/build-tracklist.mjs` – scans the audio folders and writes `tracks.json` (runs on every deploy)
- `src/worker.js` – adds byte-range support for audio so iPhone Safari can stream and seek
- `wrangler.jsonc` – Cloudflare Workers config
