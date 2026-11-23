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
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import search   # the search page and index of each site (scripts/search.py)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "translations")
# Two sites are built from this repository by the same scripts: the Bible into site/ (the default)
# and, with WORK=quran in the environment, the Quran into site-quran/ (see scripts/quran.py).
WORK = os.environ.get("WORK") or "bible"
OUT = os.path.join(ROOT, "site" if WORK == "bible" else "site-" + WORK)
if WORK == "quran":
    import quran
    import quran_ar
    import quran_site
    BOOKS = quran.books(SRC)
    SITE_TITLE, FOOTER = quran.SITE_TITLE, quran.FOOTER
    HOME, UNIT, START = "Surahs", "part", "Beginning of the Quran"
else:
    BOOKS = json.load(open(os.path.join(ROOT, "data", "books.json")))
    SITE_TITLE, FOOTER = "The Bible, Freshly Translated", "An original translation from the Hebrew and Greek."
    HOME, UNIT, START = "Books", "chapter", "Beginning of the Bible"
BY_SLUG = {b["slug"]: b for b in BOOKS}
# TV mode (scripts/tv.js and the TV page). The Bible's chapters get TV mode once their pictures are made; the
# Quran has no pictures, so every surah with a recording plays in TV mode with its words over a quiet background.
TV = WORK in ("bible", "quran")
PICTURES = WORK == "bible"
# The study site (scripts/study.py) analyzes Bible chapters. Once its address is set in data/settings.json
# ("study_url"), a chapter that has an analysis (analysis/<slug>/<NNN>.md) gets a "Meaning" link to it.
STUDY_URL = ""
if WORK == "bible":
    try:
        STUDY_URL = (json.load(open(os.path.join(ROOT, "data", "settings.json"))).get("study_url") or "").rstrip("/")
    except (OSError, ValueError):
        pass


def label(b, n):
    """What a chapter is called on the site: "Job 19"; a part of the Quran: "Quran 2:62-82"."""
    return b["labels"][n - 1] if "labels" in b else "%s %d" % (b["name"], n)

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
.times{display:flex;justify-content:space-between;align-items:center;font-size:.8rem;color:var(--text-soft);font-variant-numeric:tabular-nums;margin-top:.1rem}
.alt-t{font:inherit;font-size:.78rem;color:var(--accent);background:transparent;border:1px solid var(--rule);border-radius:999px;padding:0 .8rem;min-height:30px;cursor:pointer;-webkit-tap-highlight-color:transparent}
.alt-t:active{background:var(--shade)}
.alt-t:focus-visible{outline:2px solid var(--accent)}
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
#ch{position:relative;isolation:isolate}
body.lr #ch p{color:#A396C6}
body.lr #ch .w{color:#A396C6;cursor:pointer;transition:color .4s ease;-webkit-tap-highlight-color:transparent}
body.lr #ch .w.on{color:var(--text)}
body.lr #ch .w.now{color:#fff}
.lr-pill{position:absolute;left:0;top:0;z-index:-1;border-radius:7px;background:rgba(183,155,232,.22);pointer-events:none;opacity:0;transition:transform .26s cubic-bezier(.25,.8,.35,1),width .26s cubic-bezier(.25,.8,.35,1),opacity .3s ease}
body:not(.lr) .lr-pill{display:none}
body.lr #ch .alt,body.lr #ch .note{opacity:.5}
body.lr.noalt #ch .aside,body.lr.noalt #ch sup.n:has(+ .silent){display:none}
@media (prefers-reduced-motion:reduce){body.lr #ch .w,.lr-pill{transition:none}}
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
#ch sup.n{scroll-margin-top:1.5rem}
#ch .w.hit{background:rgba(183,155,232,.3);border-radius:3px;transition:background 1.5s ease}
.top .find{display:inline-flex;align-items:center;padding:.15rem 0}
@media (max-width:400px){.top{gap:.5rem;font-size:.74rem;letter-spacing:.03em}.top span{gap:.8rem!important}.top .lang a,.top .lang b{padding:.1rem .45rem!important}}
@media (max-width:340px){.top span{gap:.5rem!important}.top .lang a,.top .lang b{padding:.1rem .35rem!important}.top .find svg{width:1.05rem;height:1.05rem}}
.top .find svg{width:1.2rem;height:1.2rem;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round}
body.lr .toast{bottom:calc(10.5rem + env(safe-area-inset-bottom,0px))}
"""
if TV:   # the TV link beside Listen, and a chapter's TV mode button
    CSS += """.top span{display:flex;gap:1.4rem}
.btn.tv{background:var(--shade);color:var(--heading);border-color:var(--accent)}
.btn.tv svg{width:1.15em;height:1.15em;vertical-align:-.2em;margin-right:.4em;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
"""
if WORK == "quran":   # the line above a part's title that names its surah; the Arabic pages and the language switch
    CSS += ".eyebrow{font-family:var(--sans);color:var(--text-soft);font-size:.78rem;letter-spacing:.1em;text-transform:uppercase;margin:0}\n"
    CSS += quran_ar.CSS + quran_site.CSS + ".tvnote{font-family:var(--sans);font-size:.85rem;color:var(--text-soft);margin:2.5rem 0 0}\n"


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
    outside brackets (the ones read aloud) are wrapped for highlighting.

    Each bracket is wrapped in <span class="aside"> together with the space before it, so that
    Listen + Read can hide alternates and notes (they are not read aloud) without leaving a space
    before the punctuation that follows; a bracket with no read-aloud words before it takes the
    space after it instead. When nothing in the text is read aloud (a verse that is only an
    alternate reading), its asides are also marked "silent" so its verse number can be hidden."""
    out, i = [], 0
    put = spans if spoken else esc
    cls = "aside silent" if spoken and not plain(text) else "aside"
    for m in re.finditer(r"\[([^\[\]]+)\]", text):
        before = text[i:m.start()]
        kept = before.rstrip()
        out.append(put(kept))
        body = m.group(1).strip()
        if body.lower().startswith("alt:"):
            mark = '<span class="alt">[alt: %s]</span>' % esc(body[4:].strip())
        else:
            mark = '<span class="note">[%s]</span>' % esc(body)
        i = m.end()
        gap, after = before[len(kept):], ""
        if not plain(text[:m.start()]):
            after = re.match(r"\s*", text[i:]).group()
            i += len(after)
        out.append('<span class="%s">%s%s%s</span>' % (cls, esc(gap), mark, esc(after)))
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


LANG_TAG = ""   # the language switch's script on the Quran site (scripts/lang.js), set in main()


def page(title, body, depth, tail="", css="", lang="", nav=None, footer=None):
    """A whole page. lang: the Quran site's English | Arabic switch for this page (quran_ar.pill()).
    nav, footer: the top bar's contents and the footer line in place of the usual ones (the Arabic pages have their own)."""
    up = "../" * depth
    links = '<a href="%slisten/">Listen</a>%s' % (up, search.nav_link(up))
    if TV:
        links = '<span><a href="%stv/">TV</a>%s%s</span>' % (up, links, lang)
    if nav is None:
        nav = '<a href="%s?home">%s</a>%s' % (up or "./", HOME, links)
    if LANG_TAG:
        tail += LANG_TAG % up
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#171223">
<title>%s</title>
<style>%s</style></head>
<body><div class="wrap">
<nav class="top">%s</nav>
%s
<footer>%s</footer>
</div>%s</body></html>
""" % (esc(title), CSS + css, nav, body, FOOTER if footer is None else footer, tail)


TV_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2.5" y="4.5" width="19" height="12.5" rx="2"/>'
           '<path d="M8 20.5h8M12 17v3.5"/></svg>')

# Only on the TV page: the chapters that have pictures, as cards with the chapter's first picture.
TV_CSS = """
.wrap{max-width:68rem}
.tvh{display:grid;grid-template-columns:repeat(auto-fill,minmax(10.5rem,1fr));gap:1rem .9rem;font-family:var(--sans)}
.tvh a{display:block;text-decoration:none;color:var(--text);border-radius:12px;-webkit-tap-highlight-color:transparent}
.tvh a:focus-visible{outline:2px solid var(--accent);outline-offset:4px}
.tvh i{display:block;position:relative;padding-top:56.25%;border-radius:10px;overflow:hidden;background:var(--panel);border:1px solid var(--rule);transition:border-color .2s ease,transform .2s ease}
.tvh img{position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;object-position:50% 20%}
.tvh i:after{content:"";position:absolute;left:50%;top:50%;width:2.6rem;height:2.6rem;margin:-1.3rem 0 0 -1.3rem;border-radius:50%;background:rgba(23,18,35,.72) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23fff' d='M9 6.5v11l9-5.500z'/%3E%3C/svg%3E") center/60% no-repeat;opacity:0;transition:opacity .2s ease}
.tvh a:hover i,.tvh a:focus-visible i{border-color:var(--accent);transform:translateY(-2px)}
.tvh a:hover i:after,.tvh a:focus-visible i:after{opacity:1}
.tvh b{display:block;font-weight:600;font-size:.95rem;margin:.5rem .1rem 0}
.tvh small{display:block;color:var(--text-soft);font-size:.78rem;margin:.05rem .1rem 0;font-variant-numeric:tabular-nums}
.tvnote{font-family:var(--sans);font-size:.85rem;color:var(--text-soft);margin:2.5rem 0 0}
@media (min-width:1500px){
.wrap{max-width:92vw;padding-top:2rem}
.top{font-size:1rem}
h1{font-size:3rem}
.sub{font-size:1.15rem}
h3.group{font-size:1rem}
.tvh{grid-template-columns:repeat(auto-fill,minmax(17rem,1fr));gap:1.6rem 1.3rem}
.tvh b{font-size:1.3rem}
.tvh small,.tvnote{font-size:1rem}
.continue{max-width:34rem}
}
"""


def pictures_listed():
    """The TV mode pictures kept in the R2 bucket, from data/pictures.json (written by scripts/tv_publish.py):
    {"pictures/job/1/01-table.jpg": [bytes, id], ...}. Like the recordings, they are not in git."""
    try:
        return json.load(open(os.path.join(ROOT, "data", "pictures.json")))
    except (OSError, ValueError):
        return {}


def phrase_at(text, phrase):
    """How many spoken words into text the phrase starts, or None when it is not there."""
    def bare(t):
        return [w for w in (re.sub(r"\W", "", x).lower() for x in words(t)) if w]
    have, want = bare(text), bare(phrase)
    for i in range(len(have) - len(want) + 1 if want else 0):
        if have[i:i + len(want)] == want:
            return i
    return None


def tv_scenes(slug, n, verse_at, verse_text, listed):
    """Write site/tv/<slug>/<n>.json for TV mode. Returns (its site path or None when the chapter has no
    pictures yet, the site path of its small cover picture or None).

    The file holds where each verse starts, counted in spoken words, and which picture starts at which word.
    A chapter with no pictures yet still gets the file, with no scenes: TV mode then plays it with the words
    alone, so watching can carry on through chapters whose pictures are still on the way.

    A chapter's scene plan is data/tv/<slug>/<NNN>.json: {"scenes": [{"verse": 1, "image": "01-touch.jpg", ...}]},
    each scene starting at the first word of its verse (the first scene at the chapter's first word). A scene that
    shows a later sentence of its verse names the words it starts on, "from": "because the darkness", and starts
    there, so the picture arrives with the sentence it shows. How the pictures are chosen: TV_PICTURES.md.
    The pictures are pictures/<slug>/<n>/<image>, kept in the R2 bucket and listed in data/pictures.json (a
    picture found in site/pictures/, where the picture branch keeps them while they are made, counts as well).
    A chapter gets its pictures only when every picture of its plan is there."""
    def there(img):
        return img in listed or os.path.exists(os.path.join(OUT, img))

    scenes = []
    plan = os.path.join(ROOT, "data", "tv", slug, "%03d.json" % n)
    if os.path.exists(plan):
        start = dict(verse_at)
        try:
            planned = json.load(open(plan, encoding="utf-8")).get("scenes") or []
        except ValueError:
            planned = []
        for k, s in enumerate(planned):
            img = "pictures/%s/%d/%s" % (slug, n, s.get("image"))
            verse = s.get("verse")
            if verse not in start or not there(img):
                scenes = []   # a plan that is still being worked on
                break
            at = start[verse]
            if s.get("from"):
                inside = phrase_at(verse_text.get(verse, ""), s["from"])
                if inside is None:   # the wording changed since the plan was written: fall back to the verse's start
                    print("TV plan %s %d: verse %d has no words %r, scene starts at the verse" % (slug, n, verse, s["from"]))
                else:
                    at += inside
            scenes.append({"w": 0 if k == 0 else at, "img": img})
    rel = "tv/%s/%d.json" % (slug, n)
    os.makedirs(os.path.join(OUT, "tv", slug), exist_ok=True)
    json.dump({"verses": verse_at, "scenes": scenes}, open(os.path.join(OUT, rel), "w", encoding="utf-8"))
    if not scenes:
        return None, None
    poster = "pictures/%s/%d/poster.jpg" % (slug, n)
    return rel, poster if there(poster) else scenes[0]["img"]


def clock(seconds):
    return "%d:%02d" % (seconds // 60, seconds % 60)


def audio_listed():
    """The recordings in the R2 bucket, from data/audio.json (see scripts/media.py): {path: [bytes, seconds]}."""
    try:
        return json.load(open(os.path.join(ROOT, "data", "audio.json")))
    except (OSError, ValueError):
        return {}


def durations():
    """Length in seconds of each recording in the R2 bucket."""
    return {k: v[1] for k, v in audio_listed().items()}


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
            if name in ("audio", "pictures"):
                continue
            full = os.path.join(OUT, name)
            shutil.rmtree(full) if os.path.isdir(full) else os.remove(full)
    os.makedirs(OUT, exist_ok=True)
    have = {(b["slug"], n) for b, n, _ in chapters}
    manifest = []
    lengths = durations()
    read_js = open(os.path.join(ROOT, "scripts", "read.js"), encoding="utf-8").read()
    read_js = read_js.replace("The Bible, Freshly Translated", SITE_TITLE)
    if WORK == "quran":   # Listen + Read plays whole surahs
        for a, z in (("This chapter has no recording yet. It will be added soon.", "This has no recording yet."),
                     ("The next chapter has no recording yet. It will be added soon.", "The next surah has no recording yet."),
                     ("You are all caught up. More chapters arrive every day.", "You are all caught up."),
                     ("Position in chapter", "Position"), ("'Start of chapter'", "'Start of surah'"),
                     ("'All books'", "'All surahs'")):
            read_js = read_js.replace(a, z)
    open(os.path.join(OUT, "read.js"), "w", encoding="utf-8").write(read_js)
    read_tag = '<script src="../read.js?v=%s" defer></script>' % hashlib.sha1(read_js.encode("utf-8")).hexdigest()[:8]
    tv_tag = ""
    if TV:
        tv_js = open(os.path.join(ROOT, "scripts", "tv.js"), encoding="utf-8").read()
        if WORK == "quran":   # no pictures are made for the Quran: its words play over the quiet background
            for a, z in (("The Bible, Freshly Translated", SITE_TITLE),
                         ("Pictures for this chapter are on the way. Until then it plays with its words alone.", ""),
                         ("<small>Pictures for this chapter are on the way</small>", "<small></small>"),
                         ("More chapters arrive every day.", ""), ("All TV chapters", "All of TV mode"),
                         ("This chapter has no recording yet.", "This has no recording yet."),
                         ("That chapter was not found.", "That was not found."),
                         ("'Chapter before'", "'Before this'"), ("'Next chapter'", "'Next'"),
                         ("Chapter before", "Before this"), ("Next chapter", "Next"),
                         ("This chapter could not be loaded.", "This could not be loaded."),
                         ("Position in chapter", "Position")):
                tv_js = tv_js.replace(a, z)
        open(os.path.join(OUT, "tv.js"), "w", encoding="utf-8").write(tv_js)
        tv_tag = '<script src="../tv.js?v=%s" defer></script>' % hashlib.sha1(tv_js.encode("utf-8")).hexdigest()[:8]
    global LANG_TAG
    if WORK == "quran":   # the English | Arabic switch on every page
        lang_js = open(os.path.join(ROOT, "scripts", "lang.js"), encoding="utf-8").read()
        open(os.path.join(OUT, "lang.js"), "w", encoding="utf-8").write(lang_js)
        LANG_TAG = '<script src="%%slang.js?v=%s" defer></script>' % hashlib.sha1(lang_js.encode("utf-8")).hexdigest()[:8]
    listed = pictures_listed() if PICTURES else {}
    watch = []   # the chapters that have TV mode pictures, for the TV page
    surah_parts = {}   # the Quran: each surah's parts in order, for its one page (scripts/quran_site.py)

    def audio_of(c):
        """Site path of a chapter's recording, or None when it has none yet."""
        rel = "audio/%s/%d.mp3" % (c[0]["slug"], c[1])
        return rel if rel in lengths else None

    for idx, (b, n, path) in enumerate(chapters):
        meta, blocks = parse(path)
        intro = b["intros"][n - 1] if "intros" in b else "%s, chapter %d." % (b["name"], n)
        parts, speech = [], [intro]
        verse_at, spoken_words = [], len(words(intro))   # where each verse starts, counted in spoken words (for TV mode)
        verse_text = {}
        if meta.get("numbering"):
            parts.append('<div class="numbering">%s</div>' % inline(meta["numbering"]))
        for kind, val in blocks:
            if kind == "h":
                parts.append('<h2 class="sec">%s</h2>' % esc(val))
            elif kind == "t":
                parts.append('<p class="title">%s</p>' % inline(val, True))
                speech.append(plain(val))
                spoken_words += len(words(speech[-1]))
            else:
                parts.append('<p class="v">%s</p>' % " ".join(
                    '<sup class="n" id="v%d">%d</sup>%s' % (vn, vn, inline(t, True)) for vn, t in val))
                for vn, t in val:
                    verse_at.append([vn, spoken_words])
                    speech.append(plain(t))
                    verse_text[vn] = speech[-1]
                    spoken_words += len(words(speech[-1]))
        prev_ = chapters[idx - 1] if idx > 0 else None
        next_ = chapters[idx + 1] if idx + 1 < len(chapters) else None

        def link(c, cls, arrow):
            if not c:
                return '<span class="%s">%s</span>' % (cls, START)
            cb, cn, _ = c
            href = ("%d.html" % cn) if cb is b else ("../%s/%d.html" % (cb["slug"], cn))
            return '<a class="%s" href="%s">%s %s</a>' % (cls, href, arrow, esc(label(cb, cn)))

        audio_url = "audio/%s/%d.mp3" % (b["slug"], n)
        has_audio = audio_url in lengths
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
        data = ' data-id="%s-%d" data-title="%s" data-url="%s/%d.html" data-skip="%d"' % (
            b["slug"], n, esc(label(b, n)), b["slug"], n, skip)
        buttons = ""
        if has_audio:
            data += ' data-audio="../%s"' % audio_url
            buttons = '<button class="btn" id="lr-start" type="button">&#9654; Listen + Read</button> '
        if sync_url:
            data += ' data-sync="../%s"' % sync_url
        tv_url, poster = tv_scenes(b["slug"], n, verse_at, verse_text, listed) if PICTURES and has_audio else (None, None)
        if tv_url:
            # a plain link to the TV page; scripts/tv.js opens the player right here instead, full screen
            buttons += '<a class="btn tv" href="../tv/?c=%s-%d" data-tv="%s-%d">%sTV mode</a> ' % (
                b["slug"], n, b["slug"], n, TV_ICON)
            watch.append((b, n, poster, lengths.get(audio_url)))
        if next_:
            data += ' data-next="../%s/%d.html"' % (next_[0]["slug"], next_[1])
            if audio_of(next_):
                data += ' data-next-audio="../%s"' % audio_of(next_)
        eyebrow = '<p class="eyebrow">%s</p>\n' % esc(b["eyebrow"]) if b.get("eyebrow") else ""
        meaning = ""
        if STUDY_URL and os.path.exists(os.path.join(ROOT, "analysis", b["slug"], "%03d.md" % n)):
            meaning = ' <a class="btn ghost" href="%s/%s/%d.html">Meaning</a>' % (STUDY_URL, b["slug"], n)
        body = """%s<h1>%s</h1>
<p class="sub">%s<a class="btn ghost" href="../listen/?from=%s-%d">%s</a>%s</p>
<div id="ch"%s>
%s
</div>
<div class="pn">%s%s</div>""" % (
            eyebrow, esc(label(b, n)), buttons, b["slug"], n, "Listen only" if has_audio else "&#9654; Listen from here",
            meaning, data, html_body,
            link(prev_, "prev", "&larr;"), link(next_, "next", "&rarr;") if next_ else
            '<span class="next">Next %s coming soon</span>' % UNIT)
        os.makedirs(os.path.join(OUT, b["slug"]), exist_ok=True)
        if WORK == "quran":   # a part has no page of its own: its surah's page shows it (scripts/quran_site.py)
            surah_parts.setdefault(b["slug"], []).append({
                "meta": meta, "blocks": blocks, "spoken": spoken, "skip": skip, "audio": audio_url if has_audio else None,
                "range": b["ranges"][n - 1]})
        else:
            open(os.path.join(OUT, b["slug"], "%d.html" % n), "w", encoding="utf-8").write(
                page(label(b, n), body, 1, read_tag + tv_tag))
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
        if TV:   # the chapter's scene file when it has pictures, and its cover for the TV page
            manifest[-1].update(tv=tv_url, poster=poster)
        if "labels" in b:   # a part of the Quran: its own name, where it stands in its surah, and how many words
            # its recording opens with ("Quran, surah 2, verses 30 to 61."), which scripts/quran_join.py leaves out
            manifest[-1].update(title=label(b, n), total=b["planned"], sub="Part %d of %d" % (n, b["planned"]), skip=skip)

    # book pages (the Quran's surah pages are written by scripts/quran_site.py)
    for b in BOOKS if WORK == "bible" else ():
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
    for heading, t in (("Old Testament", "OT"), ("New Testament", "NT")) if WORK == "bible" else ():
        cells = []
        for b in (x for x in BOOKS if x["testament"] == t):
            k = sum(1 for n in range(1, b["chapters"] + 1) if (b["slug"], n) in have)
            if k:
                cells.append('<a href="%s/">%s<small>%d of %d</small></a>' % (b["slug"], esc(b["name"]), k, b["chapters"]))
            else:
                cells.append('<span>%s<small>coming</small></span>' % esc(b["name"]))
        groups.append('<h3 class="group">%s</h3><div class="grid">%s</div>' % (heading, "".join(cells)))
    latest = ""
    if chapters:
        lb, ln, _ = chapters[-1]
        href, newest = "%s/%d.html" % (lb["slug"], ln), "Newest %s" % UNIT
        if WORK == "quran":   # the newest verses, on their surah's page
            a, z = lb["ranges"][ln - 1]
            href, newest = "%s/%s" % (lb["slug"], "#v%d" % a if a > 1 else ""), "Newest verses"
        latest = ('<a class="continue" id="resume" href="#" hidden><small>Pick up where you left off</small><b></b></a>'
                  '<a class="continue" href="%s"><small>%s</small><b>%s</b></a>'
                  % (href, newest, esc(label(lb, ln))))
    resume_js = """<script>
(function(){
function get(k){try{return JSON.parse(localStorage.getItem(k)||'null')}catch(e){return null}}
function fmt(t){t=Math.floor(t||0);var m=Math.floor(t/60),x=t%60;return m+':'+(x<10?'0':'')+x}
var s=get('lastSpot'),r=get('lastRead'),a=document.getElementById('resume'),href,label,small;
if(s&&s.url){
  if(s.mode==='listen'){href='listen/';small='Keep listening';label=s.label+(s.t>3?' \u00b7 at '+fmt(s.t):'');}
  else if(s.mode==='tv'){href='tv/?c='+encodeURIComponent(s.id);small='Keep watching in TV mode';label=s.label+(s.t>3?' \u00b7 at '+fmt(s.t):'');}
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
    if not TV:
        resume_js = "\n".join(line for line in resume_js.split("\n") if "s.mode==='tv'" not in line)
    sub = "%d of 1,189 chapters translated. A new chapter arrives each night." % len(chapters)
    if WORK == "quran":
        sub, surahs = quran.home(BOOKS, esc)
        groups.append(surahs)
    body = '<h1>%s</h1><p class="sub">%s</p>%s%s%s' % (SITE_TITLE, sub, latest, "".join(groups), resume_js)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(
        page(SITE_TITLE, body, 0, lang=quran_ar.pill("en", "", "ar/") if WORK == "quran" else ""))

    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
    os.makedirs(os.path.join(OUT, "listen"), exist_ok=True)
    listen = open(os.path.join(ROOT, "scripts", "listen.html"), encoding="utf-8").read()
    listen = listen.replace("The Bible, Freshly Translated", SITE_TITLE)
    if WORK == "quran":   # whole surahs, not their parts
        listen = listen.replace("'../manifest.json'", "'../manifest-en.json'").replace("<h2>Chapters</h2>", "<h2>Surahs</h2>")
    open(os.path.join(OUT, "listen", "index.html"), "w", encoding="utf-8").write(
        page("Listen", listen, 1, lang=quran_ar.pill("en", "", "../ar/listen.html") if WORK == "quran" else ""))

    if WORK == "quran":   # each surah's one page; the TV page: every surah with a recording; and then the Arabic pages
        sections, surahs = quran_site.build(OUT, {
            "page": page, "esc": esc, "inline": inline, "plain": plain, "lengths": lengths, "books": BOOKS,
            "parts": surah_parts, "listed": audio_listed(), "read_tag": read_tag, "tv_tag": tv_tag, "TV_ICON": TV_ICON,
            "pill": quran_ar.pill})
        cells = "".join('<a href="?c=%s" data-tv="%s">%s<small>%s</small></a>' % (
            c["id"], c["id"], esc(c["title"]), clock(c["duration"]) if c["duration"] else "") for c in surahs)
        body = ('<h1>TV mode</h1><p class="sub">The words light up as they are read, over a calm background. '
                'Best on a TV, or on a phone turned sideways.</p>'
                '<a class="continue" id="tv-resume" href="#" hidden><small>Keep watching</small><b></b></a>'
                + ('<div class="grid">%s</div>' % cells if cells else '<p class="tvnote">The first recordings are on the way.</p>'))
        os.makedirs(os.path.join(OUT, "tv"), exist_ok=True)
        open(os.path.join(OUT, "tv", "index.html"), "w", encoding="utf-8").write(
            page("TV mode", body, 1, tv_tag, lang=quran_ar.pill("en", "", "../ar/tv.html")))
        n_ar = quran_ar.build(OUT, {"page": page, "esc": esc, "words": words, "checksum": checksum, "clock": clock,
                                    "lengths": lengths, "english": BOOKS, "read_tag": read_tag, "tv_tag": tv_tag,
                                    "TV_ICON": TV_ICON, "sections": sections})
        print("Built the Arabic pages of 114 surahs (%d read aloud)" % n_ar)
    elif TV:   # the TV page: every chapter that has pictures, book by book; scripts/tv.js plays them
        groups, book = [], None
        for b, n, poster, secs in watch:
            if b is not book:
                book = b
                groups.append('</div><h3 class="group">%s</h3><div class="tvh">' % esc(b["name"]))
            groups.append('<a href="?c=%s-%d" data-tv="%s-%d"><i><img src="../%s" alt="" loading="lazy"></i><b>%s</b>%s</a>' % (
                b["slug"], n, b["slug"], n, esc(poster), esc(label(b, n)),
                "<small>%s</small>" % clock(secs) if secs else ""))
        body = ('<h1>TV mode</h1><p class="sub">Pictures for each part of a chapter, with the words lighting up as they '
                'are read. Best on a TV, or on a phone turned sideways.</p>'
                '<a class="continue" id="tv-resume" href="#" hidden><small>Keep watching</small><b></b></a>')
        if watch:
            body += "".join(groups)[len("</div>"):] + "</div>"
            body += ('<p class="tvnote">%d chapter%s %s pictures so far. More are added as they are made; until then a '
                     'chapter plays with its words alone.</p>' % (len(watch), "" if len(watch) == 1 else "s",
                                                                 "has" if len(watch) == 1 else "have"))
        else:
            body += '<p class="tvnote">The first pictures are on the way.</p>'
        os.makedirs(os.path.join(OUT, "tv"), exist_ok=True)
        open(os.path.join(OUT, "tv", "index.html"), "w", encoding="utf-8").write(
            page("TV mode", body, 1, tv_tag, TV_CSS))
    # the search page and this site's search index (scripts/search.py); the Quran's also covers its Arabic
    search.build(WORK, OUT, {
        "chapters": chapters, "parse": parse, "books": BOOKS, "shown": quran_ar.shown if WORK == "quran" else None,
        "page": lambda body, css: page("Search", body, 1, "", css,
                                       lang=quran_ar.pill("en", "", "../ar/") if WORK == "quran" else "")})
    print("Built %d %ss into %s/" % (len(chapters), UNIT, os.path.basename(OUT)))


if __name__ == "__main__":
    main()
