// Adds HTTP Range support for audio. iPhone Safari asks for audio in chunks
// ("Range: bytes=...") and won't reliably play files served without a 206
// Partial Content reply, which Workers static assets don't do on their own.
export default {
  async fetch(request, env) {
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
  },
};
