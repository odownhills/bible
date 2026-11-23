#!/usr/bin/env python3
"""The Quran in Arabic: the Arabic text of every surah, beside the English site, read aloud in a plain voice when
its recording is ready.

Built by `WORK=quran python3 scripts/build.py` together with the English pages (it calls build() below),
into site-quran/:

    ar/index.html            all 114 surahs
    ar/<n>.html              one surah, whole, in the Arabic text of sources/quran/ (never translated)
    ar/listen.html, ar/tv.html   Listen and TV mode for the Arabic recordings
    manifest-ar.json         the surahs that have a recording (the English pages use manifest.json)
    text/ar/<n>.txt          the words as read aloud (for TV mode's captions)
    tv/ar/<n>.json           where each verse starts, counted in words (for TV mode)

Obay (2026-11-22): the Arabic is read in a plain, ordinary speaking voice, never chanted or recited in the
traditional way ("plain, honest scripture, no tradition"). A recording goes in the R2 bucket as
audio/ar/<n>.mp3, listed in data/audio.json like every other recording, with the start time of every word in
site-quran/audio/ar/<n>.json for Listen + Read and TV mode. A surah's page works with or without them:
without a recording it is text only.

Every page of the Quran site has an English | Arabic switch at the top (scripts/lang.js), which lands on
the same verse in the other language and remembers the choice in the browser.

A long surah has a bar of sections to jump between, named as in the English translation (its headings,
scripts/quran_site.py) for the verses translated so far; past those, a section runs from one quarter-hizb
mark (RUB) to the next and is named by its verses.
"""
import json
import os

import quran_site
import search

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURAHS = json.load(open(os.path.join(ROOT, "data", "quran.json"), encoding="utf-8"))
NAMES = {s["n"]: s["name"] for s in json.load(open(os.path.join(ROOT, "data", "quran_arabic.json"), encoding="utf-8"))}
# Who reads the recordings, as named on the pages (scripts/arabic_voice.py)
VOICE = "a computer voice (Gemini's Sulafat, the English pages' voice)"
SLUG = "ar"
FOOTER = ('The Arabic text of the Quran as written (the Hafs reading, from quranenc.com, CC BY-SA 4.0), with no '
          'translation.' + (' Read aloud, where a recording is ready, by %s.' % VOICE if VOICE else ''))
NOT_YET = "The Arabic is not read aloud yet: a plain reading voice is on the way."

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


def spoken_words(n):
    """The words of a surah in the order they are read aloud: the opening line (when apart), then every verse.
    A recording's word times must be for exactly these words."""
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
    """The top bar of an Arabic page: Surahs, TV, Listen, Search, and the switch."""
    return ('<a href="./">Surahs</a><span><a href="tv.html">TV</a><a href="listen.html">Listen</a>%s%s</span>'
            % (search.nav_link("../"), here_en))


def sections(n, verses, named):
    """The section bar's items for surah n: [(target id, name, first verse, last verse, group heading or None)].
    named: the English sections [(name, first verse, last verse)], which cover the verses translated so far."""
    items = [("v%d" % a, name, a, z, None) for name, a, z in named]
    upto = named[-1][2] if named else 0
    total = verses[-1][0]
    starts = [upto + 1] + [v for v, ws in verses if v > upto + 1 and ws[0].startswith(RUB)] if upto < total else []
    for k, a in enumerate(starts):
        z = starts[k + 1] - 1 if k + 1 < len(starts) else total
        items.append(("v%d" % a, "Verses %d–%d" % (a, z) if z > a else "Verse %d" % a, a, z,
                      "Not translated yet" if named and k == 0 else None))
    return items


def build(out, x):
    """Write the Arabic pages. x holds what scripts/build.py shares: page(), esc(), words(), checksum(),
    lengths (recording seconds by path), english (the English "books"), read_tag, tv_tag, TV_ICON, and
    sections (the English section names of each surah, from scripts/quran_site.py)."""
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
        lines = ([(0, opening)] if opening else []) + list(verses)
        rel = audio(n)
        secs = x["lengths"].get(rel) if rel else None

        # The recording and its word times (scripts/arabic_voice.py), which count only when made for exactly
        # these words. While a surah is only partly read, they cover a run of its verses ("range", the
        # opening line being verse 0), and only those verses' words light up.
        sync, first, last = None, lines[0][0], lines[-1][0]
        if rel:
            try:
                timing = json.load(open(os.path.join(out, rel[:-4] + ".json"), encoding="utf-8"))
                a, b = timing.get("range") or [first, last]
                said = " ".join(w for v, ws in lines if a <= v <= b for w in ws)
                n_said = len(words(said))
                if timing.get("sum") == x["checksum"](said) and timing.get("words") == n_said == len(timing.get("t") or []):
                    sync, first, last = rel[:-4] + ".json", a, b
            except (OSError, ValueError):
                pass
            if not sync:
                rel = secs = None   # no word times for these words: text only
        spoken = " ".join(w for v, ws in lines if first <= v <= last for w in ws)
        count = len(words(spoken))
        partial = bool(sync) and (first, last) != (lines[0][0], lines[-1][0])

        # the text: the opening line apart, then the verses, a new paragraph at each quarter-hizb mark
        parts, para, verse_at, at = [], [], [], 0

        def wrap(v, ws):
            if first <= v <= last:
                return " ".join('<span class="w">%s</span>' % esc(w) for w in ws)
            return " ".join(esc(w) for w in ws)
        if opening:
            parts.append('<p class="bas">%s</p>' % wrap(0, opening))
            at += len(opening) if first == 0 else 0
        for v, ws in verses:
            if para and ws[0].startswith(RUB):
                parts.append('<p class="v">%s</p>' % " ".join(para))
                para = []
            if first <= v <= last:
                verse_at.append([v, at])
                at += len(ws)
            para.append('<sup class="n" id="v%d"></sup>%s <span class="end">%s%s</span>' % (v, wrap(v, ws), END, number(v)))
        if para:
            parts.append('<p class="v">%s</p>' % " ".join(para))
        body_text = "\n".join(parts)
        if body_text.count('<span class="w">') != count:
            raise SystemExit("Arabic surah %d: %d words on the page, %d read aloud" % (n, body_text.count('<span class="w">'), count))

        nxt = n + 1 if n < len(SURAHS) else None
        data = (' data-id="%s-%d" data-title="%s" data-url="ar/%d.html" data-skip="0" data-lang="ar" data-stream="1"'
                ' data-artist="Sulafat"' % (SLUG, n, esc(title(n)), n))
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
        # the switch to English: the surah's page, as far as the translation has reached
        switch = pill("ar", "../quran-%d/" % n if b else "../?home", "",
                      ' data-surah="%d" data-upto="%d"' % (n, b["ranges"][-1][1] if b else 0))
        jumps = sections(n, verses, x["sections"].get(n, []))
        bar = quran_site.section_bar(jumps, bool(rel))
        name = english_name(n)
        eyebrow = "Surah %d%s" % (n, " · " + name if name else "")
        about = "%d verses" % s["verses"] + (" · verses %d–%d read aloud so far" % (max(1, first), last) if partial else "")
        prev_link = '<a class="prev" href="%d.html">&larr; %s</a>' % (n - 1, esc(title(n - 1))) if n > 1 else \
            '<span class="prev">Beginning of the Quran</span>'
        next_link = '<a class="next" href="%d.html">%s &rarr;</a>' % (nxt, esc(title(nxt))) if nxt else \
            '<span class="next">End of the Quran</span>'
        body = """<p class="eyebrow">%s</p>
<h1 class="arh" lang="ar" dir="rtl">سورة %s</h1>
<p class="sub">%s%s</p>
%s<div id="ch" class="ar" lang="ar" dir="rtl"%s>
%s
</div>
<div class="pn">%s%s</div>""" % (esc(eyebrow), esc(NAMES[n]), buttons,
                                 ('<br>' if buttons else '') + '<span class="lang-note">%s</span>' % esc(about),
                                 bar, data, body_text, prev_link, next_link)
        open(os.path.join(out, "ar", "%d.html" % n), "w", encoding="utf-8").write(
            x["page"](title(n), body, 1, x["read_tag"] + x["tv_tag"], footer=FOOTER, nav=nav(switch)))
        open(os.path.join(out, "text", SLUG, "%d.txt" % n), "w", encoding="utf-8").write(spoken)
        start = dict(verse_at)
        json.dump({"verses": verse_at, "scenes": [], "sections": [[start[a], name] for _, name, a, _, _ in jumps if a in start] if bar else []},
                  open(os.path.join(out, "tv", SLUG, "%d.json" % n), "w"), ensure_ascii=False)
        if rel:
            manifest.append({
                "id": "%s-%d" % (SLUG, n), "book": "Surahs", "slug": SLUG, "chapter": n, "total": len(SURAHS),
                "url": "ar/%d.html" % n, "audio": rel, "duration": secs, "text": "text/%s/%d.txt" % (SLUG, n),
                "sync": sync, "title": title(n), "sub": ("verses %d–%d of %d read aloud so far" % (max(1, first), last, s["verses"]) if partial
                        else "%d verses" % s["verses"]),
                "lang": "ar", "stream": True,
            })
        cells.append('<a href="%d.html"><b class="arn" lang="ar">%s</b>Surah %d<small>%d verses%s</small></a>' % (
            n, esc(NAMES[n]), n, s["verses"], " · " + x["clock"](secs) if secs else ""))

    json.dump(manifest, open(os.path.join(out, "manifest-ar.json"), "w", encoding="utf-8"), ensure_ascii=False)

    # the Arabic home page
    have = len(manifest)
    sub = "The Arabic text of all 114 surahs, as written, with no translation. " + (
        "Read aloud in a plain speaking voice%s." % ("" if have == len(SURAHS) else " (%d of 114 surahs so far, more are on the way)" % have)
        if have else NOT_YET)
    resume = """<a class="continue" id="resume" href="#" hidden><small>Pick up where you left off</small><b></b></a>
<script>
(function(){
function get(k){try{return JSON.parse(localStorage.getItem(k)||'null')}catch(e){return null}}
function fmt(t){t=Math.floor(t||0);var m=Math.floor(t/60),x=t%60;return m+':'+(x<10?'0':'')+x}
var s=get('lastSpot'),a=document.getElementById('resume'),href,small,label;
if(!s||!s.url||!/^ar-/.test(s.id||''))return;
if(!HEARD)s.mode='read';   // no recordings on the site (any more): pick up the reading
if(s.mode==='listen'){href='listen.html';small='Keep listening';}
else if(s.mode==='tv'){href='tv.html?c='+encodeURIComponent(s.id);small='Keep watching in TV mode';}
else if(s.mode==='lr'){href='../'+s.url+'#resume-lr';small='Keep listening and reading';}
else{href='../'+s.url+(s.v>1?'#v'+s.v:'');small='Keep reading';}
label=s.label+(s.mode==='read'?(s.v>1?', verse '+s.v:''):(s.t>3?' \\u00b7 at '+fmt(s.t):''));
a.href=href;a.querySelector('small').textContent=small;a.querySelector('b').textContent=label;a.hidden=false;
})();
</script>""".replace("HEARD", "true" if have else "false")
    body = ('<h1>The Quran in Arabic</h1><p class="sub">%s</p>%s<h3 class="group">Surahs</h3><div class="grid">%s</div>'
            % (esc(sub), resume, "".join(cells)))
    open(os.path.join(out, "ar", "index.html"), "w", encoding="utf-8").write(
        x["page"]("The Quran in Arabic", body, 1, "", footer=FOOTER, nav=nav(pill("ar", "../?home", ""))))

    # Listen: the same player as the English site, over the Arabic recordings
    listen = open(os.path.join(ROOT, "scripts", "listen.html"), encoding="utf-8").read()
    listen = (listen.replace("'../manifest.json'", "'../manifest-ar.json'").replace("<h2>Chapters</h2>", "<h2>Surahs</h2>")
              .replace("The Bible, Freshly Translated", "The Quran in Arabic"))
    if not manifest:
        listen = '<h1>Listen</h1><p class="sub">%s</p>' % esc(NOT_YET)
    open(os.path.join(out, "ar", "listen.html"), "w", encoding="utf-8").write(
        x["page"]("Listen", listen, 1, "", footer=FOOTER, nav=nav(pill("ar", "../listen/", ""))))

    # TV mode: every surah that has a recording
    tv_cells = "".join('<a href="?c=%s" data-tv="%s"><b class="arn" lang="ar">%s</b>Surah %d<small>%s</small></a>' % (
        c["id"], c["id"], esc(NAMES[c["chapter"]]), c["chapter"], x["clock"](c["duration"]) if c["duration"] else "")
        for c in manifest)
    body = ('<h1>TV mode</h1><p class="sub">The Arabic words light up as they are read aloud, over a calm background. '
            'Best on a TV, or on a phone turned sideways.</p>'
            '<a class="continue" id="tv-resume" href="#" hidden><small>Keep watching</small><b></b></a>'
            + ('<div class="grid">%s</div>' % tv_cells if manifest else
               '<p class="tvnote">%s</p>' % esc(NOT_YET)))
    open(os.path.join(out, "ar", "tv.html"), "w", encoding="utf-8").write(
        x["page"]("TV mode", body, 1, x["tv_tag"], footer=FOOTER, nav=nav(pill("ar", "../tv/", ""))))
    return have
