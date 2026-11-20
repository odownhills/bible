#!/usr/bin/env python3
"""Plan tonight's chapters.

Prints one line per chapter to translate tonight, in order: `<slug> <n> <Book> <estimated words>`.
Whole chapters are added, in canonical order, until the estimated total reaches the nightly
target in data/settings.json ("words_per_night": [low, high]); the plan stops at the chapter
that lands in or just past that range. Estimates are the chapter's word count in a standard
English Bible. Prints DONE when all 1,189 chapters exist.

    python3 scripts/next.py          # tonight's plan
    python3 scripts/next.py --one    # only the next chapter
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
low, high = json.load(open(os.path.join(ROOT, "data", "settings.json")))["words_per_night"]
total, plan = 0, []
for b in json.load(open(os.path.join(ROOT, "data", "books.json"))):
    for n in range(1, b["chapters"] + 1):
        if os.path.exists(os.path.join(ROOT, "translations", b["slug"], "%03d.md" % n)):
            continue
        w = b["words"][n - 1]
        # stop before a chapter that would overshoot the range, unless we are still under it
        if plan and total >= low:
            break
        if plan and total + w > high and (high - total) < (total + w - high) and total >= low * 0.75:
            break
        plan.append((b["slug"], n, b["name"], w))
        total += w
        if "--one" in sys.argv:
            break
    else:
        continue
    break
if not plan:
    print("DONE")
for p in plan:
    print(*p)
