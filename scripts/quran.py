#!/usr/bin/env python3
"""The Quran: a second site built by the same scripts as the Bible, into site-quran/.

    WORK=quran python3 scripts/build.py                 # build the Quran site
    python3 scripts/check.py translations/quran-2/003.md   # check one part (works out WORK itself)
    python3 scripts/quran.py                            # print the next part to translate

A short surah is one page. A long surah is published in parts of about a thousand English words,
planned in data/quran.json ("parts": [[first verse, last verse], ...]). To the other scripts each
surah is a "book" with the slug quran-<surah> whose "chapters" are its parts, so pages, recordings,
word timings and pictures all keep the usual paths: translations/quran-2/003.md,
audio/quran-2/3.mp3. What a part is called on the site comes from label(): "Quran 2:62-82", or
"Quran 1" when one part holds the whole surah. Rules for the translation: QURAN_RULES.md.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURAHS = json.load(open(os.path.join(ROOT, "data", "quran.json"), encoding="utf-8"))
SITE_TITLE = "The Quran, Freshly Translated"
FOOTER = "An original translation from the Arabic."
VERSES = sum(s["verses"] for s in SURAHS)
ENGLISH_PER_ARABIC = 1.9    # English words a plain translation needs for each Arabic word, roughly


def front(path):
    """The front matter of a part file as a dict."""
    m = re.match(r"---\n(.*?)\n---\n", open(path, encoding="utf-8").read(), re.S)
    return dict((k.strip(), v.strip()) for k, v in
                (line.split(":", 1) for line in (m.group(1).splitlines() if m else []) if ":" in line))


def span(text):
    """'30-61' -> (30, 61); a single verse '7' -> (7, 7)."""
    m = re.match(r"^(\d+)(?:\s*-\s*(\d+))?$", text or "")
    if not m:
        raise SystemExit("Bad 'verses:' line: %r (write it as 30-61)" % text)
    return int(m.group(1)), int(m.group(2) or m.group(1))


def label(surah, a, z):
    """What a part is called on the site."""
    whole = (a, z) == (1, SURAHS[surah - 1]["verses"])
    return "Quran %d" % surah if whole else "Quran %d:%d-%d" % (surah, a, z)


def spoken(surah, a, z):
    """The line read aloud before a part's words."""
    whole = (a, z) == (1, SURAHS[surah - 1]["verses"])
    return "Quran, surah %d." % surah if whole else "Quran, surah %d, verses %d to %d." % (surah, a, z)


def books(src):
    """One "book" for each surah that has at least one translated part, in order."""
    out = []
    for s in SURAHS:
        slug, ranges = "quran-%d" % s["n"], []
        while os.path.exists(os.path.join(src, slug, "%03d.md" % (len(ranges) + 1))):
            ranges.append(span(front(os.path.join(src, slug, "%03d.md" % (len(ranges) + 1))).get("verses")))
        if not ranges:
            continue
        out.append({
            "name": "Surah %d" % s["n"], "slug": slug, "chapters": len(ranges), "surah": s["n"],
            "title": s.get("name", ""), "total_verses": s["verses"], "ranges": ranges,
            "planned": max(len(s.get("parts", [])), len(ranges)),
            "labels": [label(s["n"], a, z) for a, z in ranges],
            "intros": [spoken(s["n"], a, z) for a, z in ranges],
            "eyebrow": "Surah %d%s" % (s["n"], " · " + s["name"] if s.get("name") else ""),
        })
    return out


def done(b):
    """True when every verse of the surah is translated."""
    return b["ranges"][-1][1] == b["total_verses"]


def surah_page(b, esc):
    """Body of a surah's own page: its parts by verse range."""
    cells = "".join('<a href="%d.html">Verses %d-%d</a>' % (k + 1, a, z) for k, (a, z) in enumerate(b["ranges"]))
    if not done(b):
        cells += "<span>Verses %d-%d<small>coming</small></span>" % (b["ranges"][-1][1] + 1, b["total_verses"])
    progress = ("%d verses" % b["total_verses"]) if done(b) else (
        "verses 1-%d of %d translated" % (b["ranges"][-1][1], b["total_verses"]))
    return '<h1>%s</h1><p class="sub">%s</p><div class="grid">%s</div>' % (
        esc(b["name"]), esc(" · ".join(x for x in (b["title"], progress) if x)), cells)


def home(bks, esc):
    """The list of surahs on the home page, and the line under the site's title."""
    cells = []
    for b in bks:
        if done(b):
            note = "%d verses" % b["total_verses"]
        else:
            note = "verses 1-%d of %d" % (b["ranges"][-1][1], b["total_verses"])
        href = "%s/1.html" % b["slug"] if b["chapters"] == 1 and done(b) else "%s/" % b["slug"]
        cells.append('<a href="%s">%s<small>%s</small></a>' % (
            href, esc(b["name"]), esc(" · ".join(x for x in (b["title"], note) if x))))
    started = {b["surah"] for b in bks}
    rest = [s["n"] for s in SURAHS if s["n"] not in started]
    if rest:
        cells.append("<span>%s<small>coming</small></span>" % (
            "Surah %d" % rest[0] if len(rest) == 1 else "Surahs %d to %d" % (rest[0], rest[-1])))
    verses = sum(z - a + 1 for b in bks for a, z in b["ranges"])
    sub = "%s of %s verses translated, in %d of 114 surahs." % (
        format(verses, ","), format(VERSES, ","), len(bks))
    return sub, '<h3 class="group">Surahs</h3><div class="grid">%s</div>' % "".join(cells)


def next_part():
    """(surah, part number, first verse, last verse, estimated English words) of the next part to
    translate, None when the next surah has no parts planned yet, or "DONE"."""
    for s in SURAHS:
        have = 0
        while os.path.exists(os.path.join(ROOT, "translations", "quran-%d" % s["n"], "%03d.md" % (have + 1))):
            have += 1
        if have and span(front(os.path.join(ROOT, "translations", "quran-%d" % s["n"], "%03d.md" % have))
                         .get("verses"))[1] == s["verses"]:
            continue
        parts = s.get("parts")
        if not parts or have >= len(parts):
            return None, s["n"]
        a, z = parts[have]
        lines = open(os.path.join(ROOT, "sources", "quran", "%03d.txt" % s["n"]), encoding="utf-8").read().splitlines()
        arabic = sum(len(t.split("\t", 1)[1].split()) for t in lines if a <= int(t.split("\t", 1)[0]) <= z)
        return s["n"], have + 1, a, z, int(round(arabic * ENGLISH_PER_ARABIC, -1))
    return "DONE"


if __name__ == "__main__":
    p = next_part()
    if p == "DONE":
        print("DONE")
    elif p[0] is None:
        print("PLAN surah %d: add its \"parts\" to data/quran.json first (see CLAUDE.md, Quran)" % p[1])
        sys.exit(1)
    else:
        print("quran-%d %03d verses %d-%d about %d words" % p)
