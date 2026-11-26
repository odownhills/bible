# Nightly translation run

This repository is Obay's original English translation of the Bible, published at
https://bible.odownhills.workers.dev (Cloudflare deploys the `site/` folder on every push to main).
Whole chapters are added every day, in the order of the English Bible, Genesis 1 to Revelation 22: each run
takes the first chapters that are not translated yet (Obay, 2026-11-23: "start from beginning of Bible and
continue in order"; that began at Genesis 6). Chapters done earlier out of order are passed over when the
run reaches them: Deuteronomy 5, Job 1 to 21, John 1 to 6, 1 John and Jude.
(Books listed in `"first_books"` in `data/settings.json` would come before the rest; the list is empty now.
Only Obay changes the order.)
Accuracy matters more than speed.
(The Quran is a separate translation and site built from this repository: see "Quran" below.
Bible runs leave it alone. So is the study site, which analyzes the Bible's chapters: see "Study site" at the end.)

## How much to translate
`python3 scripts/next.py` prints this run's plan: one line per chapter (`<slug> <n> <Book> <estimated words>`),
whole chapters adding up to this run's share of the pace. The pace is set in `data/settings.json`:
`"words_per_week"` (Obay's weekly word target) and `"runs_per_week"` (how many scheduled runs
there are in a week: four each weekday and one each weekend night, spaced so each falls in its
own 5-hour usage window).
Only Obay changes these. If the plan prints `DONE`, stop.

## Steps, repeated for each chapter in the plan, in order
Obay decided on 2026-11-24 to cut the Fable use per chapter (about a third of it went to publishing,
and every chapter read the whole glossary): Fable translates and does nothing else, the run around it
may be any model (a project thread runs on Opus 5.5 at extra-high effort), and the translator reads only
what the chapter needs. The translation rules and the decision log are unchanged.

1. Prepare: `python3 scripts/prepare.py <slug> <n>` writes, outside the repository, the Hebrew text of
   the chapter and of the chapters on either side (Westminster Leningrad Codex, with Ketiv, Qere and
   paragraph marks), `glossary.md` (the parts of GLOSSARY.md this chapter needs: the opening, "Decided by
   Obay", every section of this book, and every line elsewhere that names this chapter), and `brief.md`,
   the translator's brief (`scripts/translator_brief.md` filled in), and prints their paths. For a New
   Testament chapter, first put the Greek text where its note says.
2. Translate: the translation must be done by Fable 5.2 (Obay's explicit requirement), at high effort
   (Obay, 2026-11-24: "move to fable high as well with test"; extra-high before. The test on
   Genesis 8 that day, never published, cost about half of extra-high and found the same alternate as the
   published chapter: /mnt/project-files/translation-cost/genesis-8-test/). Delegate it with the Agent tool using
   `model: "fable"` and `effort: "high"`, one agent per chapter, one chapter at a time (not in parallel,
   so each chapter sees the glossary as the last one left it), with the prompt
   `Read <path of brief.md> and follow it.` Do not translate it yourself on another model, and do not
   change the wording yourself afterward. The brief has the agent read TRANSLATION_RULES.md, the
   glossary extract (searching GLOSSARY.md itself before settling any recurring word or name) and the
   previous chapter with its notes; translate verse by verse from the original text without adapting
   any existing English translation, in steps (a full draft into the file, then check, reread against
   the original and correct anything added, dropped or softened); write the decision log,
   `decisions/<slug>/<NNN>.md`, one entry for every `[alt: ...]` in the format at the end of
   TRANSLATION_RULES.md (a bracket is only for a real alternate; reasons point to Scripture, never to
   scholars, translations or tradition); append one line per newly settled recurring term to
   GLOSSARY.md; and write short notes for the next chapter, `notes/<slug>/<NNN>.md` (what was weighed
   and left unbracketed, and a last line "For <next chapter>:").
3. `python3 scripts/check.py translations/<slug>/<NNN>.md` must print OK (it also checks the
   decision log against the chapter's brackets). If it fails, send the
   failures back to the same translation agent to fix (up to 3 rounds). Never publish a failing file;
   if a chapter cannot pass, stop the run there and report it.
4. Publish, before starting the next chapter, so finished chapters are never lost:
   `python3 scripts/publish.py <slug> <n> --branch <branch> --trailer "<line>" ...` runs the check again,
   carries the chapter's files onto the newest main, refuses any change a run may not make (see Limits),
   runs `scripts/build.py`, and commits `Add <Book> <n>` (the chapter, its decision log, its notes, the
   glossary lines and the rebuilt `site/`) and pushes it to `<branch>`: `main` where the run may push
   main, otherwise its own branch, merged into main by a pull request. After the merge,
   `python3 scripts/publish.py --live <slug> <n>` waits until the page is live.

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
- Besides new chapter files, their decision logs, their notes (`notes/<slug>/<NNN>.md`) and the
  rebuilt `site/`, the only file a run may
  change is `GLOSSARY.md`, by appending lines. Never change a line under "Decided by Obay", and never
  change a `review:` line that Obay has set in a decision log.
- If usage limits or errors stop the run partway, that is fine: the next night continues from
  the first untranslated chapter.

# Quran

This repository also holds Obay's translation of the Quran, published as its own site at
https://quran.odownhills.workers.dev (a second Cloudflare Worker, `quran/wrangler.jsonc`, which deploys
the `site-quran/` folder on every push to main). The two sites do not link to each other, except through search (see "Search" at the end). A Bible run
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
`sources/quran/`, and an English | Arabic switch on every page. `WORK=quran python3 scripts/build.py`
builds those pages too (`scripts/quran_ar.py`). The Arabic is read aloud only in a plain, ordinary
speaking voice, never chanted or recited in the traditional way (Obay: "plain, honest scripture, no
tradition"): Gemini's Sulafat, read by its own GitHub Action (`.github/workflows/arabic-voice.yml`,
`scripts/arabic_voice.py`) on a model with its own free daily limit. It started at Surah 2 verse 75;
Surah 1 and 2:1-74 come next (Obay, 2026-11-22), then the rest in order. Until a surah is read, its
Arabic page is text only. A Quran run needs to do nothing for them.

The Arabic is shown in modern spelling by default (Obay, 2026-11-23: "default will be new arabic"), in an
everyday font (Noto Naskh Arabic) with plain verse numbers: the Tanzil Project's text in
`sources/quran-modern/`, the same verses and words as `sources/quran/`. A Modern | Traditional switch on the
Arabic pages keeps the traditional Uthmani script one tap away (`ar/<n>-uthmani.html`). The recordings are
read and timed from the traditional text; the modern pages light up their own words with the same times
(`scripts/quran_ar.py`). Translation still works from `sources/quran/`, as QURAN_RULES.md says.

## Limits
- A Quran run changes only new part files, their decision logs, the rebuilt `site-quran/`, lines
  appended to `QURAN_GLOSSARY.md`, and `data/quran.json` when a surah is planned.
- Never edit `sources/quran/` or `sources/quran-modern/`, an earlier part, a line under "Decided by Obay", or a `review:` line
  that Obay has set.

# Study site

A third site built from this repository: an analysis of each published Bible chapter, section by
section (what it means, and the related Scripture), at https://analysis.odownhills.workers.dev (a third
Cloudflare Worker, named `analysis`, which deploys the `site-study/` folder on every push to main).
That Worker's build has no "Root directory", so Cloudflare builds it from the top `wrangler.jsonc`, the
Bible's: the build step there, `scripts/ci_site.js`, gives the Worker named `analysis` the `site-study/`
folder in the place of `site/` and changes nothing for the `bible` Worker. Never take that step out.
(`study/wrangler.jsonc` is the other way to deploy it, for a Worker whose Root directory is `study/`. The
Worker named `study` was set up for that on 2026-11-22 and has never deployed that way: its address,
study.odownhills.workers.dev, is not the site.)
A Bible run and a Quran run never touch it, and nothing above applies to it: an analysis run follows
this section. There is no schedule for it yet. A chapter is analyzed when Obay asks (so far: 1 John 3,
as a test).

The analysis never changes the translation. It is written from the chapter as published.

## Steps, repeated for each chapter, in order
1. Follow `ANALYSIS_RULES.md` exactly (it lists what to read first) and write
   `analysis/<slug>/<NNN>.md`. Only a published chapter can be analyzed.
   The analysis is written by Opus 5.5 at extra-high effort (Obay, 2026-11-22: the analysis matters as
   much as the translation, and Opus 5.5 at extra-high effort is the model he accepted for it; the
   1 John 3 test was written by Fable 5.2). A thread that was started as Opus 5.5 at extra-high effort
   does it itself. Any other run delegates the whole of this step with the Agent tool using
   `model: "opus"` and `effort: "xhigh"`, one agent per chapter.
   The writer argues from the Hebrew, Aramaic or Greek directly, not from the English. A related
   passage from a chapter that is already published is never translated again: the site pulls the
   published wording. Only a passage that is not published yet is translated fresh, by the same writer.
   That is the one case where Opus translates: Bible and Quran chapters are still translated only by
   Fable 5.2 at extra-high effort.
2. `python3 scripts/study.py check analysis/<slug>/<NNN>.md` must print OK. If it fails, fix the
   failures (up to 3 rounds). Never publish a failing file. Then reread the analysis against the chapter
   and against every passage it quotes or names, and take out anything the text does not say.
3. `python3 scripts/study.py` rebuilds `site-study/`. The Bible site never links to the analysis (Obay,
   2026-11-25: "the Bible site should be pure Bible and plain. No analysis, only honest translation"); the
   analysis site may link to the translation.
4. Commit on `main` with message `Add analysis: <Book> <n>`, `git pull --rebase origin main`, and push.

## Limits
- An analysis run changes only new files under `analysis/` and the rebuilt `site-study/`.
  It never edits a translation, a decision log, a glossary or an earlier analysis unless Obay asks.
- `ANALYSIS_RULES.md` is Obay's prompt for this work and is improved over time: change it only when he asks.

# Search

Every build also writes its own site's search index (`scripts/search.py`): `python3 scripts/build.py` into
`site/search/`, `WORK=quran python3 scripts/build.py` into `site-quran/search/`, and `python3 scripts/study.py`
into `site-study/search/`. Each site's search page (`/search/`) searches all three sites, except the Bible site's, which leaves out the analysis (Obay, 2026-11-25). A run does nothing extra
for it: the index is part of the rebuilt site folder it already commits. Never edit those files by hand; if a
rebase conflicts in them, take main's and rebuild.

# Offline reading

Both the Bible and Quran sites work with no connection (Obay, 2026-11-26). Every build writes `offline.js`,
`offline.html` and `sw.js` (the service worker, from `scripts/offline.js` and `scripts/sw.js`) into the site it
builds, and every page loads `offline.js`. Pages and their small files are always asked of the site first, so a new
chapter or build shows up at once; a copy is kept for when there is no signal. A chapter's recording and Watch
pictures are kept only when the reader presses "Save for offline". A run does nothing extra for it; never edit those
built files by hand. To switch it off for every reader, see the comment at the top of `scripts/sw.js`.
