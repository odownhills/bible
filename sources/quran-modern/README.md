# Arabic text of the Quran in modern spelling

The same Arabic as `sources/quran/` (the Hafs reading: 114 surahs, 6,236 verses, the same words in the same
order), spelled the way Arabic is written today (imla'i spelling) instead of in the traditional Uthmani
script: يَا أَيُّهَا for يَـٰٓأَيُّهَا, الصَّلَاةَ for ٱلصَّلَوٰةَ, الْكِتَابُ for ٱلۡكِتَٰبُ. It has full vowel marks.
The Quran site shows it by default and keeps the traditional text one tap away (Obay, 2026-11-23).

- `quran-simple.txt`: one line per verse, `surah|verse|text`.
- The text is the Tanzil Project's "Simple" text (https://tanzil.net), taken unchanged from the copy in
  fawazahmed0/quran-api (edition `ara-quransimple`, https://github.com/fawazahmed0/quran-api), fetched on
  2026-11-23, because tanzil.net itself cannot be reached from the machines that build the site.
- Checked on 2026-11-23:
  - against a second copy of Tanzil's simple text (npm `@ghoran/text`, `tanzil-simple-clean`): the same
    letters in 6,230 of 6,236 verses; the other 6 differ in the spelling of one word only, as between
    versions of Tanzil's text (بعدما / بعد ما in 2:181, 8:6, 13:37, يا ويلتا / يا ويلتى in 5:31,
    يا حسرتا / يا حسرتى in 39:56, الزنا / الزنى in 17:32);
  - against `sources/quran/`: every surah has the same verses, and every verse the same words (their letters
    line up word by word once the known spelling differences are set aside; `scripts/quran_ar.py` checks
    this on every build and stops if a verse does not line up).
- As in all of Tanzil's text files, the opening line (بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ) is written at the
  start of verse 1 of every surah except Surahs 1 and 9. The pages show it apart, above verse 1, as they do
  the traditional text.
- The file has Tanzil's pause signs (ۖ ۗ ۚ ...), its quarter-hizb sign (۞) and its prostration sign (۩).
  The modern pages leave these signs out, as Tanzil's own download does when they are not asked for; they
  show only the words, their letters and their vowel marks.
- Tanzil's terms: the text may be copied and used anywhere, with its source (Tanzil Project, tanzil.net)
  clearly named and linked; the text itself must not be changed. Never edit this file. If a verse here
  seems to differ from the standard text, report it instead.
