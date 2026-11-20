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
.btn{display:inline-block;font-family:var(--sans);font-size:.85rem;color:var(--bg);background:var(--accent);border:0;border-radius:999px;padding:.5rem 1rem;text-decoration:none;cursor:pointer}
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
"""


def esc(s):
    return html.escape(s, quote=True)


def inline(text):
    """Escape text and turn [alt: ...] / [...] into styled spans."""
    out, i = [], 0
    for m in re.finditer(r"\[([^\[\]]+)\]", text):
        out.append(esc(text[i:m.start()]))
        body = m.group(1).strip()
        if body.lower().startswith("alt:"):
            out.append('<span class="alt">[alt: %s]</span>' % esc(body[4:].strip()))
        else:
            out.append('<span class="note">[%s]</span>' % esc(body))
        i = m.end()
    out.append(esc(text[i:]))
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


def page(title, body, depth):
    up = "../" * depth
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#171223">
<title>%s</title>
<style>%s</style></head>
<body><div class="wrap">
<nav class="top"><a href="%s">Books</a><a href="%slisten/">Listen</a></nav>
%s
<footer>An original translation from the Hebrew and Greek.</footer>
</div></body></html>
""" % (esc(title), CSS, up or "./", up, body)


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

    for idx, (b, n, path) in enumerate(chapters):
        meta, blocks = parse(path)
        parts, speech = [], ["%s, chapter %d." % (b["name"], n)]
        if meta.get("numbering"):
            parts.append('<div class="numbering">%s</div>' % inline(meta["numbering"]))
        for kind, val in blocks:
            if kind == "h":
                parts.append('<h2 class="sec">%s</h2>' % esc(val))
            elif kind == "t":
                parts.append('<p class="title">%s</p>' % inline(val))
                speech.append(plain(val))
            else:
                parts.append('<p class="v">%s</p>' % " ".join(
                    '<sup class="n" id="v%d">%d</sup>%s' % (vn, vn, inline(t)) for vn, t in val))
                speech.extend(plain(t) for _, t in val)
        prev_ = chapters[idx - 1] if idx > 0 else None
        next_ = chapters[idx + 1] if idx + 1 < len(chapters) else None

        def link(c, cls, label):
            if not c:
                return '<span class="%s">Beginning of the Bible</span>' % cls
            cb, cn, _ = c
            href = ("%d.html" % cn) if cb is b else ("../%s/%d.html" % (cb["slug"], cn))
            return '<a class="%s" href="%s">%s %s %d</a>' % (cls, href, label, esc(cb["name"]), cn)

        audio_rel = os.path.join("audio", b["slug"], "%d.mp3" % n)
        has_audio = os.path.exists(os.path.join(OUT, audio_rel))
        body = """<h1>%s %d</h1>
<p class="sub"><a class="btn ghost" href="../listen/?from=%s-%d">&#9654; Listen from here</a></p>
%s
<div class="pn">%s%s</div>""" % (
            esc(b["name"]), n, b["slug"], n, "\n".join(parts),
            link(prev_, "prev", "&larr;"), link(next_, "next", "&rarr;") if next_ else
            '<span class="next">Next chapter coming soon</span>')
        os.makedirs(os.path.join(OUT, b["slug"]), exist_ok=True)
        open(os.path.join(OUT, b["slug"], "%d.html" % n), "w", encoding="utf-8").write(
            page("%s %d" % (b["name"], n), body, 1))
        manifest.append({
            "id": "%s-%d" % (b["slug"], n), "book": b["name"], "chapter": n,
            "url": "%s/%d.html" % (b["slug"], n),
            "audio": audio_rel.replace(os.sep, "/") if has_audio else None,
            "text": " ".join(speech),
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
        latest = ('<a class="continue" href="%s/%d.html"><small>Newest chapter</small><b>%s %d</b></a>'
                  '<a class="continue" id="resume" href="#" hidden><small>Pick up where you left off</small><b></b></a>'
                  % (lb["slug"], ln, esc(lb["name"]), ln))
    resume_js = """<script>
try{var r=JSON.parse(localStorage.getItem('lastRead')||'null');if(r){var a=document.getElementById('resume');a.href=r.url;a.querySelector('b').textContent=r.label;a.hidden=false;}}catch(e){}
</script>"""
    body = '<h1>%s</h1><p class="sub">%d of 1,189 chapters translated. A new chapter arrives each night.</p>%s%s%s' % (
        SITE_TITLE, len(chapters), latest, "".join(groups), resume_js)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page(SITE_TITLE, body, 0))

    # remember last chapter read (tiny script appended to chapter pages)
    for b, n, _ in chapters:
        p = os.path.join(OUT, b["slug"], "%d.html" % n)
        s = open(p, encoding="utf-8").read()
        s = s.replace("</body>", "<script>try{localStorage.setItem('lastRead',JSON.stringify({url:'%s/%d.html',label:'%s %d'}))}catch(e){}</script></body>"
                      % (b["slug"], n, b["name"].replace("'", ""), n))
        open(p, "w", encoding="utf-8").write(s)

    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
    os.makedirs(os.path.join(OUT, "listen"), exist_ok=True)
    listen = open(os.path.join(ROOT, "scripts", "listen.html"), encoding="utf-8").read()
    open(os.path.join(OUT, "listen", "index.html"), "w", encoding="utf-8").write(
        page("Listen", listen, 1))
    print("Built %d chapters into site/" % len(chapters))


if __name__ == "__main__":
    main()
