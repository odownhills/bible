#!/usr/bin/env python3
"""The Quran site shows each surah as one page, though the translation is made in parts.

A long surah is translated, recorded and timed part by part (CLAUDE.md "Quran", scripts/quran.py). Readers
never see the parts: `WORK=quran python3 scripts/build.py` calls build() below, which writes for each surah
that has English

    quran-<n>/index.html   the whole surah in English: every translated part in order, with the section
                           headings of the translation, a bar to jump between those sections, and a note
                           at the end while later verses are still being translated
    quran-<n>/<part>.html  a stub that sends old links to the same verses on the surah's page
    text/en/<n>.txt, tv/en/<n>.json, manifest-en.json   the whole surah for Listen and TV mode

The surah's recording is its parts' recordings joined into one (scripts/quran_join.py, audio/en/<n>.mp3);
only the words of the parts it holds are lit up by Listen + Read and TV mode. The per-part pages' data
(manifest.json, text/quran-<n>/<part>.txt) stays as it was, because scripts/tts.py and scripts/align.py
record and time the parts from it.

The section names are the translation's own headings (the "## " lines of the part files). The Arabic pages
(scripts/quran_ar.py) use the same names for the verses that are translated.
"""
import hashlib
import json
import os
import re

WORD = re.compile(r"[^\s—–]*\w[^\s—–]*")   # one spoken word: the same rule as scripts/build.py

CSS = """
.secbar{position:sticky;top:var(--navh,3.3rem);z-index:14;background:var(--bg);margin:0 0 1.25rem;padding:.1rem 0 .55rem}
.secbar:after{content:"";position:absolute;left:0;right:0;top:100%;height:.8rem;background:linear-gradient(var(--bg),rgba(23,18,35,0));pointer-events:none}
.sec-now{width:100%;display:flex;align-items:center;gap:.6rem;font:inherit;font-family:var(--sans);font-size:.88rem;line-height:1.3;color:var(--text);background:var(--panel);border:1px solid var(--rule);border-radius:10px;padding:.55rem .75rem;cursor:pointer;text-align:left;-webkit-tap-highlight-color:transparent}
.sec-now:focus-visible{outline:2px solid var(--accent)}
.sec-now .sec-l{flex:none;color:var(--accent);text-transform:uppercase;letter-spacing:.1em;font-size:.68rem}
.sec-now b{flex:1;min-width:0;font-weight:normal;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sec-now i{flex:none;font-style:normal;color:var(--text-soft);font-size:.8rem;transition:transform .2s ease}
.sec-now[aria-expanded=true] i{transform:rotate(180deg)}
.sec-list{position:absolute;z-index:1;left:0;right:0;top:calc(100% - .3rem);max-height:66vh;overflow:auto;-webkit-overflow-scrolling:touch;background:var(--panel);border:1px solid var(--rule);border-radius:12px;box-shadow:0 12px 32px rgba(0,0,0,.55);padding:.3rem;font-family:var(--sans)}
.sec-list[hidden]{display:none}
.sec-list a{display:flex;align-items:baseline;justify-content:space-between;gap:.9rem;padding:.7rem .7rem;border-radius:8px;text-decoration:none;color:var(--text);font-size:.92rem;line-height:1.35}
.sec-list a:hover,.sec-list a:focus-visible{background:var(--shade);outline:none}
.sec-list a.on{background:var(--shade);color:var(--heading)}
.sec-list a.on:before{content:"";display:inline-block;width:.4rem;height:.4rem;border-radius:50%;background:var(--accent);margin:0 .5rem .1rem -.1rem;flex:none;align-self:center}
.sec-list a b{flex:1;font-weight:normal}
.sec-list small{flex:none;color:var(--text-soft);font-size:.78rem;font-variant-numeric:tabular-nums}
.sec-list .sec-g{display:block;padding:.6rem .7rem .2rem;color:var(--accent);font-size:.68rem;letter-spacing:.1em;text-transform:uppercase}
.secbar~#ch sup.n,.secbar~#ch h2.sec{scroll-margin-top:7.4rem}
.secbar~#ch.ar sup.n{scroll-margin-top:8.4rem}
#ch.ar sup.n{scroll-margin-top:5.6rem}
p.more{font-family:var(--sans);font-size:.9rem;color:var(--text-soft);background:var(--panel);border:1px solid var(--rule);border-radius:10px;padding:.8rem 1rem;margin:2rem 0 0}
"""


def words(text):
    return WORD.findall(text)


def checksum(text):
    """The same fingerprint of a text's spoken words as scripts/build.py's."""
    return hashlib.sha1(" ".join(words(text)).encode("utf-8")).hexdigest()[:12]


def part_words(text, skip):
    """A part's read-aloud words without the line that opens its recording."""
    return words(text)[skip:]


def fingerprint(text, skip, size):
    """What a part's place in its surah's joined recording depends on: its words and its recording."""
    return "%s:%s" % (checksum(" ".join(part_words(text, skip))), size)


def section_bar(items):
    """The bar that jumps between a surah's sections. items: [(target id, name, first verse, last verse, group)];
    group is a heading shown above an item that starts a new group (or None). A surah with fewer than three
    sections (a short one) has no bar."""
    if len(items) < 3:
        return ""
    rows = []
    for target, name, a, z, group in items:
        if group:
            rows.append('<span class="sec-g">%s</span>' % html_escape(group))
        span = "" if name.startswith("Verse") else ("%d" % a) if a == z else "%d&ndash;%d" % (a, z)   # named by its verses already
        rows.append('<a href="#%s" data-at="%s"><b>%s</b>%s</a>' % (
            target, target, html_escape(name), "<small>%s</small>" % span if span else ""))
    return ('<div class="secbar" id="secbar"><button type="button" class="sec-now" id="sec-now" aria-expanded="false" '
            'aria-controls="sec-list"><span class="sec-l">Sections</span><b id="sec-name">%s</b><i aria-hidden="true">&#9662;</i>'
            '</button><nav class="sec-list" id="sec-list" aria-label="Sections" hidden>%s</nav></div>'
            % (html_escape(items[0][1]), "".join(rows)))


def html_escape(s):
    import html
    return html.escape(s, quote=True)


def english_sections(parts, verses_total):
    """[(heading id, name, first verse, last verse)] from a surah's parsed parts [(meta, blocks)], in order."""
    out, k, pending = [], 0, None
    for meta, blocks in parts:
        for kind, val in blocks:
            if kind == "h":
                k += 1
                pending = ("s%d" % k, val)
            elif kind == "p" and pending:
                out.append([pending[0], pending[1], val[0][0], None])
                pending = None
    last = parts[-1][1] if parts else []
    end = max([vn for kind, val in last if kind == "p" for vn, _ in val] or [0])
    for i, s in enumerate(out):
        s[3] = out[i + 1][2] - 1 if i + 1 < len(out) else end
    return [tuple(s) for s in out]


def build(out, x):
    """Write the English surah pages. x: what scripts/build.py shares (page, esc, inline, plain, words, checksum,
    clock, lengths, listed, books, parts, read_tag, tv_tag, TV_ICON, pill, footer). Returns
    ({surah: [(name, first verse, last verse)]} for the Arabic pages, the manifest-en.json entries)."""
    esc, inline = x["esc"], x["inline"]
    books, parts_of = x["books"], x["parts"]
    manifest, sections_by_surah = [], {}
    for idx, b in enumerate(books):
        n, slug = b["surah"], b["slug"]
        parts = parts_of[slug]                      # [{"meta", "blocks", "spoken", "skip", "audio", "range"}] in order
        rel = "audio/en/%d.mp3" % n
        timing, joined = None, 0
        try:
            timing = json.load(open(os.path.join(out, "audio", "en", "%d.json" % n), encoding="utf-8"))
            want = [[k + 1, fingerprint(p["spoken"], p["skip"], (x["listed"].get(p["audio"]) or [None])[0])]
                    for k, p in enumerate(parts) if p["audio"]]
            if rel in x["lengths"] and timing.get("parts") and timing["parts"] == want[:len(timing["parts"])]:
                joined = len(timing["parts"])
        except (OSError, ValueError):
            timing = None

        # the whole surah: the words of the joined parts are lit up as they are read; later parts are text only
        html_parts, spoken, verse_at, section_at, k_sec = [], [], [], [], 0
        for k, p in enumerate(parts):
            live = k < joined
            for kind, val in p["blocks"]:
                if kind == "h":
                    k_sec += 1
                    html_parts.append('<h2 class="sec" id="s%d">%s</h2>' % (k_sec, esc(val)))
                    if live:
                        section_at.append([len(words(" ".join(spoken))), val])
                elif kind == "t":
                    html_parts.append('<p class="title">%s</p>' % inline(val, live))
                    if live:
                        spoken.append(x["plain"](val))
                else:
                    html_parts.append('<p class="v">%s</p>' % " ".join(
                        '<sup class="n" id="v%d">%d</sup>%s' % (vn, vn, inline(t, live)) for vn, t in val))
                    if live:
                        for vn, t in val:
                            verse_at.append([vn, len(words(" ".join(spoken)))])
                            spoken.append(x["plain"](t))
        text = " ".join(spoken)
        body_text = "\n".join(html_parts)
        sync = None
        if joined and timing and timing.get("sum") == checksum(text) and timing.get("words") == len(words(text)) \
                and body_text.count('<span class="w">') == len(words(text)):
            sync = "audio/en/%d.json" % n
        has_audio = bool(sync)

        last_v = parts[-1]["range"][1]
        secs = english_sections([(p["meta"], p["blocks"]) for p in parts], last_v)
        sections_by_surah[n] = [(name, a, z) for _, name, a, z in secs]
        bar = section_bar([(sid, name, a, z, None) for sid, name, a, z in secs])

        nxt = books[idx + 1] if idx + 1 < len(books) else None
        prv = books[idx - 1] if idx > 0 else None
        data = (' data-id="en-%d" data-title="%s" data-url="%s/" data-skip="0" data-stream="1"'
                % (n, esc(title(b)), slug))
        buttons = ""
        if has_audio:
            data += ' data-audio="../%s" data-sync="../%s"' % (rel, sync)
            buttons = ('<button class="btn" id="lr-start" type="button">&#9654; Listen + Read</button> '
                       '<a class="btn tv" href="../tv/?c=en-%d" data-tv="en-%d">%sTV mode</a> '
                       '<a class="btn ghost" href="../listen/?from=en-%d">Listen only</a>' % (n, n, x["TV_ICON"], n))
        if nxt:
            data += ' data-next="../%s/" data-next-id="en-%d"' % (nxt["slug"], nxt["surah"])
            if ("audio/en/%d.mp3" % nxt["surah"]) in x["lengths"]:
                data += ' data-next-audio="../audio/en/%d.mp3"' % nxt["surah"]
        total = b["total_verses"]
        about = ("%d verses" % total) if last_v == total else ("verses 1&ndash;%d of %d translated so far" % (last_v, total))
        more = "" if last_v == total else (
            '<p class="more">Verses %d&ndash;%d are not translated yet. <a href="../ar/%d.html#v%d">Read them in Arabic</a></p>'
            % (last_v + 1, total, n, last_v + 1))
        body = """<p class="eyebrow">%s</p>
<h1>%s</h1>
<p class="sub">%s%s<span class="lang-note">%s</span></p>
%s<div id="ch"%s>
%s
</div>
%s
<div class="pn">%s%s</div>""" % (
            esc(b["name"] if b.get("title") else ""), esc(b.get("title") or b["name"]), buttons, "<br>" if buttons else "", about, bar, data, body_text, more,
            '<a class="prev" href="../%s/">&larr; %s</a>' % (prv["slug"], esc(title(prv))) if prv else
            '<span class="prev">Beginning of the Quran</span>',
            '<a class="next" href="../%s/">%s &rarr;</a>' % (nxt["slug"], esc(title(nxt))) if nxt else
            '<span class="next">Next surah coming soon</span>')
        switch = x["pill"]("en", "", "../ar/%d.html" % n, ' data-upto="%d"' % last_v)
        os.makedirs(os.path.join(out, slug), exist_ok=True)
        open(os.path.join(out, slug, "index.html"), "w", encoding="utf-8").write(
            x["page"](title(b), body, 1, x["read_tag"] + x["tv_tag"], lang=switch))
        # old links to a part go to the same verses on the surah's page
        for k, p in enumerate(parts):
            a = p["range"][0]
            target = "./" + ("#v%d" % a if a > 1 else "")
            open(os.path.join(out, slug, "%d.html" % (k + 1)), "w", encoding="utf-8").write(
                '<!doctype html><meta charset="utf-8"><title>%s</title><meta name="robots" content="noindex">'
                '<meta http-equiv="refresh" content="0; url=%s"><script>location.replace("./"+(location.hash||"%s"))</script>'
                '<a href="%s">%s</a>' % (esc(title(b)), target, "#v%d" % a if a > 1 else "", target, esc(title(b))))
        for sub in ("text", "tv"):
            os.makedirs(os.path.join(out, sub, "en"), exist_ok=True)
        open(os.path.join(out, "text", "en", "%d.txt" % n), "w", encoding="utf-8").write(text)
        json.dump({"verses": verse_at, "scenes": [], "sections": section_at if bar else []},
                  open(os.path.join(out, "tv", "en", "%d.json" % n), "w", encoding="utf-8"), ensure_ascii=False)
        if has_audio:
            v_last = verse_at[-1][0] if verse_at else last_v
            manifest.append({
                "id": "en-%d" % n, "book": "Surahs", "slug": "en", "chapter": n, "total": 114, "url": "%s/" % slug,
                "audio": rel, "duration": x["lengths"].get(rel), "text": "text/en/%d.txt" % n, "sync": sync,
                "title": title(b), "sub": ("%d verses" % total) if v_last == total else "Verses 1-%d of %d" % (v_last, total),
                "stream": True,
            })
    json.dump(manifest, open(os.path.join(out, "manifest-en.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return sections_by_surah, manifest


def title(b):
    return "%s · %s" % (b["name"], b["title"]) if b.get("title") else b["name"]
