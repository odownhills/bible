#!/usr/bin/env python3
"""Record the short spoken notices that Story only plays where it skips a family list (Obay, 2026-11-28):
"Skipping 6 verses of family names." and "Skipping Genesis chapter 36, a list of family names."

Story only (scripts/listen.html, scripts/tv.js) skips the family lists marked in data/family_lists.json, and
scripts/build.py lists in site/manifest.json the notice each skip needs, with the address it is kept at:
audio/notices/<its words>.mp3, in the Cloudflare R2 bucket like the chapters' recordings (scripts/media.py).
This records the ones that are missing, in the chapters' own voice (scripts/tts.py), all of them in one
request so that they cost a single request of Gemini's small free daily limit: the notices are read one after
another, the recording is cut at the pause between them, and each piece is checked word for word by the
listener (scripts/align.py) before it is kept. A notice that fails the check is tried again on the next run.
Until a notice is recorded, the players say it with the phone's own voice, or skip without a word.

Needs GEMINI_API_KEY, the R2 secrets, ffmpeg and `pip install sherpa-onnx numpy`. Run scripts/build.py before
(it says which notices are needed) and after (it lists the new ones in the manifest).

    python3 scripts/notices.py            # record the missing notices
    python3 scripts/notices.py --list     # only print which are missing
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import media  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
RATE = 24000          # Gemini's samples per second (scripts/tts.py)
GAP = "\n\n"          # between notices in the one request: the voice pauses there


def needed():
    """{site path of a notice: its words} for every notice the Bible's manifest asks for."""
    from build import notice_clip
    want = {}
    for c in json.load(open(os.path.join(SITE, "manifest.json"), encoding="utf-8")):
        for item in ([c["familyAll"]] if c.get("familyAll") else []) + (c.get("family") or []):
            want[notice_clip(item["say"])] = item["say"]
    return want


def mp3(pcm, path):
    with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as f:
        f.write(pcm)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", f.name,
                    "-codec:a", "libmp3lame", "-b:a", "48k", path], check=True)
    os.remove(f.name)


def trim(pcm, lead=0.08, tail=0.25):
    """Quiet at the start and the end of a notice, cut to a short breath."""
    import numpy as np
    a = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    hop = RATE // 100
    n = len(a) // hop
    if not n:
        return pcm
    level = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(axis=1))
    loud = np.nonzero(level > max(0.01, float(level.max()) * 0.05))[0]
    if not len(loud):
        return pcm
    s = max(0, loud[0] * hop - int(lead * RATE))
    e = min(len(a), (loud[-1] + 1) * hop + int(tail * RATE))
    return pcm[s * 2:e * 2]


def split(pcm, texts, rec):
    """Cut one recording of the notices read in order into one piece each, at the pause between them.
    Returns the pieces, or None when the recording does not say exactly the notices."""
    import align
    from build import words
    whole = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
    mp3(pcm, whole)
    samples = align.load(whole)
    os.remove(whole)
    text = " ".join(texts)
    heard = align.hear(rec, samples)
    trouble = align.problems(text, heard)
    times, share = align.align(text, heard, len(samples) / float(align.RATE))
    if trouble or share < 0.8:
        print("The notices' recording does not match their words (%d%% heard): %s" % (share * 100, "; ".join(trouble)))
        return None
    times = align.snap(times, samples)
    found, _ = align.pauses(samples)                    # (first quiet frame, frame after), 20 ms frames
    cuts, k = [0.0], 0
    for t in texts[:-1]:
        k += len(words(t))
        lo, hi = times[k - 1], times[k]                 # the last word of this notice, the first of the next
        inside = [(i, j) for i, j in found if lo < i / 50.0 and j / 50.0 <= hi + 0.05]
        if inside:
            i, j = max(inside, key=lambda p: p[1] - p[0])
            cuts.append((i + j) / 100.0)
        else:
            cuts.append(max(lo, hi - 0.05))
    cuts.append(len(pcm) / 2.0 / RATE)
    return [pcm[int(a * RATE) * 2:int(b * RATE) * 2] for a, b in zip(cuts, cuts[1:])]


def main():
    listed = media.index()
    todo = {k: v for k, v in sorted(needed().items()) if k not in listed}
    if "--list" in sys.argv:
        for k, v in todo.items():
            print(k, "-", v)
        print("%d notices to record." % len(todo))
        return
    if not todo:
        print("Every family-list notice is recorded.")
        return
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key or not media.configured():
        raise SystemExit("Needs GEMINI_API_KEY and the R2 secrets (see scripts/tts.py and scripts/media.py).")
    import align
    import tts
    try:
        rec = align.recognizer()
    except Exception as e:   # no listener: a notice that cannot be checked is not kept
        print("Notices not recorded: the listener is not installed (%s)." % e)
        return
    paths, texts = list(todo), list(todo.values())
    try:
        pcm = tts.speak(GAP.join(texts), key, {"model": 0})
    except tts.OutOfQuota:
        print("Gemini's free daily limit is used up; the notices will be recorded on the next run.")
        return
    pieces = split(pcm, texts, rec) if len(texts) > 1 else [pcm]
    if not pieces:
        return
    for rel, text, piece in zip(paths, texts, pieces):
        out = os.path.join(SITE, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        mp3(trim(piece), out)
        samples = align.load(out)
        heard = align.hear(rec, samples)
        _, share = align.align(text, heard, len(samples) / float(align.RATE))
        if align.problems(text, heard) or share < 0.8:
            print("Threw away the notice %r: it does not say exactly that (%d%% heard)." % (text, share * 100))
            os.remove(out)
            continue
        media.publish(out, rel)
        print("Recorded the notice %r -> %s" % (text, rel), flush=True)


if __name__ == "__main__":
    main()
