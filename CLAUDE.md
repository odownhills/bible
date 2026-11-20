# Nightly translation run

This repository is Obay's original English translation of the Bible, published at the
Cloudflare Pages site built from `site/`. One chapter is added each night, in canonical
order from Genesis 1 to Revelation 22. Accuracy matters more than speed.

## Steps for each run
1. `python3 scripts/next.py` prints the next chapter (`<slug> <n> <Book>`). If it prints `DONE`, stop.
2. Translate that chapter following `TRANSLATION_RULES.md` exactly, and write it to
   `translations/<slug>/<NNN>.md` (three-digit chapter number).
   The translation must be done by Fable 5.2 at extra-high effort (Obay's explicit requirement):
   delegate it with the Agent tool using `model: "fable"` and `effort: "xhigh"`, giving the agent
   TRANSLATION_RULES.md and the target path. Do not translate it yourself on another model.
3. `python3 scripts/check.py translations/<slug>/<NNN>.md` must print OK. If it fails, send the
   failures back to the same translation agent to fix (up to 3 rounds). Never publish a failing file.
4. `python3 scripts/build.py`
5. Audio is recorded separately by the GitHub Action in `.github/workflows/audio.yml` after you push
   (it uses the repository secret `GEMINI_API_KEY`). You do not need to record audio in the run.
6. Commit on `main` with message `Add <Book> <n>` and push. Cloudflare Pages deploys on push.

Only add one chapter per run. Never edit an earlier chapter unless Obay asks.
