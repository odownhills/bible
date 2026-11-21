#!/usr/bin/env python3
"""Check one chapter file before publishing: python3 scripts/check.py translations/genesis/001.md
Verifies front matter, every verse present once and in order (standard English numbering),
no Hebrew/Greek script, balanced brackets, no banned archaic words, and that the chapter's
decision log (decisions/<slug>/<NNN>.md) has one well-formed entry for every [alt: ...]."""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from build import parse, BY_SLUG

BANNED = ["behold", "thee", "thy", "thou", "thine", "hearken", "iniquity", "begat", "lo", "verily", "hath", "doth", "unto", "ye"]

SCRIPT = r"[\u0590-\u05ff\u0370-\u03ff\u1f00-\u1fff]"
KINDS = ("copies differ", "grammar", "two senses", "both meant")
CALLS = ("clear", "close", "ask")
FIELDS = ("kind", "call", "why", "other", "review")
# Chapters published before the decision log existed (2026-11-21). Obay decided not to redo them,
# so they need no log: book slug -> last chapter published under the old rules.
BEFORE_LOG = {"genesis": 5, "1-john": 5, "john": 6, "jude": 1}


def check_log(slug, n, blocks, errs):
    """Every [alt: ...] needs an entry in the decision log (format: TRANSLATION_RULES.md)."""
    want = {}
    for k, v in blocks:
        for ref, t in (v if k == "p" else [("title", v)] if k == "t" else []):
            c = len(re.findall(r"\[alt:", t, flags=re.I))
            if c:
                want[str(ref)] = want.get(str(ref), 0) + c
    rel = "decisions/%s/%03d.md" % (slug, n)
    log = os.path.join(ROOT, rel)
    if not os.path.exists(log):
        if want and n > BEFORE_LOG.get(slug, 0):
            errs.append("%s is missing: it needs one entry for each of the %d [alt: ...] in the chapter"
                        % (rel, sum(want.values())))
        return
    raw = open(log, encoding="utf-8").read()
    if re.search(SCRIPT, raw):
        errs.append(rel + " contains Hebrew or Greek script")
    got, asks, entry = {}, 0, None

    def close(e):
        if e:
            for f in FIELDS:
                if not e["f"].get(f):
                    errs.append("%s, entry %s: missing '%s:' line" % (rel, e["ref"], f))

    for line in raw.split("---", 2)[-1].splitlines():
        s = line.strip()
        if s.startswith("## "):
            close(entry)
            m = re.match(r"^## (\d+):(\d+|title)\s+\S.*\s\|\s+\S", s)
            if not m:
                errs.append("%s: heading should be '## <chapter>:<verse> <main wording> | <alternate wording>': %s" % (rel, s))
                entry = None
                continue
            if int(m.group(1)) != n:
                errs.append("%s: entry %s:%s is for another chapter" % (rel, m.group(1), m.group(2)))
            entry = {"ref": "%s:%s" % (m.group(1), m.group(2)), "f": {}}
            got[m.group(2)] = got.get(m.group(2), 0) + 1
        elif entry and ":" in s:
            k, v = s.split(":", 1)
            k, v = k.strip().lower(), v.strip()
            if k in FIELDS:
                entry["f"][k] = v
                if k == "kind" and v not in KINDS:
                    errs.append("%s, entry %s: kind must be one of: %s" % (rel, entry["ref"], ", ".join(KINDS)))
                if k == "call":
                    if v not in CALLS:
                        errs.append("%s, entry %s: call must be one of: %s" % (rel, entry["ref"], ", ".join(CALLS)))
                    asks += v == "ask"
                if k == "review" and not re.match(r"^(open$|kept by Obay |switched by Obay )", v):
                    errs.append("%s, entry %s: review must be 'open' unless Obay has reviewed it" % (rel, entry["ref"]))
    close(entry)
    if asks > 3:
        errs.append("%s: %d entries are marked 'call: ask'; at most three in a chapter" % (rel, asks))
    for ref in sorted(set(want) | set(got), key=lambda r: (r != "title", int(r) if r.isdigit() else 0)):
        if want.get(ref, 0) != got.get(ref, 0):
            errs.append("%s: verse %s has %d [alt: ...] in the chapter but %d entries in the log"
                        % (rel, ref, want.get(ref, 0), got.get(ref, 0)))


def main(path):
    errs = []
    slug = os.path.basename(os.path.dirname(path))
    n = int(os.path.basename(path)[:3])
    b = BY_SLUG.get(slug)
    if not b:
        raise SystemExit("Unknown book folder: " + slug)
    meta, blocks = parse(path)
    if meta.get("book") != b["name"]: errs.append("front matter book should be %r" % b["name"])
    if meta.get("chapter") != str(n): errs.append("front matter chapter should be %d" % n)
    nums = [vn for k, v in blocks if k == "p" for vn, _ in v]
    want = list(range(1, b["verses"][n - 1] + 1))
    if nums != want:
        missing = sorted(set(want) - set(nums)); extra = sorted(set(nums) - set(want))
        errs.append("verse numbers wrong: expected 1-%d; missing %s; extra %s; order ok=%s"
                    % (want[-1], missing, extra, nums == sorted(set(nums))))
    text = open(path, encoding="utf-8").read()
    if re.search(r"[֐-׿Ͱ-Ͽἀ-῿]", text): errs.append("contains Hebrew or Greek script")
    if text.count("[") != text.count("]"): errs.append("unbalanced brackets")
    if not any(k == "h" for k, _ in blocks): errs.append("no section headings")
    body = re.sub(r"\[[^\]]*\]", "", text.split("---", 2)[2]).lower()
    hits = sorted({w for w in BANNED if re.search(r"\b%s\b" % w, body)})
    if hits: errs.append("archaic words found: " + ", ".join(hits))
    check_log(slug, n, blocks, errs)
    if errs:
        print("FAIL " + path); [print("  - " + e) for e in errs]; sys.exit(1)
    print("OK %s (%d verses)" % (path, len(nums)))

if __name__ == "__main__":
    main(sys.argv[1])
