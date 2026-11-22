#!/usr/bin/env python3
"""Bring finished TV mode pictures from the picture branch to the live site.

TV mode pictures are made on the picture branch: a chapter's scene plan is data/tv/<slug>/<NNN>.json there
and its pictures, the trial ones too, are kept in git under site/pictures/<slug>/<n>/. The live site is
built from main, which never holds pictures in git: like the recordings they live in the R2 bucket
(scripts/media.py), and the site's Worker serves them at /pictures/<slug>/<n>/<image>.

A chapter is finished when its plan lists scenes and every scene's picture is on the picture branch.
For each finished chapter that is new or has changed, this script
  - uploads its scenes' pictures to the bucket (pictures/<slug>/<n>/<image>), and a small cover made from
    the first of them (pictures/<slug>/<n>/poster.jpg) for the TV page,
  - copies its plan to data/tv/<slug>/<NNN>.json,
  - lists its pictures in data/pictures.json: {"pictures/job/1/01-table.jpg": [bytes, id], ...}
    (id is the picture's git blob id on the picture branch, so a picture that was made again is noticed).
scripts/build.py then gives the chapter its TV mode button. Trial pictures and tall (phone) pictures stay
on the picture branch. Nothing is ever taken down: a chapter whose plan is being reworked keeps the
pictures it has until the new set is complete.

    python3 scripts/tv_publish.py                # from FETCH_HEAD (.github/workflows/tv.yml fetches the branch first)
    python3 scripts/tv_publish.py --from <ref>   # from another commit or branch
    python3 scripts/tv_publish.py --local        # no bucket: put the pictures in site/pictures/, to try the site on a laptop

Uploads need the R2_* environment variables (see scripts/media.py). The cover needs Pillow
(pip install pillow); without it the TV page shows the chapter's first picture full size instead.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

import media

ROOT = media.ROOT
INDEX = os.path.join(ROOT, "data", "pictures.json")
BOOKS = {b["slug"]: b for b in json.load(open(os.path.join(ROOT, "data", "books.json")))}
SERVED = re.compile(r"^[a-z0-9\-/]+\.(jpg|jpeg|png|webp)$")   # the picture names worker/index.js serves
TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
POSTER = "poster.jpg"


def git(*args):
    r = subprocess.run(("git",) + args, cwd=ROOT, capture_output=True)
    if r.returncode:
        raise SystemExit("git %s failed: %s" % (" ".join(args[:2]), r.stderr.decode("utf-8", "replace").strip()[:500]))
    return r.stdout


def tree(ref):
    """{path: blob id} of the plans and pictures on the picture branch."""
    out = {}
    for line in git("ls-tree", "-r", "-z", ref, "--", "data/tv", "site/pictures").decode("utf-8").split("\0"):
        if line:
            meta, path = line.split("\t", 1)
            out[path] = meta.split()[2]
    return out


def fetch_blobs(ids):
    """In a clone made without file contents (the workflow's), get these files in one request.
    Without this git still fetches each one as it is read, only slower."""
    if not ids or git("config", "--get", "--default", "", "remote.origin.promisor").strip() != b"true":
        return
    subprocess.run(["git", "-c", "fetch.negotiationAlgorithm=noop", "fetch", "origin", "--no-tags",
                    "--no-write-fetch-head", "--recurse-submodules=no", "--filter=blob:none", "--stdin"],
                   cwd=ROOT, input=("\n".join(sorted(set(ids))) + "\n").encode(), capture_output=True)


def load_index():
    try:
        return json.load(open(INDEX))
    except (OSError, ValueError):
        return {}


def save_index(value):
    with open(INDEX, "w") as f:   # one picture per line, so a change reads clearly in git
        f.write("{\n" + ",\n".join("%s: %s" % (json.dumps(k), json.dumps(value[k])) for k in sorted(value)) + "\n}\n")


def poster(path, out):
    """A small cover picture for the TV page, or False when Pillow is not installed."""
    try:
        from PIL import Image
    except ImportError:
        return False
    im = Image.open(path).convert("RGB")
    im.thumbnail((640, 640))
    im.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return True


def main():
    args = sys.argv[1:]
    local = "--local" in args
    ref = args[args.index("--from") + 1] if "--from" in args else "FETCH_HEAD"
    if not local and not media.configured():
        raise SystemExit("The R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY and R2_ENDPOINT environment variables are needed "
                         "(see scripts/media.py), or use --local.")
    files = tree(ref)
    index = load_index()
    fetch_blobs([sha for path, sha in files.items() if path.startswith("data/tv/")])
    work = []   # (slug, n, plan path, plan bytes, {picture key: (branch path, blob id)}, key of the first picture)
    for path in sorted(p for p in files if p.startswith("data/tv/")):
        m = re.match(r"^data/tv/([a-z0-9\-]+)/(\d{3})\.json$", path)
        if not m or m.group(1) not in BOOKS:
            continue
        slug, n = m.group(1), int(m.group(2))
        raw = git("cat-file", "blob", files[path])
        try:
            scenes = json.loads(raw.decode("utf-8")).get("scenes") or []
        except ValueError:
            print("%s %d: the plan is not valid JSON, left alone" % (slug, n))
            continue
        if not scenes:
            continue   # still at the trial stage
        want, missing, odd = {}, [], []
        for s in scenes:
            name = str(s.get("image") or "")
            key = "pictures/%s/%d/%s" % (slug, n, name)
            if not SERVED.match(key):
                odd.append(name)
            elif "site/" + key not in files:
                missing.append(name)
            else:
                want[key] = ("site/" + key, files["site/" + key])
        if odd:
            print("%s %d: picture names the site cannot serve (%s), left alone" % (slug, n, ", ".join(odd)))
        elif missing:
            print("%s %d: waiting for %d picture%s" % (slug, n, len(missing), "" if len(missing) == 1 else "s"))
        else:
            work.append((slug, n, path, raw, want, "pictures/%s/%d/%s" % (slug, n, scenes[0]["image"])))

    fetch_blobs([sha for _, _, _, _, want, _ in work for key, (_, sha) in want.items()
                 if (index.get(key) or [None, None])[1] != sha])
    published = []
    with tempfile.TemporaryDirectory() as tmp:
        for slug, n, plan_path, raw, want, first in work:
            changed = False
            cover = "pictures/%s/%d/%s" % (slug, n, POSTER)
            for key in sorted(want):
                src, sha = want[key]
                if (index.get(key) or [None, None])[1] == sha and not local:
                    continue
                data = git("cat-file", "blob", sha)
                if local:
                    out = os.path.join(media.SITE, key)
                    if not os.path.exists(out) or open(out, "rb").read() != data:
                        os.makedirs(os.path.dirname(out), exist_ok=True)
                        open(out, "wb").write(data)
                        changed = True
                else:
                    out = os.path.join(tmp, "picture")
                    open(out, "wb").write(data)
                    media.put(out, key, TYPES[key.rsplit(".", 1)[1]])
                    index[key] = [len(data), sha]
                    changed = True
            # the cover follows the first picture
            first_sha = want[first][1]
            if local:
                out = os.path.join(media.SITE, cover)
                if not os.path.exists(out):
                    changed |= poster(os.path.join(media.SITE, first), out)
            elif (index.get(cover) or [None, None])[1] != first_sha:
                src, out = os.path.join(tmp, "first"), os.path.join(tmp, "poster.jpg")
                open(src, "wb").write(git("cat-file", "blob", first_sha))
                if poster(src, out):
                    media.put(out, cover, "image/jpeg")
                    index[cover] = [os.path.getsize(out), first_sha]
                    changed = True
            if not local:
                # pictures of an earlier choice for this chapter are no longer part of it
                mine = "pictures/%s/%d/" % (slug, n)
                for key in [k for k in index if k.startswith(mine) and k not in want and k != cover]:
                    del index[key]
                    changed = True
            dest = os.path.join(ROOT, plan_path)
            if not os.path.exists(dest) or open(dest, "rb").read() != raw:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                open(dest, "wb").write(raw)
                changed = True
            if changed:
                published.append("%s %d" % (BOOKS[slug]["name"], n))
                print("Published %s %d (%d pictures)" % (BOOKS[slug]["name"], n, len(want)), flush=True)
                if not local:
                    save_index(index)   # after each chapter, so a run that stops partway keeps what it uploaded
    if not published:
        print("No new TV mode pictures.")
    shown = published[:8] + (["and %d more" % (len(published) - 8)] if len(published) > 8 else [])
    note = os.environ.get("TV_PUBLISH_NOTE")
    if note:   # the commit message, for the workflow
        open(note, "w").write(("Add TV mode pictures: " + ", ".join(shown) if shown else "Rebuild the site") + "\n")


if __name__ == "__main__":
    main()
