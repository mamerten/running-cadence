// Two jobs:
// 1. /api/marks: favorites and never-play marks, shared by everyone who uses
//    the site, kept as one JSON object { "<track src>": "fav" | "never" } in KV.
// 2. Audio: adds HTTP Range support. iPhone Safari asks for audio in chunks
//    ("Range: bytes=...") and won't reliably play or seek files served without
//    a 206 Partial Content reply, which Workers static assets don't do on their own.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/api/marks') return marks(request, env);
    return audio(request, env);
  },
};

const KEY = 'marks';
const TRACK = /^(generated|free|cadence|music)\/[^/]{1,250}$/;   // a src from tracks.json
const MAX = 5000;                                                // tracks we could ever have
const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });

async function marks(request, env) {
  const all = (await env.MARKS.get(KEY, 'json')) || {};
  if (request.method === 'GET') return json(all);
  if (request.method !== 'POST') return json({ error: 'GET or POST' }, 405);

  let body;
  try { body = await request.json(); } catch { return json({ error: 'bad JSON' }, 400); }
  const { src, mark } = body || {};
  if (typeof src !== 'string' || !TRACK.test(src) || ![null, 'fav', 'never'].includes(mark ?? null))
    return json({ error: 'need { src, mark: "fav" | "never" | null }' }, 400);

  if (mark) all[src] = mark; else delete all[src];
  if (Object.keys(all).length > MAX) return json({ error: 'too many marks' }, 400);
  await env.MARKS.put(KEY, JSON.stringify(all));
  return json(all);
}

async function audio(request, env) {
  const res = await env.ASSETS.fetch(request.url, { headers: { 'Accept-Encoding': 'identity' } });
  const range = request.headers.get('Range');
  const m = range && /^bytes=(\d*)-(\d*)$/.exec(range);
  if (!res.ok || !m) {
    const out = new Response(res.body, res);
    out.headers.set('Accept-Ranges', 'bytes');
    return out;
  }

  const buf = await res.arrayBuffer();
  const size = buf.byteLength;
  let start = m[1] === '' ? size - Number(m[2]) : Number(m[1]);
  let end = m[1] !== '' && m[2] !== '' ? Number(m[2]) : size - 1;
  start = Math.max(0, start);
  end = Math.min(end, size - 1);
  if (start > end) {
    return new Response(null, { status: 416, headers: { 'Content-Range': `bytes */${size}` } });
  }

  const headers = new Headers(res.headers);
  headers.set('Accept-Ranges', 'bytes');
  headers.set('Content-Range', `bytes ${start}-${end}/${size}`);
  headers.set('Content-Length', String(end - start + 1));
  return new Response(buf.slice(start, end + 1), { status: 206, headers });
}
