# TV mode pictures: how they are chosen

TV mode shows still pictures behind a chapter's recording while the words light up. These are Obay's rules
for choosing the pictures. They apply to every chapter. A chapter's plan is `data/tv/<slug>/<NNN>.json`;
`scripts/pictures.py` makes the pictures and `scripts/build.py` puts them in the site.

## What a picture is
- A present-day or timeless picture of what the verses teach, one idea per picture. Not a historical scene:
  no robes, ancient buildings, halos, crosses or other religious symbols.
- God is never pictured. Biblical people, Jesus included, are not portrayed. An ordinary father, seen from
  behind or only as hands and arms, may stand as a likeness of the Father; showing what the father does is
  better than showing the father. John's own images of light and love are welcome.
- No violence, no nakedness, no words or numbers in the picture.
- Only wide pictures (for a TV or a video) are made for now. Tall phone pictures are switched off.

## Steps for a chapter
1. Split the chapter into sections that each carry one deep meaning, written as one plain sentence.
2. Write 10 different picture ideas for each section.
3. Judge the ideas with the test below, and make the top two for each picture as real pictures.
4. Choose between the real pictures by eye, with the same test. A section gets one or two pictures; a
   picture should stay up at least 8 seconds or so.
5. Check the result against the chapters before and after it, and with the words laid over it.

Family lists (Obay, 2026-11-28): before planning, look for runs of 3 or more verses that are only names,
ages and "fathered" / "sons of", and add them to `data/family_lists.json` (verse ranges; `"all"` for a chapter
that is a family list from start to end). Verses that tell something stay in (Genesis 5:22-24 Enoch, 10:8-12
Nimrod, 10:25 Peleg), and so does a heading such as "These are the generations of Shem". Watch and the
Listen page skip those verses by default with a spoken notice, so they need no pictures: a scene for the
verses after a list starts at the first verse after it. The text itself is never changed.

## The test, in this order
1. **Does the picture itself show the meaning?** Name the one thing that has to be seen for the verse to
   land ("feet landing in someone else's footprints", "a man who cannot see where he is going") and check
   that it is plainly visible in the finished picture. Judge the picture, not the idea behind it: an idea
   that reads well can come out as a picture that does not show it.
2. **Is it understood at once** by someone hearing the words, with nothing to work out?
3. **Is it the stronger picture to look at?** When two pictures show the meaning equally, the more striking
   and beautiful one wins.

A person or a face in the picture is not a goal in itself. Human moments often win because they are easy
to understand, but a picture with no face (footprints in the sand, a rusting car) wins whenever it shows
the meaning better. "Too abstract" means the watcher cannot tell why the picture is there; it does not mean
"has no person in it".

## Keeping and changing pictures
- A picture already in a chapter stays unless there is a named reason to change it: it does not show the
  meaning, it repeats a neighbour, or Obay asked. A new picture has to be clearly better, not just new.
  A tie goes to the picture that is already there.
- A layout problem is not a reason to change the idea. If the words cover the important part, remake the
  same picture with the subject higher in the frame.
- Do not repeat a picture used in the chapters beside this one, unless it is clearly the best picture for
  the meaning. A good picture that repeats is better than a weak one that does not.

## Words over the picture
The words sit on a see-through dark box at the bottom middle of the picture (Obay, 2026-11-23: "make sure it
doesn't overlay over an important part of the picture"). The box is fitted to the words, so it is only as
wide as the longest line, usually the middle half of the screen. On a TV it covers roughly the band from
three quarters down to nine tenths down. On a phone held sideways the picture is cropped at the bottom, so
the box reaches higher in the picture: roughly from 60% down to 80% down, across the middle half.

So the important part of every picture sits in the upper 60% of the frame, or out at the left or right side
if it is lower. The bottom middle is plain foreground of the same scene. `scripts/pictures.py` asks for the
subject in the upper part of the frame in every prompt (it never mentions words or a box, which makes the
image model paint a dark bar); check it by eye on the finished picture, with a line at 60% down and the
middle half marked.

## Hard text
Some verses resist a picture. In order: use the text's own image moved into today; else show what the idea
does in a life today; else hold the previous picture a little longer.

## The Quran
The Quran site's TV mode uses the same steps, test and rules, with these additions (Obay, 2026-11-22: "avoid
prophet muhammed, but any other pictures you can decide if it has meaning then include it").
- The Prophet Muhammad is never shown in any way: no face, figure, silhouette, hands or stand-in, and no one
  standing for the "you" a verse speaks to.
- God is never pictured. Other prophets and people the Quran names are shown the way the Bible's people are:
  through the text's own images (the rock and its springs, the cow, the birds on the hills) or through people
  of today, not as portraits.
- No religious symbols of any tradition: no mosque, minaret, dome, crescent, prayer rug pattern, Arabic
  writing or copy of the Quran. Prayer is shown as an ordinary person of today kneeling or bowing in a plain
  place.
- A surah is pictured part by part, in the order of its parts: the plan for part NNN is
  `data/tv/quran-<surah>/<NNN>.json`, its pictures `pictures/quran-<surah>/<part>/`. Its first scene starts at
  the part's first verse. The site shows a surah's pictured parts as one; a part without pictures yet plays
  over the quiet background. The Arabic TV mode shows the same pictures, each from the start of its verse.
