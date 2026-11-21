#!/usr/bin/env python3
"""Build the static reading site from translations/<book-slug>/<NNN>.md into site/.

Source format for one chapter (translations/genesis/001.md):

    ---
    book: Genesis
    chapter: 1
    numbering: (optional one-line note when Hebrew numbering differs)
    ---
    ## Section heading
    1 In the beginning God created ...
    2 Now the earth was ...

    3 A blank line starts a new paragraph.
    title: An unnumbered psalm title line

Inline brackets: [alt: ...] is an alternate reading; any other [ ... ] is a short note.
Run: python3 scripts/build.py   (no dependencies beyond the standard library)
"""
import hashlib
import html
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "translations")
OUT = os.path.join(ROOT, "site")
BOOKS = json.load(open(os.path.join(ROOT, "data", "books.json")))
BY_SLUG = {b["slug"]: b for b in BOOKS}
SITE_TITLE = "The Bible, Freshly Translated"

CSS = """
:root{--bg:#171223;--panel:#1E1830;--shade:#241C3A;--text:#E8E2F2;--text-soft:#B3A7C9;--heading:#C9B8EC;--rule:#372C52;--accent:#B79BE8;--num:#7A6A9A;--alt-text:#C4B4E2;--note-bg:#201A32;
--sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;--serif:Georgia,"Times New Roman",Times,serif}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--serif);font-size:19px;line-height:1.75}
a{color:var(--accent)}
.wrap{max-width:42rem;margin:0 auto;padding:1.25rem 16px 4rem}
.top{display:flex;justify-content:space-between;align-items:center;gap:1rem;font-family:var(--sans);font-size:.8rem;letter-spacing:.06em;text-transform:uppercase;padding-bottom:.75rem;border-bottom:1px solid var(--rule);margin-bottom:1.5rem}
.top a{text-decoration:none;color:var(--text-soft)}
.top a:hover{color:var(--accent)}
h1{font-family:var(--serif);color:var(--heading);font-weight:normal;font-size:2rem;line-height:1.25;margin:.5rem 0 .25rem}
.sub{font-family:var(--sans);color:var(--text-soft);font-size:.85rem;margin:0 0 1.75rem}
h2.sec{font-family:var(--sans);color:var(--accent);text-transform:uppercase;letter-spacing:.12em;font-size:.8rem;font-weight:600;line-height:1.4;border-bottom:1px solid var(--rule);padding-bottom:.4rem;margin:2.25rem 0 1rem}
h3.group{font-family:var(--sans);color:var(--accent);text-transform:uppercase;letter-spacing:.12em;font-size:.8rem;font-weight:600;border-bottom:1px solid var(--rule);padding-bottom:.4rem;margin:2rem 0 1rem}
p.v{margin:0 0 1.1rem}
p.title{font-style:italic;color:var(--text-soft);margin:0 0 1rem}
sup.n{font-family:var(--sans);font-size:.6em;color:var(--num);user-select:none;-webkit-user-select:none;margin:0 .2em 0 .1em;vertical-align:super;line-height:0}
.alt{font-style:italic;font-size:.88em;color:var(--alt-text)}
.note{font-style:italic;font-size:.85em;color:var(--text-soft);background:var(--note-bg);border-radius:4px;padding:0 .3em}
.numbering{font-family:var(--sans);font-size:.85rem;color:var(--text-soft);background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:.6rem .8rem;margin:0 0 1.5rem}
.pn{display:flex;justify-content:space-between;gap:.75rem;margin-top:3rem;font-family:var(--sans);font-size:.9rem}
.pn a,.pn span{flex:1;display:block;padding:.85rem 1rem;border:1px solid var(--rule);border-radius:10px;background:var(--panel);text-decoration:none}
.pn .next{text-align:right}
.pn span{color:var(--num)}
.btn{display:inline-block;font-family:var(--sans);font-size:.85rem;line-height:1.4;color:var(--bg);background:var(--accent);border:1px solid var(--accent);border-radius:999px;padding:.5rem 1rem;text-decoration:none;cursor:pointer}
.btn.ghost{background:transparent;color:var(--accent);border:1px solid var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(9.5rem,1fr));gap:.6rem;font-family:var(--sans);font-size:.95rem}
.grid.ch{grid-template-columns:repeat(auto-fill,minmax(3.4rem,1fr))}
.grid a,.grid span{display:block;padding:.7rem .8rem;border-radius:10px;border:1px solid var(--rule);background:var(--panel);text-decoration:none;line-height:1.3}
.grid.ch a,.grid.ch span{text-align:center;padding:.7rem 0}
.grid a{color:var(--text)}
.grid a:hover{border-color:var(--accent)}
.grid span{color:var(--num);background:transparent}
.grid small{display:block;color:var(--text-soft);font-size:.75rem;margin-top:.2rem}
.grid span small{color:var(--num)}
.continue{display:block;margin:0 0 1.5rem;padding:1rem 1.1rem;border-radius:12px;background:var(--shade);border:1px solid var(--rule);text-decoration:none;font-family:var(--sans)}
.continue b{display:block;color:var(--heading);font-family:var(--serif);font-weight:normal;font-size:1.2rem}
.continue small{color:var(--text-soft)}
.continue[hidden]{display:none}
footer{margin-top:3rem;font-family:var(--sans);font-size:.75rem;color:var(--num);text-align:center}
.seek{display:block;width:100%;margin:0;height:28px;background:transparent;-webkit-appearance:none;appearance:none;cursor:pointer;touch-action:none}
.seek:focus-visible{outline:2px solid var(--accent);outline-offset:4px;border-radius:6px}
.seek::-webkit-slider-runnable-track{height:6px;border-radius:3px;background:linear-gradient(to right,var(--accent) var(--p,0%),var(--rule) var(--p,0%))}
.seek::-moz-range-track{height:6px;border-radius:3px;background:var(--rule)}
.seek::-moz-range-progress{height:6px;border-radius:3px;background:var(--accent)}
.seek::-webkit-slider-thumb{-webkit-appearance:none;width:18px;height:18px;border-radius:50%;background:var(--heading);margin-top:-6px;border:0}
.seek::-moz-range-thumb{width:18px;height:18px;border-radius:50%;background:var(--heading);border:0}
.seek:disabled{opacity:.45}
.times{display:flex;justify-content:space-between;font-size:.8rem;color:var(--text-soft);font-variant-numeric:tabular-nums;margin-top:.1rem}
.tb{background:transparent;border:0;color:var(--text);padding:0;width:52px;height:52px;border-radius:50%;display:grid;place-items:center;cursor:pointer;position:relative;-webkit-tap-highlight-color:transparent}
.tb:active{background:var(--shade)}
.tb:focus-visible{outline:2px solid var(--accent)}
.tb:disabled{color:var(--num);cursor:default}
.tb svg{width:30px;height:30px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.tb .solid{fill:currentColor;stroke:none}
.tb.skip svg{width:36px;height:36px}
.tb.skip span{position:absolute;font-size:.62rem;font-weight:700;top:50%;left:50%;transform:translate(-50%,-38%);font-variant-numeric:tabular-nums}
.tb.main{width:72px;height:72px;background:var(--accent);color:var(--bg)}
.tb.main:active{background:var(--heading)}
.tb.main svg{width:34px;height:34px}
.chips{display:flex;gap:.5rem;flex-wrap:wrap;justify-content:center}
.chip{font:inherit;font-size:.82rem;color:var(--text);background:var(--shade);border:1px solid var(--rule);border-radius:999px;padding:.5rem .85rem;text-decoration:none;min-height:40px;display:inline-flex;align-items:center;gap:.35rem}
select.chip{-webkit-appearance:none;appearance:none;text-align:center;cursor:pointer}
.chip:focus-visible{outline:2px solid var(--accent)}
body.lr{padding-bottom:10rem}
body.lr #ch .w{color:#9383B7;border-radius:4px;cursor:pointer;transition:color .18s ease-out,background-color .18s ease-out;-webkit-tap-highlight-color:transparent}
body.lr #ch .w.on{color:#fff}
body.lr #ch .w.now{color:#fff;background:rgba(183,155,232,.3);box-shadow:0 0 0 3px rgba(183,155,232,.3)}
body.lr #ch .alt,body.lr #ch .note{opacity:.55}
.sub .btn{margin:0 .35rem .4rem 0}
.lr-bar{position:fixed;left:0;right:0;bottom:0;z-index:20;background:var(--panel);border-top:1px solid var(--rule);font-family:var(--sans);padding:.3rem 14px calc(.5rem + env(safe-area-inset-bottom,0px))}
.lr-bar[hidden]{display:none}
.lr-in{max-width:42rem;margin:0 auto}
.lr-row{display:flex;align-items:center;justify-content:space-between;gap:.25rem;margin-top:.2rem}
.lr-mid{display:flex;align-items:center;gap:.7rem}
.lr-bar .tb{width:46px;height:46px}
.lr-bar .tb.main{width:56px;height:56px}
.lr-bar .tb.main svg{width:28px;height:28px}
.lr-bar .tb.skip svg{width:32px;height:32px}
.lr-bar .tb.x svg{width:22px;height:22px}
.lr-bar .chip{min-height:40px;padding:.35rem .5rem;min-width:4.4rem;justify-content:center}
.lr-msg{font-size:.78rem;color:var(--text-soft);text-align:center;margin:.3rem 0 0}
.lr-msg[hidden]{display:none}
sup.n.here{color:var(--bg);background:var(--accent);border-radius:4px;padding:.15em .35em;transition:all .6s}
.toast{position:fixed;left:12px;right:12px;bottom:calc(14px + env(safe-area-inset-bottom,0px));z-index:30;max-width:30rem;margin:0 auto;background:var(--shade);border:1px solid var(--accent);border-radius:14px;padding:.75rem .9rem;font-family:var(--sans);font-size:.9rem;color:var(--text);box-shadow:0 6px 24px rgba(0,0,0,.45);display:flex;flex-wrap:wrap;align-items:center;gap:.5rem .6rem}
.toast p{margin:0;flex:1 1 100%}
.toast a,.toast button{font:inherit;font-size:.85rem;color:var(--accent);background:transparent;border:1px solid var(--rule);border-radius:999px;padding:.45rem .85rem;text-decoration:none;cursor:pointer;min-height:40px;display:inline-flex;align-items:center}
.toast .x{margin-left:auto;border:0;color:var(--text-soft)}
body.lr .toast{bottom:calc(10.5rem + env(safe-area-inset-bottom,0px))}
"""


def esc(s):
    return html.escape(s, quote=True)


# One spoken word: a run of characters with no space or long dash in it that holds a letter or digit.
# Chapter pages wrap each one in <span class="w">, and scripts/align.py times each one, in the same order.
WORD = re.compile(r"[^\s\u2014\u2013]*\w[^\s\u2014\u2013]*")


def words(text):
    return WORD.findall(text)


def checksum(text):
    """Fingerprint of a chapter's read-aloud words, so stale word timings are noticed."""
    return hashlib.sha1(" ".join(words(text)).encode("utf-8")).hexdigest()[:12]


def spans(text):
    """Escape text and wrap each spoken word for Listen + Read highlighting."""
    out, i = [], 0
    for m in WORD.finditer(text):
        out.append(esc(text[i:m.start()]))
        out.append('<span class="w">%s</span>' % esc(m.group()))
        i = m.end()
    out.append(esc(text[i:]))
    return "".join(out)


def inline(text, spoken=False):
    """Escape text and turn [alt: ...] / [...] into styled spans. With spoken=True the words
    outside brackets (the ones read aloud) are wrapped for highlighting."""
    out, i = [], 0
    put = spans if spoken else esc
    for m in re.finditer(r"\[([^\[\]]+)\]", text):
        out.append(put(text[i:m.start()]))
        body = m.group(1).strip()
        if body.lower().startswith("alt:"):
            out.append('<span class="alt">[alt: %s]</span>' % esc(body[4:].strip()))
        else:
            out.append('<span class="note">[%s]</span>' % esc(body))
        i = m.end()
    out.append(put(text[i:]))
    return "".join(out)


def plain(text):
    """Text for read-aloud: drop bracketed alternates and notes."""
    return re.sub(r"\s+", " ", re.sub(r"\s*\[[^\[\]]*\]", "", text)).strip()


def parse(path):
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        raise SystemExit("Missing front matter: " + path)
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    blocks = []  # ("h", text) | ("p", [(n, text)]) | ("t", text)
    para = []

    def flush():
        nonlocal para
        if para:
            blocks.append(("p", para))
            para = []

    for line in m.group(2).splitlines():
        s = line.strip()
        if not s:
            flush()
        elif s.startswith("## "):
            flush()
            blocks.append(("h", s[3:].strip()))
        elif s.lower().startswith("title:"):
            flush()
            blocks.append(("t", s[6:].strip()))
        else:
            vm = re.match(r"^(\d+)\s+(.*)$", s)
            if vm:
                para.append((int(vm.group(1)), vm.group(2)))
            elif para:  # continuation line of the previous verse
                n, t = para[-1]
                para[-1] = (n, t + " " + s)
            else:
                raise SystemExit("Unrecognized line in %s: %r" % (path, s))
    flush()
    return meta, blocks


def page(title, body, depth, tail=""):
    up = "../" * depth
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#171223">
<title>%s</title>
<style>%s</style></head>
<body><div class="wrap">
<nav class="top"><a href="%s?home">Books</a><a href="%slisten/">Listen</a></nav>
%s
<footer>An original translation from the Hebrew and Greek.</footer>
</div>%s</body></html>
""" % (esc(title), CSS, up or "./", up, body, tail)


def durations():
    """Length in seconds of each recording, cached in site/audio/durations.json."""
    import subprocess
    adir = os.path.join(OUT, "audio")
    cache_path = os.path.join(adir, "durations.json")
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    fresh = {}
    for base, _, files in os.walk(adir):
        for f in files:
            if not f.endswith(".mp3"):
                continue
            full = os.path.join(base, f)
            rel = os.path.relpath(full, OUT).replace(os.sep, "/")
            size = os.path.getsize(full)
            old = cache.get(rel)
            if old and old[0] == size:
                fresh[rel] = old
                continue
            try:
                out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                      "-of", "csv=p=0", full], capture_output=True, text=True).stdout.strip()
                fresh[rel] = [size, round(float(out))]
            except (OSError, ValueError):
                fresh[rel] = [size, None]
    if fresh != cache and os.path.isdir(adir):
        json.dump(fresh, open(cache_path, "w"), sort_keys=True)
    return {k: v[1] for k, v in fresh.items()}


def collect():
    """Ordered list of available chapters across the canon."""
    chapters = []
    for b in BOOKS:
        d = os.path.join(SRC, b["slug"])
        if not os.path.isdir(d):
            continue
        for n in range(1, b["chapters"] + 1):
            p = os.path.join(d, "%03d.md" % n)
            if os.path.exists(p):
                chapters.append((b, n, p))
    return chapters


def main():
    chapters = collect()
    if os.path.isdir(OUT):
        # keep audio; rebuild everything else
        for name in os.listdir(OUT):
            if name == "audio":
                continue
            full = os.path.join(OUT, name)
            shutil.rmtree(full) if os.path.isdir(full) else os.remove(full)
    os.makedirs(OUT, exist_ok=True)
    have = {(b["slug"], n) for b, n, _ in chapters}
    manifest = []
    lengths = durations()
    read_js = open(os.path.join(ROOT, "scripts", "read.js"), encoding="utf-8").read()
    open(os.path.join(OUT, "read.js"), "w", encoding="utf-8").write(read_js)
    read_tag = '<script src="../read.js?v=%s" defer></script>' % hashlib.sha1(read_js.encode("utf-8")).hexdigest()[:8]

    def audio_of(c):
        """Site path of a chapter's recording, or None when it has none yet."""
        rel = "audio/%s/%d.mp3" % (c[0]["slug"], c[1])
        return rel if os.path.exists(os.path.join(OUT, rel)) else None

    for idx, (b, n, path) in enumerate(chapters):
        meta, blocks = parse(path)
        intro = "%s, chapter %d." % (b["name"], n)
        parts, speech = [], [intro]
        if meta.get("numbering"):
            parts.append('<div class="numbering">%s</div>' % inline(meta["numbering"]))
        for kind, val in blocks:
            if kind == "h":
                parts.append('<h2 class="sec">%s</h2>' % esc(val))
            elif kind == "t":
                parts.append('<p class="title">%s</p>' % inline(val, True))
                speech.append(plain(val))
            else:
                parts.append('<p class="v">%s</p>' % " ".join(
                    '<sup class="n" id="v%d">%d</sup>%s' % (vn, vn, inline(t, True)) for vn, t in val))
                speech.extend(plain(t) for _, t in val)
        prev_ = chapters[idx - 1] if idx > 0 else None
        next_ = chapters[idx + 1] if idx + 1 < len(chapters) else None

        def link(c, cls, label):
            if not c:
                return '<span class="%s">Beginning of the Bible</span>' % cls
            cb, cn, _ = c
            href = ("%d.html" % cn) if cb is b else ("../%s/%d.html" % (cb["slug"], cn))
            return '<a class="%s" href="%s">%s %s %d</a>' % (cls, href, label, esc(cb["name"]), cn)

        audio_url = "audio/%s/%d.mp3" % (b["slug"], n)
        has_audio = os.path.exists(os.path.join(OUT, audio_url))
        spoken = " ".join(speech)
        html_body = "\n".join(parts)
        # Word timings for Listen + Read (written by scripts/align.py) count only if they were made
        # for exactly this text and the page has one highlightable word for each timed word.
        sync_url, skip = None, len(words(intro))
        if has_audio:
            try:
                timing = json.load(open(os.path.join(OUT, audio_url[:-4] + ".json")))
                if (timing.get("sum") == checksum(spoken) and timing.get("words") == len(words(spoken))
                        and html_body.count('<span class="w">') == len(words(spoken)) - skip):
                    sync_url = audio_url[:-4] + ".json"
            except (OSError, ValueError):
                pass
        data = ' data-id="%s-%d" data-title="%s %d" data-url="%s/%d.html" data-skip="%d"' % (
            b["slug"], n, esc(b["name"]), n, b["slug"], n, skip)
        buttons = ""
        if has_audio:
            data += ' data-audio="../%s"' % audio_url
            buttons = '<button class="btn" id="lr-start" type="button">&#9654; Listen + Read</button> '
        if sync_url:
            data += ' data-sync="../%s"' % sync_url
        if next_:
            data += ' data-next="../%s/%d.html"' % (next_[0]["slug"], next_[1])
            if audio_of(next_):
                data += ' data-next-audio="../%s"' % audio_of(next_)
        body = """<h1>%s %d</h1>
<p class="sub">%s<a class="btn ghost" href="../listen/?from=%s-%d">%s</a></p>
<div id="ch"%s>
%s
</div>
<div class="pn">%s%s</div>""" % (
            esc(b["name"]), n, buttons, b["slug"], n, "Listen only" if has_audio else "&#9654; Listen from here",
            data, html_body,
            link(prev_, "prev", "&larr;"), link(next_, "next", "&rarr;") if next_ else
            '<span class="next">Next chapter coming soon</span>')
        os.makedirs(os.path.join(OUT, b["slug"]), exist_ok=True)
        open(os.path.join(OUT, b["slug"], "%d.html" % n), "w", encoding="utf-8").write(
            page("%s %d" % (b["name"], n), body, 1, read_tag))
        os.makedirs(os.path.join(OUT, "text", b["slug"]), exist_ok=True)
        open(os.path.join(OUT, "text", b["slug"], "%d.txt" % n), "w", encoding="utf-8").write(spoken)
        manifest.append({
            "id": "%s-%d" % (b["slug"], n), "book": b["name"], "slug": b["slug"], "chapter": n,
            "total": b["chapters"], "url": "%s/%d.html" % (b["slug"], n),
            "audio": audio_url if has_audio else None,
            "duration": lengths.get(audio_url) if has_audio else None,
            "text": "text/%s/%d.txt" % (b["slug"], n),
            "sync": sync_url,
        })

    # book pages
    for b in BOOKS:
        done = [n for n in range(1, b["chapters"] + 1) if (b["slug"], n) in have]
        if not done:
            continue
        cells = "".join(
            ('<a href="%d.html">%d</a>' % (n, n)) if (b["slug"], n) in have else '<span>%d</span>' % n
            for n in range(1, b["chapters"] + 1))
        body = '<h1>%s</h1><p class="sub">%d of %d chapters translated</p><div class="grid ch">%s</div>' % (
            esc(b["name"]), len(done), b["chapters"], cells)
        os.makedirs(os.path.join(OUT, b["slug"]), exist_ok=True)
        open(os.path.join(OUT, b["slug"], "index.html"), "w", encoding="utf-8").write(page(b["name"], body, 1))

    # home page
    groups = []
    for label, t in (("Old Testament", "OT"), ("New Testament", "NT")):
        cells = []
        for b in (x for x in BOOKS if x["testament"] == t):
            k = sum(1 for n in range(1, b["chapters"] + 1) if (b["slug"], n) in have)
            if k:
                cells.append('<a href="%s/">%s<small>%d of %d</small></a>' % (b["slug"], esc(b["name"]), k, b["chapters"]))
            else:
                cells.append('<span>%s<small>coming</small></span>' % esc(b["name"]))
        groups.append('<h3 class="group">%s</h3><div class="grid">%s</div>' % (label, "".join(cells)))
    latest = ""
    if chapters:
        lb, ln, _ = chapters[-1]
        latest = ('<a class="continue" id="resume" href="#" hidden><small>Pick up where you left off</small><b></b></a>'
                  '<a class="continue" href="%s/%d.html"><small>Newest chapter</small><b>%s %d</b></a>'
                  % (lb["slug"], ln, esc(lb["name"]), ln))
    resume_js = """<script>
(function(){
function get(k){try{return JSON.parse(localStorage.getItem(k)||'null')}catch(e){return null}}
function fmt(t){t=Math.floor(t||0);var m=Math.floor(t/60),x=t%60;return m+':'+(x<10?'0':'')+x}
var s=get('lastSpot'),r=get('lastRead'),a=document.getElementById('resume'),href,label,small;
if(s&&s.url){
  if(s.mode==='listen'){href='listen/';small='Keep listening';label=s.label+(s.t>3?' \u00b7 at '+fmt(s.t):'');}
  else if(s.mode==='lr'){href=s.url+'#resume-lr';small='Keep listening and reading';label=s.label+(s.t>3?' \u00b7 at '+fmt(s.t):'');}
  else{href=s.url;small='Keep reading';label=s.label+(s.v>1?', verse '+s.v:'');}
}else if(r&&r.url){href=r.url;small='Pick up where you left off';label=r.label;}
if(!href||!a)return;
a.href=href;a.querySelector('small').textContent=small;a.querySelector('b').textContent=label;a.hidden=false;
// Opening the site from outside (a bookmark, the home screen, a typed address) goes straight back
// to the last spot. Coming here from another page of the site, or asking for ?home, stays here.
var nav=performance.getEntriesByType?performance.getEntriesByType('navigation')[0]:null;
var inside=document.referrer&&document.referrer.indexOf(location.origin)===0;
if(s&&s.url&&(!nav||nav.type==='navigate')&&!inside&&!/[?&]home/.test(location.search)) location.replace(href);
})();
</script>"""
    body = '<h1>%s</h1><p class="sub">%d of 1,189 chapters translated. A new chapter arrives each night.</p>%s%s%s' % (
        SITE_TITLE, len(chapters), latest, "".join(groups), resume_js)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page(SITE_TITLE, body, 0))

    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
    os.makedirs(os.path.join(OUT, "listen"), exist_ok=True)
    listen = open(os.path.join(ROOT, "scripts", "listen.html"), encoding="utf-8").read()
    open(os.path.join(OUT, "listen", "index.html"), "w", encoding="utf-8").write(
        page("Listen", listen, 1))
    print("Built %d chapters into site/" % len(chapters))


if __name__ == "__main__":
    main()
