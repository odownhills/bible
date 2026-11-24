# Translation rules

These are Obay's standing rules. Every chapter follows them exactly.

## Translating
- Translate from the original text: the Hebrew Masoretic Text for the Old Testament (Aramaic portions of Daniel and Ezra from the Aramaic), the Greek for the New Testament. Do not adapt or paraphrase an existing English translation.
- Plain, common English. No archaic or churchy words (no "behold," "thee," "thy," "hearken," "iniquity," "begat," "lo," "verily"). Write it the way a clear modern writer would.
- Add nothing, drop nothing, change nothing. Good flow, but fidelity first. Stay true to Scripture. Do not filter the text through church tradition, doctrine, or commentary. Only translate the Scripture itself.
- Divine names: YHWH is "Yahweh," Elohim is "God," Adonai is "Lord."
- Follow the Ketiv (the written text). Where the Qere differs in a way that changes meaning, give it as an alternate reading. If the Ketiv can't be read as meaningful Hebrew (a clear scribal slip), follow the Qere and note it in brackets.
- Where the original itself can be read in two ways that say different things, put the best reading in the main text and the other in brackets, `[alt: ...]`. How to tell, and how to choose, is under "Alternate readings and wording choices" below.
- When wordplay can't survive translation (names, puns, sound echoes), keep the primary sense and add a short bracketed note explaining it in English, e.g. `[In Hebrew the name sounds like the word for "ground."]`
- Where the syntax runs a sentence across a verse break, keep the sentence intact rather than chopping it at the number.
- Use standard English chapter and verse numbering (KJV/NIV scheme). Where the Hebrew numbering differs (psalm titles, Joel, Malachi, etc.), say so once in the `numbering:` line of the front matter.
- English only. No Hebrew or Greek script, and no transliteration anywhere, including inside bracketed notes (describe a sound echo in English instead). No translation notes beyond the bracketed alternates and wordplay notes.
- Section headings: short editorial labels breaking the chapter into narrative units.
- Consistency: `GLOSSARY.md` lists the default English for each recurring original-language term. Use it wherever it fits, and keep distinct original terms distinct in English. Where another wording fits a sentence better, use it (see "Choosing a wording" below).

## Alternate readings and wording choices
Decided by Obay on 2026-11-21. The main text is the translation. It is the only thing a listener hears, so it has to be the best reading on its own. The brackets are for Read mode.

These rules apply to chapters translated from 2026-11-21 on. Chapters published before then keep their wording and their brackets as they are: Obay decided not to redo them. So an example of wording below may differ from what an earlier chapter says.

### Two different things
- A real alternate is a place where the original itself can be read in two ways that say different things: the old copies differ, the grammar lets the sentence be put together two ways, or a word has two senses. It gets a bracket, `[alt: ...]`, and an entry in the decision log.
- A wording choice is one meaning that English can put two ways: a familiar word or a plainer one ("baptize", "immerse"), an idiom word for word or what it means ("admiring faces", "showing favoritism"), two near-synonyms ("stay", "remain"). It gets no bracket. The translator picks the wording that fits the sentence best, and it does not have to be the same wording every time.
- The test for a bracket: would a careful reader who saw only the main text miss something the original could really mean? If not, write no bracket.
- No standing brackets: never repeat a bracket from chapter to chapter for the same word.

### Choosing the main reading of a real alternate
Only Scripture itself is evidence. Check in this order and stop when the answer is clear:
1. The sentences around it: what has just been said, what is said next, and how the people in the passage respond.
2. How the same writer uses the same word or phrase elsewhere.
3. What the rest of Scripture says about the same thing.
4. Where the old copies differ. In the Old Testament the main text is always the Masoretic Text, read by its Ketiv as set out above; a reading from another old copy or an ancient version can only be the alternate. In the New Testament the main text follows the earliest copies; where the earliest copies themselves split, tests 1 to 3 decide, together with which wording better explains how the other could have arisen in copying.

- Never a reason: that a reading is familiar or unfamiliar; that a translation, a tradition, a church or scholars prefer it; that it fits a teaching better. Scholars and traditions change; Scripture does not. Printed editions of the Hebrew and Greek are used only as records of what the old copies say, never as judges of which reading is right.
- Where the writer seems to mean both senses of a word, the main text takes the sense the speaker goes on to build on, the other sense is the alternate, and a short bracketed note says that the one word carries both.
- If the evidence is still near even after all four tests, choose by test 1 and mark the entry `close` or `ask` in the decision log.

### Choosing a wording
- Say what the original means in plain English. An idiom, a set phrase that means something other than its words, is translated by its meaning: "was intimate with" (not "knew"), "showing favoritism to people" (not "admiring faces"), "lived among us" (not "pitched his tent among us"). An image the writer is drawing on purpose (light and darkness, bread, a shepherd, a vine) stays an image.
- A word in everyday use today is plain English even when it is also a church word: "baptize", "betray". The words to avoid are the archaic and churchy ones that nobody uses in ordinary speech.
- `GLOSSARY.md` gives the default wording for a recurring term. Keep it wherever it fits, so that echoes survive and distinct original words stay distinct. Where another wording fits a sentence better, use it, with no bracket.

### Obay's reviews
Obay reviews the decision log from time to time and switches any call he disagrees with. His call is final for that verse, and the reason he gives becomes a rule for similar verses: add it under "Decided by Obay" in `GLOSSARY.md`. Never wait for a review before publishing a chapter.

## File format
One file per chapter: `translations/<book-slug>/<NNN>.md` (three-digit chapter, e.g. `translations/genesis/001.md`, `translations/1-kings/002.md`). Book slugs are in `data/books.json`.

```
---
book: Genesis
chapter: 1
---
## Section heading
1 Verse one text.
2 Verse two text.

3 A blank line starts a new paragraph.
```

- Every verse is on its own line, starting with its number and a space. Every verse of the chapter must be present.
- A new paragraph inside a verse: a blank line, then a line that starts with `¶ ` and goes on with the verse above it. The page starts a new paragraph there with no verse number; nothing changes in what is read aloud. Used at Deuteronomy 5:21, where the Hebrew has a paragraph break inside the verse (Obay, 2026-11-23).
- `## ` starts a section heading.
- `title: ...` is an unnumbered line such as a psalm superscription (when English numbering does not count it as a verse).
- Optional front matter line `numbering: ...` for a one-time numbering note.
- Brackets: `[alt: ...]` for alternate readings, any other `[...]` for a short note. Do not nest brackets.

## Decision log
Every `[alt: ...]` in a chapter has an entry in `decisions/<book-slug>/<NNN>.md`, written with the chapter. Obay reads these to review the calls, so write them for him: plain English, no Hebrew or Greek script, no transliteration, and reasons he can look up in Scripture. A chapter with no brackets needs no file.

```
---
book: John
chapter: 3
---
## 3:3 born from above | born again
kind: two senses
call: ask
why: Jesus goes on to speak of where this birth comes from: "from water and spirit" (3:5), "from the spirit" (3:6, 8). John uses the same word at 3:31 ("the one who comes from above") and 19:11, where it can only be "from above", and has already said that the children of God are born "from God" (1:13).
other: Nicodemus answers as if he heard "again": "enter his mother's womb a second time" (3:4).
review: open
```

- Heading: `## <chapter>:<verse> <main text wording> | <alternate wording>`. One entry for each bracket, in the order of the chapter.
- `kind:` is `copies differ`, `grammar` (the sentence can be put together two ways), `two senses` (a word or phrase has two meanings) or `both meant` (the writer seems to intend both senses).
- `call:` is `clear`, `close` (the evidence is near even) or `ask` (near even, and the meaning changes enough that Obay should see it first). At most three `ask` entries in a chapter.
- `why:` what in Scripture supports the main text. `other:` what supports the alternate. Each is one line.
- `review:` starts as `open`. Only Obay's reviews change it, to `kept by Obay <date>` or `switched by Obay <date>: <his reason>`.
