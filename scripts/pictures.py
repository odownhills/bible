#!/usr/bin/env python3
"""Make the TV mode pictures that scene plans ask for and that are not in site/pictures/ yet.

Needs the OPENAI_API_KEY environment variable. Run by .github/workflows/pictures.yml.

A scene plan is data/tv/<slug>/<NNN>.json. Each scene names a wide picture ("image") and usually a
tall one ("tall", for a phone held upright), and carries the "prompt" that describes the picture.
Both shapes are made from the same prompt plus a fixed style block (below), wide at 1920x1088 and
tall at 1088x1920 (tall ones only when PICTURES_TALL=1; they are switched off for now). A scene with "people": false gets the style block that forbids any figure,
because the image model otherwise tends to add one.

A plan may also carry "candidates": scenes in the same form (usually wide only, named cand/<name>.jpg) that are
made so the best of several ideas can be chosen by eye. The site ignores them; the losers are deleted afterwards.

Pictures that already exist are never remade: to redo one, delete its file (or change its name in
the plan) and run again. Spending is capped per run by PICTURES_MAX_USD (default 1.00).

    python3 scripts/pictures.py            # make what is missing
    python3 scripts/pictures.py --list     # only say what is missing
Run scripts/build.py afterwards: a chapter gets its TV mode button once all its pictures are there.
"""
import base64
import concurrent.futures
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2.5-sunburst")
QUALITY = os.environ.get("OPENAI_IMAGE_QUALITY", "medium")
MAX_USD = float(os.environ.get("PICTURES_MAX_USD", "1.00"))
# Tall pictures (for a phone held upright) are switched off for now, at Obay's wish (2026-11-21): only the wide
# TV pictures are made. Plans keep their "tall" names and the tall pictures already made stay in the site, so
# setting PICTURES_TALL=1 brings them back and fills in the ones that are missing.
MAKE_TALL = os.environ.get("PICTURES_TALL", "0") == "1"
WORKERS = 4
# Measured 2026-11-20: a medium picture of either shape is 344 output tokens, $0.0103.
USD_PER_OUTPUT_TOKEN = 30.0 / 1e6
USD_PER_INPUT_TOKEN = 5.0 / 1e6
GUESS_USD = 0.0105          # what one picture is counted as until its real cost is known

_BASE = ("A simple symbolic image, like a visual parable: one clear idea, one subject, nothing else competing "
         "for the eye. Present-day or timeless everyday setting. %s"
         "This is not a historical or biblical-era scene: no robes, no ancient buildings, no halos, no glowing "
         "figures, no crosses or other religious symbols. No text, letters, numbers, captions, logos, borders or "
         "watermarks anywhere. %s Bright enough to read clearly on a small phone screen.")
_PEOPLE = "Any people are ordinary people of today in plain everyday clothes. "
_NOBODY = "There are no people, faces or figures of any kind anywhere in the frame, not even small or far away. "
SHAPES = {
    "wide": ("1920x1088",
             "Photorealistic cinematic photograph, wide 16:9 frame, shallow depth of field, natural light. ",
             "Compose it so that the subject and every important detail are in the upper two thirds of the frame. "
             "The bottom third is plain foreground of the same scene (floor, ground, table or water) in soft shadow, "
             "with nothing that matters in it. The scene fills the whole frame to every edge: no black bar, band, "
             "border or blank strip."),
    "tall": ("1088x1920",
             "Photorealistic cinematic photograph in a tall 9:16 portrait frame, made to fill a phone held upright, "
             "shallow depth of field, natural light. ",
             "Put the subject in the upper two thirds of the frame, and keep the lower third simple, darker and "
             "uncluttered, because words will be shown over it."),
}


def full_prompt(scene, shape):
    _, head, tail = SHAPES[shape]
    return scene["prompt"] + "\n\n" + head + _BASE % (_PEOPLE if scene.get("people", True) else _NOBODY, tail)


def missing():
    """Every picture a plan asks for that is not on disk: (label, scene, shape, path). Scenes without a
    prompt cannot be made here and are reported separately."""
    jobs, no_prompt = [], []
    base = os.path.join(ROOT, "data", "tv")
    for slug in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        if not os.path.isdir(os.path.join(base, slug)):
            continue
        for name in sorted(os.listdir(os.path.join(base, slug))):
            if not name.endswith(".json"):
                continue
            n = int(name[:-5])
            plan = json.load(open(os.path.join(base, slug, name), encoding="utf-8"))
            for scene in plan["scenes"] + plan.get("candidates", []):
                for shape, key in (("wide", "image"), ("tall", "tall")):
                    if not scene.get(key) or (shape == "tall" and not MAKE_TALL):
                        continue
                    path = os.path.join(ROOT, "site", "pictures", slug, str(n), scene[key])
                    if os.path.exists(path):
                        continue
                    label = "%s %d %s" % (slug, n, scene[key])
                    (jobs if scene.get("prompt") else no_prompt).append((label, scene, shape, path))
    return jobs, no_prompt


class Refused(Exception):
    pass


def make(scene, shape, key):
    """One picture: (jpeg bytes, cost in dollars)."""
    body = json.dumps({"model": MODEL, "prompt": full_prompt(scene, shape), "n": 1, "size": SHAPES[shape][0],
                       "quality": QUALITY, "output_format": "jpeg", "output_compression": 88}).encode()
    for attempt in range(5):
        req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body, headers={
            "Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                out = json.load(r)
            usage = out.get("usage") or {}
            cost = (usage.get("output_tokens", 344) * USD_PER_OUTPUT_TOKEN +
                    usage.get("input_tokens", 0) * USD_PER_INPUT_TOKEN)
            return base64.b64decode(out["data"][0]["b64_json"]), cost
        except urllib.error.HTTPError as e:
            try:
                err = (json.load(e).get("error") or {})
            except Exception:
                err = {}
            if e.code in (401, 403):
                # never echo the message for these: it can quote part of the key
                raise Refused("the key was refused (HTTP %d, %s)" % (e.code, err.get("code") or err.get("type")))
            if e.code == 429 and (err.get("code") in ("insufficient_quota", "billing_hard_limit_reached")):
                raise Refused("the OpenAI account is out of credit or over its budget (%s)" % err.get("code"))
            if e.code == 429 or e.code >= 500:
                time.sleep(8 * (attempt + 1))
                continue
            raise RuntimeError("HTTP %d %s: %s" % (e.code, err.get("code") or err.get("type") or "",
                                                  (err.get("message") or "")[:300]))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(8 * (attempt + 1))
    raise RuntimeError("no answer after 5 tries")


def main():
    jobs, no_prompt = missing()
    for label, _, _, _ in no_prompt:
        print("no prompt, cannot make: " + label)
    if "--list" in sys.argv:
        for label, _, _, _ in jobs:
            print("missing: " + label)
        print("%d to make, about $%.2f" % (len(jobs), len(jobs) * GUESS_USD))
        return 0
    if not jobs:
        print("Every picture is already there.")
        return 0
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        print("No OPENAI_API_KEY; %d pictures are waiting." % len(jobs))
        return 1
    lock = threading.Lock()
    state = {"spent": 0.0, "booked": 0.0, "made": 0, "failed": [], "stop": None}

    def work(job):
        label, scene, shape, path = job
        with lock:
            if state["stop"]:
                return
            if state["spent"] + state["booked"] + GUESS_USD > MAX_USD:
                state["stop"] = "spending cap of $%.2f for one run reached" % MAX_USD
                return
            state["booked"] += GUESS_USD
        try:
            data, cost = make(scene, shape, key)
        except Refused as e:
            with lock:
                state["booked"] -= GUESS_USD
                state["stop"] = state["stop"] or str(e)
            return
        except Exception as e:
            with lock:
                state["booked"] -= GUESS_USD
                state["failed"].append("%s: %s" % (label, e))
            print("failed " + label + ": " + str(e), flush=True)
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        with lock:
            state["booked"] -= GUESS_USD
            state["spent"] += cost
            state["made"] += 1
        print("made %s  $%.4f" % (label, cost), flush=True)

    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        list(pool.map(work, jobs))
    left = len(jobs) - state["made"]
    print("DONE made %d, failed %d, still missing %d, cost $%.3f" % (
        state["made"], len(state["failed"]), left, state["spent"]))
    if state["stop"]:
        print("Stopped early: " + state["stop"])
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("Made %d pictures for $%.3f. Failed: %d. Still missing: %d.\n\n" % (
                state["made"], state["spent"], len(state["failed"]), left))
            for line in state["failed"]:
                f.write("- " + line + "\n")
            if state["stop"]:
                f.write("\nStopped early: " + state["stop"] + "\n")
    return 1 if (state["failed"] or state["stop"]) else 0


if __name__ == "__main__":
    sys.exit(main())
