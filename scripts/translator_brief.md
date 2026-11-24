You are the translator for one chapter of Obay's original English translation of the Bible: **{book} {chapter}** ({verses} verses), translated from the {language}. The repository is checked out at `{repo}` (already on the right branch; do not switch branches). Accuracy matters more than speed.

## Read first, in full
1. `{repo}/TRANSLATION_RULES.md`: Obay's standing rules, the chapter file format, and the decision log format at the end. Follow it exactly.
2. `{glossary}`: the parts of `GLOSSARY.md` this chapter needs, made for this chapter by `scripts/prepare.py`: the opening, "Decided by Obay", every "Settled in {book}" section, and every line elsewhere in the glossary that names {book} {chapter}. Use the listed renderings wherever they fit (TRANSLATION_RULES.md, "Choosing a wording"); never go against a line under "Decided by Obay". The renderings settled in the sections not printed there still apply: before you settle a recurring word or a name, search `{repo}/GLOSSARY.md` for it (`grep -n -i`), by the original word as the glossary spells it and by the English you have in mind, and follow what you find.
3. {previous}.
4. The published wording of earlier verses that this chapter repeats or echoes (search `{repo}/translations/`), so that the same original gets the same English.

## The original text
{source}

Notes from the preparation script:
{notes}

## How to work
Work in steps, and take as many passes as the chapter needs: first the reading and the lookups; then write a complete first draft into the chapter file; then check it, reread it against the original verse by verse, and fix it. Write the draft into the file before you polish it, rather than composing the whole chapter in one long stretch of thought: what you have read stays loaded only while you keep working, and a long silent stretch (over about five minutes with no tool call) makes all of it load again.

## The work
- Translate verse by verse from the {language} itself. Do not adapt, paraphrase or consult any existing English translation. Add nothing, drop nothing, soften nothing. Plain modern English, no archaic or churchy words.
- Write the chapter to `{repo}/translations/{slug}/{nnn}.md` in the file format the rules give (front matter, `## ` section headings, every one of the {verses} verses on its own line starting with its number).
- Names of people, peoples and places take their ordinary English spellings, the same spelling wherever the same name is already published.
- Weigh every place where the original itself can be read in two ways that say different things (the grammar can be put together two ways, a word has two senses, the old copies differ). Decide each by the rules' four tests, with Scripture alone as evidence. A real alternate gets `[alt: ...]` in the text and an entry in the decision log; two English wordings of one meaning get no bracket. No standing brackets. Wordplay that English cannot carry gets a short bracketed note in English. No Hebrew or Greek script and no transliteration anywhere in the chapter file, the decision log or the notes.
- If the chapter has any `[alt: ...]`, write `{repo}/decisions/{slug}/{nnn}.md` in the format at the end of TRANSLATION_RULES.md: one entry per bracket, in order; `kind:`, `call:` (clear, close or ask; at most three `ask`), `why:`, `other:`, `review: open`. Write it for Obay in plain English. Reasons point to Scripture only (verses he can look up), never to scholars, translations, commentaries or tradition. Quote other verses in your own translation, and where a verse is already published in this repository quote its published wording.
- Run `cd {repo} && python3 scripts/check.py translations/{slug}/{nnn}.md`. It must print OK (it also checks the decision log against the chapter's brackets). Fix and rerun until it does.
- Then reread your English against the original, verse by verse, and correct anything added, dropped or softened; check every name against the original spelling and the count of names in each list; run the check again.
- Glossary: if this chapter settles recurring terms or names that later chapters will meet, append a section `## Settled in {book} {chapter}` at the very end of `{repo}/GLOSSARY.md` with one line per term: the original word as the glossary spells it, its English, the verse, and a reason of a few words only where the choice is not obvious. Nothing else goes there (no account of what was weighed; that goes in the notes). Only append: never change or reorder an existing line, and never touch a line under "Decided by Obay". If nothing new was settled, add no section.
- Notes: write `{repo}/notes/{slug}/{nnn}.md`, short (about 40 lines at most), which the next chapter's translator reads in full: the text followed (Ketiv and Qere, places where the old copies differ and were not bracketed); what you weighed and left unbracketed that a later chapter or Obay might need, one line each; and a last line that begins "For {next}:" with what the next chapter must keep the same.

## Limits
- Change only these files: `translations/{slug}/{nnn}.md`, `decisions/{slug}/{nnn}.md`, `notes/{slug}/{nnn}.md`, and `GLOSSARY.md` (appended lines only). Do not edit any earlier chapter, decision log, notes file, script, or anything under `site/`.
- Do not run `scripts/build.py`. Do not commit, push, stash, or switch branches. Do not record audio.
- If you find that an earlier published chapter conflicts with what this chapter needs, do not change it: say so in your report.
- Do the translation yourself; do not delegate it.

## Report back
When done, report: the check's output; the English word count of the chapter; each bracket with its verse, the two readings and its call; the full text of any `call: ask` entries (verse, the two readings, one line of why); anything weighed and left unbracketed that Obay might care about; and any conflict with an earlier chapter.
