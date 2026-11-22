#!/usr/bin/env python3
"""Work out when each word of a chapter is spoken in its recording, for Listen + Read mode.

For every recording listed in data/audio.json (fetched from R2 when not on disk) that has no up-to-date site/audio/<slug>/<n>.json, this
listens to the recording with an offline speech recognizer, matches what it heard against the
chapter's read-aloud text (site/text/<slug>/<n>.txt) and writes the start time of every word:

    {"words": 812, "sum": "<checksum of the text>", "size": <bytes of the mp3>, "t": [0, 41, 78, ...]}

("t" is in hundredths of a second.) The same listening is used by scripts/tts.py to check every new
recording word for word before it is published: see problems() and check().

"words" counts the words exactly as scripts/build.py wraps them on a chapter page (build.words).
Words the recognizer missed (mostly unusual names) get a time estimated from the words on either
side, and a word that follows a pause is moved to the exact moment the voice starts again.

Needs ffmpeg plus `pip install sherpa-onnx numpy`. The speech model (about 300 MB) is downloaded
once into ALIGN_MODEL_DIR (default ~/.cache/bible-align).

    python3 scripts/build.py && python3 scripts/align.py && python3 scripts/build.py
    python3 scripts/align.py --force genesis-1     # redo one chapter
    python3 scripts/align.py --pending             # only print how many chapters need timing
"""
import difflib
import json
import os
import re
import subprocess
import sys
import tarfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import checksum, words as display_words  # noqa: E402  (the same word rule as the pages)
import media  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = media.SITE   # site/, or site-quran/ with WORK=quran
MODEL = "sherpa-onnx-zipformer-en-2023-06-26"
MODEL_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/%s.tar.bz2" % MODEL
MODEL_DIR = os.environ.get("ALIGN_MODEL_DIR", os.path.expanduser("~/.cache/bible-align"))
RATE = 16000
MAX_PIECE = 22.0    # seconds of audio handed to the recognizer at once

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen " \
       "sixteen seventeen eighteen nineteen".split()
TENS = "x x twenty thirty forty fifty sixty seventy eighty ninety".split()


def spoken_number(n):
    if n < 20:
        return [ONES[n]]
    if n < 100:
        return [TENS[n // 10]] + ([ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [ONES[n // 100], "hundred"] + (spoken_number(n % 100) if n % 100 else [])
    return [c for d in str(n) for c in [ONES[int(d)]]]


def sound_words(word):
    """How one written word is heard, as lower-case recognizer-style words."""
    out = []
    for part in re.split(r"[^0-9A-Za-z'’]+", word.replace("’", "'")):
        part = part.strip("'").lower()
        if not part:
            continue
        if part.isdigit():
            out.extend(spoken_number(int(part)))
        else:
            out.append(part)
    return out or [word.lower()]


def model_files():
    d = os.path.join(MODEL_DIR, MODEL)
    if not os.path.exists(os.path.join(d, "tokens.txt")):
        os.makedirs(MODEL_DIR, exist_ok=True)
        tar = os.path.join(MODEL_DIR, MODEL + ".tar.bz2")
        print("Downloading the speech model ...", flush=True)
        urllib.request.urlretrieve(MODEL_URL, tar)
        with tarfile.open(tar) as t:
            t.extractall(MODEL_DIR)
        os.remove(tar)
    return d


def recognizer():
    import sherpa_onnx
    d = model_files()
    return sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=os.path.join(d, "encoder-epoch-99-avg-1.int8.onnx"),
        decoder=os.path.join(d, "decoder-epoch-99-avg-1.onnx"),
        joiner=os.path.join(d, "joiner-epoch-99-avg-1.int8.onnx"),
        tokens=os.path.join(d, "tokens.txt"),
        num_threads=os.cpu_count() or 2, decoding_method="greedy_search")


def load(mp3):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp3, "-f", "s16le", "-ar", str(RATE),
                          "-ac", "1", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def pauses(samples):
    """Pauses of at least 160 ms as (first quiet frame, first frame after it), in 20 ms frames."""
    import numpy as np
    hop = RATE // 50
    n = len(samples) // hop
    if n == 0:
        return [], 0
    level = np.sqrt((samples[:n * hop].reshape(n, hop) ** 2).mean(axis=1))
    quiet = level < max(0.004, float(np.percentile(level, 90)) * 0.04)
    found, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if j - i >= 8:
                found.append((i, j))
            i = j
        else:
            i += 1
    return found, n


def pieces(samples):
    """Cut the recording at pauses into pieces short enough for the recognizer: [(start, end)] in samples."""
    hop = RATE // 50                                    # 20 ms
    found, n = pauses(samples)
    if n == 0:
        return []
    cuts = [((i + j) // 2, j - i) for i, j in found]    # (frame at the middle of a pause, pause length)
    out, start, limit = [], 0, int(MAX_PIECE * 50)
    while n - start > limit:
        inside = [c for c in cuts if start + 150 < c[0] <= start + limit]
        if inside:
            # the longest pause in the later part of the window
            late = [c for c in inside if c[0] > start + limit // 2] or inside
            cut = max(late, key=lambda c: c[1])[0]
        else:
            cut = start + limit
        out.append((start * hop, cut * hop))
        start = cut
    out.append((start * hop, len(samples)))
    return out


def hear(rec, samples):
    """[(word, start seconds)] for everything the recognizer heard."""
    heard = []
    for a, b in pieces(samples):
        s = rec.create_stream()
        s.accept_waveform(RATE, samples[a:b])
        rec.decode_stream(s)
        r = s.result
        word, t0 = "", 0.0
        for tok, t in zip(r.tokens, r.timestamps):
            if tok.startswith("▁") or tok.startswith(" "):
                if word:
                    heard.append((word.lower(), t0))
                word, t0 = tok[1:], a / RATE + t
            else:
                if not word:
                    t0 = a / RATE + t
                word += tok
        if word:
            heard.append((word.lower(), t0))
    return [(re.sub(r"[^a-z0-9']", "", w), t) for w, t in heard if re.sub(r"[^a-z0-9']", "", w)]


def align(text, heard, length):
    """Start time (seconds) of every display word, plus the share of sounds matched directly."""
    shown = display_words(text)
    ref, owner = [], []                                 # sounds, and the display word each belongs to
    for k, w in enumerate(shown):
        for s in sound_words(w):
            ref.append(s)
            owner.append(k)
    hyp = [w for w, _ in heard]
    times = [None] * len(ref)
    sm = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)
    matched = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for d in range(i2 - i1):
                times[i1 + d] = heard[j1 + d][1]
            matched += i2 - i1
        elif tag == "replace" and i2 - i1 == j2 - j1:   # misheard words, one for one
            for d in range(i2 - i1):
                times[i1 + d] = heard[j1 + d][1]
    # fill the rest by spreading them between known neighbours, longer words taking longer
    i = 0
    while i < len(ref):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(ref) and times[j] is None:
            j += 1
        lo = times[i - 1] if i else 0.0
        hi = times[j] if j < len(ref) else length
        span = ref[i - 1:j] if i else ref[i:j]
        weights = [len(w) + 2 for w in span]
        total, run = float(sum(weights)), 0.0
        for k, w in enumerate(weights):
            idx = (i - 1 if i else i) + k
            if times[idx] is None:
                times[idx] = lo + (hi - lo) * run / total
            run += w
        i = j
    out, last = [None] * len(shown), 0.0
    for idx, k in enumerate(owner):
        if out[k] is None:
            last = max(last, times[idx])                # never step backwards
            out[k] = last
    return out, (matched / float(len(ref)) if ref else 0.0)


def problems(text, heard):
    """Places where the recording does not say what the text says: speech that is not in the
    chapter (the voice sometimes invents or repeats lines), or text that was skipped.
    Single misheard words and unusual names are ignored; only runs of 5 or more words count."""
    ref = [s for w in display_words(text) for s in sound_words(w)]
    hyp = [w for w, _ in heard]
    found = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ref, hyp, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        extra, missing = (j2 - j1) - (i2 - i1), (i2 - i1) - (j2 - j1)
        at = heard[min(j1, len(heard) - 1)][1] if heard else 0.0
        if extra >= 5:
            found.append("at %d:%02d the voice says words that are not in the chapter: \"%s\""
                         % (at // 60, at % 60, " ".join(hyp[j1:j2])[:160]))
        elif missing >= 5:
            found.append("at %d:%02d the voice skips: \"%s\"" % (at // 60, at % 60, " ".join(ref[i1:i2])[:160]))
    return found


def check(mp3, text, rec=None):
    """Problems found in one recording (an empty list means it matches the text)."""
    return problems(text, hear(rec or recognizer(), load(mp3)))


def snap(times, samples):
    """Move the word nearest the end of each pause onto the moment the voice starts again."""
    found, n = pauses(samples)
    out = list(times)
    for i, j in found:
        if j - i < 12 or j >= n:                        # only clear pauses (240 ms or more)
            continue
        onset = j / 50.0 - 0.02
        k = min(range(len(out)), key=lambda x: abs(out[x] - onset))
        if abs(out[k] - onset) <= 0.3 and (k == 0 or out[k - 1] < onset) and (k + 1 == len(out) or out[k + 1] > onset):
            out[k] = onset
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    manifest = json.load(open(os.path.join(SITE, "manifest.json"), encoding="utf-8"))
    listed = media.index()
    todo = []
    for c in manifest:
        if not c.get("audio") or (args and c["id"] not in args):
            continue
        text = open(os.path.join(SITE, c["text"]), encoding="utf-8").read()
        out = os.path.join(SITE, c["audio"][:-4] + ".json")
        if not force and os.path.exists(out):
            try:
                old = json.load(open(out))
                if old.get("sum") == checksum(text) and old.get("size") == listed.get(c["audio"], [None])[0]:
                    continue
            except ValueError:
                pass
        todo.append((c, text, out))
    if "--pending" in sys.argv:
        print(len(todo))
        return
    if not todo:
        print("Word timings are up to date.")
        return
    rec = recognizer()
    for c, text, out in todo:
        mp3 = media.local(c["audio"])
        samples = load(mp3)
        length = len(samples) / float(RATE)
        heard = hear(rec, samples)
        for p in problems(text, heard):
            print("CHECK %s %d: %s" % (c["book"], c["chapter"], p), flush=True)
        times, share = align(text, heard, length)
        times = snap(times, samples)
        if share < 0.5:
            # the recording does not match this text (for example the chapter was reworded later)
            print("Skipped %s %d: only %d%% of the words were found in the recording."
                  % (c["book"], c["chapter"], share * 100), flush=True)
            if os.path.exists(out):
                os.remove(out)
            continue
        json.dump({"words": len(times), "sum": checksum(text), "size": os.path.getsize(mp3),
                   "t": [int(round(t * 100)) for t in times]},
                  open(out, "w"), separators=(",", ":"))
        print("Timed %s %d: %d words, %d%% heard directly -> %s"
              % (c["book"], c["chapter"], len(times), share * 100, os.path.relpath(out, ROOT)), flush=True)


if __name__ == "__main__":
    main()
