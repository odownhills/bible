#!/usr/bin/env python3
"""Record chapter audio with Gemini text-to-speech into site/audio/<slug>/<n>.mp3.

Needs the GEMINI_API_KEY environment variable and ffmpeg. Each recording that passes the check is
uploaded to the Cloudflare R2 bucket and listed in data/audio.json (see scripts/media.py); the
mp3 files themselves are never committed to git.

Works through chapters that have text but no audio yet, in site order. The free Gemini tier
allows only about 10 requests per model per day, so:
  * each request carries as much text as is safe (CHUNK characters, usually a whole chapter);
  * when a model's daily limit is reached, the next model in GEMINI_TTS_MODELS (comma-separated,
    one model by default so the voice stays the same) is used;
  * when every model is used up, the script stops cleanly (exit 0), keeping the chapters it
    finished. The next run picks up where it stopped.

Every new recording is checked word for word against the chapter before it is kept (the voice
model now and then invents, repeats or skips lines). The check listens with scripts/align.py and
needs `pip install sherpa-onnx numpy`; without those it is skipped with a warning. A recording that
fails is thrown away and counted in site/audio/rejected.json; the chapter is tried again on the
next run, in shorter pieces, up to 3 times. To record a chapter again, add its id (for example "genesis-5") to the
list in site/audio/redo.json: the old recording stays until a new one passes the check.

    python3 scripts/tts.py --max 5
    python3 scripts/tts.py --max 5 --strict   # exit non-zero when the key is refused
Run scripts/build.py afterwards so pages and the Listen playlist pick up the new audio.
"""
import array
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import media  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.environ.get("GEMINI_TTS_MODELS", "gemini-3.8-flash-tts").split(",")
VOICE = os.environ.get("GEMINI_TTS_VOICE", "Sulafat")
# Send only the words to be spoken. Any instruction placed before the passage is read aloud
# by the voice model (found 2026-11-20), so there is deliberately no style prompt.
# Gemini also ends every reply with a short burst of static, which trim_noise() removes.
CHUNK = 6000        # characters per request
RATE = 24000        # samples per second, 16-bit mono
MIN_CPS = 26        # faster than this many characters per second means the audio was cut short


class OutOfQuota(Exception):
    pass


def chunks(text, size):
    sents = re.findall(r"[^.!?]+[.!?]+[\"'”’)]*\s*|.+$", text)
    out, cur = [], ""
    for s in sents:
        if cur and len(cur) + len(s) > size:
            out.append(cur.strip())
            cur = ""
        cur += s
    if cur.strip():
        out.append(cur.strip())
    return out


def trim_noise(pcm):
    """Cut the burst of static that Gemini puts at the very end of a reply.

    Every reply measured on 2026-11-20 ended with a pause and then about 0.16 seconds of loud
    static, heard as a scratchy sound at the end of a chapter. Speech never looks like that (a short,
    very loud block right after silence, at the very end), so it is safe to remove when found.
    """
    frame = RATE // 100                                 # 10 ms
    a = array.array("h")
    a.frombytes(pcm[max(0, len(pcm) - 2 * RATE):])      # the last second
    if sys.byteorder == "big":
        a.byteswap()
    level = [(sum(x * x for x in a[i:i + frame]) / frame) ** 0.5 / 32768
             for i in range(0, len(a) - frame + 1, frame)]
    quiet = None                                        # frame just after the last pause of 60 ms or more
    for i in range(len(level) - 6, -1, -1):
        if max(level[i:i + 6]) < 0.02:
            quiet = i + 6
            break
    if quiet is None:
        return pcm
    while quiet < len(level) and level[quiet] < 0.02:
        quiet += 1
    tail = level[quiet:]
    if not tail or len(tail) > 40 or sum(1 for v in tail if v > 0.3) < 0.6 * len(tail):
        return pcm
    cut = len(pcm) - (len(a) - quiet * frame) * 2
    print("Removed %.2f seconds of static from the end of a reply." % ((len(pcm) - cut) / 2.0 / RATE), flush=True)
    return pcm[:cut]


def request(text, key, model):
    body = json.dumps({
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}},
        },
    }).encode()
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model
    for attempt in range(4):
        headers = {"Content-Type": "application/json"}
        if key:
            headers["x-goog-api-key"] = key
        req = urllib.request.Request(url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.load(r)
            parts = [p["inlineData"] for p in data["candidates"][0]["content"]["parts"] if "inlineData" in p]
            sound = [p for p in parts if p.get("mimeType", "audio/").startswith("audio/")]
            if len(parts) != 1 or len(sound) != len(parts):
                print("Reply parts:", ", ".join("%s (%d characters)" % (p.get("mimeType"), len(p["data"]))
                                                for p in parts), flush=True)
            pcm = b"".join(base64.b64decode(p["data"]) for p in sound)
            return trim_noise(pcm[:len(pcm) // 2 * 2])
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:600]
            if e.code in (401, 403) or (e.code == 400 and "API key" in msg):
                if "--strict" in sys.argv:
                    raise SystemExit("Gemini refused the request (HTTP %s): %s" % (e.code, msg))
                print("No working Gemini key (HTTP %s); skipping audio." % e.code)
                raise SystemExit(0)
            if e.code == 429 and "free_tier_requests" in msg and "PerMinute" not in msg and "per minute" not in msg.lower():
                raise OutOfQuota(model)
            if e.code == 404:
                print("Model %s is not available; trying the next one." % model)
                raise OutOfQuota(model)
            if e.code in (429, 500, 503) and attempt < 3:
                time.sleep(40 * (attempt + 1))
                continue
            raise SystemExit("Gemini TTS error %s: %s" % (e.code, msg))
        except (KeyError, IndexError):
            if attempt < 3:
                time.sleep(20)
                continue
            raise SystemExit("Gemini returned no audio for a passage")
        except (urllib.error.URLError, OSError) as e:
            if attempt < 3:
                time.sleep(20)
                continue
            raise SystemExit("Could not reach Gemini: %s" % e)
    raise SystemExit("Gemini TTS failed after retries")


def speak(text, key, state):
    """Audio for one passage, moving to the next model when one runs out for the day."""
    while state["model"] < len(MODELS):
        try:
            pcm = request(text, key, MODELS[state["model"]])
        except OutOfQuota:
            print("Daily limit reached for", MODELS[state["model"]])
            state["model"] += 1
            continue
        seconds = len(pcm) / 2 / RATE
        if seconds and len(text) / seconds > MIN_CPS and len(text) > 1200:
            # the audio stopped early: read the passage in two halves instead
            half = chunks(text, len(text) // 2 + 200)
            time.sleep(25)
            return b"".join(speak(h, key, state) for h in half)
        time.sleep(25)  # stay under the requests-per-minute limit
        return pcm
    raise OutOfQuota("all models")


def note(name, default):
    """A small JSON file kept beside the recordings (site/audio/<name>)."""
    path = os.path.join(media.SITE, "audio", name)
    try:
        return json.load(open(path)), path
    except (OSError, ValueError):
        return default, path


def save(value, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(value, open(path, "w"), sort_keys=True)


def checker():
    """A function (mp3 path, text) -> list of problems, or None when the listener is not installed."""
    try:
        import align
        rec = align.recognizer()
    except Exception as e:  # missing packages, or the speech model could not be downloaded
        print("WARNING: recordings are not being checked against the text (%s)." % e, flush=True)
        return None
    return lambda mp3, text: align.check(mp3, text, rec)


def main():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not media.configured():
        raise SystemExit("Recordings are stored in Cloudflare R2: set R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY "
                         "and R2_ENDPOINT (see scripts/media.py).")
    limit = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 2
    manifest = json.load(open(os.path.join(media.SITE, "manifest.json"), encoding="utf-8"))
    redo, redo_path = note("redo.json", [])
    rejected, rejected_path = note("rejected.json", {})
    todo = [c for c in manifest if (not c.get("audio") or c["id"] in redo) and rejected.get(c["id"], 0) < 3][:limit]
    state = {"model": 0}
    check = False                                       # loaded when the first recording is ready
    for c in todo:
        slug = c["id"].rsplit("-", 1)[0]
        out = os.path.join(media.SITE, "audio", slug, "%d.mp3" % c["chapter"])
        text = open(os.path.join(media.SITE, c["text"]), encoding="utf-8").read()
        try:
            # A chapter whose last take failed the check is read in shorter pieces: the voice loses
            # its place less often in short passages (long lists of names and ages trip it up).
            size = (CHUNK, 1600, 900)[min(rejected.get(c["id"], 0), 2)]
            pieces = [speak(p, key, state) for p in chunks(text, size)]
        except OutOfQuota:
            print("Gemini's free daily limit is used up; %s %d and later chapters will be recorded on the next run."
                  % (c["book"], c["chapter"]))
            return
        pcm = (b"\x00\x00" * (RATE // 2)).join(pieces)  # half-second pause between pieces
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as f:
            f.write(pcm)
        new = f.name[:-4] + ".mp3"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(RATE), "-ac", "1",
                        "-i", f.name, "-codec:a", "libmp3lame", "-b:a", "40k", new], check=True)
        os.remove(f.name)
        if check is False:
            check = checker()
        wrong = check(new, text) if check else []
        if wrong:
            os.remove(new)
            rejected[c["id"]] = rejected.get(c["id"], 0) + 1
            save(rejected, rejected_path)
            print("Threw away a recording of %s %d (attempt %d of 3) because it does not match the text:"
                  % (c["book"], c["chapter"], rejected[c["id"]]), flush=True)
            for w in wrong[:6]:
                print("   " + w, flush=True)
            continue
        shutil.move(new, out)
        media.publish(out, "audio/%s/%d.mp3" % (slug, c["chapter"]))
        if c["id"] in redo:
            redo.remove(c["id"])
            save(redo, redo_path)
        if c["id"] in rejected:
            del rejected[c["id"]]
            save(rejected, rejected_path)
        print("Recorded %s %d (%d characters, %.0f seconds, %s) -> %s"
              % (c["book"], c["chapter"], len(text), len(pcm) / 2 / RATE,
                 MODELS[min(state["model"], len(MODELS) - 1)], os.path.relpath(out, ROOT)), flush=True)


if __name__ == "__main__":
    main()
