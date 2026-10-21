// Builds public/tracks.json, which the player reads. Runs on every deploy.
//
// Three sources:
//   public/generated/  beat tracks named cadence-<bpm>-<style>.mp3
//   public/free/       freely licensed tracks; details in tools/free-tracks.json
//   public/music/      your own files. Name them "180 - Song Title.mp3", or run
//                      tools/detect_bpm.py to fill tools/bpm-cache.json.
import { readdirSync, readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { join, parse } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const pub = join(root, 'public');
const AUDIO = /\.(mp3|m4a|aac|wav)$/i;
const readJson = (p, fallback) => (existsSync(p) ? JSON.parse(readFileSync(p, 'utf8')) : fallback);

const bpmCache = readJson(join(root, 'tools', 'bpm-cache.json'), {});
const freeMeta = Object.fromEntries(
  readJson(join(root, 'tools', 'free-tracks.json'), []).map(t => [t.file, t]));

function files(dir) {
  mkdirSync(join(pub, dir), { recursive: true });
  return readdirSync(join(pub, dir)).filter(f => AUDIO.test(f));
}
const src = (dir, f) => `${dir}/${encodeURIComponent(f)}`;

// Length in seconds of an MP3, from its frame headers (no dependencies, so it
// also runs in Cloudflare's build). Non-MP3 files get null.
const KBPS = { 1: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
               2: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160] };
const RATES = { 3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000] };
function mp3Seconds(path) {
  if (!/\.mp3$/i.test(path)) return null;
  const b = readFileSync(path);
  let i = 0, samples = 0, rate = 0;
  if (b.toString('latin1', 0, 3) === 'ID3')            // skip ID3v2 tag
    i = 10 + ((b[6] << 21) | (b[7] << 14) | (b[8] << 7) | b[9]);
  while (i + 4 <= b.length) {
    const ver = (b[i + 1] >> 3) & 3, br = b[i + 2] >> 4, sr = (b[i + 2] >> 2) & 3;
    if (b[i] !== 0xff || (b[i + 1] & 0xe0) !== 0xe0 || ((b[i + 1] >> 1) & 3) !== 1
        || ver === 1 || br === 0 || br === 15 || sr === 3) { i++; continue; }  // not a Layer III frame
    rate = RATES[ver][sr];
    const perFrame = ver === 3 ? 1152 : 576;
    const kbps = KBPS[ver === 3 ? 1 : 2][br];
    i += Math.floor(perFrame / 8 * kbps * 1000 / rate) + ((b[i + 2] >> 1) & 1);
    samples += perFrame;
  }
  return rate ? Math.round(samples / rate) : null;
}
const cap = s => s[0].toUpperCase() + s.slice(1);

const tracks = [];

for (const f of files('generated')) {
  const m = parse(f).name.match(/^cadence-(\d+)-(\w+)$/);
  if (!m) continue;
  tracks.push({ title: `${cap(m[2])} beat`, artist: 'Generated', bpm: +m[1], src: src('generated', f), kind: 'music',
                seconds: mp3Seconds(join(pub, 'generated', f)) });
}

// Licensed tracks with a metadata file: free music, and military cadence calls.
const cadenceMeta = Object.fromEntries(
  readJson(join(root, 'tools', 'cadence-tracks.json'), []).map(t => [t.file, t]));
for (const [dir, metaFor] of [['free', freeMeta], ['cadence', cadenceMeta]]) {
  for (const f of files(dir)) {
    const meta = metaFor[f];
    if (!meta || !meta.bpm) continue;             // only list tracks with a known tempo
    tracks.push({
      title: meta.title, bpm: meta.bpm, src: src(dir, f),
      artist: dir === 'cadence' ? 'Military cadence' : meta.artist,
      kind: dir === 'cadence' ? 'military' : 'music',
      license: meta.license, license_url: meta.license_url, source_url: meta.source_url,
      seconds: mp3Seconds(join(pub, dir, f)),
    });
  }
}

for (const f of files('music')) {
  const name = parse(f).name;
  const m = name.match(/^(\d{3})\s*-\s*(.*)$/);
  tracks.push({
    title: m ? m[2] : name, artist: 'My music', kind: 'music',
    bpm: m ? +m[1] : (bpmCache[`music/${f}`] ?? null), src: src('music', f),
    seconds: mp3Seconds(join(pub, 'music', f)),
  });
}

tracks.sort((a, b) => (a.bpm ?? 999) - (b.bpm ?? 999) || a.title.localeCompare(b.title));
writeFileSync(join(pub, 'tracks.json'), JSON.stringify(tracks, null, 1));
console.log(`tracks.json: ${tracks.length} tracks`);
