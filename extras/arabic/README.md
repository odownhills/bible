# Arabic translations (one-off files)

Files here are not part of any site build. They are translated straight from the original text
into Arabic, by the same rules as the English (`TRANSLATION_RULES.md`), when Obay asks for one.

## Deuteronomy 5 (the Ten Commandments)

Translated from the Hebrew Masoretic Text on 2026-11-23, not adapted from any Arabic or English Bible.

- [deuteronomy-5.md](deuteronomy-5.md): reads right here on GitHub.
- [deuteronomy-5.html](deuteronomy-5.html): one standalone page (dark, right to left, the font is inside
  the file, nothing is loaded from outside). Download it and open it on any computer or phone, or
  [open it in a browser](https://htmlpreview.github.io/?https://github.com/odownhills/bible/blob/main/extras/arabic/deuteronomy-5.html).

### Choices made

- Plain modern standard Arabic. Vowel marks only where a word could be misread (for example أَمَتك,
  "your female slave", which without marks reads as "your nation").
- YHWH is the name itself in Arabic letters, يهوه (with vowel marks the first time: يَهْوَه), as the
  English has "Yahweh".
- Elohim is the ordinary Arabic word for God: الله where it stands alone (5:24, 26), إله where it
  takes "your" or "our" or an adjective ("Yahweh your God", "a jealous God"), and آلهة for "other
  gods". All three are one Arabic word, as they are one word in the Hebrew.
- "You" is singular or plural exactly as in the Hebrew, which Arabic can show and English cannot:
  Moses speaks to "you" plural, and the ten words speak to "you" singular.
- The paragraphs of the ten words (5:6-21) are the paragraph breaks of the Hebrew text itself, which
  make ten paragraphs. No church's way of counting the ten was used.
- One Hebrew word stands in both 5:11 ("for what is empty or false") and 5:20 ("empty or false
  testimony"); one Arabic word, باطل, which has both senses, stands in both.
- Two different Hebrew verbs in 5:21 stay two different Arabic verbs: "covet" (the wife) and "crave"
  (the house and the rest).
- Verse numbers are the English ones. Many printed Hebrew Bibles count verses 17 to 20 as one verse;
  a note at the top of the chapter says so.

### Where Arabic is less exact than the Hebrew

- 5:17: the Hebrew verb is the one for unlawful killing ("murder"). Everyday Arabic has one verb for
  "kill" and "murder", so the text has لا تقتل.
- 5:18: the Hebrew verb is the one for adultery, the breaking of a marriage. The everyday Arabic word,
  لا تزنِ, is wider and covers any unlawful sex.

### Decision log

The chapter has one bracket, in the format of `TRANSLATION_RULES.md`.

```
## 5:10 keep his commandments | keep my commandments
kind: copies differ
call: clear
why: The written Hebrew text has "his commandments", and the rules follow the written text wherever it can be read. It can be read here: from the next sentence on, the speaker names Yahweh as "he" ("Yahweh will not clear anyone who utters his name", 5:11; "as Yahweh your God commanded you", 5:12, 15, 16), so "his" at the end of 5:10 is where that way of speaking begins. Deuteronomy 7:9 says the same thing in the same way: "those who love him and keep his commandments".
other: The traditional way of reading the verse aloud has "my commandments", which matches "those who love me" just before it and the same sentence in Exodus 20:6.
review: open
```
