#!/usr/bin/env python3
"""The study site: an analysis of each published chapter, section by section (rules: ANALYSIS_RULES.md).

    python3 scripts/study.py                               build site-study/ from analysis/<slug>/<NNN>.md
    python3 scripts/study.py check analysis/1-john/003.md  check one analysis before publishing

The analysis never changes the translation: this script only reads translations/.

A related passage is given by its address ("### John 1:10-13"). When that chapter is published, the page
shows the published wording (its main text, as it is read aloud) and links to it; until then it shows the
fresh translation that the analysis file carries in its "> " lines.
"""
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["WORK"] = "bible"   # build.py also builds the Quran's site; the study site is about the Bible
import build
from build import ROOT, SRC, BOOKS, BY_SLUG, esc, plain

SRC_A = os.path.join(ROOT, "analysis")
OUT = os.path.join(ROOT, "site-study")
BIBLE_URL = "https://bible.odownhills.workers.dev"
SITE_TITLE = "The Bible, Closely Read"
FOOTER = "A close reading of each chapter of The Bible, Freshly Translated, with Scripture explaining Scripture."
# The rules in numbers (ANALYSIS_RULES.md): the analysis's own words as a share of the chapter's words,
# the words of the opening, and the related passages in a section.
LENGTH = (0.75, 4 / 3)
OPENING = (40, 80)
RELATED = (1, 2)

BY_NAME = {b["name"]: b for b in BOOKS}
NAMES = "|".join(re.escape(n) for n in sorted(BY_NAME, key=len, reverse=True))
REF = re.compile(r"^(%s) (\d+):(\d+)(?:-(\d+))?$" % NAMES)
NAMED = re.compile(r"(?<![\w-])(%s) (\d+):(\d+)(?:-(\d+))?" % NAMES)   # an address inside a sentence
BARE = re.compile(r"(?<![\w:,-])(\d+):(\d+)(?:-(\d+))?(?![\w:])")       # "2:19": a verse of the same book
VERSES = re.compile(r"\bverses?\s+(\d+(?:-\d+)?(?:(?:,\s*|,?\s+and\s+)\d+(?:-\d+)?)*)", re.I)
SCRIPT = r"[֐-׿Ͱ-Ͽἀ-῿؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]"
ARCHAIC = ["behold", "thee", "thy", "thou", "thine", "hearken", "iniquity", "begat", "lo", "verily", "hath",
           "doth", "unto", "ye", "shall"]
# Only Scripture is evidence: an analysis does not lean on scholars, translations or tradition, and YHWH is "Yahweh".
NOT_EVIDENCE = [r"\bscholar", r"\bcommentar", r"\btheologian", r"\bchurch fathers?\b", r"\bdenominat",
                r"\btraditionally\b", r"\btradition (says|holds|teaches|has it)\b",
                r"\b(church|christian|jewish|rabbinic) tradition\b",
                r"\b(KJV|NKJV|NIV|ESV|NASB|NRSV|NLT|King James)\b", r"\bLORD\b"]

CSS = build.CSS + """
.top a.out{color:var(--accent)}
p.open{color:var(--text-soft);margin:0 0 .5rem}
h2.sec{display:flex;justify-content:space-between;align-items:baseline;gap:1rem}
h2.sec a{color:var(--text-soft);font-weight:400;letter-spacing:.06em;text-decoration:none;white-space:nowrap}
h2.sec a:hover{color:var(--accent)}
h3.rel{font-family:var(--sans);font-size:.7rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--num);margin:1.6rem 0 .6rem}
.rs{background:var(--panel);border:1px solid var(--rule);border-left:3px solid var(--accent);border-radius:8px;padding:.8rem 1rem .9rem;margin:0 0 .9rem}
.rs .ref{font-family:var(--sans);font-size:.8rem;letter-spacing:.04em;color:var(--accent);margin:0 0 .35rem}
.rs .ref a{text-decoration:none}
.rs .ref a:hover{text-decoration:underline}
.rs blockquote{margin:0 0 .7rem;color:var(--text)}
.rs .why{margin:0;font-size:.92em;line-height:1.65;color:var(--text-soft)}
.rs .why+.why{margin-top:.6rem}
"""


def count(texts):
    return sum(len(t.split()) for t in texts)


def chapter_path(b, c):
    return os.path.join(SRC, b["slug"], "%03d.md" % c)


def published(b, c):
    return os.path.exists(chapter_path(b, c))


_verses = {}


def verses(b, c):
    """A published chapter's verses: {number: main text}, with alternates and notes left out, as it is read aloud."""
    key = (b["slug"], c)
    if key not in _verses:
        _, blocks = build.parse(chapter_path(b, c))
        _verses[key] = {vn: plain(t) for k, v in blocks if k == "p" for vn, t in v}
    return _verses[key]


def sections_of(blocks):
    """The translation's sections: [[heading or None, first verse, last verse]]."""
    out = []
    for kind, val in blocks:
        if kind == "h":
            out.append([val, None, None])
        elif kind == "p":
            if not out:
                out.append([None, None, None])
            for vn, _ in val:
                if out[-1][1] is None:
                    out[-1][1] = vn
                out[-1][2] = vn
    out = [s for s in out if s[1] is not None]
    if len(out) > 1 and out[0][0] is None:   # verses ahead of the first heading belong to the first section
        out[1][1] = out[0][1]
        out.pop(0)
    return out


def parse_analysis(path):
    """An analysis file: (front matter, opening paragraphs, sections). A section is
    {"heading", "paras": [deep meaning], "related": [{"ref", "quote": [(verse, text)], "paras": [the connection]}]}."""
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        raise SystemExit("Missing front matter: " + path)
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    opening, sections = [], []
    paras, fresh, rel = opening, True, None
    for line in m.group(2).splitlines():
        s = line.strip()
        if not s:
            fresh = True
        elif s.startswith("### "):
            if not sections:   # a chapter the translation does not divide
                sections.append({"heading": None, "paras": [], "related": []})
            rel = {"ref": s[4:].strip(), "quote": [], "paras": []}
            sections[-1]["related"].append(rel)
            paras, fresh = rel["paras"], True
        elif s.startswith("## "):
            sections.append({"heading": s[3:].strip(), "paras": [], "related": []})
            paras, fresh, rel = sections[-1]["paras"], True, None
        elif s.startswith(">"):
            if rel is None:
                raise SystemExit("A quote line outside a related passage in %s: %r" % (path, s))
            q = re.match(r"^(\d+)\s+(.*)$", s[1:].strip())
            rel["quote"].append((int(q.group(1)), q.group(2)) if q else (None, s[1:].strip()))
            fresh = True
        else:
            if fresh:
                paras.append(s)
            else:
                paras[-1] += " " + s
            fresh = False
    if len(sections) == 1 and sections[0]["heading"] is None:   # undivided: the first paragraph is the opening
        sections[0]["paras"], opening = opening[1:], opening[:1]
    return meta, opening, sections


def resolve(ref):
    """("John 1:10-13") -> (book, chapter, first verse, last verse), or None when it is not an address."""
    m = REF.match(ref)
    if not m:
        return None
    a = int(m.group(3))
    return BY_NAME[m.group(1)], int(m.group(2)), a, int(m.group(4) or a)


def exists(b, c, a, z):
    return 1 <= c <= b["chapters"] and 1 <= a <= z <= b["verses"][c - 1]


def quote_of(rel):
    """The verses a related passage shows: ([(verse, text)], published or not)."""
    b, c, a, z = resolve(rel["ref"])
    if published(b, c):
        have = verses(b, c)
        return [(n, have[n]) for n in range(a, z + 1) if n in have], True
    return rel["quote"], False


def paired(text):
    """What to put before and after a quote lifted out of a longer speech so its quotation marks pair up."""
    marks = [m.start() for m in re.finditer('"', text)]
    if len(marks) % 2 == 0:
        return "", ""
    first = marks[0]
    closing = first > 0 and not text[first - 1].isspace() and text[first - 1] not in "(—"
    return ('"', "") if closing else ("", '"')


def check(path):
    errs = []
    rel_path = os.path.relpath(os.path.abspath(path), ROOT)
    m = re.match(r"^analysis/([^/]+)/(\d{3})\.md$", rel_path.replace(os.sep, "/"))
    if not m or m.group(1) not in BY_SLUG:
        print("FAIL  %s: an analysis is analysis/<book-slug>/<NNN>.md" % rel_path)
        return 1
    b, n = BY_SLUG[m.group(1)], int(m.group(2))
    meta, opening, sections = parse_analysis(path)
    if meta.get("book") != b["name"] or meta.get("chapter") != str(n):
        errs.append("front matter should say book: %s and chapter: %d" % (b["name"], n))
    if not published(b, n):
        print("FAIL  %s: %s %d is not published yet, so it cannot be analyzed" % (rel_path, b["name"], n))
        return 1
    _, blocks = build.parse(chapter_path(b, n))
    want = sections_of(blocks)
    last = b["verses"][n - 1]

    got = [s["heading"] for s in sections]
    if got != [s[0] for s in want]:
        errs.append("sections should be the translation's, in order: %s (found: %s)" % (
            " | ".join(str(s[0]) for s in want), " | ".join(str(g) for g in got)))
    k = count(opening)
    if not OPENING[0] <= k <= OPENING[1]:
        errs.append("the opening has %d words; it should have %d to %d" % (k, OPENING[0], OPENING[1]))

    prose, quoted, fresh_n, pub_n = list(opening), [], 0, 0
    for s in sections:
        name = s["heading"] or "the chapter"
        prose += s["paras"]
        if not s["paras"]:
            errs.append("%s: no deep meaning" % name)
        if not RELATED[0] <= len(s["related"]) <= RELATED[1]:
            errs.append("%s: %d related passages; a section has %d to %d" % (name, len(s["related"]), RELATED[0], RELATED[1]))
        for r in s["related"]:
            prose += r["paras"]
            where = "%s, %s" % (name, r["ref"])
            at = resolve(r["ref"])
            if not at:
                errs.append("%s: not an address like 'John 1:10-13' with a book name from data/books.json" % where)
                continue
            rb, c, a, z = at
            if not exists(rb, c, a, z):
                errs.append("%s: there is no such passage" % where)
                continue
            if rb is b and c == n:
                errs.append("%s: a related passage comes from outside the chapter" % where)
            if not r["paras"]:
                errs.append("%s: nothing says what the connection is" % where)
            if published(rb, c):
                pub_n += 1
                if r["quote"]:
                    errs.append("%s: this chapter is published, so write no quote; the site shows the published wording" % where)
                elif len(quote_of(r)[0]) != z - a + 1:
                    errs.append("%s: the published chapter does not have all of these verses" % where)
            else:
                fresh_n += 1
                if [q[0] for q in r["quote"]] != list(range(a, z + 1)):
                    errs.append("%s: not published yet, so it needs a fresh translation, one '> <verse> ...' line "
                                "for each of verses %d to %d" % (where, a, z))
                for _, t in r["quote"]:
                    quoted.append(t)
                    if "[" in t or "]" in t:
                        errs.append("%s: a quote is main text only, with no brackets" % where)

    text = "\n".join(prose)
    for mm in NAMED.finditer(text):
        rb, c, a = BY_NAME[mm.group(1)], int(mm.group(2)), int(mm.group(3))
        if not exists(rb, c, a, int(mm.group(4) or a)):
            errs.append("there is no %s" % mm.group(0))
    for mm in BARE.finditer(NAMED.sub("", text)):
        c, a = int(mm.group(1)), int(mm.group(2))
        if not exists(b, c, a, int(mm.group(3) or a)):
            errs.append("there is no %s %s" % (b["name"], mm.group(0)))
    for mm in VERSES.finditer(text):
        for v in re.findall(r"\d+", mm.group(1)):
            if not 1 <= int(v) <= last:
                errs.append("'%s': %s %d has %d verses" % (mm.group(0), b["name"], n, last))
    everything = text + "\n" + "\n".join(quoted)
    if re.search(SCRIPT, open(path, encoding="utf-8").read()):
        errs.append("contains Hebrew, Greek or Arabic script")
    for w in ARCHAIC:
        if re.search(r"\b%s\b" % w, everything, re.I):
            errs.append("archaic word: %s" % w)
    for pat in NOT_EVIDENCE:
        hit = re.search(pat, text, 0 if "LORD" in pat or "KJV" in pat else re.I)
        if hit:
            errs.append("only Scripture is evidence, and YHWH is \"Yahweh\": found '%s'" % hit.group(0))

    own = count(prose)
    scripture = sum(len(plain(t).split()) for k_, v in blocks if k_ == "p" for _, t in v)
    ratio = own / max(scripture, 1)
    if not LENGTH[0] <= ratio <= LENGTH[1]:
        errs.append("%d words of analysis for %d of scripture (%.2f); it should be %d to %d words" % (
            own, scripture, ratio, -(-scripture * LENGTH[0] // 1), scripture * LENGTH[1] // 1))
    if errs:
        print("FAIL  " + rel_path)
        for e in errs:
            print("  - " + e)
        return 1
    print("OK  %s: %d words of analysis for %d of scripture (%.2f); %d related passages, %d in the published "
          "wording and %d translated fresh" % (rel_path, own, scripture, ratio, pub_n + fresh_n, pub_n, fresh_n))
    return 0


def page(title, body, depth):
    up = "../" * depth
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#171223">
<title>%s</title>
<style>%s</style></head>
<body><div class="wrap">
<nav class="top"><a href="%s">Books</a><a class="out" href="%s/">The translation</a></nav>
%s
<footer>%s</footer>
</div></body></html>
""" % (esc(title), CSS, up or "./", BIBLE_URL, body, esc(FOOTER))


def span(a, z):
    return "verse %d" % a if a == z else "verses %d-%d" % (a, z)


def related_html(rel):
    b, c, a, z = resolve(rel["ref"])
    quote, pub = quote_of(rel)
    before, after = paired(" ".join(t for _, t in quote))
    many = len(quote) > 1
    words = " ".join(('<sup class="n">%d</sup>' % vn if many else "") + esc(t) for vn, t in quote)
    ref = esc(rel["ref"])
    if pub:   # the published chapter, at the verse
        ref = '<a href="%s/%s/%d.html#v%d">%s</a>' % (BIBLE_URL, b["slug"], c, a, ref)
    return '<div class="rs"><p class="ref">%s</p><blockquote>%s%s%s</blockquote>%s</div>' % (
        ref, esc(before), words, esc(after), "".join('<p class="why">%s</p>' % esc(p) for p in rel["paras"]))


def collect():
    """The chapters that have an analysis, in the order of the canon: [(book, chapter, path)]."""
    out = []
    for b in BOOKS:
        for n in range(1, b["chapters"] + 1):
            p = os.path.join(SRC_A, b["slug"], "%03d.md" % n)
            if os.path.exists(p) and published(b, n):
                out.append((b, n, p))
    return out


def main():
    chapters = collect()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    have = {(b["slug"], n) for b, n, _ in chapters}

    for idx, (b, n, path) in enumerate(chapters):
        _, opening, sections = parse_analysis(path)
        _, blocks = build.parse(chapter_path(b, n))
        ranges = sections_of(blocks)
        there = "%s/%s/%d.html" % (BIBLE_URL, b["slug"], n)
        parts = ['<p class="open">%s</p>' % esc(p) for p in opening]
        for k, s in enumerate(sections):
            a, z = (ranges[k][1], ranges[k][2]) if k < len(ranges) else (1, b["verses"][n - 1])
            parts.append('<h2 class="sec" id="s%d"><span>%s</span><a href="%s#v%d">%s</a></h2>' % (
                k + 1, esc(s["heading"] or "The whole chapter"), there, a, span(a, z)))
            parts += ['<p class="v">%s</p>' % esc(p) for p in s["paras"]]
            if s["related"]:
                parts.append('<h3 class="rel">Related Scripture</h3>')
                parts += [related_html(r) for r in s["related"]]
        prev_ = chapters[idx - 1] if idx > 0 else None
        next_ = chapters[idx + 1] if idx + 1 < len(chapters) else None

        def link(c, cls, arrow, none):
            if not c:
                return '<span class="%s">%s</span>' % (cls, none)
            cb, cn, _ = c
            href = ("%d.html" % cn) if cb is b else ("../%s/%d.html" % (cb["slug"], cn))
            return '<a class="%s" href="%s">%s %s %d</a>' % (cls, href, arrow, esc(cb["name"]), cn)

        body = """<h1>%s %d</h1>
<p class="sub">What the chapter means, section by section. <a class="btn ghost" href="%s">Read the chapter</a></p>
%s
<div class="pn">%s%s</div>""" % (esc(b["name"]), n, there, "\n".join(parts),
                                 link(prev_, "prev", "&larr;", "The first chapter here"),
                                 link(next_, "next", "&rarr;", "More chapters coming"))
        os.makedirs(os.path.join(OUT, b["slug"]), exist_ok=True)
        open(os.path.join(OUT, b["slug"], "%d.html" % n), "w", encoding="utf-8").write(
            page("%s %d: what it means" % (b["name"], n), body, 1))

    for b in BOOKS:   # book pages
        done = [n for n in range(1, b["chapters"] + 1) if (b["slug"], n) in have]
        if not done:
            continue
        cells = "".join(('<a href="%d.html">%d</a>' % (n, n)) if (b["slug"], n) in have else '<span>%d</span>' % n
                        for n in range(1, b["chapters"] + 1))
        body = '<h1>%s</h1><p class="sub">%d of %d chapters</p><div class="grid ch">%s</div>' % (
            esc(b["name"]), len(done), b["chapters"], cells)
        open(os.path.join(OUT, b["slug"], "index.html"), "w", encoding="utf-8").write(page(b["name"], body, 1))

    groups = []   # home page
    for heading, t in (("Old Testament", "OT"), ("New Testament", "NT")):
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
        latest = '<a class="continue" href="%s/%d.html"><small>Newest</small><b>%s %d</b></a>' % (
            lb["slug"], ln, esc(lb["name"]), ln)
    sub = ("What each chapter of the translation means, section by section, and the Scripture that lights it up. "
           "%d chapter%s so far." % (len(chapters), "" if len(chapters) == 1 else "s"))
    body = '<h1>%s</h1><p class="sub">%s</p>%s%s' % (SITE_TITLE, sub, latest, "".join(groups))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page(SITE_TITLE, body, 0))
    print("Built %d chapter%s into %s/" % (len(chapters), "" if len(chapters) == 1 else "s", os.path.basename(OUT)))


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "check":
        sys.exit(check(sys.argv[2]))
    main()
