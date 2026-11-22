# Quran translation rules

These are Obay's standing rules for the Quran. Every part follows them exactly. They follow the same
approach as the Bible's rules in `TRANSLATION_RULES.md`; for the Quran this file is the one that governs.

## Translating
- Translate from the original Arabic, verse by verse. The Arabic text is in `sources/quran/<NNN>.txt`,
  one verse per line. Do not adapt or paraphrase an existing English translation.
- Plain, common English. No archaic or fancy words (no "haughty," "exalted," "thee," "thy," "wherein,"
  "behold," "verily," "lo"). Write it the way a clear modern writer would.
- Add nothing, drop nothing, change nothing. Good flow, but fidelity first. Do not supply words the
  Arabic does not have: no parentheses, no inserted explanations of who "they" are or which event is
  meant. Where English grammar needs a small word the Arabic leaves unsaid (a verb "is", a pronoun),
  write it plainly, with no brackets.
- Stay true to the Scripture itself. Do not filter the text through commentary, the reports and
  biographies written later, stories of when a verse came down, legal schools, sects or scholars. Those
  change over the centuries. Translate only what the Arabic says.
- God: the Arabic name for God is "God" (decided by Obay, 2026-11-22). The common noun for a god is
  "god". Pronouns for God are lowercase ("he", "we", "us"), as in the Bible translation; a capital is
  used only for a name or title that stands in place of God's name.
- The main text follows the standard written Arabic text in the Hafs reading, which is the text in
  `sources/quran/`. Where another of the old established readings of the same written letters says
  something different in meaning, give it as an alternate reading. A difference of sound or spelling
  alone is not noted.
- Where the Arabic itself can be read in two ways that say different things, put the best reading in
  the main text and the other in brackets, `[alt: ...]`. How to tell, and how to choose, is under
  "Alternate readings and wording choices" below.
- When wordplay can't survive translation (names, puns, sound echoes), keep the primary sense and add
  a short bracketed note explaining it in English.
- Where the Arabic runs a sentence across a verse break (common in legal passages), keep the sentence
  intact rather than chopping it at the number.
- Numbering is that of the standard text: 114 surahs, 6,236 verses, as in `sources/quran/`. The line
  "In the name of God ..." is verse 1 of Surah 1. At the head of every other surah except Surah 9 it
  stands unnumbered (line `0` in the source file): write it as a `title:` line at the top of the
  surah's first part, worded exactly as 1:1 is worded.
- English only. No Arabic script, and no transliteration anywhere, including inside bracketed notes
  (describe a sound echo in English instead). No translation notes beyond the bracketed alternates
  and wordplay notes.
  - A person or place whose name has an established English form takes it: Moses, Abraham, Noah,
    Mary, Jesus, Gabriel, Pharaoh, Egypt, Babylon. A name with no English form is written in plain
    Latin letters with no accents or marks.
  - A word that has a meaning is translated by that meaning and never carried over as a label: the
    Arabic words behind "Islam" and "Muslim" are "submission" and "one who submits"; so also the words
    for prayer, the giving of alms, fasting, pilgrimage and the like.
  - The single letters that open some surahs (2:1 is the first) are written as the matching English
    capital letters, each with a period ("A. L. M."), followed the first time in a surah by a short
    bracketed note that these are letters of the Arabic alphabet standing on their own.
- Section headings: short editorial labels breaking the part into units of thought.
- Consistency: `QURAN_GLOSSARY.md` lists the default English for each recurring Arabic term. Use it
  wherever it fits, and keep distinct Arabic terms distinct in English. Where another wording fits a
  sentence better, use it (see "Choosing a wording" below).

## Alternate readings and wording choices
The main text is the translation. It is the only thing a listener hears, so it has to be the best
reading on its own. The brackets are for Read mode.

### Two different things
- A real alternate is a place where the Arabic itself can be read in two ways that say different
  things: the old readings differ, the grammar lets the sentence be put together two ways (where a
  pause falls, what a pronoun points back to), or a word has two senses. It gets a bracket,
  `[alt: ...]`, and an entry in the decision log.
- A wording choice is one meaning that English can put two ways: two near-synonyms ("mindful of God",
  "God-fearing"), an idiom word for word or what it means. It gets no bracket. The translator picks
  the wording that fits the sentence best, and it does not have to be the same wording every time.
- The test for a bracket: would a careful reader who saw only the main text miss something the Arabic
  could really mean? If not, write no bracket. Most verses have none; a part of a thousand words
  usually has only a few.
- No standing brackets: never repeat a bracket from part to part for the same word.

### Choosing the main reading of a real alternate
Only the Quran itself is evidence. Check in this order and stop when the answer is clear:
1. The sentences around it: what has just been said, what is said next, and how those spoken to or
   spoken of respond.
2. How the Quran uses the same word or phrase elsewhere.
3. What the rest of the Quran says about the same thing.
4. Where the old readings differ, the main text is always the Hafs reading; another reading can only
   be the alternate.

- Never a reason: that a reading is familiar or unfamiliar; that a translation, a commentary, a
  report handed down, a story of the occasion, a school, a sect or scholars prefer it; that it fits a
  teaching better. Scholars and traditions change; the Scripture does not. Dictionaries and grammars
  are used only as records of what Arabic words and forms can mean, never as judges of which reading
  is right.
- Where the text seems to mean both senses of a word, the main text takes the sense the passage goes
  on to build on, the other sense is the alternate, and a short bracketed note says that the one word
  carries both.
- If the evidence is still near even after all four tests, choose by test 1 and mark the entry
  `close` or `ask` in the decision log.

### Choosing a wording
- Say what the Arabic means in plain English. An idiom, a set phrase that means something other than
  its words, is translated by its meaning. An image the text is drawing on purpose (light and
  darkness, a path, a garden, a sealed heart) stays an image.
- A word in everyday use today is plain English even when it is also a religious word: "prayer",
  "prophet", "angel". The words to avoid are the archaic and fancy ones that nobody uses in ordinary
  speech.
- `QURAN_GLOSSARY.md` gives the default wording for a recurring term. Keep it wherever it fits, so
  that echoes survive and distinct Arabic words stay distinct. Where another wording fits a sentence
  better, use it, with no bracket.

### Obay's reviews
Obay reviews the decision log from time to time and switches any call he disagrees with. His call is
final for that verse, and the reason he gives becomes a rule for similar verses: add it under
"Decided by Obay" in `QURAN_GLOSSARY.md`. Never wait for a review before publishing a part.

## Parts and file format
A short surah is one part. A long surah is published in several parts of about 1,000 English words
each (500 to 1,500), cut where the subject changes and never inside a sentence. Each part is a page
of the site with its own recording and pictures, the way a Bible chapter is. The parts of each surah
are planned in `data/quran.json` (`"parts": [[first verse, last verse], ...]`).

One file per part: `translations/quran-<surah>/<NNN>.md` (three-digit part number, e.g.
`translations/quran-2/003.md`).

```
---
surah: 2
part: 1
verses: 1-29
---
title: In the name of God ...
## Section heading
1 Verse one text.
2 Verse two text.

3 A blank line starts a new paragraph.
```

- Every verse is on its own line, starting with its number and a space. Every verse in the part's
  range must be present, in order.
- `## ` starts a section heading.
- `title: ...` is the unnumbered opening line of a surah (first part only; none in Surah 1 or 9).
- Brackets: `[alt: ...]` for alternate readings, any other `[...]` for a short note. Do not nest
  brackets.

## Decision log
Every `[alt: ...]` in a part has an entry in `decisions/quran-<surah>/<NNN>.md`, written with the
part. Obay reads these to review the calls, so write them for him: plain English, no Arabic script, no
transliteration, and reasons he can look up in the Quran. A part with no brackets needs no file.

```
---
surah: 1
part: 1
---
## 1:4 Master of the Day of Judgment | King of the Day of Judgment
kind: readings differ
call: clear
why: (what in the Quran supports the main text, with verse numbers)
other: (what in the Quran supports the alternate, with verse numbers)
review: open
```

- Heading: `## <surah>:<verse> <main text wording> | <alternate wording>`. One entry for each
  bracket, in the order of the part.
- `kind:` is `readings differ` (the old established readings of the written text differ), `grammar`
  (the sentence can be put together two ways), `two senses` (a word or phrase has two meanings) or
  `both meant` (the text seems to intend both senses).
- `call:` is `clear`, `close` (the evidence is near even) or `ask` (near even, and the meaning changes
  enough that Obay should see it first). At most three `ask` entries in a part.
- `why:` what in the Quran supports the main text. `other:` what supports the alternate. Each is one
  line.
- `review:` starts as `open`. Only Obay's reviews change it, to `kept by Obay <date>` or
  `switched by Obay <date>: <his reason>`.
