# Nightly translation run

This repository is Obay's original English translation of the Bible, published at
https://bible.odownhills.workers.dev (Cloudflare deploys the `site/` folder on every push to main).
Whole chapters are added every day, in canonical order from Genesis 1 to Revelation 22.
Accuracy matters more than speed.

## How much to translate
`python3 scripts/next.py` prints this run's plan: one line per chapter (`<slug> <n> <Book> <estimated words>`),
whole chapters adding up to this run's share of the pace. The pace is set in `data/settings.json`:
`"words_per_week"` (Obay's weekly word target) and `"runs_per_week"` (how many scheduled runs
there are in a week: four each weekday and one each weekend night, spaced so each falls in its
own 5-hour usage window).
Only Obay changes these. If the plan prints `DONE`, stop.

## Steps, repeated for each chapter in the plan, in order
1. Translate the chapter following `TRANSLATION_RULES.md` and the settled renderings in `GLOSSARY.md`
   exactly, and write it to `translations/<slug>/<NNN>.md` (three-digit chapter number).
   The translation must be done by Fable 5.2 at extra-high effort (Obay's explicit requirement):
   delegate it with the Agent tool using `model: "fable"` and `effort: "xhigh"`, one agent per chapter,
   one chapter at a time (not in parallel, so each chapter sees the glossary as the last one left it).
   Tell the agent to read TRANSLATION_RULES.md, GLOSSARY.md and the previous chapter's file (for
   continuity of wording), translate verse by verse from the original text without adapting any
   existing English translation, write the file, run the check, reread the result against the
   original and correct anything added, dropped or softened, and append any newly settled recurring
   term to GLOSSARY.md. Do not translate it yourself on another model.
2. `python3 scripts/check.py translations/<slug>/<NNN>.md` must print OK. If it fails, send the
   failures back to the same translation agent to fix (up to 3 rounds). Never publish a failing file;
   if a chapter cannot pass, stop the run there and report it.
3. `python3 scripts/build.py`
4. Commit on `main` with message `Add <Book> <n>` and push, before starting the next chapter, so
   finished chapters are never lost.

Audio is recorded separately by the GitHub Action in `.github/workflows/audio.yml` after each push
(it uses the repository secret `GEMINI_API_KEY`). Do not record audio in the run. That Action also
pushes to main, so `git pull --rebase origin main` before each push.

## Limits
- Translate only the chapters in this run's plan. Never edit an earlier chapter unless Obay asks.
  If a translator finds that an earlier chapter conflicts with the new one, do not change it:
  say so in the summary.
- Besides new chapter files and the rebuilt `site/`, the only file a run may change is `GLOSSARY.md`,
  by appending lines. Never change a line under "Decided by Obay".
- If usage limits or errors stop the run partway, that is fine: the next night continues from
  the first untranslated chapter.
