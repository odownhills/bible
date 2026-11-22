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
- TV mode (`scripts/tv.js`, the TV page `site/tv/`): a chapter's recording, full screen, with a picture for each
  part of it and the words lighting up as they are read. A chapter has pictures when its scene plan
  `data/tv/<slug>/<NNN>.json` is here and all of its pictures are listed in `data/pictures.json`; any other
  recorded chapter plays in TV mode with its words alone. The pictures are made and chosen on the picture
  branch (`TV_PICTURES.md` has the rules); `.github/workflows/tv.yml` runs `scripts/tv_publish.py`, which
  brings each finished chapter here: pictures to the bucket, plan and picture list to main
