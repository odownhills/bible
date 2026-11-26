/* The sites' service worker: offline reading (Obay, 2026-11-26). scripts/build.py copies it to the top of
   site/ and site-quran/ as sw.js, filling in VERSION and PRECACHE; scripts/offline.js registers it.

   Three kinds of file, three ways:
   - Pages and the small files they read (chapter text, word timings, the lists of chapters, the search index):
     always asked of the site first, so a new chapter or a new build shows up at once, and a copy is kept of
     each one. With no connection (or one so slow that 4 seconds pass), the kept copy is used. A page that was
     never opened gives the "You're offline" page, which lists what can be read.
   - The scripts with ?v=<hash> and the fonts never change under one address: kept the first time, then used
     from the copy. Only the newest copy of each script is kept.
   - Recordings and Watch pictures (audio/*.mp3, pictures/*) are large, so they are kept only when the reader
     presses "Save for offline" on a chapter (scripts/offline.js puts them in the "saved" store). A saved one is
     played from the copy, also in pieces (Range), which the audio player asks for; any other goes to the site.

   To switch all of this off for every reader, replace this file with one whose only lines are
     self.addEventListener('install',function(){self.skipWaiting()});
     self.addEventListener('activate',function(e){e.waitUntil(self.registration.unregister())});
*/
var VERSION = "b1f20ac3";
var PRECACHE = ["./", "offline.html", "offline.js?v=5f503327", "manifest.json", "genesis/", "deuteronomy/", "job/", "john/", "1-john/", "jude/", "read.js?v=dde1f244", "tv.js?v=3adb601b"];   // the home page, the offline page and the current scripts
var PAGES = 'pages', ASSETS = 'assets', SAVED = 'saved';
var WAIT = 4000;   // how long a page waits for the site before its kept copy is used

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(ASSETS).then(function (assets) {
    return Promise.all(PRECACHE.map(function (u) {
      var url = new URL(u, self.registration.scope).href;
      return fetch(url, { cache: 'no-cache' }).then(function (r) {
        if (!r.ok) return;
        return versioned(url) ? keep(assets, url, r) : caches.open(PAGES).then(function (p) { return keep(p, url, r); });
      }).catch(function () {});   // one missing file never stops the rest
    }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (names) {
    // only these three stores are ours; anything else is from an older version of this file
    return Promise.all(names.filter(function (n) { return [PAGES, ASSETS, SAVED].indexOf(n) < 0; })
      .map(function (n) { return caches.delete(n); }));
  }).then(function () { return self.clients.claim(); }));
});

function versioned(url) { var u = new URL(url); return /[?&]v=/.test(u.search) || /^\/fonts\//.test(u.pathname); }
function media(url) { return /^\/(audio|pictures)\/.+\.(mp3|jpe?g|png|webp)$/.test(new URL(url).pathname); }

// One address for a page however it is asked for: the host answers genesis/1.html at genesis/1 and
// genesis/index.html at genesis/, and what follows ? or # never changes the page.
function key(url) {
  var u = new URL(url);
  if (/\/index\.html$/.test(u.pathname)) u.pathname = u.pathname.slice(0, -10);
  else if (/\.html$/.test(u.pathname)) u.pathname = u.pathname.slice(0, -5);
  if (!versioned(url)) u.search = '';
  u.hash = '';
  return u.href;
}

// A copy that can be kept and given back for any request (one that was redirected cannot answer a page).
function keep(cache, url, r) {
  return r.clone().blob().then(function (b) {
    var h = new Headers(r.headers);
    h.delete('content-encoding'); h.delete('content-length');   // the copy is already unpacked
    var copy = new Response(b, { status: 200, statusText: 'OK', headers: h });
    return cache.put(key(url), copy).then(function () {
      if (!versioned(url) || !/[?&]v=/.test(new URL(url).search)) return;
      // the older copies of this same script are no longer asked for by any page as built now
      return cache.keys().then(function (ks) {
        var path = new URL(url).pathname;
        return Promise.all(ks.filter(function (k) { var x = new URL(k.url); return x.pathname === path && k.url !== key(url); })
          .map(function (k) { return cache.delete(k); }));
      });
    });
  }).catch(function () {});
}

function kept(url, store) {
  var k = key(url);
  return caches.open(store).then(function (c) {
    return c.match(k).then(function (r) { return r || c.match(k, { ignoreSearch: true }); });
  });
}

function offlinePage() {
  return kept(new URL('offline.html', self.registration.scope).href, PAGES).then(function (r) {
    return r || new Response('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">' +
      '<body style="background:#171223;color:#E8E2F2;font:19px Georgia,serif;padding:2rem 16px">' +
      '<p>You are offline, and this page has not been saved on this device yet.</p>',
      { headers: { 'content-type': 'text/html; charset=utf-8' } });
  });
}

// Asked of the site first; a kept copy when there is no answer (or none within WAIT, if a copy is kept).
function fresh(e, isPage) {
  var req = e.request, url = req.url;
  var saving = null;
  var net = fetch(req).then(function (r) {
    if (r.ok && r.type !== 'opaqueredirect') {
      var copy = r.clone();
      saving = caches.open(PAGES).then(function (c) { return keep(c, url, copy); });
    }
    return r;
  });
  e.waitUntil(net.then(function () { return saving; }).catch(function () {}));
  var fallback = function () {
    return kept(url, PAGES).then(function (r) { return r || kept(url, SAVED); }).then(function (r) {
      if (r) return r;
      if (isPage) return offlinePage();
      return net;   // nothing kept: the site's own answer, or its failure
    });
  };
  return new Promise(function (resolve) {
    var done = false, timer = setTimeout(function () {
      kept(url, PAGES).then(function (r) { if (r && !done) { done = true; resolve(r); } });
    }, WAIT);
    net.then(function (r) {
      if (done) return;
      if (!r.ok && r.type !== 'opaqueredirect' && r.status >= 500) throw new Error('site');
      done = true; clearTimeout(timer); resolve(r);
    }).catch(function () {
      if (done) return;
      done = true; clearTimeout(timer); resolve(fallback());
    });
  });
}

function once(req) {   // a script or font that never changes under its address
  return caches.open(ASSETS).then(function (c) {
    var k = key(req.url);
    return c.match(k).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (net) {
        if (net.ok) keep(c, req.url, net);
        return net;
      }).catch(function () {
        // offline and this exact version was never kept: any kept version of the same file
        return c.match(k, { ignoreSearch: true }).then(function (any) { return any || Response.error(); });
      });
    });
  });
}

// A saved recording or picture, from the copy; the audio player asks for pieces of a recording.
function saved(req) {
  return caches.open(SAVED).then(function (c) { return c.match(req.url, { ignoreSearch: true }); }).then(function (r) {
    if (!r) return fetch(req);
    var range = req.headers.get('range');
    if (!range) return r;
    return r.blob().then(function (b) {
      var m = /^bytes=(\d*)-(\d*)$/.exec(range.trim()), size = b.size, start, end;
      if (!m || (m[1] === '' && m[2] === '')) return new Response(b, { status: 200, headers: r.headers });
      if (m[1] === '') { start = Math.max(0, size - parseInt(m[2], 10)); end = size - 1; }
      else { start = parseInt(m[1], 10); end = m[2] === '' ? size - 1 : Math.min(parseInt(m[2], 10), size - 1); }
      if (start >= size || start > end) {
        return new Response(null, { status: 416, headers: { 'content-range': 'bytes */' + size } });
      }
      var part = b.slice(start, end + 1);
      return new Response(part, { status: 206, statusText: 'Partial Content', headers: {
        'content-type': r.headers.get('content-type') || b.type || 'application/octet-stream',
        'content-range': 'bytes ' + start + '-' + end + '/' + size,
        'content-length': String(part.size), 'accept-ranges': 'bytes' } });
    });
  });
}

self.addEventListener('fetch', function (e) {
  var req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin) return;   // other sites go straight through
  if (/^\/(sw\.js|cast\/)/.test(url.pathname)) return;
  if (media(req.url)) { e.respondWith(saved(req)); return; }
  if (versioned(req.url)) { e.respondWith(once(req)); return; }
  e.respondWith(fresh(e, req.mode === 'navigate'));
});

// which version is running (asked when testing)
self.addEventListener('message', function (e) {
  if (e.data === 'version' && e.source) e.source.postMessage({ version: VERSION });
});
