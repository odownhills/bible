#!/usr/bin/env python3
"""Prepare one Bible chapter for its translator (CLAUDE.md, step 1).

    python3 scripts/prepare.py genesis 11              # files go to <tmp>/bible-prep/genesis-011/
    python3 scripts/prepare.py genesis 11 --out DIR

Writes, outside the repository (these files are never committed):
  - hebrew.txt          the chapter in Hebrew (Westminster Leningrad Codex, from the Open Scriptures
                        Hebrew Bible), one verse per line: "N text", with [K: ...] for the written text
                        (Ketiv), [Q: ...] for the read text (Qere) after it, and {S} / {P} for the Hebrew
                        text's own paragraph breaks. hebrew-prev.txt and hebrew-next.txt hold the
                        chapters on either side, for continuity only.
  - glossary.md         the parts of GLOSSARY.md this chapter needs (see glossary_extract below).
  - brief.md            the translator's brief: scripts/translator_brief.md with this chapter filled in.
and prints the paths. The thread hands brief.md to the Fable translator (CLAUDE.md, step 1).

New Testament chapters: the Greek text is not fetched by this script yet. brief.md then says where
the thread must put it (greek.txt in the same folder) before the translator starts.
"""
import json, os, re, sys, tempfile, textwrap, unicodedata, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS = json.load(open(os.path.join(ROOT, "data", "books.json")))
BY_SLUG = {b["slug"]: b for b in BOOKS}
ORDER = [b["slug"] for b in BOOKS]

# Abbreviations the glossary uses for references (Gen 11:9, 1 Chr 1:7, Ps 55:9 ...), and the
# Open Scriptures Hebrew Bible file name (OSIS book id) for each Old Testament book.
ABBR = {
    "genesis": ("Gen", "Gen"), "exodus": ("Exod", "Exod"), "leviticus": ("Lev", "Lev"),
    "numbers": ("Num", "Num"), "deuteronomy": ("Deut", "Deut"), "joshua": ("Josh", "Josh"),
    "judges": ("Judg", "Judg"), "ruth": ("Ruth", "Ruth"), "1-samuel": ("1 Sam", "1Sam"),
    "2-samuel": ("2 Sam", "2Sam"), "1-kings": ("1 Kgs", "1Kgs"), "2-kings": ("2 Kgs", "2Kgs"),
    "1-chronicles": ("1 Chr", "1Chr"), "2-chronicles": ("2 Chr", "2Chr"), "ezra": ("Ezra", "Ezra"),
    "nehemiah": ("Neh", "Neh"), "esther": ("Esth", "Esth"), "job": ("Job", "Job"),
    "psalms": ("Ps", "Ps"), "proverbs": ("Prov", "Prov"), "ecclesiastes": ("Eccl", "Eccl"),
    "song-of-songs": ("Song", "Song"), "isaiah": ("Isa", "Isa"), "jeremiah": ("Jer", "Jer"),
    "lamentations": ("Lam", "Lam"), "ezekiel": ("Ezek", "Ezek"), "daniel": ("Dan", "Dan"),
    "hosea": ("Hos", "Hos"), "joel": ("Joel", "Joel"), "amos": ("Amos", "Amos"),
    "obadiah": ("Obad", "Obad"), "jonah": ("Jonah", "Jonah"), "micah": ("Mic", "Mic"),
    "nahum": ("Nah", "Nah"), "habakkuk": ("Hab", "Hab"), "zephaniah": ("Zeph", "Zeph"),
    "haggai": ("Hag", "Hag"), "zechariah": ("Zech", "Zech"), "malachi": ("Mal", "Mal"),
    "matthew": ("Matt", None), "mark": ("Mark", None), "luke": ("Luke", None), "john": ("John", None),
    "acts": ("Acts", None), "romans": ("Rom", None), "1-corinthians": ("1 Cor", None),
    "2-corinthians": ("2 Cor", None), "galatians": ("Gal", None), "ephesians": ("Eph", None),
    "philippians": ("Phil", None), "colossians": ("Col", None), "1-thessalonians": ("1 Thess", None),
    "2-thessalonians": ("2 Thess", None), "1-timothy": ("1 Tim", None), "2-timothy": ("2 Tim", None),
    "titus": ("Titus", None), "philemon": ("Phlm", None), "hebrews": ("Heb", None),
    "james": ("Jas", None), "1-peter": ("1 Pet", None), "2-peter": ("2 Pet", None),
    "1-john": ("1 Jn", None), "2-john": ("2 Jn", None), "3-john": ("3 Jn", None),
    "jude": ("Jude", None), "revelation": ("Rev", None),
}
WLC = "https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc/%s.xml"
NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"
WRAP = 1800  # the Read tool cuts a line at 2,000 characters; longer glossary lines are wrapped below this


def chapter_path(slug, n, kind="translations"):
    return os.path.join(ROOT, kind, slug, "%03d.md" % n)


def previous_chapter(slug, n):
    """The chapter before this one in canonical order that is already translated."""
    i = ORDER.index(slug)
    for s in ORDER[i::-1]:
        top = n - 1 if s == slug else BY_SLUG[s]["chapters"]
        for m in range(top, 0, -1):
            if os.path.exists(chapter_path(s, m)):
                return s, m
    return None


def next_label(slug, n):
    b = BY_SLUG[slug]
    if n < b["chapters"]:
        return "%s %d" % (b["name"], n + 1)
    i = ORDER.index(slug)
    return "%s 1" % BY_SLUG[ORDER[i + 1]]["name"] if i + 1 < len(ORDER) else "the end"


# ---------------------------------------------------------------- Hebrew text

def wlc_book(osis, cache):
    path = os.path.join(cache, "%s.xml" % osis)
    if not os.path.exists(path):
        os.makedirs(cache, exist_ok=True)
        req = urllib.request.Request(WLC % osis, headers={"User-Agent": "bible-prepare"})
        data = urllib.request.urlopen(req, timeout=120).read()
        open(path, "wb").write(data)
    return ET.parse(path).getroot()


def word_text(w):
    return "".join(w.itertext()).replace("/", "")


def verse_line(v):
    out = []
    kids = list(v)
    i = 0
    while i < len(kids):
        el = kids[i]
        tag = el.tag.replace(NS, "")
        if tag == "w":
            t = word_text(el)
            if el.get("type") == "x-ketiv":
                q = ""
                if i + 1 < len(kids) and kids[i + 1].tag.replace(NS, "") == "note":
                    rdg = kids[i + 1].find(NS + "rdg")
                    if rdg is not None:
                        q = " ".join(word_text(x) for x in rdg.iter(NS + "w"))
                    i += 1
                out.append("[K: %s]%s" % (t, " [Q: %s]" % q if q else ""))
            else:
                out.append(t)
        elif tag == "seg":
            kind = el.get("type")
            if kind == "x-maqqef":
                out.append("־")
            elif kind == "x-sof-pasuq":
                out.append("׃")
            elif kind == "x-samekh":
                out.append("{S}")
            elif kind == "x-pe":
                out.append("{P}")
        elif tag == "note":
            rdg = el.find(NS + "rdg")
            if rdg is not None and rdg.get("type") == "x-qere":  # a Qere with no Ketiv word before it
                out.append("[Q: %s]" % " ".join(word_text(x) for x in rdg.iter(NS + "w")))
        i += 1
    s = ""
    for tok in out:
        if tok == "־" or tok == "׃":
            s += tok
        elif s.endswith("־"):
            s += tok
        else:
            s += (" " if s else "") + tok
    return s


def hebrew_chapter(root, osis, n):
    ch = root.find(".//%schapter[@osisID='%s.%d']" % (NS, osis, n))
    if ch is None:
        return None
    lines = []
    for v in ch.iter(NS + "verse"):
        num = v.get("osisID").split(".")[-1]
        lines.append("%s %s" % (num, verse_line(v)))
    return lines


# ---------------------------------------------------------------- glossary

def ref_pattern(slug, n):
    names = {BY_SLUG[slug]["name"], ABBR[slug][0]}
    if slug == "psalms":
        names |= {"Psalm", "Pss"}
    if slug == "1-john":
        names |= {"1 John"}
    alt = "|".join(sorted((re.escape(x) for x in names), key=len, reverse=True))
    return re.compile(r"(?<![\w-])(?:%s)\.? %d(?=[:\s,;.)]|$)" % (alt, n))


def wrap(line):
    if len(line) <= WRAP:
        return line
    parts, rest = [], line
    while len(rest) > WRAP:
        cut = max(rest.rfind("; ", 0, WRAP), rest.rfind(". ", 0, WRAP))
        if cut < WRAP // 2:
            cut = rest.rfind(" ", 0, WRAP)
        parts.append(rest[:cut + 1].rstrip())
        rest = "  " + rest[cut + 1:].lstrip()
    parts.append(rest)
    return "\n".join(parts)


def glossary_extract(slug, n):
    """Everything that is not a "Settled in <Book> <n>" section (the opening, "Decided by Obay", the
    2026-11-21 note), every section of this book, and from all other sections the lines that name
    this chapter. Then the headings of the sections left out, for searching."""
    text = open(os.path.join(ROOT, "GLOSSARY.md"), encoding="utf-8").read()
    secs = re.split(r"(?m)^(?=## )", text)
    book = BY_SLUG[slug]["name"]
    own = re.compile(r"^## Settled in %s \d" % re.escape(book))
    other = re.compile(r"^## Settled in .+ \d")
    ref = ref_pattern(slug, n)
    keep, mentions, skipped = [], [], []
    for s in secs:
        if not s.startswith("## ") or own.match(s) or not other.match(s):
            keep.append(s.rstrip("\n"))
            continue
        head, *body = s.rstrip("\n").split("\n")
        hits = [l for l in body if ref.search(l)]
        if hits:
            mentions.append("### From \"%s\"\n%s" % (head[3:], "\n".join(hits)))
        skipped.append(head[3:].replace("Settled in ", ""))
    out = ["<!-- Extract of GLOSSARY.md made by scripts/prepare.py for %s %d. The file itself is the"
           " record; search it for anything not here. -->" % (book, n)]
    out += keep
    if mentions:
        out.append("## Lines in other sections that name %s %d\n\n%s" % (book, n, "\n\n".join(mentions)))
    out.append("## Other sections, not printed here\n\nGLOSSARY.md also has \"Settled in\" sections for: "
               + ", ".join(skipped) + ". Their settled renderings still apply. Before you settle a"
               " recurring word or a name, search GLOSSARY.md for it (grep -n -i), by the original"
               " word as the glossary spells it and by the English you have in mind.")
    return "\n".join(wrap(l) for l in "\n\n".join(out).split("\n")) + "\n"


# ---------------------------------------------------------------- brief

def main():
    args, out = sys.argv[1:], None
    if "--out" in args:
        i = args.index("--out")
        out = args[i + 1] if i + 1 < len(args) else sys.exit("--out needs a folder")
        del args[i:i + 2]
    if len(args) != 2 or args[0] not in BY_SLUG or not args[1].isdigit():
        sys.exit(__doc__)
    slug, n = args[0], int(args[1])
    b = BY_SLUG[slug]
    if not 1 <= n <= b["chapters"]:
        sys.exit("%s has %d chapters" % (b["name"], b["chapters"]))
    nnn = "%03d" % n
    out = out or os.path.join(tempfile.gettempdir(), "bible-prep", "%s-%s" % (slug, nnn))
    os.makedirs(out, exist_ok=True)
    cache = os.path.join(tempfile.gettempdir(), "bible-prep", "wlc")
    notes = []

    osis = ABBR[slug][1]
    if osis:
        root = wlc_book(osis, cache)
        lines = hebrew_chapter(root, osis, n)
        if lines is None:
            sys.exit("chapter %d not found in %s.xml" % (n, osis))
        open(os.path.join(out, "hebrew.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
        for name, m in (("hebrew-prev.txt", n - 1), ("hebrew-next.txt", n + 1)):
            other = hebrew_chapter(root, osis, m) if m >= 1 else None
            p = os.path.join(out, name)
            if other:
                open(p, "w", encoding="utf-8").write("\n".join(other) + "\n")
            elif os.path.exists(p):
                os.remove(p)
        want = b["verses"][n - 1]
        if len(lines) != want:
            notes.append("The Hebrew chapter has %d verses and the English numbering %d: the numbering"
                         " differs here (see hebrew-prev.txt / hebrew-next.txt), so say so once in the"
                         " `numbering:` line, as TRANSLATION_RULES.md asks." % (len(lines), want))
        lang = "Hebrew"
        source = ("The Masoretic Text of %s %d (Westminster Leningrad Codex), one verse per line, is at\n"
                  "`%s`\n`[K: ...]` is the written text (Ketiv) and `[Q: ...]` the read text (Qere) after"
                  " it; `{S}` and `{P}` mark the Hebrew text's own paragraph breaks. The chapters on"
                  " either side are beside it (`hebrew-prev.txt`, `hebrew-next.txt`) for continuity"
                  " only: translate only %s %d. These files are never committed; do not copy them into"
                  " the repository. Where the text is Aramaic (parts of Daniel and Ezra), translate"
                  " from the Aramaic." % (b["name"], n, os.path.join(out, "hebrew.txt"), b["name"], n))
    else:
        lang = "Greek"
        source = ("The Greek text of %s %d is at `%s` (one verse per line). Translate only %s %d; the"
                  " file is never committed." % (b["name"], n, os.path.join(out, "greek.txt"), b["name"], n))
        notes.append("New Testament: this script does not fetch Greek yet. The thread must put the Greek"
                     " text at %s before starting the translator." % os.path.join(out, "greek.txt"))

    gpath = os.path.join(out, "glossary.md")
    open(gpath, "w", encoding="utf-8").write(glossary_extract(slug, n))
    if not any(os.path.exists(chapter_path(slug, m)) for m in range(1, b["chapters"] + 1)):
        notes.append("This is the first chapter of %s to be translated, so the glossary has no %s section"
                     " yet: search GLOSSARY.md for every recurring word and name before you settle it."
                     % (b["name"], b["name"]))

    prev = previous_chapter(slug, n)
    if prev:
        ps, pn = prev
        prev_line = "`%s` (%s %d, the chapter before this one, for continuity of wording)" % (
            chapter_path(ps, pn), BY_SLUG[ps]["name"], pn)
        pnotes = chapter_path(ps, pn, "notes")
        if os.path.exists(pnotes):
            prev_line += ", and its notes `%s`, which end with what this chapter must keep the same" % pnotes
        plog = chapter_path(ps, pn, "decisions")
        if os.path.exists(plog):
            prev_line += ", and its decision log `%s`, a model of the format" % plog
    else:
        prev_line = "(no earlier chapter is translated)"

    tpl = open(os.path.join(ROOT, "scripts", "translator_brief.md"), encoding="utf-8").read()
    brief = tpl.format(book=b["name"], chapter=n, slug=slug, nnn=nnn, verses=b["verses"][n - 1],
                       language=lang, repo=ROOT, glossary=gpath, previous=prev_line, source=source,
                       next=next_label(slug, n), notes="\n".join("- " + x for x in notes) or "- none")
    bpath = os.path.join(out, "brief.md")
    open(bpath, "w", encoding="utf-8").write(brief)

    size = lambda p: "%d KB" % (os.path.getsize(p) // 1024) if os.path.exists(p) else "missing"
    print("brief     %s (%s)" % (bpath, size(bpath)))
    print("glossary  %s (%s, GLOSSARY.md is %s)" % (gpath, size(gpath), size(os.path.join(ROOT, "GLOSSARY.md"))))
    print("source    %s" % os.path.join(out, "hebrew.txt" if osis else "greek.txt"))
    for x in notes:
        print("NOTE      " + x)


if __name__ == "__main__":
    main()
