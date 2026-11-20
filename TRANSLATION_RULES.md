# Translation rules

These are Obay's standing rules. Every chapter follows them exactly.

## Translating
- Translate from the original text: the Hebrew Masoretic Text for the Old Testament (Aramaic portions of Daniel and Ezra from the Aramaic), the Greek for the New Testament. Do not adapt or paraphrase an existing English translation.
- Plain, common English. No archaic or churchy words (no "behold," "thee," "thy," "hearken," "iniquity," "begat," "lo," "verily"). Write it the way a clear modern writer would.
- Add nothing, drop nothing, change nothing. Good flow, but fidelity first. Stay true to Scripture. Do not filter the text through church tradition, doctrine, or commentary. Only translate the Scripture itself.
- Divine names: YHWH is "Yahweh," Elohim is "God," Adonai is "Lord."
- Follow the Ketiv (the written text). Where the Qere differs in a way that changes meaning, give it as an alternate reading. If the Ketiv can't be read as meaningful Hebrew (a clear scribal slip), follow the Qere and note it in brackets.
- When a word or phrase has more than one likely reading, put the primary reading in the main text and the alternative in brackets: `[alt: ...]`
- When wordplay can't survive translation (names, puns, sound echoes), keep the primary sense and add a short bracketed note explaining it in English, e.g. `[In Hebrew the name sounds like the word for "ground."]`
- Where the syntax runs a sentence across a verse break, keep the sentence intact rather than chopping it at the number.
- Use standard English chapter and verse numbering (KJV/NIV scheme). Where the Hebrew numbering differs (psalm titles, Joel, Malachi, etc.), say so once in the `numbering:` line of the front matter.
- English only. No Hebrew or Greek script, and no transliteration anywhere, including inside bracketed notes (describe a sound echo in English instead). No translation notes beyond the bracketed alternates and wordplay notes.
- Section headings: short editorial labels breaking the chapter into narrative units.

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
- `## ` starts a section heading.
- `title: ...` is an unnumbered line such as a psalm superscription (when English numbering does not count it as a verse).
- Optional front matter line `numbering: ...` for a one-time numbering note.
- Brackets: `[alt: ...]` for alternate readings, any other `[...]` for a short note. Do not nest brackets.
