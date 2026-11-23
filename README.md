# The Bible, Freshly Translated

An original plain-English translation from the Hebrew and Greek, one chapter a night.

- `translations/` chapter sources (see `TRANSLATION_RULES.md` for rules and format)
- `decisions/` the reasons for every bracketed alternate reading, one file per chapter, for Obay's reviews
- `site/` the generated website (Cloudflare Pages output folder, no build command)
- `scripts/build.py` regenerates `site/`; `scripts/check.py` validates a chapter;
  `scripts/next.py` names the next chapter; `scripts/tts.py` records audio with Gemini
- Recordings and TV mode pictures live in the Cloudflare R2 bucket `bible-media`, not in git;
  `worker/index.js` serves them at the same addresses (`/audio/<slug>/<n>.mp3`, `/pictures/<slug>/<n>/...`),
  see `scripts/media.py`
- Watch (called "TV mode" until 2026-11-23; code, data and pictures keep the name `tv`): `scripts/tv.js` plays a
  chapter's recording full screen, with a picture for each part of it and the words lighting up as they are read.
  Every recorded chapter has a Watch button. The Watch pages browse like the reading pages: `site/watch/` lists the
  books, `site/watch/<slug>/` a book's chapters (the Quran's `site-quran/watch/` and `ar/watch.html` list its
  surahs); the old addresses `site/tv/` and `ar/tv.html` send readers on to them. A chapter has pictures when its
  scene plan `data/tv/<slug>/<NNN>.json` is here and all of its pictures are listed in `data/pictures.json`; any
  other recorded chapter plays with its words alone. The pictures are made and chosen on the picture
  branch (`TV_PICTURES.md` has the rules); `.github/workflows/tv.yml` runs `scripts/tv_publish.py`, which
  brings each finished chapter here: pictures to the bucket, plan and picture list to main

## The Quran

The same scripts build a second, separate site for an original translation of the Quran from the
Arabic (`WORK=quran python3 scripts/build.py` builds it into `site-quran/`; see `scripts/quran.py`).

- `QURAN_RULES.md`, `QURAN_GLOSSARY.md` rules and settled wordings
- `sources/quran/` the Arabic text it is translated from
- `translations/quran-<surah>/`, `decisions/quran-<surah>/` the parts and the reasons for their bracketed alternates
- `quran/wrangler.jsonc` the Cloudflare Worker that serves `site-quran/`

## The study site

A third site: an analysis of each published Bible chapter, section by section, with the related Scripture
(`python3 scripts/study.py` builds it into `site-study/`).

- `ANALYSIS_RULES.md` the rules for an analysis
- `analysis/<book-slug>/<NNN>.md` one analysis per chapter, beside `translations/<book-slug>/<NNN>.md`
- `study/wrangler.jsonc` the Cloudflare Worker that serves `site-study/`

## Search

Every page of the three sites has a search button (the magnifier in the top bar), which opens `/search/`.
One search covers all three sites: verses of the Bible, verses of the Quran (English, and the Arabic of
every surah when the search is typed in Arabic) and sections of the study notes, each linked to its place.
It runs in the reader's browser with no server and no cost per search (`scripts/search.js`). Each site's
build writes its own index into `site/search/`, `site-quran/search/` or `site-study/search/`
(`scripts/search.py` describes the files), so new chapters are searchable as soon as they are published.
The `_headers` file in each site folder lets the other two sites read that index.
