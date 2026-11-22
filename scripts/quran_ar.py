#!/usr/bin/env python3
"""The Quran in Arabic: the Arabic text of every surah with a reciter's voice, beside the English site.

Built by `WORK=quran python3 scripts/build.py` together with the English pages (it calls build() below),
into site-quran/:

    ar/index.html            all 114 surahs
    ar/<n>.html              one surah, whole, in the Arabic text of sources/quran/ (never translated)
    ar/listen.html, ar/tv.html   Listen and TV mode for the Arabic recordings
    manifest-ar.json         the surahs that have a recording (the English pages use manifest.json)
    text/ar/<n>.txt          the words as recited (for TV mode's captions)
    tv/ar/<n>.json           where each verse starts, counted in words (for TV mode)

Recordings are a human reciter's (see RECITER), fetched by scripts/recite.py into the R2 bucket as
audio/ar/<n>.mp3 and listed in data/audio.json like every other recording; recite.py also writes the
start time of every word, audio/ar/<n>.json, for Listen + Read and TV mode. A surah's page works with
or without them: without a recording it is text only.

Every page of the Quran site has an English | Arabic switch at the top (scripts/lang.js), which lands on
the same verse in the other language and remembers the choice in the browser.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURAHS = json.load(open(os.path.join(ROOT, "data", "quran.json"), encoding="utf-8"))
NAMES = {s["n"]: s["name"] for s in json.load(open(os.path.join(ROOT, "data", "quran_arabic.json"), encoding="utf-8"))}
RECITER = "Mahmoud Khalil al-Husary"
SLUG = "ar"
FOOTER = ('The Arabic text of the Quran as written (the Hafs reading, from quranenc.com, CC BY-SA 4.0), with no '
          'translation. Recitation by %s, from everyayah.com.' % RECITER)

# sources/quran/ writes the open (staggered) tanween with three older code points that only the
# King Fahd Complex's own font draws as open tanween. On screen they are shown with the standard
# characters for open tanween, which the site's Quran font (Scheherazade New) draws correctly.
# Nothing else in the text is changed.
OPEN_TANWEEN = str.maketrans({"ٗ": "ࣰ", "ٞ": "ࣱ", "ٖ": "ࣲ"})
DIGITS = "٠١٢٣٤٥٦٧٨٩"
END = "۝"            # the end-of-verse sign; the font draws it around the number that follows
RUB = "۞"            # the mark that opens each quarter of a hizb: a new paragraph starts there

CSS = """
@font-face{font-family:"Quran Text";src:url(/fonts/scheherazade-new-arabic.woff2) format("woff2");font-display:swap;unicode-range:U+0600-06FF,U+0750-077F,U+0870-08FF,U+200C-200E,U+FB50-FDFF,U+FE70-FEFF}
.top{position:sticky;top:0;z-index:15;background:var(--bg);padding-top:.7rem;margin-top:-.7rem}
#ch sup.n{scroll-margin-top:4.5rem}
.top .lang{display:inline-flex;align-items:stretch;gap:0;border:1px solid var(--rule);border-radius:999px;overflow:hidden;letter-spacing:.04em}
.top .lang a,.top .lang b{display:flex;align-items:center;padding:.1rem .6rem;font-weight:normal;min-height:28px}
.top .lang b{background:var(--shade);color:var(--heading)}
.top .lang [lang=ar]{font-family:"Quran Text",var(--sans);font-size:1.15rem;line-height:1;letter-spacing:0;text-transform:none;padding-bottom:.25rem}
#ch.ar{font-family:"Quran Text","Noto Naskh Arabic","Geeza Pro","Arabic Typesetting",serif;font-size:1.7rem;line-height:2.25;text-align:justify;word-spacing:.06em}
#ch.ar p.v{margin:0 0 1.3rem}
#ch.ar p.bas{text-align:center;color:var(--heading);margin:0 0 1.3rem}
body.lr #ch.ar p.bas{color:#A396C6}
#ch.ar sup.n{display:inline-block;width:0;height:1em;margin:0;padding:0;overflow:hidden}
#ch.ar .end{color:var(--accent);margin:0 .12em;user-select:none;-webkit-user-select:none;white-space:nowrap}
h1.arh{font-family:"Quran Text",var(--serif);font-size:2.6rem;line-height:1.6;margin:.2rem 0 .1rem}
.top>span{align-items:center}
.grid .arn{display:block;font-family:"Quran Text",var(--serif);font-weight:normal;font-size:1.5rem;line-height:1.55;color:var(--heading)}
.lang-note{font-family:var(--sans);font-size:.85rem;color:var(--text-soft)}
"""


def shown(t):
    return t.translate(OPEN_TANWEEN)


def number(n):
    return "".join(DIGITS[int(c)] for c in str(n))


def surah(n):
    """(the opening line "In the name of God..." when the surah has it apart from its verses, else None,
    [(verse number, [words]), ...]) in the form shown on the page."""
    opening, verses = None, []
    for line in open(os.path.join(ROOT, "sources", "quran", "%03d.txt" % n), encoding="utf-8"):
        k, t = line.rstrip("\n").split("\t", 1)
        if int(k) == 0:
            opening = shown(t).split()
        else:
            verses.append((int(k), shown(t).split()))
    return opening, verses


def recited(n):
    """The words of a surah in the order they are recited: the opening line (when apart), then every verse.
    scripts/recite.py times exactly these words."""
    opening, verses = surah(n)
    return " ".join((opening or []) + [w for _, ws in verses for w in ws])


def english_name(n):
    return SURAHS[n - 1].get("name")


def title(n):
    return "Surah %d · %s" % (n, NAMES[n])


def pill(here, en_href, ar_href, attrs=""):
    """The English | Arabic switch in the top bar."""
    en = '<b>English</b>' if here == "en" else '<a href="%s" data-lang="en"%s>English</a>' % (en_href, attrs)
    ar = '<b lang="ar">عربي</b>' if here == "ar" else '<a href="%s" data-lang="ar" lang="ar"%s>عربي</a>' % (ar_href, attrs)
    return '<span class="lang" role="group" aria-label="Language">%s%s</span>' % (en, ar)


def nav(here_en):
    """The top bar of an Arabic page: Surahs, TV, Listen, and the switch."""
    return ('<a href="./">Surahs</a><span><a href="tv.html">TV</a><a href="listen.html">Listen</a>%s</span>'
            % here_en)


def build(out, x):
    """Write the Arabic pages. x holds what scripts/build.py shares: page(), esc(), words(), checksum(),
    lengths (recording seconds by path), english (the English "books"), read_tag, tv_tag, TV_ICON."""
    esc, words = x["esc"], x["words"]
    english = {b["surah"]: b for b in x["english"]}
    os.makedirs(os.path.join(out, "ar"), exist_ok=True)
    for sub in ("text", "tv"):
        os.makedirs(os.path.join(out, sub, SLUG), exist_ok=True)
    os.makedirs(os.path.join(out, "fonts"), exist_ok=True)
    with open(os.path.join(ROOT, "scripts", "fonts", "scheherazade-new-arabic.woff2"), "rb") as f:
        font = f.read()
    with open(os.path.join(out, "fonts", "scheherazade-new-arabic.woff2"), "wb") as f:
        f.write(font)

    def audio(n):
        rel = "audio/%s/%d.mp3" % (SLUG, n)
        return rel if rel in x["lengths"] else None

    manifest, cells = [], []
    for s in SURAHS:
        n = s["n"]
        opening, verses = surah(n)
        spoken = recited(n)
        count = len(words(spoken))
        rel = audio(n)
        secs = x["lengths"].get(rel) if rel else None

        # the text: the opening line apart, then the verses, a new paragraph at each quarter-hizb mark
        parts, para, verse_at, at = [], [], [], 0

        def wrap(ws):
            return " ".join('<span class="w">%s</span>' % esc(w) for w in ws)
        if opening:
            parts.append('<p class="bas">%s</p>' % wrap(opening))
            at += len(opening)
        for v, ws in verses:
            if para and ws[0].startswith(RUB):
                parts.append('<p class="v">%s</p>' % " ".join(para))
                para = []
            verse_at.append([v, at])
            at += len(ws)
            para.append('<sup class="n" id="v%d"></sup>%s <span class="end">%s%s</span>' % (v, wrap(ws), END, number(v)))
        if para:
            parts.append('<p class="v">%s</p>' % " ".join(para))
        body_text = "\n".join(parts)
        if body_text.count('<span class="w">') != count:
            raise SystemExit("Arabic surah %d: %d words on the page, %d recited" % (n, body_text.count('<span class="w">'), count))

        # word timings from scripts/recite.py count only when made for exactly these words
        sync = None
        if rel:
            try:
                timing = json.load(open(os.path.join(out, rel[:-4] + ".json"), encoding="utf-8"))
                if timing.get("sum") == x["checksum"](spoken) and timing.get("words") == count and len(timing.get("t") or []) == count:
                    sync = rel[:-4] + ".json"
            except (OSError, ValueError):
                pass

        nxt = n + 1 if n < len(SURAHS) else None
        data = (' data-id="%s-%d" data-title="%s" data-url="ar/%d.html" data-skip="0" data-lang="ar" data-stream="1"'
                ' data-artist="%s"' % (SLUG, n, esc(title(n)), n, esc(RECITER)))
        buttons = ""
        if rel:
            data += ' data-audio="../%s"' % rel
            if sync:
                data += ' data-sync="../%s"' % sync
            buttons = ('<button class="btn" id="lr-start" type="button">&#9654; Listen + Read</button> '
                       '<a class="btn tv" href="tv.html?c=%s-%d" data-tv="%s-%d">%sTV mode</a> '
                       '<a class="btn ghost" href="listen.html?from=%s-%d">Listen only</a>'
                       % (SLUG, n, SLUG, n, x["TV_ICON"], SLUG, n))
        if nxt:
            data += ' data-next="../ar/%d.html"' % nxt
            if audio(nxt):
                data += ' data-next-audio="../%s"' % audio(nxt)
        b = english.get(n)
        parts_attr = ' data-surah="%d"' % n
        if b:
            parts_attr += ' data-parts="%s"' % ",".join("%d-%d" % (a, z) for a, z in b["ranges"])
        switch = pill("ar", "../quran-%d/1.html" % n if b else "../?home", "", parts_attr)
        name = english_name(n)
        eyebrow = "Surah %d%s" % (n, " · " + name if name else "")
        about = "%d verses" % s["verses"] + (" · recited by %s" % RECITER if rel else "")
        prev_link = '<a class="prev" href="%d.html">&larr; %s</a>' % (n - 1, esc(title(n - 1))) if n > 1 else \
            '<span class="prev">Beginning of the Quran</span>'
        next_link = '<a class="next" href="%d.html">%s &rarr;</a>' % (nxt, esc(title(nxt))) if nxt else \
            '<span class="next">End of the Quran</span>'
        body = """<p class="eyebrow">%s</p>
<h1 class="arh" lang="ar" dir="rtl">سورة %s</h1>
<p class="sub">%s%s</p>
<div id="ch" class="ar" lang="ar" dir="rtl"%s>
%s
</div>
<div class="pn">%s%s</div>""" % (esc(eyebrow), esc(NAMES[n]), buttons,
                                 ('<br>' if buttons else '') + '<span class="lang-note">%s</span>' % esc(about),
                                 data, body_text, prev_link, next_link)
        open(os.path.join(out, "ar", "%d.html" % n), "w", encoding="utf-8").write(
            x["page"](title(n), body, 1, x["read_tag"] + x["tv_tag"], footer=FOOTER, nav=nav(switch)))
        open(os.path.join(out, "text", SLUG, "%d.txt" % n), "w", encoding="utf-8").write(spoken)
        json.dump({"verses": verse_at, "scenes": []}, open(os.path.join(out, "tv", SLUG, "%d.json" % n), "w"))
        if rel:
            manifest.append({
                "id": "%s-%d" % (SLUG, n), "book": "Surahs", "slug": SLUG, "chapter": n, "total": len(SURAHS),
                "url": "ar/%d.html" % n, "audio": rel, "duration": secs, "text": "text/%s/%d.txt" % (SLUG, n),
                "sync": sync, "title": title(n), "sub": "%d verses · %s" % (s["verses"], RECITER),
                "lang": "ar", "stream": True,
            })
        cells.append('<a href="%d.html"><b class="arn" lang="ar">%s</b>Surah %d<small>%d verses%s</small></a>' % (
            n, esc(NAMES[n]), n, s["verses"], " · " + x["clock"](secs) if secs else ""))

    json.dump(manifest, open(os.path.join(out, "manifest-ar.json"), "w", encoding="utf-8"), ensure_ascii=False)

    # the Arabic home page
    have = len(manifest)
    sub = "The Arabic text of all 114 surahs, as written, with no translation. " + (
        "Recited by %s%s." % (RECITER, "" if have == len(SURAHS) else " (%d of 114 surahs so far, more are on the way)" % have)
        if have else "A recitation by %s is on the way." % RECITER)
    resume = """<a class="continue" id="resume" href="#" hidden><small>Pick up where you left off</small><b></b></a>
<script>
(function(){
function get(k){try{return JSON.parse(localStorage.getItem(k)||'null')}catch(e){return null}}
function fmt(t){t=Math.floor(t||0);var m=Math.floor(t/60),x=t%60;return m+':'+(x<10?'0':'')+x}
var s=get('lastSpot'),a=document.getElementById('resume'),href,small,label;
if(!s||!s.url||!/^ar-/.test(s.id||''))return;
if(s.mode==='listen'){href='listen.html';small='Keep listening';}
else if(s.mode==='tv'){href='tv.html?c='+encodeURIComponent(s.id);small='Keep watching in TV mode';}
else if(s.mode==='lr'){href='../'+s.url+'#resume-lr';small='Keep listening and reading';}
else{href='../'+s.url+(s.v>1?'#v'+s.v:'');small='Keep reading';}
label=s.label+(s.mode==='read'?(s.v>1?', verse '+s.v:''):(s.t>3?' \\u00b7 at '+fmt(s.t):''));
a.href=href;a.querySelector('small').textContent=small;a.querySelector('b').textContent=label;a.hidden=false;
})();
</script>"""
    body = ('<h1>The Quran in Arabic</h1><p class="sub">%s</p>%s<h3 class="group">Surahs</h3><div class="grid">%s</div>'
            % (esc(sub), resume, "".join(cells)))
    open(os.path.join(out, "ar", "index.html"), "w", encoding="utf-8").write(
        x["page"]("The Quran in Arabic", body, 1, "", footer=FOOTER, nav=nav(pill("ar", "../?home", ""))))

    # Listen: the same player as the English site, over the Arabic recordings
    listen = open(os.path.join(ROOT, "scripts", "listen.html"), encoding="utf-8").read()
    listen = (listen.replace("'../manifest.json'", "'../manifest-ar.json'").replace("<h2>Chapters</h2>", "<h2>Surahs</h2>")
              .replace("The Bible, Freshly Translated", RECITER))
    if not manifest:
        listen = '<h1>Listen</h1><p class="sub">%s</p>' % esc("A recitation by %s is on the way." % RECITER)
    open(os.path.join(out, "ar", "listen.html"), "w", encoding="utf-8").write(
        x["page"]("Listen", listen, 1, "", footer=FOOTER, nav=nav(pill("ar", "../listen/", ""))))

    # TV mode: every surah that has a recording
    tv_cells = "".join('<a href="?c=%s" data-tv="%s"><b class="arn" lang="ar">%s</b>Surah %d<small>%s</small></a>' % (
        c["id"], c["id"], esc(NAMES[c["chapter"]]), c["chapter"], x["clock"](c["duration"]) if c["duration"] else "")
        for c in manifest)
    body = ('<h1>TV mode</h1><p class="sub">The Arabic words light up as they are recited, over a calm background. '
            'Best on a TV, or on a phone turned sideways.</p>'
            '<a class="continue" id="tv-resume" href="#" hidden><small>Keep watching</small><b></b></a>'
            + ('<div class="grid">%s</div>' % tv_cells if manifest else
               '<p class="tvnote">%s</p>' % esc("A recitation by %s is on the way." % RECITER)))
    open(os.path.join(out, "ar", "tv.html"), "w", encoding="utf-8").write(
        x["page"]("TV mode", body, 1, x["tv_tag"], footer=FOOTER, nav=nav(pill("ar", "../tv/", ""))))
    return have
