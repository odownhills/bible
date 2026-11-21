# Nightly translation run

This repository is Obay's original English translation of the Bible, published at
https://bible.odownhills.workers.dev (Cloudflare deploys the `site/` folder on every push to main).
Whole chapters are added every day. Books listed in `"first_books"` in `data/settings.json` come first
(currently Job, then John; 1 John is done); after them the run continues in canonical order from the first
untranslated chapter, Genesis 1 to Revelation 22.
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
   continuity of wording; for a book's first chapter, the last chapter translated), translate verse by verse from the original text without adapting any
   existing English translation, write the file, run the check, reread the result against the
   original and correct anything added, dropped or softened, and append any newly settled recurring
   term to GLOSSARY.md. Do not translate it yourself on another model.
   The same agent writes the chapter's decision log, `decisions/<slug>/<NNN>.md`: one entry for every
   `[alt: ...]` in the chapter, in the format at the end of TRANSLATION_RULES.md. A bracket is only
   for a real alternate; two English wordings of one meaning get no bracket and no log entry.
   Reasons in the log point to Scripture, never to scholars, translations or tradition.
2. `python3 scripts/check.py translations/<slug>/<NNN>.md` must print OK (it also checks the
   decision log against the chapter's brackets). If it fails, send the
   failures back to the same translation agent to fix (up to 3 rounds). Never publish a failing file;
   if a chapter cannot pass, stop the run there and report it.
3. `python3 scripts/build.py`
4. Commit on `main` with message `Add <Book> <n>` and push, before starting the next chapter, so
   finished chapters are never lost. The commit includes the chapter's decision log.

Obay reviews the decision logs from time to time. Never wait for him: publish, and end the run's
summary with the new chapters' `call: ask` entries (verse, the two readings, one line of why).

Audio is recorded separately by the GitHub Action in `.github/workflows/audio.yml` after each push
(it uses the repository secret `GEMINI_API_KEY`); the same Action then runs `scripts/align.py`, which
times every word of each recording for the Listen + Read mode on chapter pages. Do not record audio
or run the alignment in the run. Recordings are stored in the Cloudflare R2 bucket `bible-media`
(`scripts/media.py`, listed in `data/audio.json`), never in git. That Action also
pushes to main, so `git pull --rebase origin main` before each push.

## Limits
- Translate only the chapters in this run's plan. Never edit an earlier chapter unless Obay asks.
  If a translator finds that an earlier chapter conflicts with the new one, do not change it:
  say so in the summary.
- Besides new chapter files, their decision logs and the rebuilt `site/`, the only file a run may
  change is `GLOSSARY.md`, by appending lines. Never change a line under "Decided by Obay", and never
  change a `review:` line that Obay has set in a decision log.
- If usage limits or errors stop the run partway, that is fine: the next night continues from
  the first untranslated chapter.
