#!/usr/bin/env python3
"""Search across the three sites: the Bible (site/), the Quran (site-quran/) and the study site (site-study/).

Every build writes its own site's search index next to its pages, so a new chapter, part or analysis can be
found as soon as it is published, with nothing else to run:

    python3 scripts/build.py               -> site/search/
    WORK=quran python3 scripts/build.py    -> site-quran/search/   (the English translation and the Arabic)
    python3 scripts/study.py               -> site-study/search/

Each site has a search page (/search/) and a search button on every page. The page asks all three sites, so
one search finds verses in the Bible, verses in the Quran and sections of the study notes, each linked to its
place. The search runs in the reader's browser (scripts/search.js): there is no server, no AI and no cost
per search, and only the small pieces of the index that a search needs are downloaded.

The index of one site, under <site>/search/:
    meta.json        what the site holds: its books, the index's pieces, and a fingerprint for caching
    w/<ab>.json      every word that starts with those two letters: {"loved": ["love", places], ...}
                     The first item is the word's family (the word its endings come off to: loved, loves and
                     loving all belong to "love"; "" when the word is its own family), so a search for one form
                     finds them all. Places: "43003:16,17;43004:2" is John 3:16, John 3:17 and John 4:2
                     (book * 1000 + chapter, then verses); on the Quran site the number is the surah, and on the
                     study site the units are sections (0 is the opening).
    w/_<word>.json   the places of a very common word ("the", "god"), in a file of its own (its entry says 1)
    t/...json        the text a result shows: a chapter's verses, a surah's verses, a study chapter's sections
    ar.txt, ar/      (the Quran site) every verse of the Arabic, in plain letters for matching and as the pages
                     show it in the traditional script (see arabic_files)
    arm/             the same verses as the pages show them in modern spelling, the default
    index.html, search.js   the search page
The site's _headers file lets the other two sites read its index (and the Quran's font).

Nothing here changes a translation: the index is only read from the published files.
"""
import hashlib
import json
import os
import re
import shutil
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The three sites, in the order their results are listed (the site being searched from comes first).
SITES = [
    {"id": "bible", "name": "Bible", "base": "https://bible.odownhills.workers.dev"},
    {"id": "quran", "name": "Quran", "base": "https://quran.odownhills.workers.dev"},
    {"id": "study", "name": "Study", "base": "https://study.odownhills.workers.dev"},
]
QURAN_FONT = "https://quran.odownhills.workers.dev/fonts/scheherazade-new-arabic.woff2"
ARABIC_FONT = "https://quran.odownhills.workers.dev/fonts/noto-naskh-arabic-400.woff2"   # the modern spelling's
BIG = 6000   # a word whose places take more characters than this gets a file of its own


# ---------------------------------------------------------------------------------------------- English words

TOKEN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)*")


def tokens(text):
    """The words of a text as the search sees them: lower case, no accents, "God's" -> "god", "don't" -> "dont".
    scripts/search.js does exactly the same to what is typed (normEn, tokens)."""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    t = re.sub("[\u2019\u02bc]", "'", t)
    t = re.sub("[\u02be\u02bf]", "", t)
    out = []
    for w in TOKEN.findall(t):
        if w.endswith("'s"):
            w = w[:-2]
        w = w.replace("'", "")
        if w:
            out.append(w)
    return out


def index_text(text):
    """A verse's words to index: its main text, its alternate readings and its notes (all shown on the page)."""
    return re.sub(r"\[alt:\s*", "[", text)


# Words that look like a form of another word but are not: evening is not a form of even.
NOT_A_FORM = {"evening", "morning", "wedding", "meaning", "wicked", "crooked", "news", "shed", "needs"}
AS_FORM = {"died": "die", "lied": "lie", "tied": "tie", "used": "use", "freed": "free"}


def bases(w):
    """The words w could be a form of, most likely first: loving -> love, lov; cities -> city; stopped -> stop."""
    if w in AS_FORM:
        return [AS_FORM[w]]
    if w in NOT_A_FORM or not w.isalpha():
        return []
    out = []
    n = len(w)
    if n >= 5 and w.endswith("ies"):
        out.append(w[:-3] + "y")
    if n >= 5 and (w.endswith(("ses", "xes", "zes", "ches", "shes"))):
        out.append(w[:-2])
    if n >= 4 and w.endswith("s") and not w.endswith(("ss", "us", "is", "ous")):
        out.append(w[:-1])
    if n >= 5 and w.endswith("ied"):
        out.append(w[:-3] + "y")
    if n >= 5 and w.endswith("ed") and not (w.endswith("eed") and n <= 5):
        b = w[:-2]
        out += [b + "e", b]
        if len(b) > 3 and b[-1] == b[-2] and b[-1] not in "lsz":
            out.append(b[:-1])
    if n >= 6 and w.endswith("ing"):
        b = w[:-3]
        out += [b + "e", b]
        if len(b) > 3 and b[-1] == b[-2] and b[-1] not in "lsz":
            out.append(b[:-1])
    return [x for x in out if len(x) >= 3]


def families(vocab):
    """{word: the word it is a form of}, judged by which words the text itself uses: "loving" belongs to "love"
    only when "love" appears somewhere. A family's words share their first two letters, so they sit in one piece
    of the index."""
    fam = {}

    def root(w, depth=0):
        if w not in fam:
            r = w
            if depth < 3:
                for b in bases(w):
                    if b in vocab and b != w:
                        r = root(b, depth + 1)
                        break
            fam[w] = r
        return fam[w]

    for w in sorted(vocab):
        root(w)
    return fam


# ----------------------------------------------------------------------------------------------- Arabic words

MARKS = re.compile("[\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")   # vowel signs, Quranic signs, small alef, tatweel


def plain_ar(s):
    """Arabic in plain letters, as a reader would type it: no vowel signs or Quranic signs; one alef for its
    forms; ta marbuta as ha; alef maqsura as ya. scripts/search.js does exactly the same to what is typed (normAr)."""
    s = MARKS.sub("", s)
    s = re.sub("[\u0671\u0623\u0625\u0622]", "\u0627", s)
    s = s.replace("\u0624", "\u0648")
    s = re.sub("[\u0626\u0649]", "\u064A", s)
    s = s.replace("\u0629", "\u0647")
    s = s.replace("\u0621\u0627", "\u0627").replace("\u0627\u0627", "\u0627")
    return s


def arabic_forms(word):
    """The plain spellings a word of the Quran's Arabic can be found by. Its written form marks some long vowels
    with a small alef where everyday spelling writes a full alef in some words (al-kitab) and none in others
    (al-rahman, hadha); so both are kept: one with each small alef as a full alef, one without it (and one with
    only a plural's last alef, as samawat is often spelled)."""
    w = re.sub("[\u064B-\u0653\u0655-\u065F]", "", word)   # vowel signs (not the small alef or the hamza sign)
    w = w.replace("\u06E7", "\u064A").replace("\u06E8", "\u0646")   # small high ya, small high noon: real letters
    full, bare = w, w
    full = full.replace("\u0640\u0654", "\u0627")           # a hamza on a tatweel: sa'ala ...
    bare = bare.replace("\u0640\u0654", "\u0626")           # ... or shay'an
    full = full.replace("\u0649\u0670", "\u0649")           # 'ala: the small alef over alef maqsura adds nothing
    full = re.sub("\u0648\u0670(?=[\u0629\u0627])", "\u0627", full)   # salat, zakat, hayat, riba: the waw is the alef
    full = full.replace("\u0670", "\u0627")
    plural = re.sub("\u0670(?=\u062A$)", "\u0627", bare)   # samawat: everyday spelling keeps the last alef only
    out = []
    for f in (plain_ar(full), plain_ar(bare), plain_ar(plural)):
        if f not in out:
            out.append(f)
    if "\u0644\u0644\u0647" in out:   # lillah: to God
        out.append("\u0627\u0644\u0644\u0647")
    return out


# ------------------------------------------------------------------------------------------- what is indexed

def bible_units(x):
    """The Bible's verses: (books, text files, [(place number, verse, text)])."""
    order = {b["slug"]: i + 1 for i, b in enumerate(x["books"])}
    books, files, units = {}, {}, []
    for b, n, path in x["chapters"]:
        _, blocks = x["parse"](path)
        rows = []
        for kind, val in blocks:
            if kind == "t":            # a psalm's title line: "verse 0"
                rows.append([0, val])
            elif kind == "p":   # a verse set in two paragraphs holds a line break: here it is a space
                rows += [[vn, " ".join(t.split())] for vn, t in val]
        key = order[b["slug"]] * 1000 + n
        books[str(order[b["slug"]])] = [b["name"], b["slug"]]
        files["t/%s/%d.json" % (b["slug"], n)] = rows
        units += [(key, vn, t) for vn, t in rows]
    return books, files, units


def quran_units(x):
    """The Quran's translated verses, surah by surah (a surah's parts make one text file)."""
    names = {s["n"]: s.get("name") for s in json.load(open(os.path.join(ROOT, "data", "quran.json"), encoding="utf-8"))}
    books, files, units = {}, {}, []
    for b, n, path in x["chapters"]:
        s = int(b["slug"].split("-")[1])
        _, blocks = x["parse"](path)
        rows = files.setdefault("t/%d.json" % s, [])
        for kind, val in blocks:
            if kind == "p":
                rows += [[vn, t] for vn, t in val]
        books[str(s)] = [names.get(s) or "Surah %d" % s, b["slug"]]
    for f, rows in files.items():
        s = int(f[2:-5])
        rows.sort()
        units += [(s, vn, t) for vn, t in rows]
    return books, files, units


AR_CHUNK = 300   # verses in each file of the Arabic as shown (search/ar/<k>.txt)


def arabic_files(shown, slots):
    """Every verse of the Arabic (sources/quran/), never changed. ar.txt, read whole by an Arabic search:
    "2:255<TAB>plain words", a word's other plain spellings after "|" (see arabic_forms; the modern spelling of
    the word is one of them, from sources/quran-modern/). ar/<k>.txt: the same verses as the pages show them in
    the traditional script, one a line, AR_CHUNK verses a file, read only for the results on screen. arm/<k>.txt:
    the same in modern spelling, word for word with the traditional words (slots(), scripts/quran_ar.py): the
    modern words that start in one traditional word are joined by a no-break space (يَا أَيُّهَا), and a
    traditional word in which no modern word starts is left empty, so that the n-th word is the same in both."""
    plain, shown_lines, modern_lines = [], [], []
    for s in range(1, 115):
        groups = slots(s)
        for line in open(os.path.join(ROOT, "sources", "quran", "%03d.txt" % s), encoding="utf-8"):
            if "\t" not in line:
                continue
            v, text = line.rstrip("\n").split("\t", 1)
            if int(v) == 0:   # the opening line before the first verse
                continue
            ws, mod = text.split(" "), groups[int(v)]
            if len(mod) != len(ws):
                raise SystemExit("Search: surah %d verse %s has %d words in modern spelling, %d traditional" % (s, v, len(mod), len(ws)))
            forms = []
            for w, g in zip(ws, mod):
                f = arabic_forms(w)
                m = plain_ar("".join(g))
                if m and m not in f:
                    f.append(m)
                forms.append("|".join(f))
            plain.append("%d:%s\t%s" % (s, v, " ".join(forms)))
            shown_lines.append(shown(text))
            modern_lines.append(" ".join("\u00a0".join(g) for g in mod))
    files = {"ar.txt": "\n".join(plain) + "\n"}
    for k in range(0, len(shown_lines), AR_CHUNK):
        files["ar/%d.txt" % (k // AR_CHUNK)] = "\n".join(shown_lines[k:k + AR_CHUNK]) + "\n"
        files["arm/%d.txt" % (k // AR_CHUNK)] = "\n".join(modern_lines[k:k + AR_CHUNK]) + "\n"
    return files


def study_units(x):
    """The study site's sections: the opening is section 0, then the chapter's sections in order. A section's
    text is its own words and, for each related passage, the passage's address and what it says about it."""
    order = {b["slug"]: i + 1 for i, b in enumerate(x["books"])}
    books, files, units = {}, {}, []
    for b, n, path in x["chapters"]:
        _, opening, sections = x["parse"](path)
        rows = []
        if opening:
            rows.append([0, "", " ".join(opening)])
        for k, s in enumerate(sections):
            words = list(s["paras"])
            for r in s["related"]:
                words.append("%s. %s" % (r["ref"], " ".join(r["paras"])))
            rows.append([k + 1, s["heading"] or "", " ".join(words)])
        key = order[b["slug"]] * 1000 + n
        books[str(order[b["slug"]])] = [b["name"], b["slug"]]
        files["t/%s/%d.json" % (b["slug"], n)] = rows
        units += [(key, r[0], r[1] + " " + r[2]) for r in rows]
    return books, files, units


# ------------------------------------------------------------------------------------------------- the index

def dumps(o):
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def write_index(work, out, books, files, units, extra=None):
    """Write <out>/search/: the word index, the text files and meta.json. Returns how many words it knows."""
    places = {}
    for key, unit, text in units:
        for w in set(tokens(index_text(text))):
            places.setdefault(w, {}).setdefault(key, set()).add(unit)
    fam = families(set(places))
    shards, written = {}, {}
    for w in sorted(places):
        p = ";".join("%d:%s" % (k, ",".join(str(u) for u in sorted(places[w][k]))) for k in sorted(places[w]))
        entry = [fam[w] if fam[w] != w else "", p]
        if len(p) > BIG:
            written["w/_%s.json" % w] = dumps(p)
            entry[1] = 1
        shards.setdefault(w[:2], {})[w] = entry
    for k, v in shards.items():
        written["w/%s.json" % k] = dumps(v)
    for f, rows in files.items():
        written[f] = dumps(rows)
    for f, text in (extra or {}).items():
        written[f] = text
    h = hashlib.sha1()
    for f in sorted(written):
        h.update(f.encode("utf-8"))
        h.update(written[f].encode("utf-8"))
    meta = {"v": 1, "site": work, "b": books, "w": sorted(shards), "n": len(units), "h": h.hexdigest()[:10]}
    if "ar.txt" in written:   # the Arabic never changes: its own fingerprint keeps it cached across new parts
        h = hashlib.sha1()
        for f in sorted(written):
            if f == "ar.txt" or f.startswith(("ar/", "arm/")):
                h.update(f.encode("utf-8"))
                h.update(written[f].encode("utf-8"))
        meta["ar"] = h.hexdigest()[:10]
        meta["arc"] = AR_CHUNK
        meta["arm"] = 1   # the verses in modern spelling are there too (arm/)
    written["meta.json"] = dumps(meta)
    for f, text in written.items():
        p = os.path.join(out, "search", f)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(text)
    return len(places)


CSS = """
.top .find{display:inline-flex;align-items:center}
.top .find svg{width:1.15rem;height:1.15rem;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round}
.sf{position:sticky;top:0;z-index:12;background:var(--bg);padding:.6rem 0 .5rem;margin:-.6rem 0 .2rem}
.sf input{width:100%;font-family:var(--sans);font-size:1.05rem;line-height:1.3;color:var(--text);background:var(--panel) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23B3A7C9' stroke-width='2.2' stroke-linecap='round'%3E%3Ccircle cx='10.5' cy='10.5' r='6.5'/%3E%3Cpath d='M15.5 15.5 21 21'/%3E%3C/svg%3E") no-repeat .9rem 50%/1.15rem;border:1px solid var(--rule);border-radius:12px;padding:.8rem .9rem .8rem 2.7rem;outline:none;-webkit-appearance:none;appearance:none}
.sf input:focus{border-color:var(--accent)}
.sf input::placeholder{color:var(--num)}
.sf input::-webkit-search-cancel-button{-webkit-appearance:none;appearance:none;width:1.1rem;height:1.1rem;cursor:pointer;background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23B3A7C9' stroke-width='2.4' stroke-linecap='round'%3E%3Cpath d='M6 6l12 12M18 6 6 18'/%3E%3C/svg%3E") center/contain no-repeat}
.scope{display:flex;gap:.45rem;flex-wrap:wrap;margin:.35rem 0 .5rem;font-family:var(--sans)}
.scope[hidden]{display:none}
.scope button{font:inherit;font-size:.82rem;color:var(--text-soft);background:transparent;border:1px solid var(--rule);border-radius:999px;padding:.3rem .8rem;min-height:36px;cursor:pointer;-webkit-tap-highlight-color:transparent}
.scope button b{font-weight:600;color:var(--text);margin-left:.35rem;font-variant-numeric:tabular-nums}
.scope button[aria-pressed=true]{background:var(--shade);color:var(--heading);border-color:var(--accent)}
.scope button:disabled{opacity:.45;cursor:default}
.sstat{font-family:var(--sans);font-size:.82rem;color:var(--text-soft);margin:.2rem 0 .6rem;min-height:1.2em}
.sstat em{font-style:normal;color:var(--text)}
h2.grp{font-family:var(--sans);color:var(--accent);text-transform:uppercase;letter-spacing:.12em;font-size:.8rem;font-weight:600;border-bottom:1px solid var(--rule);padding-bottom:.4rem;margin:1.8rem 0 .2rem;display:flex;justify-content:space-between;gap:1rem}
h2.grp span{color:var(--text-soft);font-weight:400;letter-spacing:.06em}
.hit{display:block;text-decoration:none;color:var(--text);padding:.85rem 0 .9rem;border-bottom:1px solid var(--rule);-webkit-tap-highlight-color:transparent}
.hit:hover .ref,.hit:focus-visible .ref{text-decoration:underline}
.hit .ref{display:block;font-family:var(--sans);font-size:.8rem;letter-spacing:.04em;color:var(--accent);margin:0 0 .25rem}
.hit .ref small{color:var(--text-soft);font-size:inherit;letter-spacing:0}
.hit p{margin:0;line-height:1.65}
.hit mark{background:rgba(183,155,232,.3);color:#fff;border-radius:3px;padding:0 .08em}
.hit .alt{font-style:italic;font-size:.88em;color:var(--alt-text)}
.hit .note{font-style:italic;font-size:.85em;color:var(--text-soft)}
.hit p.ar{font-family:"Arabic Text","Noto Naskh Arabic","Geeza Pro","Arabic Typesetting",serif;font-size:1.35rem;line-height:2.1;direction:rtl;text-align:right}
.hit p.ar.uth{font-family:"Quran Text","Noto Naskh Arabic","Geeza Pro","Arabic Typesetting",serif;font-size:1.5rem}
.hit p.ar mark{padding:0}
.hit p.en{font-size:.9em;color:var(--text-soft);margin-top:.35rem}
.smore{display:block;width:100%;margin:1rem 0 0;font-family:var(--sans);font-size:.88rem;color:var(--accent);background:transparent;border:1px solid var(--rule);border-radius:10px;padding:.75rem;cursor:pointer}
.stips{font-family:var(--sans);font-size:.88rem;color:var(--text-soft);line-height:1.6;margin:1.2rem 0 0}
.stips p{margin:0 0 .8rem}
.stips .chips{justify-content:flex-start;margin:.2rem 0 1.2rem}
.stips .chip{cursor:pointer}
.stips .chip[lang=ar]{font-family:"Arabic Text","Noto Naskh Arabic","Geeza Pro",serif;font-size:1.05rem}
.snote{font-family:var(--sans);font-size:.82rem;color:var(--text-soft);background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:.55rem .8rem;margin:.8rem 0}
"""

ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/>'
        '<path d="M15.5 15.5 21 21"/></svg>')


def nav_link(up):
    """The search button in a page's top bar."""
    return '<a class="find" href="%ssearch/" aria-label="Search" title="Search">%s</a>' % (up, ICON)


def page_body(work, js_name):
    first = {"bible": "the Bible", "quran": "the Quran", "study": "the study notes"}[work]
    others = [s for s in ("the Bible", "the Quran", "the study notes") if s != first]
    config = {"home": work, "sites": SITES}
    examples = ['<button class="chip" type="button">%s</button>' % w for w in
                ("mercy", "light", "covenant", "&quot;living creature&quot;", "forgive")]
    examples.append('<button class="chip" type="button" lang="ar">\u0631\u062D\u0645\u0629</button>')
    return """<h1>Search</h1>
<form class="sf" id="sf" role="search" action="./" method="get">
<input id="q" name="q" type="search" autocomplete="off" autocapitalize="off" spellcheck="false" enterkeyhint="search"
 placeholder="A word, or &quot;words in quotes&quot;" aria-label="Search %s, %s and %s">
</form>
<div class="scope" id="scope" hidden></div>
<p class="sstat" id="sstat" aria-live="polite"></p>
<div id="res"></div>
<div class="stips" id="stips">
<p>Type a word to find every verse that uses it, in the Bible, the Quran and the study notes. Its other forms are
found too: <em>love</em> also finds <em>loved</em>, <em>loves</em> and <em>loving</em>.</p>
<p>Several words find the verses that have all of them. Put words in quotes to find them together, in that order.
Typing in Arabic searches the Quran's Arabic, every surah, with or without vowel marks.</p>
<div class="chips">%s</div>
</div>
<script id="search-config" type="application/json">%s</script>
<script src="%s" defer></script>""" % (first, others[0], others[1], "".join(examples), dumps(config), js_name)


def build(work, out, x):
    """Write <out>/search/ for one site. x holds the site's chapters and its parse and page functions:
    {"chapters": [(book, n, path)], "parse": ..., "books": [...], "page": page(body, css, tail) -> html,
     "shown": (Quran) the Arabic as the pages show it}."""
    if os.path.isdir(os.path.join(out, "search")):
        shutil.rmtree(os.path.join(out, "search"))
    extra = {}
    if work == "bible":
        books, files, units = bible_units(x)
    elif work == "quran":
        books, files, units = quran_units(x)
        extra = arabic_files(x["shown"], x["slots"])
    else:
        books, files, units = study_units(x)
    known = write_index(work, out, books, files, units, extra)
    js = open(os.path.join(ROOT, "scripts", "search.js"), encoding="utf-8").read()
    open(os.path.join(out, "search", "search.js"), "w", encoding="utf-8").write(js)
    js_name = "search.js?v=%s" % hashlib.sha1(js.encode("utf-8")).hexdigest()[:8]
    css = CSS
    if work != "quran":   # the Quran site has the fonts already
        css = ''.join('@font-face{font-family:"%s";src:url(%s) format("woff2");font-display:swap;'
                      'unicode-range:U+0600-06FF,U+0750-077F,U+0870-08FF,U+FB50-FDFF,U+FE70-FEFF}\n' % (name, url)
                      for name, url in (("Quran Text", QURAN_FONT), ("Arabic Text", ARABIC_FONT))) + css
    open(os.path.join(out, "search", "index.html"), "w", encoding="utf-8").write(
        x["page"](page_body(work, js_name), css))
    # Let the other two sites read this one's index, and on the Quran site its Arabic font.
    rules = "/search/*\n  Access-Control-Allow-Origin: *\n"
    if work == "quran":
        rules += "/fonts/*\n  Access-Control-Allow-Origin: *\n"
    open(os.path.join(out, "_headers"), "w", encoding="utf-8").write(rules)
    print("Search: %d %s, %d words indexed into %s/search/" % (
        len(units), {"bible": "verses", "quran": "verses", "study": "sections"}[work], known, os.path.basename(out)))
