#!/usr/bin/env python3
"""Check one chapter file before publishing: python3 scripts/check.py translations/genesis/001.md
Verifies front matter, every verse present once and in order (standard English numbering),
no Hebrew/Greek script, balanced brackets, and no banned archaic words."""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from build import parse, BY_SLUG

BANNED = ["behold", "thee", "thy", "thou", "thine", "hearken", "iniquity", "begat", "lo", "verily", "hath", "doth", "unto", "ye"]

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
    if errs:
        print("FAIL " + path); [print("  - " + e) for e in errs]; sys.exit(1)
    print("OK %s (%d verses)" % (path, len(nums)))

if __name__ == "__main__":
    main(sys.argv[1])
