// The site's Worker. Pages, chapter text and word timings are static files from site/ (the ASSETS
// binding). Recordings, and later the TV-mode pictures, live in the Cloudflare R2 bucket bound as
// MEDIA under the same paths (audio/<slug>/<n>.mp3, pictures/<slug>/<n>/...), so the site's own
// addresses do not change. Anything not found in the bucket falls back to the static files.
const TYPES = { mp3: "audio/mpeg", jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", webp: "image/webp" };
const MEDIA = /^\/((?:audio|pictures)\/[a-z0-9\-\/]+\.(mp3|jpg|jpeg|png|webp))$/;

// The word timings under audio/ (audio/<slug>/<n>.json) pass through this Worker, where the site's _headers file
// may not reach, so they get the header that lets the TV's casting page (site/cast/ on the Bible site) read the
// Quran's too. Everything here is public.
async function files(request, env, url) {
  const res = await env.ASSETS.fetch(request);
  if (!url.pathname.endsWith(".json") || res.headers.has("access-control-allow-origin")) return res;
  const out = new Response(res.body, res);
  out.headers.set("access-control-allow-origin", "*");
  return out;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const m = url.pathname.match(MEDIA);
    if (!m || !env.MEDIA || (request.method !== "GET" && request.method !== "HEAD")) {
      return files(request, env, url);
    }
    const key = m[1];
    const wantsRange = request.headers.has("range");
    let obj;
    try {
      obj = request.method === "HEAD"
        ? await env.MEDIA.head(key)
        : await env.MEDIA.get(key, { range: request.headers, onlyIf: request.headers });
    } catch (e) {
      // a malformed Range header: answer with the whole file instead
      obj = await env.MEDIA.get(key);
    }
    if (!obj) return files(request, env, url);

    const headers = new Headers();
    obj.writeHttpMetadata(headers);
    headers.set("content-type", TYPES[m[2]]);
    headers.set("etag", obj.httpEtag);
    headers.set("accept-ranges", "bytes");
    // Short browser cache: a chapter can be recorded again under the same address.
    headers.set("cache-control", "public, max-age=3600");

    if (request.method === "HEAD") {
      headers.set("content-length", String(obj.size));
      return new Response(null, { headers });
    }
    if (!("body" in obj) || !obj.body) {
      // If-None-Match / If-Modified-Since matched: the browser's copy is current
      return new Response(null, { status: 304, headers });
    }
    if (wantsRange && obj.range) {
      let start, length;
      if ("suffix" in obj.range) {
        length = Math.min(obj.range.suffix, obj.size);
        start = obj.size - length;
      } else {
        start = obj.range.offset || 0;
        length = obj.range.length ?? obj.size - start;
      }
      headers.set("content-range", `bytes ${start}-${start + length - 1}/${obj.size}`);
      headers.set("content-length", String(length));
      return new Response(obj.body, { status: 206, headers });
    }
    headers.set("content-length", String(obj.size));
    return new Response(obj.body, { headers });
  },
};
