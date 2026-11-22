#!/usr/bin/env python3
"""Fetch a human reciter's recitation of each surah for the Quran site's Arabic pages (scripts/quran_ar.py),
with the time at which every word is recited, for Listen + Read and TV mode.

Nothing here is generated: the voice is the reciter's own recording (RECITER in scripts/quran_ar.py, from
everyayah.com, which keeps one recording per verse). For each surah that has no recording yet, in order:

  1. download the reciter's recording of each verse; for a surah that opens with "In the name of God..."
     apart from its verses (all but surahs 1 and 9), also the reciter's recording of 1:1, which is those words;
  2. join them into one recording of the surah (64 kbps mono mp3), noting exactly where each verse starts;
  3. time each word: within its verse, by the word timings the quran-align project published for this
     reciter's verse recordings (github.com/cpfair/quran-align, CC BY 4.0), when they fit the verse's words;
     otherwise spread over the verse by the length of each word, so a word lights up within its own verse;
  4. upload the recording to the R2 bucket as audio/ar/<n>.mp3 (scripts/media.py), list it in
     data/audio.json, and write site-quran/audio/ar/<n>.json:
     {"sum": fingerprint of the words, "words": how many, "t": [start of each word, hundredths of a second],
      "verses": [[verse, start], ...], "timed": {"aligned": words timed by quran-align, "spread": the rest}}

    python3 scripts/recite.py --max 5 --minutes 40   # record up to 5 surahs, starting none after 40 minutes
    python3 scripts/recite.py publish                # commit and push what was recorded (GitHub Action)

Needs ffmpeg and the R2 secrets (see scripts/media.py). The GitHub Action .github/workflows/recitation.yml
runs it until all 114 surahs are recorded. To record a surah again, remove its line from data/audio.json.
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["WORK"] = "quran"
import media      # noqa: E402
import quran_ar   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site-quran")
FOLDER = "Husary_128kbps"            # the reciter's folder on everyayah.com (Mahmoud Khalil al-Husary, murattal)
VERSE_URL = "https://everyayah.com/data/%s/%03d%03d.mp3"
ALIGN_RELEASES = "https://api.github.com/repos/cpfair/quran-align/releases"
RATE = 44100
AGENT = {"User-Agent": "quran-site-build (github.com/odownhills/bible)"}

# One spoken word: the same rule as scripts/build.py (a run with no space that holds a letter or digit)
WORD = re.compile(r"[^\s—–]*\w[^\s—–]*")


def words(text):
    return WORD.findall(text)


def checksum(text):
    import hashlib
    return hashlib.sha1(" ".join(words(text)).encode("utf-8")).hexdigest()[:12]


def fetch(url, tries=4, headers=None):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=dict(AGENT, **(headers or {})))
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:   # network hiccups: wait and try again
            last = e
            time.sleep(2 + 4 * k)
    raise SystemExit("Could not download %s: %s" % (url, last))


def alignments():
    """{(surah, verse): [[first word, word after the last, start ms, end ms], ...]} for FOLDER, from the
    quran-align release; {} when it cannot be found (the words are then spread over each verse)."""
    try:
        headers = {"Accept": "application/vnd.github+json"}
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
        releases = json.loads(fetch(ALIGN_RELEASES, headers=headers))
        assets = [a for r in releases for a in r.get("assets", [])]
        mine = [a for a in assets if FOLDER.lower() in a["name"].lower()]
        data = None
        for a in mine or [a for a in assets if a["name"].lower().endswith(".zip")]:
            blob = fetch(a["browser_download_url"])
            if a["name"].lower().endswith(".zip"):
                z = zipfile.ZipFile(io.BytesIO(blob))
                names = [n for n in z.namelist() if FOLDER.lower() in n.lower() and n.lower().endswith(".json")]
                if names:
                    data = json.loads(z.read(names[0]))
                    print("Word timings: %s from %s" % (names[0], a["name"]))
                    break
            else:
                data = json.loads(blob)
                print("Word timings: %s" % a["name"])
                break
        if data is None:
            print("::warning::No quran-align word timings found for %s; words are spread over each verse." % FOLDER)
            return {}
        out = {}
        for e in data:
            segs = [s for s in (e.get("segments") or []) if isinstance(s, list) and len(s) >= 4]
            out[(int(e["surah"]), int(e["ayah"]))] = segs
        return out
    except SystemExit as e:
        print("::warning::%s; words are spread over each verse." % e)
        return {}
    except Exception as e:   # a changed format must not stop the recordings
        print("::warning::Could not read the quran-align word timings (%s); words are spread over each verse." % e)
        return {}


def letters(w):
    return max(1, len(re.findall(r"\w", w)))


def spread(ws, start, end):
    """Start times for words spread over [start, end] by their length."""
    total = sum(letters(w) for w in ws)
    out, run = [], 0
    for w in ws:
        out.append(start + (end - start) * run / total)
        run += letters(w)
    return out


def verse_times(ws, segs, start, length):
    """Start time (seconds into the surah) of each word of one verse whose recording starts at `start` and
    lasts `length` seconds. Returns (times, True when quran-align's timings were used)."""
    n = len(ws)
    known = [None] * n
    if segs and max(s[1] for s in segs) == n and min(s[0] for s in segs) >= 0:
        for a, b, t0, t1 in (s[:4] for s in segs):
            if 0 <= a < b <= n and 0 <= t0 < t1 <= length * 1000 + 500:
                part = spread(ws[a:b], t0 / 1000.0, t1 / 1000.0)
                for k, t in zip(range(a, b), part):
                    if known[k] is None:
                        known[k] = t
    if sum(1 for t in known if t is not None) >= max(1, n // 2) and all(
            known[k] is None or known[k + 1] is None or known[k] <= known[k + 1] for k in range(n - 1)):
        # a word the timings missed: spread it, with the word before it, up to the next timed word
        k = 0
        while k < n:
            if known[k] is not None:
                k += 1
                continue
            hi = k
            while hi < n and known[hi] is None:
                hi += 1
            end = known[hi] if hi < n else max((known[k - 1] if k else 0) + 0.3 * (hi - k), length - 0.4)
            if k:
                part = spread(ws[k - 1:hi], known[k - 1], end)[1:]
            else:
                part = spread(ws[:hi], min(0.1, end), end)
            for j, t in zip(range(k, hi), part):
                known[j] = t
            k = hi
        return [start + t for t in known], True
    # no usable timings: the reciter's pause at each end of a verse recording is about a third of a second
    return [start + t for t in spread(ws, min(0.3, length * 0.05), max(0.35, length - 0.45))], False


def decode(path, out):
    """Append a recording to the raw sample file `out`; returns its length in samples."""
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    out.write(pcm)
    return len(pcm) // 2


def record(n, aligned, work):
    """Make the recording of surah n and its word times. Returns (mp3 path, timing dict)."""
    opening, verses = quran_ar.surah(n)
    pieces = ([(0, (1, 1), opening)] if opening else []) + [(v, (n, v), ws) for v, ws in verses]
    raw = os.path.join(work, "%d.raw" % n)
    times, starts, at, used, spread_n = [], [], 0, 0, 0
    with open(raw, "wb") as out:
        for v, (s, a), ws in pieces:
            src = os.path.join(work, "%03d%03d.mp3" % (s, a))
            if not os.path.exists(src):
                open(src, "wb").write(fetch(VERSE_URL % (FOLDER, s, a)))
            length = decode(src, out)
            secs = length / float(RATE)
            t, ok = verse_times(ws, aligned.get((s, a)), at / float(RATE), secs)
            times += t
            if ok:
                used += len(ws)
            else:
                spread_n += len(ws)
            if v:
                starts.append([v, int(round(at * 100.0 / RATE))])
            at += length
    mp3 = os.path.join(work, "%d.mp3" % n)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", raw,
                    "-c:a", "libmp3lame", "-b:a", "64k", mp3], check=True)
    os.remove(raw)
    spoken = quran_ar.recited(n)
    if len(times) != len(words(spoken)):
        raise SystemExit("Surah %d: %d word times for %d words" % (n, len(times), len(words(spoken))))
    cs = [int(round(t * 100)) for t in times]
    for k in range(1, len(cs)):   # never backwards
        cs[k] = max(cs[k], cs[k - 1])
    return mp3, {"sum": checksum(spoken), "words": len(cs), "t": cs, "verses": starts,
                 "reciter": quran_ar.RECITER, "source": "everyayah.com/data/" + FOLDER,
                 "timed": {"aligned": used, "spread": spread_n}}


def todo():
    listed = media.index()
    return [s["n"] for s in quran_ar.SURAHS if "audio/ar/%d.mp3" % s["n"] not in listed]


def main(limit, minutes):
    if not media.configured():
        raise SystemExit("The R2 secrets are missing (see scripts/media.py).")
    left = todo()
    if not left:
        print("All 114 surahs have a recitation.")
        return
    began, aligned = time.time(), alignments()
    print("%d surahs still need a recitation; %d word timings loaded." % (len(left), len(aligned)))
    with tempfile.TemporaryDirectory() as work:
        for k, n in enumerate(left[:limit]):
            if k and time.time() - began > minutes * 60:
                print("Time is up for this run; the next run carries on from surah %d." % n)
                break
            mp3, timing = record(n, aligned, work)
            rel = "audio/ar/%d.mp3" % n
            media.publish(mp3, rel)
            os.makedirs(os.path.join(SITE, "audio", "ar"), exist_ok=True)
            json.dump(timing, open(os.path.join(SITE, "audio", "ar", "%d.json" % n), "w"), separators=(",", ":"))
            print("Surah %d: %s, %d words (%d timed by quran-align, %d spread over their verse)" % (
                n, time.strftime("%H:%M:%S", time.gmtime(media.index()[rel][1] or 0)), timing["words"],
                timing["timed"]["aligned"], timing["timed"]["spread"]), flush=True)
            for f in os.listdir(work):
                os.remove(os.path.join(work, f))


def git(*args, check=True):
    return subprocess.run(["git"] + list(args), cwd=ROOT, check=check, capture_output=True, text=True)


def publish():
    """Commit the new recordings' listing and word times on main and push, starting again from the newest
    main when another run pushed first (the voice recordings for the Bible push to main too)."""
    mine = {k: v for k, v in media.index().items() if k.startswith("audio/ar/")}
    folder = os.path.join(SITE, "audio", "ar")
    timings = {f: open(os.path.join(folder, f), encoding="utf-8").read()
               for f in (os.listdir(folder) if os.path.isdir(folder) else []) if f.endswith(".json")}
    for attempt in range(5):
        git("fetch", "--quiet", "origin", "main")
        git("reset", "--quiet", "--hard", "origin/main")
        idx = media.index()
        new = sorted(int(k.split("/")[-1][:-4]) for k in mine if k not in idx)
        idx.update(mine)
        media.save_index(idx)
        os.makedirs(folder, exist_ok=True)
        for f, text in timings.items():
            open(os.path.join(folder, f), "w", encoding="utf-8").write(text)
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build.py")], cwd=ROOT, check=True,
                       env=dict(os.environ, WORK="quran"))
        git("add", "-A", "data/audio.json", "site-quran")
        if any(p.endswith(".mp3") for p in git("diff", "--cached", "--name-only").stdout.split()):
            raise SystemExit("A recording is about to be committed to git.")
        if git("diff", "--cached", "--quiet", check=False).returncode == 0:
            print("Nothing new to publish.")
            return
        what = ("surah %d" % new[0]) if len(new) == 1 else ("surahs %d to %d" % (new[0], new[-1])) if new else "word times"
        git("commit", "--quiet", "-m", "Add Arabic recitation: " + what)
        if git("push", "--quiet", "origin", "HEAD:main", check=False).returncode == 0:
            print("Published " + what)
            return
        print("Main moved on; trying again.")
        time.sleep(5 + 10 * attempt)
    raise SystemExit("Could not push to main after 5 tries.")


if __name__ == "__main__":
    if sys.argv[1:2] == ["publish"]:
        publish()
    else:
        args = sys.argv[1:]
        opt = lambda name, default: int(args[args.index(name) + 1]) if name in args else default
        main(opt("--max", 114), opt("--minutes", 40))
