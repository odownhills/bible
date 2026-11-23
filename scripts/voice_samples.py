#!/usr/bin/env python3
"""A trial, not part of the site: short samples of the Arabic read aloud in a plain speaking voice, for Obay
to listen to and choose from (2026-11-22). Reads Surah 1 and Surah 2:1-5 (with its opening line) with
Gemini's Sulafat (the English site's voice; Obay: "close to Sulafat") and, to compare, one OpenAI voice, uploads each sample to the R2 bucket as audio/samples/<name>.mp3, transcribes
each one back (to see that every word was read) and prints its pace.

    python3 scripts/voice_samples.py
Needs OPENAI_API_KEY, GEMINI_API_KEY, ffmpeg and the R2 secrets.
"""
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["WORK"] = "quran"
import media      # noqa: E402
import quran_ar   # noqa: E402

INSTRUCTIONS = ("Read the Arabic text aloud in a plain, natural, everyday speaking voice, the way a person "
                "reads a book aloud to a friend. Do not chant, sing or recite it, and use no melody and no "
                "drawn-out vowels. Keep an even, unhurried conversational pace. Say every word exactly as "
                "written, with all its vowels, and pause briefly at the end of each line.")
OPENAI_MODELS = ["gpt-4o-mini-tts"]
OPENAI_VOICES = ["marin"]
# (model, words said before the passage as a style instruction, or "")
GEMINI = [("gemini-3.8-flash-tts", ""), ("gemini-2.5-flash-preview-tts", ""), ("gemini-2.5-pro-preview-tts", ""),
          ("gemini-2.5-flash-preview-tts", "Read this aloud in a plain, natural speaking voice, not chanted: ")]


def passage():
    lines = []
    for n, upto in ((1, 7), (2, 5)):
        opening, verses = quran_ar.surah(n)
        if opening:
            lines.append(" ".join(opening))
        lines += [" ".join(ws) for v, ws in verses if v <= upto]
    return "\n".join(lines)


MARKS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭ࣓-ࣿـ]")


def plain(t):
    t = MARKS.sub("", t)
    for a, b in (("ٱ", "ا"), ("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي"), ("ة", "ه"), ("ۥ", ""), ("ۦ", "")):
        t = t.replace(a, b)
    return re.sub(r"[^ء-ي ]", "", t)


def openai(path, model, voice):
    body = json.dumps({"model": model, "voice": voice, "input": passage(), "instructions": INSTRUCTIONS,
                       "response_format": "mp3"}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/audio/speech", data=body, headers={
        "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        open(path, "wb").write(r.read())


def gemini(path, model, prefix):
    import tts
    tts.VOICE = "Sulafat"
    pcm = tts.request(prefix + passage(), os.environ["GEMINI_API_KEY"], model)
    raw = path + ".pcm"
    open(raw, "wb").write(pcm)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", raw,
                    "-codec:a", "libmp3lame", "-b:a", "64k", path], check=True)


def transcribe(path):
    r = subprocess.run(["curl", "-sS", "https://api.openai.com/v1/audio/transcriptions",
                        "-H", "Authorization: Bearer " + os.environ["OPENAI_API_KEY"],
                        "-F", "file=@" + path, "-F", "model=gpt-4o-transcribe", "-F", "language=ar"],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)["text"]
    except (ValueError, KeyError):
        return "(no transcript: %s)" % r.stdout[:300]


def report(name, path):
    secs = media.seconds(path) or 1
    words = len(passage().split())
    heard = transcribe(path)
    match = difflib.SequenceMatcher(None, plain(passage()).replace(" ", ""), plain(heard).replace(" ", "")).ratio()
    key = "audio/samples/%s.mp3" % name
    media.put(path, key)
    print("SAMPLE %s: %d seconds, %d words a minute, %.0f%% of the letters match the text" % (
        name, secs, round(words * 60.0 / secs), match * 100))
    print("  listen: https://quran.odownhills.workers.dev/%s" % key)
    print("  heard: %s" % heard)


def main():
    out = tempfile.mkdtemp()
    print("TEXT:", passage().replace("\n", " / "))
    for model in OPENAI_MODELS:
        for voice in OPENAI_VOICES:
            path = os.path.join(out, "openai-%s.mp3" % voice)
            try:
                openai(path, model, voice)
            except urllib.error.HTTPError as e:
                print("OpenAI %s %s refused: %s %s" % (model, voice, e.code, e.read().decode(errors="replace")[:300]))
                continue
            report("ar-openai-%s" % voice, path)
    for k, (model, prefix) in enumerate(GEMINI):
        path = os.path.join(out, "gemini-%d.mp3" % k)
        try:
            gemini(path, model, prefix)
        except BaseException as e:   # tts.request ends with SystemExit or OutOfQuota on refusals
            print("Gemini %s: no sample (%s %s)" % (model, type(e).__name__, e))
            continue
        report("ar-sulafat-%s%s" % (re.sub(r"[^a-z0-9]+", "-", model.replace("gemini-", "")), "-styled" if prefix else ""), path)


if __name__ == "__main__":
    main()
