#!/usr/bin/env python3
"""Recordings (and later TV-mode pictures) live in the Cloudflare R2 bucket, not in git.

The bucket keeps the site's own paths: site/audio/genesis/1.mp3 is the object audio/genesis/1.mp3,
served by the site's Worker (worker/index.js) at /audio/genesis/1.mp3. data/audio.json lists every
recording in the bucket, {"audio/genesis/1.mp3": [bytes, seconds], ...}, so the site can be built
without the files themselves.

Uploads use the AWS command line tool (preinstalled on GitHub's runners) against R2's S3 endpoint.
Needs these environment variables (GitHub repository secrets):
    R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY   an R2 API token with Object Read & Write
    R2_ENDPOINT                              https://<account id>.r2.cloudflarestorage.com
                                             (the account id alone also works)
    R2_BUCKET                                optional, default bible-media

    python3 scripts/media.py migrate   # move recordings still kept in git into the bucket
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# WORK=quran in the environment works on the Quran site (site-quran/) instead: see scripts/build.py.
# Both sites share the bucket and data/audio.json; their recordings have different paths.
WORK = os.environ.get("WORK") or "bible"
SITE = os.path.join(ROOT, "site" if WORK == "bible" else "site-" + WORK)
INDEX = os.path.join(ROOT, "data", "audio.json")
BUCKET = os.environ.get("R2_BUCKET") or "bible-media"


def configured():
    return all(os.environ.get(k) for k in ("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT"))


def _endpoint():
    e = os.environ["R2_ENDPOINT"].strip().rstrip("/")
    if "://" not in e:
        e = "https://%s.r2.cloudflarestorage.com" % e
    # the dashboard sometimes shows the endpoint with the bucket name on the end
    if e.endswith("/" + BUCKET):
        e = e[:-len(BUCKET) - 1]
    return e


def _aws(*args, check=True):
    env = dict(os.environ,
               AWS_ACCESS_KEY_ID=os.environ["R2_ACCESS_KEY_ID"].strip(),
               AWS_SECRET_ACCESS_KEY=os.environ["R2_SECRET_ACCESS_KEY"].strip(),
               AWS_DEFAULT_REGION="auto",
               # R2 does not accept the newer default checksum headers of the AWS tool
               AWS_REQUEST_CHECKSUM_CALCULATION="when_required",
               AWS_RESPONSE_CHECKSUM_VALIDATION="when_required")
    r = subprocess.run(["aws", "--endpoint-url", _endpoint()] + list(args),
                       capture_output=True, text=True, env=env)
    if check and r.returncode:
        raise SystemExit("R2 request failed (%s): %s" % (" ".join(args[:2]), (r.stderr or r.stdout).strip()[:500]))
    return r


def size(key):
    """Bytes of an object in the bucket, or None when it is not there."""
    r = _aws("s3api", "head-object", "--bucket", BUCKET, "--key", key, check=False)
    if r.returncode:
        if "404" in r.stderr or "Not Found" in r.stderr or "NoSuchKey" in r.stderr:
            return None
        raise SystemExit("R2 request failed (head-object): %s" % r.stderr.strip()[:500])
    return json.loads(r.stdout)["ContentLength"]


def put(path, key, content_type="audio/mpeg"):
    """Upload a file and confirm the bucket holds all of it."""
    _aws("s3", "cp", "--only-show-errors", "--content-type", content_type, path, "s3://%s/%s" % (BUCKET, key))
    if size(key) != os.path.getsize(path):
        raise SystemExit("R2 upload of %s did not arrive whole" % key)


def get(key, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _aws("s3", "cp", "--only-show-errors", "s3://%s/%s" % (BUCKET, key), path)


def index():
    try:
        return json.load(open(INDEX))
    except (OSError, ValueError):
        return {}


def save_index(value):
    with open(INDEX, "w") as f:
        json.dump(value, f, sort_keys=True, indent=0)
        f.write("\n")


def seconds(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                             capture_output=True, text=True).stdout.strip()
        return round(float(out))
    except (OSError, ValueError):
        return None


def publish(path, rel):
    """Upload a finished recording (rel = audio/<slug>/<n>.mp3) and list it in data/audio.json."""
    put(path, rel)
    idx = index()
    idx[rel] = [os.path.getsize(path), seconds(path)]
    save_index(idx)


def local(rel):
    """Path of a recording on disk, downloading it from the bucket when it is not here."""
    path = os.path.join(SITE, rel)
    want = index().get(rel, [None])[0]
    if os.path.exists(path) and (want is None or os.path.getsize(path) == want):
        return path
    get(rel, path)
    return path


def migrate():
    """Upload recordings still kept in git, list them, and stop tracking them in git."""
    tracked = subprocess.run(["git", "ls-files", "site/audio"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.split()
    mp3s = [t for t in tracked if t.endswith(".mp3")]
    if not mp3s:
        print("No recordings left in git.")
        return
    idx = index()
    for t in mp3s:
        rel = t[len("site/"):]
        path = os.path.join(ROOT, t)
        if size(rel) != os.path.getsize(path):
            put(path, rel)
            print("Uploaded", rel, flush=True)
        idx[rel] = [os.path.getsize(path), seconds(path) or (idx.get(rel) or [0, None])[1]]
    save_index(idx)
    subprocess.run(["git", "rm", "--cached", "--quiet"] + mp3s, cwd=ROOT, check=True)
    print("Moved %d recordings from git to R2." % len(mp3s))


if __name__ == "__main__":
    if sys.argv[1:] == ["migrate"]:
        migrate()
    else:
        print(__doc__)
