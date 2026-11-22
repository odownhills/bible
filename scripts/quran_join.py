#!/usr/bin/env python3
"""Join each surah's recorded English parts into one recording, for the surah's page on the Quran site.

The translation is made and recorded part by part (scripts/tts.py records audio/quran-<surah>/<part>.mp3,
and scripts/align.py times its words), and every part's recording opens with a spoken line naming the
part ("Quran, surah 2, verses 30 to 61."). The site shows a surah as one page (scripts/quran_site.py), so
this joins the parts' recordings, in order and without those opening lines, into one recording:
audio/en/<surah>.mp3 in the R2 bucket (scripts/media.py, listed in data/audio.json), and writes the start
of every word in it, site-quran/audio/en/<surah>.json:

    {"sum": fingerprint of the words, "words": how many, "t": [start of each word, hundredths of a second],
     "parts": [[part, fingerprint of that part's words and recording], ...]}

A surah's recording holds its parts from the first one on, up to the first part that has no recording or
no word times yet. When a part is added or recorded again, the surah's recording is made again.
Run it after scripts/align.py, with the site built (the GitHub Action .github/workflows/audio.yml does):

    WORK=quran python3 scripts/build.py && WORK=quran python3 scripts/quran_join.py
"""
import json
import os
import subprocess
import sys
import tempfile

os.environ["WORK"] = "quran"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import media        # noqa: E402
import quran_site   # noqa: E402

SITE = media.SITE
RATE = 24000        # the voice recordings' own sample rate


def joined_parts(listed):
    """{surah: [(part, mp3 path in the site, its word times, words skipped at its start, fingerprint), ...]}
    for the parts that can be joined now, from the built site's per-part list (manifest.json)."""
    out = {}
    for c in json.load(open(os.path.join(SITE, "manifest.json"), encoding="utf-8")):
        surah, part = int(c["slug"].split("-")[1]), c["chapter"]
        run = out.setdefault(surah, [])
        if len(run) != part - 1 or (run and run[-1] is None):
            continue
        if not (c.get("audio") and c.get("sync")):
            run.append(None)   # a gap: no later part of this surah can be joined yet
            continue
        timing = json.load(open(os.path.join(SITE, c["sync"]), encoding="utf-8"))
        text = open(os.path.join(SITE, c["text"]), encoding="utf-8").read()
        skip = c.get("skip", 0)
        run.append((part, c["audio"], timing["t"], skip,
                    quran_site.fingerprint(text, skip, listed.get(c["audio"], [None])[0])))
    return {s: [p for p in run if p] for s, run in out.items() if any(run)}


def cut_at(t, skip):
    """Where a part's recording starts once its opening line is left out, in seconds."""
    if not skip:
        return 0.0
    first, before = t[skip] / 100.0, t[skip - 1] / 100.0
    return max(0.0, min(first - 0.05, max(before + 0.35, first - 0.3)))


def join(surah, parts, work):
    raw = os.path.join(work, "all.raw")
    times, at = [], 0
    with open(raw, "wb") as out:
        for part, rel, t, skip, _ in parts:
            src = media.local(rel)
            start = cut_at(t, skip)
            pcm = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % start, "-i", src, "-ac", "1", "-ar", str(RATE),
                                  "-f", "s16le", "-"], capture_output=True, check=True).stdout
            out.write(pcm)
            times += [int(round(at * 100.0 / RATE + x - start * 100)) for x in t[skip:]]
            at += len(pcm) // 2
    mp3 = os.path.join(work, "%d.mp3" % surah)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", raw,
                    "-c:a", "libmp3lame", "-b:a", "48k", mp3], check=True)
    for k in range(1, len(times)):
        times[k] = max(times[k], times[k - 1])
    return mp3, times


def main():
    listed = media.index()
    made = 0
    for surah, parts in sorted(joined_parts(listed).items()):
        rel = "audio/en/%d.mp3" % surah
        out = os.path.join(SITE, "audio", "en", "%d.json" % surah)
        want = [[p[0], p[4]] for p in parts]
        try:
            have = json.load(open(out, encoding="utf-8"))
            if have.get("parts") == want and rel in listed:
                continue
        except (OSError, ValueError):
            pass
        if not media.configured():
            raise SystemExit("The R2 secrets are missing (see scripts/media.py).")
        with tempfile.TemporaryDirectory() as work:
            mp3, times = join(surah, parts, work)
            media.publish(mp3, rel)
        words = [w for p in parts for w in quran_site.part_words(open(os.path.join(SITE, "text", "quran-%d" % surah,
                                                                                       "%d.txt" % p[0]), encoding="utf-8").read(), p[3])]
        if len(words) != len(times):
            raise SystemExit("Surah %d: %d word times for %d words" % (surah, len(times), len(words)))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump({"sum": quran_site.checksum(" ".join(words)), "words": len(times), "t": times, "parts": want},
                  open(out, "w", encoding="utf-8"), separators=(",", ":"))
        made += 1
        print("Surah %d: joined parts 1-%d into one recording" % (surah, len(parts)), flush=True)
    print("Joined %d surah recording%s." % (made, "" if made == 1 else "s"))


if __name__ == "__main__":
    main()
