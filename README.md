# The Bible, Freshly Translated

An original plain-English translation from the Hebrew and Greek, one chapter a night.

- `translations/` chapter sources (see `TRANSLATION_RULES.md` for rules and format)
- `site/` the generated website (Cloudflare Pages output folder, no build command)
- `scripts/build.py` regenerates `site/`; `scripts/check.py` validates a chapter;
  `scripts/next.py` names the next chapter; `scripts/tts.py` records audio with Gemini
- TV mode (`site/tv/`, from `scripts/tv.html`): a chapter's recording with a picture for each part and the words
  lighting up. A chapter has it when `data/tv/<book>/<NNN>.json` (which picture starts at which verse) and its
  pictures in `site/pictures/<book>/<n>/` are there. How the pictures are chosen: `TV_PICTURES.md`.
- Recordings (and later TV-mode pictures) live in the Cloudflare R2 bucket `bible-media`, not in git;
  `worker/index.js` serves them at the same addresses (`/audio/<slug>/<n>.mp3`), see `scripts/media.py`
