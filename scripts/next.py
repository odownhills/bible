#!/usr/bin/env python3
"""Print the next untranslated chapter in canonical order, e.g. `genesis 1 Genesis`.
Prints DONE when all 1,189 chapters exist."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for b in json.load(open(os.path.join(ROOT, "data", "books.json"))):
    for n in range(1, b["chapters"] + 1):
        if not os.path.exists(os.path.join(ROOT, "translations", b["slug"], "%03d.md" % n)):
            print(b["slug"], n, b["name"])
            raise SystemExit
print("DONE")
