# The Bible, Freshly Translated

An original plain-English translation from the Hebrew and Greek, one chapter a night.

- `translations/` chapter sources (see `TRANSLATION_RULES.md` for rules and format)
- `decisions/` the reasons for every bracketed alternate reading, one file per chapter, for Obay's reviews
- `site/` the generated website (Cloudflare Pages output folder, no build command)
- `scripts/build.py` regenerates `site/`; `scripts/check.py` validates a chapter;
  `scripts/next.py` names the next chapter; `scripts/tts.py` records audio with Gemini
- TV mode (`site/tv/`, from `scripts/tv.html`): a chapter's recording with a picture for each part and the words
  lighting up. A chapter has it when `data/tv/<book>/<NNN>.json` (which picture starts at which verse) and its
  pictures in `site/pictures/<book>/<n>/` are there. How the pictures are chosen: `TV_PICTURES.md`.
- Recordings (and later TV-mode pictures) live in the Cloudflare R2 bucket `bible-media`, not in git;
  `worker/index.js` serves them at the same addresses (`/audio/<slug>/<n>.mp3`), see `scripts/media.py`

## The Quran

The same scripts build a second, separate site for an original translation of the Quran from the
Arabic (`WORK=quran python3 scripts/build.py` builds it into `site-quran/`; see `scripts/quran.py`).

- `QURAN_RULES.md`, `QURAN_GLOSSARY.md` rules and settled wordings
- `sources/quran/` the Arabic text it is translated from
- `translations/quran-<surah>/`, `decisions/quran-<surah>/` the parts and the reasons for their bracketed alternates
- `quran/wrangler.jsonc` the Cloudflare Worker that serves `site-quran/`
