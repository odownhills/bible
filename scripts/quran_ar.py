#!/usr/bin/env python3
"""The Quran in Arabic: the Arabic text of every surah, beside the English site, read aloud in a plain voice when
its recording is ready.

Built by `WORK=quran python3 scripts/build.py` together with the English pages (it calls build() below),
into site-quran/:

    ar/index.html            all 114 surahs
    ar/<n>.html              one surah, whole, in modern spelling (sources/quran-modern/), never translated
    ar/<n>-uthmani.html      the same surah in the traditional Uthmani script (sources/quran/)
    ar/listen.html, ar/tv.html   Listen and TV mode for the Arabic recordings
    manifest-ar.json         the surahs that have a recording, in modern spelling (the English pages use
                             manifest.json); manifest-ar-uthmani.json the same in the traditional script
    text/ar/<n>.txt          the words as read aloud (for TV mode's captions); text/ar-uthmani/<n>.txt
    tv/ar/<n>.json           where each verse starts, counted in words (for TV mode); tv/ar-uthmani/<n>.json
    sync/ar/<n>.json         the start time of every word of the modern spelling (see modern_times())

Two spellings of the same Arabic (Obay, 2026-11-23: "default will be new arabic", keep the old as a toggle).
The modern spelling (the Tanzil Project's text, sources/quran-modern/) is how Arabic is written today, in an
everyday book and newspaper font (Noto Naskh Arabic), with full vowel marks and plain verse numbers. The
traditional Uthmani script (sources/quran/) keeps the Quran font and its ornate verse signs. Both have the
same verses and the same words; only the spelling differs, and sometimes where a word is cut (the traditional
script writes "O" joined to the word it calls: يَـٰٓأَيُّهَا is يَا أَيُّهَا). A Modern | Traditional switch on
every Arabic page lands on the same verse in the other spelling and is remembered in the browser (arScript,
scripts/lang.js): a modern page sends a reader who chose the traditional script to its traditional twin.

Obay (2026-11-22): the Arabic is read in a plain, ordinary speaking voice, never chanted or recited in the
traditional way ("plain, honest scripture, no tradition"). A recording goes in the R2 bucket as
audio/ar/<n>.mp3, listed in data/audio.json like every other recording, with the start time of every word in
site-quran/audio/ar/<n>.json for Listen + Read and TV mode. A surah's page works with or without them:
without a recording it is text only.

Every page of the Quran site has an English | Arabic switch at the top (scripts/lang.js), which lands on
the same verse in the other language and remembers the choice in the browser.

The recordings are read from the traditional text and timed word by word against it (scripts/arabic_voice.py).
The modern pages light up their own words with the same times: line_up() finds where each modern word starts
among the traditional words of its verse, and modern_times() gives it that moment of the recording.

A long surah has a bar of sections to jump between, named as in the English translation (its headings,
scripts/quran_site.py) for the verses translated so far; past those, a section runs from one quarter-hizb
mark (RUB) to the next and is named by its verses.
"""
import bisect
import difflib
import json
import os
import re

import quran_site
import search

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURAHS = json.load(open(os.path.join(ROOT, "data", "quran.json"), encoding="utf-8"))
NAMES = {s["n"]: s["name"] for s in json.load(open(os.path.join(ROOT, "data", "quran_arabic.json"), encoding="utf-8"))}
# Who reads the recordings, as named on the pages (scripts/arabic_voice.py)
VOICE = "a computer voice (Gemini's Sulafat, the English pages' voice)"
SLUG = "ar"
MODERN, UTHMANI = "modern", "uthmani"   # the two spellings; modern is the default
FOOTER = ('The Arabic text of the Quran (the Hafs reading), with no translation: in modern spelling from the Tanzil '
          'Project (<a href="https://tanzil.net">tanzil.net</a>), and in the traditional Uthmani script from '
          'quranenc.com (CC BY-SA 4.0).' + (' Read aloud, where a recording is ready, by %s.' % VOICE if VOICE else ''))
NOT_YET = "The Arabic is not read aloud yet: a plain reading voice is on the way."

# sources/quran/ writes the open (staggered) tanween with three older code points that only the
# King Fahd Complex's own font draws as open tanween. On screen they are shown with the standard
# characters for open tanween, which the site's Quran font (Scheherazade New) draws correctly.
# Nothing else in the text is changed.
OPEN_TANWEEN = str.maketrans({"ٗ": "ࣰ", "ٞ": "ࣱ", "ٖ": "ࣲ"})
DIGITS = "٠١٢٣٤٥٦٧٨٩"
END = "۝"            # the end-of-verse sign; the font draws it around the number that follows
RUB = "۞"            # the mark that opens each quarter of a hizb: a new paragraph starts there

MODERN_SOURCE = os.path.join(ROOT, "sources", "quran-modern", "quran-simple.txt")
SIGNS = re.compile("[\u06D6-\u06ED]")   # Tanzil's pause signs, quarter-hizb sign and prostration sign: not shown
PAUSE = re.compile("[\u06D6-\u06DC]")   # the pause signs: TV mode may start a new line of words after one
FONT_RANGE = "unicode-range:U+0600-06FF,U+0750-077F,U+0870-08FF,U+200C-200E,U+FB50-FDFF,U+FE70-FEFF"

CSS = """
@font-face{font-family:"Quran Text";src:url(/fonts/scheherazade-new-arabic.woff2) format("woff2");font-display:swap;%(r)s}
@font-face{font-family:"Arabic Text";src:url(/fonts/noto-naskh-arabic-400.woff2) format("woff2");font-weight:400;font-display:swap;%(r)s}
@font-face{font-family:"Arabic Text";src:url(/fonts/noto-naskh-arabic-700.woff2) format("woff2");font-weight:700;font-display:swap;%(r)s}
.top{position:sticky;top:0;z-index:15;background:var(--bg);padding-top:.7rem;margin-top:-.7rem}
#ch sup.n{scroll-margin-top:4.5rem}
.top .lang{display:inline-flex;align-items:stretch;gap:0;border:1px solid var(--rule);border-radius:999px;overflow:hidden;letter-spacing:.04em}
.top .lang a,.top .lang b{display:flex;align-items:center;padding:.1rem .6rem;font-weight:normal;min-height:28px}
.top .lang b{background:var(--shade);color:var(--heading)}
.top .lang [lang=ar]{font-family:"Arabic Text",var(--sans);font-size:1.05rem;line-height:1;letter-spacing:0;text-transform:none;padding-bottom:.15rem}
#ch.ar{font-family:"Arabic Text","Noto Naskh Arabic","Geeza Pro","Arabic Typesetting",serif;font-size:1.5rem;line-height:2.2;text-align:justify}
#ch.ar.uth{font-family:"Quran Text","Noto Naskh Arabic","Geeza Pro","Arabic Typesetting",serif;font-size:1.7rem;line-height:2.25;word-spacing:.06em}
#ch.ar p.v{margin:0 0 1.3rem}
#ch.ar p.bas{text-align:center;color:var(--heading);margin:0 0 1.3rem}
body.lr #ch.ar p.bas{color:#A396C6}
#ch.ar sup.n{display:inline-block;width:0;height:1em;margin:0;padding:0;overflow:hidden}
#ch.ar .end{display:inline-block;min-width:1.75em;padding:0 .3em;margin:0 .2em;font-size:.62em;line-height:1.7;text-align:center;vertical-align:.18em;color:var(--accent);border:1px solid var(--rule);border-radius:999px;user-select:none;-webkit-user-select:none;white-space:nowrap}
#ch.ar.uth .end{display:inline;min-width:0;padding:0;margin:0 .12em;font-size:1em;line-height:inherit;vertical-align:baseline;border:0;border-radius:0}
h1.arh{font-family:"Arabic Text",var(--serif);font-weight:700;font-size:2.3rem;line-height:1.7;margin:.2rem 0 .1rem}
h1.arh.uth{font-family:"Quran Text",var(--serif);font-weight:normal;font-size:2.6rem;line-height:1.6}
.top>span{align-items:center}
.grid .arn{display:block;font-family:"Arabic Text",var(--serif);font-weight:normal;font-size:1.35rem;line-height:1.7;color:var(--heading)}
.lang-note{font-family:var(--sans);font-size:.85rem;color:var(--text-soft)}
.spell{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;margin:.35rem 0 .9rem;font-family:var(--sans);font-size:.82rem;color:var(--text-soft)}
.spell span{display:inline-flex;border:1px solid var(--rule);border-radius:999px;overflow:hidden}
.spell a,.spell b{display:flex;align-items:center;min-height:34px;padding:0 .85rem;font-weight:normal;color:var(--accent);text-decoration:none;-webkit-tap-highlight-color:transparent}
.spell b,.spell a.on{background:var(--shade);color:var(--heading)}
.spell a:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
""" % {"r": FONT_RANGE}


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


_MODERN = {}


def modern(n):
    """Surah n in modern spelling, as the pages show it: (the opening line when the surah has it apart from its
    verses, else None, [(verse number, [words]), ...], {(verse, k): word k of the verse is followed by a pause
    sign}). Tanzil's text writes the opening line at the start of verse 1 of every surah but 1 and 9; it is set
    apart here, as sources/quran/ has it. Tanzil's signs are left out of the words."""
    if not _MODERN:
        for line in open(MODERN_SOURCE, encoding="utf-8"):
            s, v, t = line.rstrip("\n").split("|", 2)
            _MODERN.setdefault(int(s), {})[int(v)] = t
    verses, pauses = [], set()
    for v in sorted(_MODERN[n]):
        ws = []
        for token in _MODERN[n][v].split():
            word = SIGNS.sub("", token)
            if word:
                ws.append(word)
            if PAUSE.search(token) and ws:
                pauses.add((v, len(ws) - 1))
        verses.append((v, ws))
    opening = None
    if n not in (1, 9):
        bismillah = _MODERN[1][1].split()
        if verses[0][1][:len(bismillah)] != bismillah:
            raise SystemExit("sources/quran-modern/: surah %d verse 1 does not start with the opening line" % n)
        opening = bismillah
        verses[0] = (1, verses[0][1][len(bismillah):])
        pauses = {(v, k - len(bismillah)) if v == 1 else (v, k) for v, k in pauses if v != 1 or k >= len(bismillah)}
    return opening, verses, pauses


def letters(w):
    """A word's letters alone, the same in both spellings: no vowel signs or Quranic signs, every kind of alef as
    one alef (the small alef too), the hamza's seat as its letter, and no small waw or ya at the end (bihi is
    written بِهِۦ in the traditional script, بِهِ in modern spelling). Used only to line the two spellings up."""
    w = re.sub("[\u064B-\u065F\u0640\u06D6-\u06E4\u06E9-\u06ED\u08F0-\u08F2]", "", w)
    w = re.sub("[\u06E5\u06E6]+$", "", w)
    for a, b in (("\u06E5", "\u0648"), ("\u06E6", "\u064A"), ("\u06E7", "\u064A"), ("\u06E8", "\u0646"),
                 ("\u0670", "\u0627"), ("\u0671", "\u0627"), ("\u0623", "\u0627"), ("\u0625", "\u0627"),
                 ("\u0622", "\u0627"), ("\u0624", "\u0648"), ("\u0626", "\u064A"), ("\u0649", "\u064A"),
                 ("\u0629", "\u0647"), ("\u0621", "")):
        w = w.replace(a, b)
    return re.sub("\u0627+", "\u0627", w)


def line_up(trad, mod):
    """Where each word of a verse in modern spelling (mod) starts among the words of the same verse in the
    traditional script (trad): [(index of the traditional word, how far into it, from 0 to 1)], in order.
    The two have the same letters but do not always cut them into words at the same places: the traditional
    يَـٰٓأَيُّهَا is يَا أَيُّهَا (two words starting in one), and its بَعۡدَ مَا is بَعْدَمَا (no word starting
    in the second). Raises ValueError when the verse does not line up: then the two texts differ."""
    ts, ms = [letters(w) for w in trad], [letters(w) for w in mod]
    tcat, mcat = "|" + "|".join(ts) + "|", "|" + "|".join(ms) + "|"   # the bars keep word ends lined up
    match = difflib.SequenceMatcher(None, mcat, tcat, autojunk=False)
    if match.ratio() < 0.85:
        raise ValueError("the letters differ")
    blocks = match.get_matching_blocks()

    def where(i):   # the place in tcat of the letter at mcat[i]
        before = (0, 0)
        for a, b, size in blocks:
            if a <= i < a + size:
                return b + i - a
            if a > i:
                return before[1] + (b - before[1]) * (i - before[0]) / max(1, a - before[0])
            before = (a + size, b + size)
        return len(tcat)
    starts, p = [], 1
    for t in ts:
        starts.append(p)
        p += len(t) + 1
    out, p = [], 1
    for m in ms:
        x = where(p)
        p += len(m) + 1
        k = max(0, bisect.bisect_right(starts, x) - 1)
        if out and k < out[-1][0]:
            raise ValueError("out of order")
        out.append((k, min(0.95, max(0.0, (x - starts[k]) / max(1, len(ts[k]))))))
    return out


def modern_times(times, pairs):
    """The start time of every word in modern spelling, from the recording's times for the traditional words.
    times: the traditional words' start times in hundredths of a second, in order; pairs: [(traditional words,
    line_up() of the modern words)] for each verse read aloud, in order. A modern word starts when the
    traditional word it starts in does, or partway through it when it starts partway (يَا أَيُّهَا)."""
    out, base = [], 0
    for trad, places in pairs:
        for k, f in places:
            g = base + k
            a = times[g]
            b = times[g + 1] if g + 1 < len(times) else a + 50
            t = int(round(a + f * max(0, b - a)))
            out.append(max(t, out[-1]) if out else t)
        base += len(trad)
    return out


def slots(n):
    """For search (scripts/search.py): {verse: [the modern words that start in each traditional word, in order]}
    for every verse of surah n (the opening line apart is not a verse)."""
    _, verses = surah(n)
    _, m_verses, _ = modern(n)
    out = {}
    for (v, trad), (_, mod) in zip(verses, m_verses):
        groups = [[] for _ in trad]
        for w, (k, _) in zip(mod, line_up(trad, mod)):
            groups[k].append(w)
        out[v] = groups
    return out


def href(n, script):
    """A surah's page in one spelling, beside the other pages of ar/."""
    return "%d.html" % n if script == MODERN else "%d-uthmani.html" % n


def spelling(script, n=None):
    """The Modern | Traditional switch. On a surah's page it goes to the same verse in the other spelling; on the
    Arabic home and TV pages (n None) it only sets the reader's choice, shown by scripts/lang.js."""
    if n is None:
        links = ('<a href="#" data-script="modern">Modern</a><a href="#" data-script="uthmani">Traditional</a>')
    else:
        links = ('<b>Modern</b>' if script == MODERN else '<a href="%s" data-script="modern">Modern</a>' % href(n, MODERN)) + \
                ('<b>Traditional</b>' if script == UTHMANI else '<a href="%s" data-script="uthmani">Traditional</a>' % href(n, UTHMANI))
    return ('<div class="spell"%s>Spelling <span role="group" aria-label="Spelling">%s</span></div>'
            % ("" if n else " data-choice", links))


# A modern page sends a reader who chose the traditional script to its traditional twin, before it shows.
TO_UTHMANI = ("<script>try{if(JSON.parse(localStorage.getItem('arScript')||'null')==='uthmani')"
              "location.replace('%s'+location.search+location.hash)}catch(e){}</script>")


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
    lengths (recording seconds by path), english (the English "books"), read_tag, tv_tag, TV_ICON,
    sections (the English section names of each surah, from scripts/quran_site.py), and there (a TV picture
    is published: TV mode shows the English parts' pictures over the Arabic too)."""
    esc, words = x["esc"], x["words"]
    english = {b["surah"]: b for b in x["english"]}
    os.makedirs(os.path.join(out, "ar"), exist_ok=True)
    for sub in ("text", "tv"):
        for slug in (SLUG, SLUG + "-uthmani"):
            os.makedirs(os.path.join(out, sub, slug), exist_ok=True)
    os.makedirs(os.path.join(out, "sync", SLUG), exist_ok=True)
    os.makedirs(os.path.join(out, "fonts"), exist_ok=True)
    for font in ("scheherazade-new-arabic.woff2", "noto-naskh-arabic-400.woff2", "noto-naskh-arabic-700.woff2"):
        with open(os.path.join(ROOT, "scripts", "fonts", font), "rb") as f:
            data = f.read()
        with open(os.path.join(out, "fonts", font), "wb") as f:
            f.write(data)

    def audio(n):
        rel = "audio/%s/%d.mp3" % (SLUG, n)
        return rel if rel in x["lengths"] else None

    manifest, manifest_u, cells = [], [], []
    for s in SURAHS:
        n = s["n"]
        opening, verses = surah(n)
        lines = ([(0, opening)] if opening else []) + list(verses)
        m_opening, m_verses, pauses = modern(n)
        m_lines = ([(0, m_opening)] if m_opening else []) + list(m_verses)
        if [v for v, _ in lines] != [v for v, _ in m_lines]:
            raise SystemExit("Arabic surah %d: the modern spelling has other verses than sources/quran/" % n)
        places = {}
        for (v, trad), (_, mod) in zip(lines, m_lines):
            try:
                places[v] = line_up(trad, mod)
            except ValueError as e:
                raise SystemExit("Arabic surah %d verse %d: the modern spelling does not line up with sources/quran/ (%s)"
                                 % (n, v, e))
        rel = audio(n)
        secs = x["lengths"].get(rel) if rel else None

        # The recording and its word times (scripts/arabic_voice.py), which count only when made for exactly
        # these words. While a surah is only partly read, they cover a run of its verses ("range", the
        # opening line being verse 0), and only those verses' words light up.
        sync, first, last, timing = None, lines[0][0], lines[-1][0], None
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
        partial = bool(sync) and (first, last) != (lines[0][0], lines[-1][0])
        rub = {v for v, ws in verses if ws[0].startswith(RUB)}   # a new paragraph at each quarter-hizb mark

        def text(script):
            """The surah's text in one spelling: (its HTML, [[verse, its first word read aloud]], the words read
            aloud, the words read aloud that a pause sign follows)."""
            parts, para, verse_at, said, breaks = [], [], [], [], []
            for v, ws in (lines if script == UTHMANI else m_lines):
                heard = first <= v <= last
                inner = " ".join(('<span class="w">%s</span>' if heard else "%s") % esc(w) for w in ws)
                if heard:
                    if v:
                        verse_at.append([v, len(said)])
                    if script == MODERN:
                        breaks += [len(said) + k for k in range(len(ws)) if (v, k) in pauses]
                    said += ws
                if v == 0:
                    parts.append('<p class="bas">%s</p>' % inner)
                    continue
                if para and v in rub:
                    parts.append('<p class="v">%s</p>' % " ".join(para))
                    para = []
                para.append('<sup class="n" id="v%d"></sup>%s <span class="end">%s</span>'
                            % (v, inner, (END if script == UTHMANI else "") + number(v)))
            if para:
                parts.append('<p class="v">%s</p>' % " ".join(para))
            html = "\n".join(parts)
            if html.count('<span class="w">') != len(words(" ".join(said))):
                raise SystemExit("Arabic surah %d (%s): %d words on the page, %d read aloud"
                                 % (n, script, html.count('<span class="w">'), len(words(" ".join(said)))))
            return html, verse_at, said, breaks

        # the modern words' times, from the recording's times for the traditional words
        m_sync = None
        if sync:
            m_said = [w for v, ws in m_lines if first <= v <= last for w in ws]
            t = modern_times(timing["t"], [(trad, places[v]) for v, trad in lines if first <= v <= last])
            if len(t) != len(m_said):
                raise SystemExit("Arabic surah %d: %d modern words, %d times" % (n, len(m_said), len(t)))
            m_sync = "sync/%s/%d.json" % (SLUG, n)
            json.dump({"t": t, "words": len(t), "sum": x["checksum"](" ".join(m_said)), "range": [first, last],
                       "from": sync}, open(os.path.join(out, m_sync), "w"), separators=(",", ":"))

        nxt = n + 1 if n < len(SURAHS) else None
        b = english.get(n)
        # the switch to English: the surah's page, as far as the translation has reached
        switch = pill("ar", "../quran-%d/" % n if b else "../?home", "",
                      ' data-surah="%d" data-upto="%d"' % (n, b["ranges"][-1][1] if b else 0))
        jumps = sections(n, verses, x["sections"].get(n, []))
        bar = quran_site.section_bar(jumps, bool(rel))
        name = english_name(n)
        eyebrow = "Surah %d%s" % (n, " · " + name if name else "")
        about = "%d verses" % s["verses"] + (" · verses %d–%d read aloud so far" % (max(1, first), last) if partial else "")
        if not rel:   # Obay looked for Listen + Read on a page with no recording yet (2026-11-22)
            about += " · not read aloud yet. Listen + Read and TV mode appear here once the voice reaches this surah."
        b_en = english.get(n)   # the English parts' TV pictures, each from the start of its verse
        runs = quran_site.picture_runs(n, b_en["ranges"], x["there"]) if b_en else []
        for script in (MODERN, UTHMANI):
            slug = SLUG if script == MODERN else SLUG + "-uthmani"
            body_text, verse_at, said, breaks = text(script)
            spoken = " ".join(said)
            data = (' data-id="%s-%d" data-title="%s" data-url="ar/%d.html" data-skip="0" data-lang="ar" data-stream="1"'
                    ' data-artist="Sulafat" data-script="%s"' % (SLUG, n, esc(title(n)), n, script))
            buttons = ""
            if rel:
                data += ' data-audio="../%s" data-sync="../%s"' % (rel, sync if script == UTHMANI else m_sync)
                buttons = ('<button class="btn" id="lr-start" type="button">&#9654; Listen + Read</button> '
                           '<a class="btn tv" href="tv.html?c=%s-%d" data-tv="%s-%d">%sTV mode</a> '
                           '<a class="btn ghost" href="listen.html?from=%s-%d">Listen only</a>'
                           % (SLUG, n, SLUG, n, x["TV_ICON"], SLUG, n))
            if nxt:
                data += ' data-next="../ar/%s"' % href(nxt, script)
                if audio(nxt):
                    data += ' data-next-audio="../%s"' % audio(nxt)
            prev_link = '<a class="prev" href="%s">&larr; %s</a>' % (href(n - 1, script), esc(title(n - 1))) if n > 1 else \
                '<span class="prev">Beginning of the Quran</span>'
            next_link = '<a class="next" href="%s">%s &rarr;</a>' % (href(nxt, script), esc(title(nxt))) if nxt else \
                '<span class="next">End of the Quran</span>'
            uth = " uth" if script == UTHMANI else ""
            body = """%s<p class="eyebrow">%s</p>
<h1 class="arh%s" lang="ar" dir="rtl">سورة %s</h1>
%s<p class="sub">%s%s</p>
%s<div id="ch" class="ar%s" lang="ar" dir="rtl"%s>
%s
</div>
<div class="pn">%s%s</div>""" % (TO_UTHMANI % href(n, UTHMANI) if script == MODERN else "", esc(eyebrow), uth,
                                     esc(NAMES[n]), spelling(script, n), buttons,
                                     ('<br>' if buttons else '') + '<span class="lang-note">%s</span>' % esc(about),
                                     bar, uth, data, body_text, prev_link, next_link)
            open(os.path.join(out, "ar", href(n, script)), "w", encoding="utf-8").write(
                x["page"](title(n), body, 1, x["read_tag"] + x["tv_tag"], footer=FOOTER, nav=nav(switch)))
            open(os.path.join(out, "text", slug, "%d.txt" % n), "w", encoding="utf-8").write(spoken)
            start = dict(verse_at)
            tv = {"verses": verse_at, "scenes": quran_site.scenes_at(runs, verse_at) if b_en else [],
                  "sections": [[start[a], name] for _, name, a, _, _ in jumps if a in start] if bar else []}
            if script == MODERN:
                tv["breaks"] = breaks
            json.dump(tv, open(os.path.join(out, "tv", slug, "%d.json" % n), "w"), ensure_ascii=False)
            if rel:
                (manifest if script == MODERN else manifest_u).append({
                    "id": "%s-%d" % (SLUG, n), "book": "Surahs", "slug": SLUG, "chapter": n, "total": len(SURAHS),
                    "url": "ar/%d.html" % n, "audio": rel, "duration": secs, "text": "text/%s/%d.txt" % (slug, n),
                    "tv": "tv/%s/%d.json" % (slug, n), "sync": sync if script == UTHMANI else m_sync, "title": title(n),
                    "sub": ("verses %d–%d of %d read aloud so far" % (max(1, first), last, s["verses"]) if partial
                            else "%d verses" % s["verses"]),
                    "lang": "ar", "script": script, "stream": True,
                })
        cells.append('<a href="%d.html"><b class="arn" lang="ar">%s</b>Surah %d<small>%d verses%s</small></a>' % (
            n, esc(NAMES[n]), n, s["verses"], " · " + x["clock"](secs) if secs else ""))

    json.dump(manifest, open(os.path.join(out, "manifest-ar.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(manifest_u, open(os.path.join(out, "manifest-ar-uthmani.json"), "w", encoding="utf-8"), ensure_ascii=False)

    # the Arabic home page
    have = len(manifest)
    sub = ("The Arabic text of all 114 surahs, with no translation, in modern spelling or in the traditional "
           "Uthmani script: the same words, spelled two ways. ") + (
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
    body = ('<h1>The Quran in Arabic</h1><p class="sub">%s</p>%s%s<h3 class="group">Surahs</h3><div class="grid">%s</div>'
            % (esc(sub), spelling(MODERN), resume, "".join(cells)))
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
    body = ('<h1>TV mode</h1><p class="sub">The Arabic words light up as they are read aloud, over pictures of what they say (a calm background where the pictures are still to come). '
            'Best on a TV, or on a phone turned sideways.</p>' + spelling(MODERN) +
            '<a class="continue" id="tv-resume" href="#" hidden><small>Keep watching</small><b></b></a>'
            + ('<div class="grid">%s</div>' % tv_cells if manifest else
               '<p class="tvnote">%s</p>' % esc(NOT_YET)))
    open(os.path.join(out, "ar", "tv.html"), "w", encoding="utf-8").write(
        x["page"]("TV mode", body, 1, x["tv_tag"], footer=FOOTER, nav=nav(pill("ar", "../tv/", ""))))
    return have
