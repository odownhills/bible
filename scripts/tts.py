#!/usr/bin/env python3
"""Record chapter audio with Gemini text-to-speech into site/audio/<slug>/<n>.mp3.

Needs the GEMINI_API_KEY environment variable and ffmpeg.

Works through chapters that have text but no audio yet, in site order. The free Gemini tier
allows only about 10 requests per model per day, so:
  * each request carries as much text as is safe (CHUNK characters, usually a whole chapter);
  * when a model's daily limit is reached, the next model in GEMINI_TTS_MODELS (comma-separated,
    one model by default so the voice stays the same) is used;
  * when every model is used up, the script stops cleanly (exit 0), keeping the chapters it
    finished. The next run picks up where it stopped.

    python3 scripts/tts.py --max 5
    python3 scripts/tts.py --max 5 --strict   # exit non-zero when the key is refused
Run scripts/build.py afterwards so pages and the Listen playlist pick up the new audio.
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.environ.get("GEMINI_TTS_MODELS", "gemini-3.8-flash-tts").split(",")
VOICE = os.environ.get("GEMINI_TTS_VOICE", "Sulafat")
STYLE = ("Read the following Bible passage aloud as an audiobook narrator: calm, warm, unhurried, "
         "clear, with natural pauses between paragraphs. Read only the passage text.\n\n")
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


def request(text, key, model):
    body = json.dumps({
        "contents": [{"parts": [{"text": STYLE + text}]}],
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
            parts = data["candidates"][0]["content"]["parts"]
            return b"".join(base64.b64decode(p["inlineData"]["data"]) for p in parts if "inlineData" in p)
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


def main():
    key = os.environ.get("GEMINI_API_KEY", "")
    limit = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 2
    manifest = json.load(open(os.path.join(ROOT, "site", "manifest.json"), encoding="utf-8"))
    todo = [c for c in manifest if not c.get("audio")][:limit]
    state = {"model": 0}
    for c in todo:
        slug = c["id"].rsplit("-", 1)[0]
        out = os.path.join(ROOT, "site", "audio", slug, "%d.mp3" % c["chapter"])
        try:
            pieces = [speak(p, key, state) for p in chunks(c["text"], CHUNK)]
        except OutOfQuota:
            print("Gemini's free daily limit is used up; %s %d and later chapters will be recorded on the next run."
                  % (c["book"], c["chapter"]))
            return
        pcm = (b"\x00\x00" * (RATE // 2)).join(pieces)  # half-second pause between pieces
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as f:
            f.write(pcm)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(RATE), "-ac", "1",
                        "-i", f.name, "-codec:a", "libmp3lame", "-b:a", "40k", out], check=True)
        os.remove(f.name)
        print("Recorded %s %d (%d characters, %.0f seconds, %s) -> %s"
              % (c["book"], c["chapter"], len(c["text"]), len(pcm) / 2 / RATE,
                 MODELS[min(state["model"], len(MODELS) - 1)], os.path.relpath(out, ROOT)), flush=True)


if __name__ == "__main__":
    main()
