# Analysis rules

The study site gives each chapter of the translation a short analysis, section by section: what the
passage means, and the other places in Scripture that light it up. These rules began as Obay's
"Universal Biblical Analysis Prompt" (2026-11-22) and are meant to be improved over time. Lines marked
(pick) are the translator's recommendations, in force until Obay decides otherwise. Lines marked
(Obay, date) are his decisions.

The analysis never changes the translation. It is written after a chapter is published, from the
chapter as published, and an analysis run never edits a file under `translations/` or `decisions/`.

## Before writing
Read, in this order: these rules; the chapter in `translations/<slug>/<NNN>.md` and its decision log if it
has one; the original Hebrew, Aramaic or Greek of the chapter; the chapters before and after it (one to
three each way, more for the first analysis in a book); and the analyses already written for the book,
so that points are not repeated and threads are picked up. Work slowly. Depth matters more than speed.

## What a chapter's analysis holds
1. An opening of 40 to 80 words: where the chapter stands in its book and what it is doing. One
   opening for the chapter, not one for each section. (pick)
2. One section for each section of the translation, under the same heading, in the same order. A
   chapter the translation does not divide is analyzed all at once. (pick)
3. In each section, the deep meaning: what the passage is saying underneath its surface, anchored to
   verse numbers. For narrative, the plot and what moves the people in it. For poetry, prophecy and
   law, the images and what the passage is for. Say the thing a careful reader would miss: a word the
   writer repeats, a turn in the argument, what is left unsaid, how one verse answers another.
4. In each section, related Scripture: the one or two passages that most light up this section, one
   from each Testament when both truly fit. Never a weak link added to fill a slot. (pick)

## Evidence
- Only Scripture is evidence for what a passage means: the chapter itself, the original words, the
  rest of the book, and the rest of Scripture. This is the same rule as for the translation. (pick)
- Work from the original language (Obay, 2026-11-22): the meaning is argued from the Hebrew, Aramaic
  or Greek directly, never from the English. The translation gives the page its sections and the
  wording quoted to the reader. It is not the evidence.
- Never a reason: what scholars, commentaries, translations, churches or traditions say. Do not name
  them. Do not summarize a denomination's view.
- Outside history (dates, places, customs, who ruled) may appear only as plain background, only when
  it is not in doubt, and it never decides what a verse means. Prefer the setting the book itself
  gives.
- No speculation. Every claim must be something the reader can check in the text. A claim about the
  original language (a repeated word, a word used only here, a play on words) must be true of the
  Hebrew or Greek and is stated in plain English, with no Hebrew or Greek script and no
  transliteration. If a point cannot be shown from the text, leave it out.
- Where the chapter has an `[alt: ...]` that changes the meaning of the section, say what each reading
  would mean. Do not argue for a reading the translation did not choose.

## Related Scripture
- A related passage is whole verses, given by its address: `### John 1:10-13`.
- If that chapter is already published in this translation, write no quote. The site shows the
  published wording (its main text) and links to it. (Obay, 2026-11-22)
- If it is not published yet, translate the verses fresh from the Hebrew or Greek, by
  `TRANSLATION_RULES.md` and the settled wordings in `GLOSSARY.md`, main text only, with no brackets.
  Translate from the original, never from an English version. When that chapter is published later,
  the site switches to the published wording by itself, so do not build the connection on an English
  word that the glossary has not settled.
- After the quote, one to three sentences on the connection itself: the shared word or phrase, the
  promise and its fulfilment, the contrast, the earlier story the writer has in mind. Say what the
  link is, not just that there is one.
- Other passages may be mentioned inside the deep meaning by address alone (`John 3:19-20`), sparingly.
- Check every address and every quote against the text before publishing: the verse must exist and
  must say what the analysis says it says.

## Language
- Modern, everyday English at a high-school reading level. Short sentences. No archaic words and no
  heavy theological terms: say the thing itself.
- YHWH is "Yahweh", as in the translation. (pick)
- Quote the chapter in the translation's own wording, in quotation marks, and only in short phrases.
  Do not reprint the chapter.
- Do not preach and do not apply the passage to the reader's life. Say what the text says and
  means, and let it stand.

## Length
The analysis's own words (everything except the quoted related Scripture) come to about the length of
the chapter itself: between three quarters and one and a third of the chapter's word count. (pick)
Depth comes from choosing the points that matter, not from more words.

## File format
`analysis/<book-slug>/<NNN>.md`, beside the chapter it belongs to:

```
---
book: 1 John
chapter: 3
---
The opening paragraph.

## Children of God
The deep meaning, in one or more paragraphs.

### John 1:10-13
The connection. (This chapter is published, so there is no quote.)

### Hosea 1:10
> 10 A fresh translation, each verse on its own line starting with its number.
The connection.
```

- `## ` is a section heading, word for word the translation's heading.
- `### ` starts a related passage: the book's name as in `data/books.json`, then `chapter:verse` or
  `chapter:first-last`.
- `> ` lines are the quote of a passage that is not published yet.

## Checking and publishing
1. `python3 scripts/study.py check analysis/<slug>/<NNN>.md` must print OK. It checks the sections
   against the translation, every address, the quotes, the length, and the banned words.
2. `python3 scripts/study.py` rebuilds `site-study/`.
3. Commit the analysis file and the rebuilt `site-study/` with the message `Add analysis: <Book> <n>`.
