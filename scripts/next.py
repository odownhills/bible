#!/usr/bin/env python3
"""Plan this run's chapters.

Prints one line per chapter to translate in this run, in order:
`<slug> <n> <Book> <estimated words>`.

The pace is set in data/settings.json:
    "words_per_week": how many words to translate per week (Obay's setting)
    "runs_per_week":  how many scheduled runs there are in a week
                      (4 each weekday + 1 each weekend day = 22)
    "first_books":    optional list of book slugs to translate before the rest, in that order
                      (Obay, 2026-11-20: 1 John, then John; 2026-11-21: Job first, then John;
                      2026-11-23 morning: Deuteronomy first, then back to Job where it stopped;
                      2026-11-23 afternoon: none, "start from beginning of Bible and continue in
                      order", so the list is empty and the next chapter is Genesis 6;
                      2026-11-27, with Genesis done: "Finish Job and then go back to Exodus and
                      continue forward", so the list is Job, and Exodus 1 follows Job 42)
Each run's target is words_per_week / runs_per_week. Whole chapters are added in canonical
order (after any "first_books"), stopping at whichever chapter boundary lands closest to the target (always at least one
chapter). Estimates are each chapter's word count in a standard English Bible.
Prints DONE when all 1,189 chapters exist.

    python3 scripts/next.py          # this run's plan
    python3 scripts/next.py --one    # only the next chapter
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(os.path.join(ROOT, "data", "settings.json")))
target = cfg["words_per_week"] / cfg["runs_per_week"]
books = json.load(open(os.path.join(ROOT, "data", "books.json")))
first = cfg.get("first_books", [])
books.sort(key=lambda b: first.index(b["slug"]) if b["slug"] in first else len(first))
todo = [(b["slug"], n, b["name"], b["words"][n - 1])
        for b in books
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
