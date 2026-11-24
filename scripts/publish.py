#!/usr/bin/env python3
"""Publish one translated Bible chapter in one step (CLAUDE.md, steps 2 to 4).

    python3 scripts/publish.py genesis 11 --branch <branch> --trailer "Co-Authored-By: ..." --trailer "Claude-Session: ..."
    python3 scripts/publish.py genesis 11 --dry-run      # only the checks; changes nothing
    python3 scripts/publish.py --live genesis 11         # after the merge: wait until the page is live

In order, stopping at the first failure:
  1. scripts/check.py on the chapter must print OK.
  2. The chapter's uncommitted files are carried onto the newest main, on <branch>.
  3. Only the files a run may change are changed: the chapter, its decision log, its notes
     (notes/<slug>/<NNN>.md) and GLOSSARY.md, and GLOSSARY.md only by lines added at its end.
  4. scripts/build.py rebuilds site/.
  5. One commit, "Add <Book> <n>", with the trailer lines given, pushed to <branch> (up to 4 tries).
It prints the commit's full SHA for the pull request merge.
"""
import html, json, os, subprocess, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS = {b["slug"]: b for b in json.load(open(os.path.join(ROOT, "data", "books.json")))}
SITE = "https://bible.odownhills.workers.dev"


def run(*cmd, check=True):
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if check and p.returncode:
        sys.exit("FAILED: %s\n%s%s" % (" ".join(cmd), p.stdout, p.stderr))
    return p


def git(*args, check=True):
    return run("git", *args, check=check)


def option(args, name, many=False):
    vals = []
    while name in args:
        i = args.index(name)
        if i + 1 >= len(args):
            sys.exit(name + " needs a value")
        vals.append(args[i + 1])
        del args[i:i + 2]
    return vals if many else (vals[-1] if vals else None)


def live(slug, n):
    path = os.path.join(ROOT, "translations", slug, "%03d.md" % n)
    heads = [l[3:].strip() for l in open(path, encoding="utf-8") if l.startswith("## ")]
    url = "%s/%s/%d" % (SITE, slug, n)
    for _ in range(40):
        try:
            page = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "bible-publish"}),
                                          timeout=30).read().decode("utf-8", "replace")
            if not heads or any(h in page or html.escape(h) in page for h in heads[:1]):
                print("LIVE %s" % url)
                return
        except Exception:
            pass
        time.sleep(15)
    sys.exit("NOT LIVE after 10 minutes: %s" % url)


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    want_live = "--live" in args
    args = [a for a in args if a not in ("--dry-run", "--live")]
    branch = option(args, "--branch")
    trailers = option(args, "--trailer", many=True)
    if len(args) != 2 or args[0] not in BOOKS or not args[1].isdigit():
        sys.exit(__doc__)
    slug, n = args[0], int(args[1])
    if want_live:
        return live(slug, n)
    if not dry and not branch:
        sys.exit("--branch is required (or --dry-run)")
    book = BOOKS[slug]["name"]
    nnn = "%03d" % n
    chapter = "translations/%s/%s.md" % (slug, nnn)
    allowed = {chapter, "decisions/%s/%s.md" % (slug, nnn), "notes/%s/%s.md" % (slug, nnn), "GLOSSARY.md"}

    # 1. the check
    p = run("python3", "scripts/check.py", chapter, check=False)
    print(p.stdout.strip() or p.stderr.strip())
    if p.returncode or not p.stdout.startswith("OK"):
        sys.exit("FAILED: the check did not print OK")

    # 2. onto the newest main
    git("fetch", "origin", "main")
    if not dry:
        stashed = git("stash", "push", "-u", "-m", "publish %s %d" % (book, n)).stdout.strip() != "No local changes to save"
        git("checkout", "-B", branch, "origin/main")
        if stashed:
            p = git("stash", "pop", check=False)
            if p.returncode:
                sys.exit("FAILED: the chapter's files conflict with the newest main (often GLOSSARY.md, when"
                         " another chapter was added meanwhile). Resolve by keeping main's lines and appending"
                         " this chapter's section after them, then run this again.\n" + p.stdout + p.stderr)

    # 3. only the files a run may change
    changed = []
    for line in git("status", "--porcelain", "-uall").stdout.splitlines():
        changed.append(line[3:].strip().strip('"'))
    stray = [c for c in changed if c not in allowed and not c.startswith("site/")]
    if stray:
        sys.exit("FAILED: files a run may not change are changed:\n  " + "\n  ".join(stray))
    if chapter not in changed:
        sys.exit("FAILED: %s is not a new or changed file" % chapter)
    old = git("show", "origin/main:GLOSSARY.md").stdout
    new = open(os.path.join(ROOT, "GLOSSARY.md"), encoding="utf-8").read()
    if not new.startswith(old.rstrip("\n")):
        sys.exit("FAILED: GLOSSARY.md was changed above its end; a run may only append lines to it")
    print("files: " + ", ".join(sorted(c for c in changed if not c.startswith("site/"))))
    if dry:
        print("DRY RUN: checks passed; nothing built, committed or pushed")
        return

    # 4. build
    p = run("python3", "scripts/build.py")
    print((p.stdout.strip().splitlines() or ["built"])[-1])

    # 5. commit and push
    git("add", "--", *[c for c in allowed if os.path.exists(os.path.join(ROOT, c))])
    git("add", "-A", "site")
    msg = "Add %s %d" % (book, n)
    if trailers:
        msg += "\n\n" + "\n".join(trailers)
    git("commit", "-q", "-m", msg)
    push(branch)
    print("PUSHED %s %s" % (branch, git("rev-parse", "HEAD").stdout.strip()))


def push(branch):
    """Push; if main moved meanwhile (the audio Action pushes to it too), replay the commit on the newest
    main, taking main's side of any conflict in the built site/ and building again."""
    for i in range(4):
        p = git("push", "-u", "origin", "%s:%s" % (branch, branch), check=False)
        if not p.returncode:
            return
        if i == 3:
            sys.exit("FAILED: push\n" + p.stderr)
        if "rejected" in p.stderr or "fetch first" in p.stderr or "non-fast-forward" in p.stderr:
            subject = git("log", "-1", "--format=%s").stdout.strip()
            git("fetch", "origin", "main")
            r = git("rebase", "origin/main", check=False)
            while r.returncode:
                bad = git("diff", "--name-only", "--diff-filter=U").stdout.split()
                if not bad or any(not f.startswith("site/") for f in bad):
                    git("rebase", "--abort", check=False)
                    sys.exit("FAILED: the commit conflicts with the newest main outside site/: %s" % " ".join(bad))
                git("checkout", "--ours", "--", *bad)  # in a rebase, "ours" is main
                git("add", "--", *bad)
                r = run("env", "GIT_EDITOR=true", "git", "rebase", "--continue", check=False)
            if git("log", "-1", "--format=%s").stdout.strip() != subject:
                sys.exit("FAILED: after replaying on the newest main, the commit \"%s\" is gone (main may"
                         " already hold this chapter); nothing pushed" % subject)
            run("python3", "scripts/build.py")
            git("add", "-A", "site")
            if git("diff", "--cached", "--quiet", check=False).returncode:
                git("commit", "-q", "--amend", "--no-edit")
        time.sleep(2 ** (i + 1))


if __name__ == "__main__":
    main()
