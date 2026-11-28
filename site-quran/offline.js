/* Offline reading (Obay, 2026-11-26), on every page of the Bible and Quran sites; scripts/build.py copies it
   to the top of each site as offline.js.

   - Starts the site's service worker (sw.js, from scripts/sw.js), which keeps a copy of every page that is
     opened, with its text, so it opens again with no connection. Nothing to press for that.
   - On a chapter (or surah) with a recording: a "Save for offline" line under the buttons. It keeps the
     recording and the Watch pictures too (several megabytes, so only when asked), in the worker's "saved"
     store, and says how much it took. "Remove" gives the space back. A saved chapter is brought up to date
     quietly when it is opened with a connection (a new recording, pictures added later).
   - On the Bible, the next chapter's page is kept ahead of time, so reading can carry on with no signal.
   - On the "You're offline" page (offline.html): the list of what can be read now.
   It never changes the text of a page. */
(function () {
  'use strict';
  var d = document, here = d.currentScript && d.currentScript.src;
  var ROOT = new URL('.', here || location.href).href;
  if (!('serviceWorker' in navigator) || !window.caches) return;
  navigator.serviceWorker.register(ROOT + 'sw.js', { scope: ROOT }).catch(function () {});

  var SAVED = 'saved';
  var ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5v11.5M7 10.5l5 5 5-5M4.5 19.5h15"/></svg>';
  var TICK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>';
  var CSS = '.off{display:flex;flex-wrap:wrap;align-items:center;column-gap:.75rem;font-size:.8rem;color:var(--text-soft);margin:.1rem 0 0}' +
    '.off button{font:inherit;color:var(--accent);background:none;border:0;padding:.4rem 0;min-height:36px;cursor:pointer;' +
    'display:inline-flex;align-items:center;gap:.4rem;-webkit-tap-highlight-color:transparent}' +
    '.off button:disabled{cursor:default;color:var(--text-soft)}' +
    '.off svg{width:1.15em;height:1.15em;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}' +
    '.off .ok{display:inline-flex;align-items:center;gap:.4rem;color:var(--text-soft);padding:.4rem 0;min-height:36px}' +
    '.off .ok svg{color:var(--accent)}' +
    '.off .rm{color:var(--text-soft);text-decoration:underline;text-underline-offset:2px}' +
    '.offl{list-style:none;padding:0;margin:1rem 0 0;font-family:var(--sans);font-size:.95rem}' +
    '.offl li{border-bottom:1px solid var(--rule)}' +
    '.offl a{display:flex;justify-content:space-between;align-items:baseline;gap:1rem;padding:.75rem .1rem;text-decoration:none;color:var(--text)}' +
    '.offl small{color:var(--text-soft);font-size:.78rem;white-space:nowrap}';

  function abs(u) { return new URL(u, ROOT).href; }
  function mb(n) { return n >= 1e6 ? (n / 1e6).toFixed(n >= 1e8 ? 0 : 1) + ' MB' : Math.max(1, Math.round(n / 1e3)) + ' KB'; }
  function json(u) { return fetch(abs(u)).then(function (r) { if (!r.ok) throw new Error('load'); return r.json(); }); }
  function esc(t) { return String(t).replace(/[<&"]/g, function (x) { return x === '<' ? '&lt;' : x === '&' ? '&amp;' : '&quot;'; }); }
  function online() { return navigator.onLine !== false; }
  function style() {
    if (d.getElementById('off-css')) return;
    var s = d.createElement('style'); s.id = 'off-css'; s.textContent = CSS; d.head.appendChild(s);
  }

  /* ---- what a chapter needs to be played, listened to and watched with no connection ---- */
  function listFile(ch) {   // the same lists scripts/tv.js reads
    var id = ch.dataset.id || '';
    if (/^ar-/.test(id)) return ch.dataset.script === 'uthmani' ? 'manifest-ar-uthmani.json' : 'manifest-ar.json';
    return /^en-/.test(id) ? 'manifest-en.json' : 'manifest.json';
  }
  function recordUrl(ch) { return ROOT + 'saved/' + ch.dataset.id + (ch.dataset.script ? '.' + ch.dataset.script : '') + '.json'; }
  function plan(ch) {
    var list = listFile(ch);
    return json(list).then(function (m) {
      var c = null;
      for (var i = 0; i < m.length; i++) if (m[i].id === ch.dataset.id) { c = m[i]; break; }
      if (!c || !c.audio) throw new Error('none');
      var small = [list, c.text, c.sync, location.href.split('#')[0]];
      var big = [c.audio];
      if (c.poster) big.push(c.poster);
      // Story only's spoken notices for the family lists it skips in this chapter
      ((c.family || []).concat(c.familyAll ? [c.familyAll] : [])).forEach(function (f) { if (f.clip && small.indexOf(f.clip) < 0) small.push(f.clip); });
      var tv = c.tv || 'tv/' + c.slug + '/' + c.chapter + '.json';
      return json(tv).then(function (t) {
        small.push(tv);
        (JSON.stringify(t.scenes || []).match(/pictures\/[^"]+?\.(?:jpe?g|png|webp)/g) || []).forEach(function (p) {
          if (big.indexOf(p) < 0) big.push(p);
        });
      }, function () {}).then(function () {
        return { id: ch.dataset.id, title: ch.dataset.title || d.title, url: c.url, small: small.filter(Boolean), big: big };
      });
    });
  }
  function record(ch) {
    return caches.open(SAVED).then(function (c) { return c.match(recordUrl(ch)); })
      .then(function (r) { return r ? r.json() : null; }).catch(function () { return null; });
  }
  function allRecords() {
    return caches.open(SAVED).then(function (c) {
      return c.keys().then(function (ks) {
        return Promise.all(ks.filter(function (k) { return /\/saved\/[^/]+\.json$/.test(k.url); })
          .map(function (k) { return c.match(k).then(function (r) { return r.json(); }).catch(function () { return null; }); }));
      });
    }).then(function (rs) { return rs.filter(Boolean); });
  }
  function head(u) {
    return fetch(abs(u), { method: 'HEAD', cache: 'no-store' }).then(function (r) {
      return { size: parseInt(r.headers.get('content-length') || '0', 10) || 0, etag: r.headers.get('etag') || '' };
    }).catch(function () { return { size: 0, etag: '' }; });
  }
  // One large file into the saved store, counting its bytes as they arrive.
  function fetchInto(cache, u, tick) {
    return fetch(abs(u), { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('load');
      var type = r.headers.get('content-type') || '', etag = r.headers.get('etag') || '', parts = [];
      var done = function (blob) {
        var h = { 'content-type': type, 'content-length': String(blob.size) };
        if (etag) h.etag = etag;
        return cache.put(abs(u), new Response(blob, { headers: h })).then(function () { return { size: blob.size, etag: etag }; });
      };
      if (!r.body || !r.body.getReader) return r.blob().then(function (b) { tick(b.size); return done(b); });
      var reader = r.body.getReader();
      return (function pump() {
        return reader.read().then(function (x) {
          if (x.done) return done(new Blob(parts, { type: type }));
          parts.push(x.value); tick(x.value.byteLength); return pump();
        });
      })();
    });
  }
  function keepSmall(p) {   // the worker keeps a copy of each as it passes (pages and small files)
    return Promise.all(p.small.map(function (u) { return fetch(abs(u)).catch(function () {}); }));
  }
  function save(ch, p, only, progress) {
    // only: the files to fetch (all of p.big when saving for the first time)
    var want = only || p.big, got = 0, total = 0;
    return caches.open(SAVED).then(function (cache) {
      return Promise.all(want.map(head)).then(function (hs) {
        hs.forEach(function (h) { total += h.size; });
        var etags = {}, i = 0;
        function next() {
          if (i >= want.length) return etags;
          var u = want[i++];
          return fetchInto(cache, u, function (n) { got += n; if (progress) progress(got, Math.max(total, got)); })
            .then(function (x) { etags[u] = x.etag; return next(); });
        }
        return keepSmall(p).then(next);
      }).then(function (etags) {
        return record(ch).then(function (old) {
          var sizes = {};
          return Promise.all(p.big.map(function (u) {
            return cache.match(abs(u)).then(function (r) { if (r) return r.blob().then(function (b) { sizes[u] = b.size; }); });
          })).then(function () {
            var bytes = 0, missing = p.big.filter(function (u) { return !(u in sizes); });
            if (missing.length && !only) throw new Error('incomplete');
            p.big.forEach(function (u) { bytes += sizes[u] || 0; });
            var rec = { key: recordUrl(ch), id: p.id, title: p.title, url: p.url, files: p.big, bytes: bytes,
                        etags: Object.assign({}, old && old.etags || {}, etags), at: Date.now() };
            return cache.put(recordUrl(ch), new Response(JSON.stringify(rec), { headers: { 'content-type': 'application/json' } }))
              .then(function () { return rec; });
          });
        });
      });
    });
  }
  function remove(ch, rec) {
    return allRecords().then(function (all) {
      var others = {};   // a picture shared with another saved page (the Quran's English and Arabic) stays
      all.forEach(function (r) { if (r.key !== rec.key) r.files.forEach(function (f) { others[f] = 1; }); });
      return caches.open(SAVED).then(function (cache) {
        return Promise.all(rec.files.filter(function (f) { return !others[f]; }).map(function (f) { return cache.delete(abs(f)); }))
          .then(function () { return cache.delete(recordUrl(ch)); });
      });
    });
  }
  // A saved chapter opened with a connection: fetch what changed (a new recording, pictures added since).
  function refresh(ch, rec, show) {
    if (!online()) return;
    plan(ch).then(function (p) {
      return head(p.big[0]).then(function (h) {
        var redo = p.big.filter(function (u) { return rec.files.indexOf(u) < 0; });
        if (h.etag && rec.etags && rec.etags[p.big[0]] && h.etag !== rec.etags[p.big[0]] && redo.indexOf(p.big[0]) < 0) redo.unshift(p.big[0]);
        var gone = rec.files.filter(function (u) { return p.big.indexOf(u) < 0; });
        if (!redo.length && !gone.length) return keepSmall(p);
        return caches.open(SAVED).then(function (cache) {
          return Promise.all(gone.map(function (u) { return cache.delete(abs(u)); }));
        }).then(function () { return save(ch, p, redo, null); }).then(function (r) { show(r); });
      });
    }).catch(function () {});
  }

  /* ---- the line under a chapter's buttons ---- */
  function line(ch) {
    var sub = d.querySelector('.wrap .sub');
    if (!sub || !ch.dataset.audio || d.getElementById('off')) return;
    style();
    var el = d.createElement('span'); el.className = 'off'; el.id = 'off';
    sub.appendChild(el);
    var busy = false;
    function idle(note) {
      el.innerHTML = '<button type="button" id="off-save">' + ICON + 'Save for offline</button>' +
        (note ? '<span>' + note + '</span>' : '');
      el.firstChild.onclick = start;
    }
    function shown(rec) {
      el.innerHTML = '<span class="ok">' + TICK + 'Saved for offline &middot; ' + mb(rec.bytes) + '</span>' +
        '<button type="button" class="rm" id="off-remove">Remove</button>';
      el.lastChild.onclick = function () {
        if (busy) return; busy = true;
        remove(ch, rec).then(function () { busy = false; idle(''); }, function () { busy = false; });
      };
    }
    function start() {
      if (busy) return;
      if (!online()) { idle('Connect to the internet to save this.'); return; }
      busy = true;
      el.innerHTML = '<button type="button" disabled>' + ICON + 'Saving&hellip;</button>';
      var b = el.firstChild;
      if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(function () {});
      plan(ch).then(function (p) {
        return save(ch, p, null, function (got, total) {
          b.innerHTML = ICON + 'Saving&hellip; ' + (total ? mb(got) + ' of ' + mb(total) : mb(got));
        });
      }).then(function (rec) { busy = false; shown(rec); }, function () {
        busy = false; idle('That did not finish. Try again with a connection.');
      });
    }
    record(ch).then(function (rec) {
      if (rec) { shown(rec); refresh(ch, rec, shown); } else idle('');
    });
  }

  /* ---- the next chapter, kept ahead of time (the Bible's pages are small) ---- */
  function ahead(ch) {
    var c = navigator.connection;
    if (!ch.dataset.next || ch.dataset.stream || !online() || (c && c.saveData)) return;
    setTimeout(function () { fetch(abs(new URL(ch.dataset.next, location.href).href)).catch(function () {}); }, 2500);
  }

  /* ---- the offline page: what can be read with no connection ---- */
  function shelf(box) {
    style();
    var lists = (box.dataset.lists || 'manifest.json').split(' ');
    function page(u) {   // the address a page is kept under (scripts/sw.js key())
      var x = new URL(u, ROOT); x.search = ''; x.hash = '';
      x.pathname = x.pathname.replace(/\/index\.html$/, '/').replace(/\.html$/, '');
      return x.href;
    }
    Promise.all([
      caches.open('pages').then(function (c) { return c.keys(); }).then(function (ks) {
        var have = {}; ks.forEach(function (k) { have[k.url] = 1; }); return have;
      }),
      allRecords(),
      Promise.all(lists.map(function (f) { return json(f).catch(function () { return []; }); }))
    ]).then(function (g) {
      var have = g[0], saved = {}, rows = [];
      g[1].forEach(function (r) { saved[r.id + '|' + r.url] = r; });
      g[2].forEach(function (m, li) {
        m.forEach(function (c) {
          if (!have[page(c.url)]) return;
          var name = c.title || (c.book + ' ' + c.chapter), rec = saved[c.id + '|' + c.url];
          if (/^ar-/.test(c.id)) name += c.script === 'uthmani' ? ' (Arabic, traditional)' : ' (Arabic)';
          rows.push('<li><a href="' + abs(c.url) + '"><span>' + esc(name) + '</span><small>' +
            (rec ? 'with its recording' : 'text only') + '</small></a></li>');
        });
      });
      box.innerHTML = rows.length ? '<ul class="offl">' + rows.join('') + '</ul>' :
        '<p>Nothing is saved on this device yet. Pages you open while connected are kept here.</p>';
    }).catch(function () {});
  }

  function setUp() {
    var ch = d.getElementById('ch');
    if (ch) { line(ch); ahead(ch); }
    var box = d.getElementById('off-list');
    if (box) shelf(box);
  }
  function go() {
    setUp();
    // Listen + Read moves to the next chapter without leaving the page (scripts/read.js): set it up again
    var wrap = d.querySelector('.wrap');
    if (wrap && window.MutationObserver) new MutationObserver(function () {
      var ch = d.getElementById('ch');
      if (ch && !d.getElementById('off')) { line(ch); ahead(ch); }
    }).observe(wrap, { childList: true });
  }
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', go); else go();
})();
