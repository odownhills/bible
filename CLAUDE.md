# Nightly translation run

This repository is Obay's original English translation of the Bible, published at
https://bible.odownhills.workers.dev (Cloudflare deploys the `site/` folder on every push to main).
Whole chapters are added every day. Books listed in `"first_books"` in `data/settings.json` come first
(currently Job, then John; 1 John is done); after them the run continues in canonical order from the first
untranslated chapter, Genesis 1 to Revelation 22.
Accuracy matters more than speed.
(The Quran is a separate translation and site built from this repository: see "Quran" at the end.
Bible runs leave it alone.)

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

# Quran

This repository also holds Obay's translation of the Quran, published as its own site at
https://quran.odownhills.workers.dev (a second Cloudflare Worker, `quran/wrangler.jsonc`, which deploys
the `site-quran/` folder on every push to main). The two sites do not link to each other. A Bible run
never touches the Quran, and nothing above applies to it: a Quran run follows this section.
There is no schedule for it yet. Quran parts are translated when Obay asks (so far: Surahs 1 and 2).

A short surah is one part. A long surah is published in parts of about a thousand English words,
planned in `data/quran.json`. `python3 scripts/quran.py` prints the next part
(`quran-<surah> <NNN> verses <first>-<last> about <n> words`), or `DONE`, or `PLAN surah <n>` when the
next surah has no parts planned. Plan it first then: read its Arabic in `sources/quran/<NNN>.txt`, cut
where the subject changes and never inside a sentence, 500 to 1,500 English words a part, and add
`"name"` (the surah's name in English) and `"parts"` for it to `data/quran.json`.

## Steps, repeated for each part, in order
Obay decided on 2026-11-22 that each part of a long surah is translated in its own fresh thread, one
part after another and never two at once, and that the translator has the whole surah in view. So a
thread translates one part (the next one `scripts/quran.py` prints), publishes it and stops.

1. Before translating, read in full: `QURAN_RULES.md`; `QURAN_GLOSSARY.md`; the Arabic of the whole
   surah in `sources/quran/<NNN>.txt` (all of it, so that the part is translated knowing where the
   surah is going and how its words recur); every part of this surah translated so far
   (`translations/quran-<surah>/`) and their decision logs (`decisions/quran-<surah>/`); and Surah 1
   (`translations/quran-1/001.md`), whose wording recurs everywhere.
   Then translate only this part, verse by verse from the Arabic without adapting any existing English
   translation, into `translations/quran-<surah>/<NNN>.md`, with its decision log
   `decisions/quran-<surah>/<NNN>.md`. Reasons in the log point to the Quran itself, never to
   scholars, commentaries, translations or tradition. Reread the result against the Arabic and
   correct anything added, dropped or softened, and append any newly settled recurring term to
   QURAN_GLOSSARY.md under a heading for the surah.
   The translation must be done by Fable 5.2 at extra-high effort (Obay's explicit requirement). A
   thread that was started as Fable 5.2 at extra-high effort to translate this one part does it
   itself. Any other run delegates the whole of this step with the Agent tool using `model: "fable"`
   and `effort: "xhigh"`, one agent per part, and gives the agent this step's reading list.
2. `python3 scripts/check.py translations/quran-<surah>/<NNN>.md` must print OK. If it fails, fix the
   failures (the translator fixes its own; up to 3 rounds). Never publish a failing file; if a part
   cannot pass, stop and report it.
3. `WORK=quran python3 scripts/build.py`
4. Commit on `main` with message `Add Quran <surah>:<first>-<last>` (`Add Quran <surah>` when the part
   is the whole surah), `git pull --rebase origin main`, and push. The commit holds the part, its
   decision log, the glossary lines and the rebuilt `site-quran/`.

End the summary with the new part's `call: ask` entries, as for the Bible, and say which part comes
next (`python3 scripts/quran.py`). If the new part shows that an earlier part should be worded
differently, do not change the earlier part: say so in the summary. Audio is recorded by the same
GitHub Action (Bible chapters first, then the Quran's parts), and pictures are made afterward by
other threads; neither ever changes the text.

Pace (Obay, 2026-11-22): about 15,000 English words of the Quran a week, with the Bible at about
30,000. Surah 1 and all of Surah 2 (about 12,000 words) are to be done straight through.

Readers never see the parts (Obay, 2026-11-22): the site shows each surah as one page with a list of its
sections to jump between (`scripts/quran_site.py`), and the same audio Action joins a surah's recorded
parts into one recording (`scripts/quran_join.py`). A Quran run needs to do nothing for this.

The Quran site also shows the Arabic alone (Obay, 2026-11-22): every surah's Arabic text from
`sources/quran/` with a human reciter's voice, Listen + Read and TV mode, and an English | Arabic switch
on every page. `WORK=quran python3 scripts/build.py` builds those pages too (`scripts/quran_ar.py`), and
the recitation is fetched by its own GitHub Action (`.github/workflows/recitation.yml`, `scripts/recite.py`).
A Quran run needs to do nothing for them.

## Limits
- A Quran run changes only new part files, their decision logs, the rebuilt `site-quran/`, lines
  appended to `QURAN_GLOSSARY.md`, and `data/quran.json` when a surah is planned.
- Never edit `sources/quran/`, an earlier part, a line under "Decided by Obay", or a `review:` line
  that Obay has set.
