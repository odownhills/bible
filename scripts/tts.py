#!/usr/bin/env python3
"""Record chapter audio with Gemini text-to-speech into site/audio/<slug>/<n>.mp3.

Needs the GEMINI_API_KEY environment variable and ffmpeg. Without a key it exits quietly,
so the nightly run never fails because of audio.

Works through chapters that have text but no audio yet, oldest first, so a day that hits
the free-tier limit simply catches up the next night.

    python3 scripts/tts.py            # up to 2 chapters
    python3 scripts/tts.py --max 5
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
MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
VOICE = os.environ.get("GEMINI_TTS_VOICE", "Sulafat")
STYLE = ("Read the following Bible passage aloud as an audiobook narrator: calm, warm, unhurried, "
         "clear, with natural pauses between paragraphs. Read only the passage text.\n\n")
CHUNK = 2800  # characters per request


def chunks(text):
    sents = re.findall(r"[^.!?]+[.!?]+[\"'”’)]*\s*|.+$", text)
    out, cur = [], ""
    for s in sents:
        if cur and len(cur) + len(s) > CHUNK:
            out.append(cur.strip())
            cur = ""
        cur += s
    if cur.strip():
        out.append(cur.strip())
    return out


def speak(text, key):
    body = json.dumps({
        "contents": [{"parts": [{"text": STYLE + text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}},
        },
    }).encode()
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % MODEL
    for attempt in range(5):
        headers = {"Content-Type": "application/json"}
        if key:
            headers["x-goog-api-key"] = key
        req = urllib.request.Request(url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.load(r)
            part = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
            return base64.b64decode(part)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:500]
            if e.code in (400, 401, 403) and ("API key" in msg or "API_KEY" in msg or "blocked" in msg.lower() or e.code != 400):
                print("No working Gemini key or host not allowed (HTTP %s); skipping audio." % e.code)
                raise SystemExit(0)
            if e.code == 429 and ("per day" in msg.lower() or "PerDay" in msg):
                raise SystemExit("Gemini daily free limit reached; audio will catch up tomorrow.\n" + msg)
            if e.code in (429, 500, 503) and attempt < 4:
                time.sleep(30 * (attempt + 1))
                continue
            raise SystemExit("Gemini TTS error %s: %s" % (e.code, msg))
        except (urllib.error.URLError, OSError) as e:
            print("Could not reach Gemini (%s); skipping audio." % e)
            raise SystemExit(0)
    raise SystemExit("Gemini TTS failed after retries")


def main():
    # The key comes from GEMINI_API_KEY, or is added to the request by the environment's
    # network secret for generativelanguage.googleapis.com (then no variable is set here).
    key = os.environ.get("GEMINI_API_KEY", "")
    limit = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 2
    manifest = json.load(open(os.path.join(ROOT, "site", "manifest.json"), encoding="utf-8"))
    todo = [c for c in manifest if not c.get("audio")][:limit]
    for c in todo:
        slug = c["id"].rsplit("-", 1)[0]
        out = os.path.join(ROOT, "site", "audio", slug, "%d.mp3" % c["chapter"])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        pcm = b""
        for k, piece in enumerate(chunks(c["text"])):
            if k:
                time.sleep(25)  # stay under the free tier's requests-per-minute limit
                pcm += b"\x00\x00" * 12000  # half-second pause between pieces
            pcm += speak(piece, key)
        with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as f:
            f.write(pcm)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1",
                        "-i", f.name, "-codec:a", "libmp3lame", "-b:a", "40k", out], check=True)
        os.remove(f.name)
        print("Recorded", c["book"], c["chapter"], "->", os.path.relpath(out, ROOT))
        time.sleep(25)


if __name__ == "__main__":
    main()
