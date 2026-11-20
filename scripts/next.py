#!/usr/bin/env python3
"""Plan this run's chapters.

Prints one line per chapter to translate in this run, in order:
`<slug> <n> <Book> <estimated words>`.

The pace is set in data/settings.json:
    "words_per_week": how many words to translate per week (Obay's setting)
    "runs_per_day":   how many scheduled runs share each day's words
Each run's target is words_per_week / 7 / runs_per_day. Whole chapters are added in canonical
order, stopping at whichever chapter boundary lands closest to the target (always at least one
chapter). Estimates are each chapter's word count in a standard English Bible.
Prints DONE when all 1,189 chapters exist.

    python3 scripts/next.py          # this run's plan
    python3 scripts/next.py --one    # only the next chapter
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(os.path.join(ROOT, "data", "settings.json")))
target = cfg["words_per_week"] / 7 / cfg.get("runs_per_day", 1)
todo = [(b["slug"], n, b["name"], b["words"][n - 1])
        for b in json.load(open(os.path.join(ROOT, "data", "books.json")))
        for n in range(1, b["chapters"] + 1)
        if not os.path.exists(os.path.join(ROOT, "translations", b["slug"], "%03d.md" % n))]
plan, total = [], 0
for ch in todo:
    if plan and ("--one" in sys.argv or abs(total + ch[3] - target) >= abs(total - target)):
        break
    plan.append(ch)
    total += ch[3]
if not plan:
    print("DONE")
for p in plan:
    print(*p)
