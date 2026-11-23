#!/usr/bin/env python3
"""Read the Quran's Arabic aloud in a plain speaking voice, for the Quran site's Arabic pages (scripts/quran_ar.py).

Obay (2026-11-22): a plain, ordinary speaking voice, never chanted or recited ("plain, honest scripture, no
tradition"), as close as can be to Sulafat, the English site's voice; free, over about two weeks; starting at
Surah 2 verse 75 and going on in order from there (Surah 1 and 2:1-74 come last).

The voice is Gemini's Sulafat from MODEL, which has its own free daily limit, so the Bible's and the English
Quran's recordings (scripts/tts.py, another model) keep theirs. Each request reads one chunk of the text, one
verse to a line: several whole short surahs, or a run of verses of a long one, up to CHUNK characters.

Every chunk's recording is checked word for word before it is kept: it is transcribed back (OpenAI's
whisper-1, which also says when each word starts), the transcript is lined up with the text, and a take that
skips, adds or garbles words is thrown away and read again on a later run (up to 3 takes). A kept chunk goes in
the R2 bucket as audio/ar/chunks/<id>.mp3, with the start of each of its words in data/arabic_voice/<id>.json.

Then each surah's chunks are joined into its recording, audio/ar/<n>.mp3 (listed in data/audio.json), with the
start of every word in site-quran/audio/ar/<n>.json:

    {"sum": fingerprint of the words, "words": how many, "t": [start of each word, hundredths of a second],
     "range": [first verse, last verse], "verses": [[verse, index of its first word], ...], "chunks": [...]}

The opening line "In the name of God..." of a surah that has it apart from its verses counts as verse 0.
While a surah is only partly read, its recording holds the longest run of verses read so far, and its page
lights up only those verses' words.

    python3 scripts/arabic_voice.py --minutes 100   # read chunks until the free limit or the time runs out
    python3 scripts/arabic_voice.py --max 2          # read at most 2 chunks
    python3 scripts/arabic_voice.py --publish main  # and put each chunk on the site as soon as it is kept
    python3 scripts/arabic_voice.py publish         # commit and push what was read to main (the GitHub Action does)
    python3 scripts/arabic_voice.py plan            # list the chunks in the order they are read
Needs GEMINI_API_KEY, OPENAI_API_KEY, ffmpeg and the R2 secrets (scripts/media.py).
The GitHub Action .github/workflows/arabic-voice.yml runs it every few hours until all 114 surahs are read.
"""
import array
import concurrent.futures
import difflib
import functools
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["WORK"] = "quran"
import media      # noqa: E402
import quran_ar   # noqa: E402
import quran_site  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = media.SITE
DATA = os.path.join(ROOT, "data", "arabic_voice")
MODEL = "gemini-2.5-flash-preview-tts"
VOICE = "Sulafat"
# Said before each chunk. This model takes it as an instruction and does not read it aloud (tried
# 2026-11-22); a take where it is read aloud fails the check, since those words are not in the text.
STYLE = "Read this aloud in a plain, natural speaking voice, not chanted: "
# Characters of Arabic (with its vowel marks) per request. The voice reads about 16 a second, so 8,000 is
# about 8 minutes of speech: fewer requests a day out of a small free allowance (first takes were 5,000).
CHUNK = 8000
START = (2, 75)       # Obay: start at Surah 2 verse 75
# Obay, 2026-11-22 evening, once 2:75 onward had begun: go back and read Surah 1 and 2:1-74 next. So the verses
# before START are read first, then the rest in order from START.
# Requests at once. The free tier lets only about 3 requests start each minute (a request over that is
# answered "too many" and tried again a little later), and each takes a few minutes, so a few run together.
PARALLEL = int(os.environ.get("ARABIC_PARALLEL") or 5)
SPACING = 21          # seconds between starting two requests
TAKES = 3
RATE = 24000          # the voice's own sample rate
SIGNS = str.maketrans({"۞": "", "۩": ""})   # marks on the page that are not words


# ---------------------------------------------------------------- the text and the chunks

def lines(n):
    """[(verse, [words])] of surah n as read: the opening line apart (verse 0) when it has one."""
    opening, verses = quran_ar.surah(n)
    return ([(0, opening)] if opening else []) + list(verses)


def size(ls):
    return sum(len(" ".join(ws)) + 1 for _, ws in ls)


def split(ls):
    """A long run of verses in near-equal pieces of at most CHUNK characters, cut at verse ends."""
    k = max(1, math.ceil(size(ls) / float(CHUNK)))
    target = size(ls) / float(k)
    out, cur, acc = [], [], 0
    for line in ls:
        n = len(" ".join(line[1])) + 1
        if cur and (acc + n > CHUNK or (acc >= target and len(out) < k - 1)):
            out.append(cur)
            cur, acc = [], 0
        cur.append(line)
        acc += n
    out.append(cur)
    return out


def plan(have=None):
    """The chunks still to read, in the order they are read: [{"id", "segments": [[surah, first verse, last verse],
    ...]}]. Verses already in a kept chunk (have) are left out, so the plan can change (a different CHUNK) without
    reading anything twice or leaving a verse out."""
    covered = set()
    for c in (have or {}).values():
        for n, a, b in c["segments"]:
            covered.update((n, v) for v in range(a, b + 1))
    chunks, cur, room = [], [], 0
    for s in quran_ar.SURAHS:
        n = s["n"]
        whole = lines(n)
        ls = [x for x in whole if (n, x[0]) not in covered]
        if not ls:
            continue
        regions = []   # runs of verses still to read, cut at START
        for x in ls:
            if regions and x[0] == regions[-1][-1][0] + 1 and (n, x[0]) != START:
                regions[-1].append(x)
            else:
                regions.append([x])
        if len(ls) == len(whole) and len(regions) == 1 and size(ls) <= CHUNK:
            # a short surah: packed with the short surahs before it while they fit
            if cur and room + size(ls) > CHUNK:
                chunks.append(cur)
                cur, room = [], 0
            cur.append([n, ls[0][0], ls[-1][0]])
            room += size(ls)
            continue
        pieces = [[[n, p[0][0], p[-1][0]]] for reg in regions for p in split(reg)]
        if cur and regions[0][0][0] == whole[0][0] and room + size(regions[0][:len(split(regions[0])[0])]) <= CHUNK:
            # the short surahs before it fit in one request with its opening piece (Surah 1 with 2:0-40)
            pieces[0] = cur + pieces[0]
        elif cur:
            chunks.append(cur)
        cur, room = [], 0
        chunks += pieces
    if cur:
        chunks.append(cur)
    out = [{"id": "%d-%d" % (c[0][0], c[0][1]), "segments": c} for c in chunks]
    return [c for c in out if tuple(c["segments"][0][:2]) < START] + \
        [c for c in out if tuple(c["segments"][0][:2]) >= START]


def chunk_lines(chunk):
    """[(surah, verse, [words])] of a chunk, in order."""
    out = []
    for n, a, b in chunk["segments"]:
        out += [(n, v, ws) for v, ws in lines(n) if a <= v <= b]
    return out


def seg_ranges(chunk):
    """[(index of the segment's first word in the chunk, index after its last word)] for each segment."""
    out, at = [], 0
    for n, a, b in chunk["segments"]:
        count = sum(len(ws) for v, ws in lines(n) if a <= v <= b)
        out.append((at, at + count))
        at += count
    return out


def chunk_text(chunk):
    return "\n".join(re.sub(r"\s+", " ", " ".join(ws).translate(SIGNS)).strip() for _, _, ws in chunk_lines(chunk))


# ---------------------------------------------------------------- checking a take, and timing its words

MARKS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭ࣓-ࣿـ]")


def skeleton(w):
    """A word with its vowel marks and the letters that the Quran's spelling and ordinary spelling write
    differently (alef, hamza and their seats) taken out, for lining up the text with the transcript."""
    w = MARKS.sub("", w)
    for a, b in (("ؤ", "و"), ("ئ", "ي"), ("ى", "ي"), ("ة", "ه"), ("ۥ", ""), ("ۦ", "")):
        w = w.replace(a, b)
    return re.sub("[^ب-ي]", "", w).replace("ا", "")


@functools.lru_cache(maxsize=200000)
def like(a, b):
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def line_up(text, heard):
    """Pairs (text word, heard word) that are the same word, by dynamic programming in a band around the
    diagonal. text, heard: lists of skeletons."""
    n, m = len(text), len(heard)
    if not n or not m:
        return []
    band = max(60, abs(n - m) + 40)
    GAP = -0.6
    score, back = {}, {}
    score[(0, 0)] = 0.0
    for i in range(0, n + 1):
        mid = i * m / float(n)
        lo, hi = max(0, int(mid) - band), min(m, int(mid) + band)
        for j in range(lo, hi + 1):
            if i == 0 and j == 0:
                continue
            best, how = None, None
            if i and j and (i - 1, j - 1) in score:
                s = like(text[i - 1], heard[j - 1])
                v = score[(i - 1, j - 1)] + (2 * s if s >= 0.5 else -1.0)
                best, how = v, "d"
            if i and (i - 1, j) in score and (best is None or score[(i - 1, j)] + GAP > best):
                best, how = score[(i - 1, j)] + GAP, "t"
            if j and (i, j - 1) in score and (best is None or score[(i, j - 1)] + GAP > best):
                best, how = score[(i, j - 1)] + GAP, "h"
            if best is not None:
                score[(i, j)], back[(i, j)] = best, how
    i, j = n, m
    if (i, j) not in score:
        return []
    pairs = []
    while i or j:
        how = back[(i, j)]
        if how == "d":
            if like(text[i - 1], heard[j - 1]) >= 0.5:
                pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif how == "t":
            i -= 1
        else:
            j -= 1
    return pairs[::-1]


def letters(w):
    return max(1, len(skeleton(w)) + 1)


def check_and_time(cl, heard, seconds):
    """(word start times in seconds, report, list of problems) for a take of the chunk whose lines are cl,
    from its transcript heard = [{"word", "start", "end"}, ...]."""
    toks = [w for _, _, ws in cl for w in ws]
    text = [skeleton(w) for w in toks]
    said = [skeleton(h["word"]) for h in heard]
    pairs = line_up(text, said)
    at = [None] * len(toks)
    for i, j in pairs:
        at[i] = float(heard[j]["start"])
    # never backwards
    last = -1.0
    for i in range(len(at)):
        if at[i] is not None:
            if at[i] < last:
                at[i] = None
            else:
                last = at[i]
    # words not heard as such: spread between their neighbours by length
    i = 0
    end = max([float(h["end"]) for h in heard] + [0.5])
    while i < len(at):
        if at[i] is not None:
            i += 1
            continue
        k = i
        while k < len(at) and at[k] is None:
            k += 1
        a = at[i - 1] if i else 0.05
        z = at[k] if k < len(at) else min(seconds, end)
        ws = toks[i - 1:k] if i else toks[i:k]
        total = sum(letters(w) for w in ws)
        run = 0
        times = []
        for w in ws:
            times.append(a + (z - a) * run / float(total))
            run += letters(w)
        for x, t in zip(range(i, k), times[1:] if i else times):
            at[x] = t
        i = k
    matched = set(i for i, _ in pairs)
    used = set(j for _, j in pairs)

    def longest(flags):
        best = run = 0
        for f in flags:
            run = run + 1 if f else 0
            best = max(best, run)
        return best
    miss_text = longest([i not in matched for i in range(len(toks))])
    miss_heard = longest([j not in used for j in range(len(heard))])
    problems = []
    share = len(matched) / float(max(1, len(toks)))
    if share < 0.8:
        problems.append("only %.0f%% of the words were heard" % (share * 100))
    if miss_text > 8:
        problems.append("%d words in a row were not heard (skipped?)" % miss_text)
    if miss_heard > 8:
        problems.append("%d words in a row were heard that are not in the text (added?)" % miss_heard)
    k = 0
    for n, v, ws in cl:
        got = sum(1 for x in range(k, k + len(ws)) if x in matched)
        if len(ws) >= 4 and got < 0.3 * len(ws):
            problems.append("surah %d verse %d was hardly heard (%d of %d words)" % (n, v, got, len(ws)))
        k += len(ws)
    report = {"heard": round(share, 3), "missed_run": miss_text, "added_run": miss_heard, "transcript_words": len(heard)}
    return at, report, problems


# ---------------------------------------------------------------- the voice and the listener

def speak(text):
    import tts
    tts.VOICE = VOICE
    return tts.request(STYLE + text, os.environ.get("GEMINI_API_KEY", ""), MODEL)


def transcribe(path):
    last = None
    for attempt in range(4):
        r = subprocess.run(["curl", "-sS", "--max-time", "900", "https://api.openai.com/v1/audio/transcriptions",
                            "-H", "Authorization: Bearer " + os.environ.get("OPENAI_API_KEY", ""),
                            "-F", "file=@" + path, "-F", "model=whisper-1", "-F", "language=ar",
                            "-F", "response_format=verbose_json", "-F", "timestamp_granularities[]=word"],
                           capture_output=True, text=True)
        try:
            j = json.loads(r.stdout)
            if "words" in j:
                return j["words"]
            last = r.stdout[:300]
        except ValueError:
            last = (r.stdout or r.stderr)[:300]
        time.sleep(10 * (attempt + 1))
    raise RuntimeError("the transcription failed: %s" % last)


def seconds_of(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def read_chunk(chunk, work):
    """One take of a chunk: (mp3 path, word times, report, problems)."""
    cl = chunk_lines(chunk)
    pcm = speak(chunk_text(chunk))
    raw = os.path.join(work, chunk["id"] + ".raw")
    mp3 = os.path.join(work, chunk["id"] + ".mp3")
    open(raw, "wb").write(pcm)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", raw,
                    "-c:a", "libmp3lame", "-b:a", "64k", mp3], check=True)
    os.remove(raw)
    secs = seconds_of(mp3)
    heard = transcribe(mp3)
    at, report, problems = check_and_time(cl, heard, secs)
    report["seconds"] = round(secs, 2)
    return mp3, at, report, problems


# ---------------------------------------------------------------- what has been read

def load(name, default):
    try:
        return json.load(open(os.path.join(DATA, name), encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save(name, value):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, separators=(",", ":"))


def chunk_sum(chunk):
    return quran_site.checksum(" ".join(w for _, _, ws in chunk_lines(chunk) for w in ws))


def done():
    """{id: the chunk's saved data} for every chunk read and kept whose text is still the same."""
    out = {}
    for f in sorted(os.listdir(DATA)) if os.path.isdir(DATA) else []:
        if f.endswith(".json") and f[0].isdigit():
            c = load(f, None)
            if c and c.get("sum") == chunk_sum(c) and len(c.get("t", [])) == c.get("words"):
                out[c["id"]] = c
    return out


# ---------------------------------------------------------------- joining a surah's chunks

def quiet_cut(src, lo, hi):
    """The middle of the longest quiet stretch of src between lo and hi seconds, or None."""
    if hi - lo < 0.1:
        return None
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % lo, "-t", "%.3f" % (hi - lo), "-i", src,
                          "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"], capture_output=True, check=True).stdout
    samples = array.array("h")
    samples.frombytes(pcm[:len(pcm) // 2 * 2])
    step = RATE // 100
    loud = [20 * math.log10(max(1.0, math.sqrt(sum(x * x for x in samples[i:i + step]) / float(step))))
            for i in range(0, len(samples) - step + 1, step)]
    if len(loud) < 10:
        return None
    quiet = min(50.0, max(loud) - 25)
    best, run = (0, 0), None
    for k, v in enumerate(loud):
        if v < quiet:
            run = k if run is None else run
            if k + 1 - run > best[1] - best[0]:
                best = (run, k + 1)
        else:
            run = None
    if best[1] - best[0] < 12:
        return None
    return lo + (best[0] + best[1]) / 200.0


def surah_run(n, have):
    """The longest run of verses of surah n read so far: [(chunk, segment index)], in order."""
    segs = []
    for c in have.values():
        for k, (s, a, b) in enumerate(c["segments"]):
            if s == n:
                segs.append((a, b, c, k))
    segs.sort(key=lambda x: x[0])
    runs, cur = [], []
    for a, b, c, k in segs:
        if cur and a != cur[-1][1] + 1:
            runs.append(cur)
            cur = []
        cur.append((a, b, c, k))
    if cur:
        runs.append(cur)
    if not runs:
        return []
    best = max(runs, key=lambda r: (r[-1][1] - r[0][0], -r[0][0]))
    return [(c, k) for _, _, c, k in best]


def join_surah(n, run, work):
    """(mp3 path, timing) for surah n from its run of chunks."""
    raw = os.path.join(work, "%d.raw" % n)
    times, verses, at = [], [], 0
    pad = b"\x00\x00" * int(RATE * 0.3)
    with open(raw, "wb") as out:
        for c, k in run:
            src = os.path.join(work, "chunk-%s.mp3" % c["id"])
            if not os.path.exists(src):
                media.get("audio/ar/chunks/%s.mp3" % c["id"], src)
            t = [x / 100.0 for x in c["t"]]
            first, last = seg_ranges(c)[k]
            sn, sa, sb = c["segments"][k]
            total = seconds_of(src)
            if first == 0:
                lo = 0.0
            else:
                lo = quiet_cut(src, t[first - 1] + 0.2, t[first] + 0.15)
                lo = lo if lo is not None else max(t[first - 1] + 0.3, t[first] - 0.25)
            if last >= len(t):
                hi = total
            else:
                hi = quiet_cut(src, t[last - 1] + 0.2, t[last] + 0.15)
                hi = hi if hi is not None else max(t[last - 1] + 0.3, t[last] - 0.25)
            pcm = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % lo, "-t", "%.3f" % (hi - lo), "-i", src,
                                  "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"], capture_output=True, check=True).stdout
            if at:
                out.write(pad)
                at += len(pad) // 2
            base = at / float(RATE)
            k0 = len(times)
            for v, ws in lines(sn):
                if sa <= v <= sb:
                    if v > 0:
                        verses.append([v, k0])
                    k0 += len(ws)
            times += [base + max(0.0, x - lo) for x in t[first:last]]
            out.write(pcm)
            at += len(pcm) // 2
    mp3 = os.path.join(work, "%d.mp3" % n)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", raw,
                    "-c:a", "libmp3lame", "-b:a", "48k", mp3], check=True)
    os.remove(raw)
    cs = [int(round(x * 100)) for x in times]
    for i in range(1, len(cs)):
        cs[i] = max(cs[i], cs[i - 1])
    a, b = run[0][0]["segments"][run[0][1]][1], run[-1][0]["segments"][run[-1][1]][2]
    spoken = " ".join(w for v, ws in lines(n) if a <= v <= b for w in ws)
    if len(cs) != len(quran_site.words(spoken)):
        raise SystemExit("Surah %d: %d word times for %d words" % (n, len(cs), len(quran_site.words(spoken))))
    return mp3, {"sum": quran_site.checksum(spoken), "words": len(cs), "t": cs, "range": [a, b], "verses": verses,
                 "chunks": [[c["id"], c["sum"], c["bytes"]] for c, _ in run], "voice": VOICE, "model": MODEL}


def join_all(have):
    """Make again every surah recording whose run of chunks has changed. Returns the surahs made."""
    made = []
    listed = media.index()
    folder = os.path.join(SITE, "audio", "ar")
    os.makedirs(folder, exist_ok=True)
    for s in quran_ar.SURAHS:
        n = s["n"]
        run = surah_run(n, have)
        if not run:
            continue
        want = [[c["id"], c["sum"], c["bytes"]] for c, _ in run]
        path = os.path.join(folder, "%d.json" % n)
        try:
            old = json.load(open(path, encoding="utf-8"))
            if old.get("chunks") == want and "audio/ar/%d.mp3" % n in listed:
                continue
        except (OSError, ValueError):
            pass
        with tempfile.TemporaryDirectory() as work:
            mp3, timing = join_surah(n, run, work)
            media.publish(mp3, "audio/ar/%d.mp3" % n)
        json.dump(timing, open(path, "w", encoding="utf-8"), separators=(",", ":"))
        made.append(n)
        print("Surah %d: verses %d-%d read aloud, %d words" % (n, timing["range"][0], timing["range"][1], timing["words"]),
              flush=True)
    return made


# ---------------------------------------------------------------- a run

def main(minutes, most=None, publish_to=None):
    """Read chunks; with publish_to (a branch), each kept chunk goes on the site at once: its surah is joined
    again and pushed, so the pages fill in while the run goes on."""
    if not media.configured():
        raise SystemExit("The R2 secrets are missing (see scripts/media.py).")
    for k in ("GEMINI_API_KEY", "OPENAI_API_KEY"):
        if not os.environ.get(k):
            raise SystemExit("%s is not set." % k)
    import tts
    began = time.time()
    have = done()
    rejected = load("rejected.json", {})
    todo = [c for c in plan(have) if rejected.get(c["id"], 0) < TAKES][:most]
    print("%d chunks read, %d to go." % (len(have), len(todo)), flush=True)
    stop, failures = [False], [0]
    with tempfile.TemporaryDirectory() as work, concurrent.futures.ThreadPoolExecutor(PARALLEL) as pool:
        running = {}
        queue = list(todo)
        while queue or running:
            while queue and not stop[0] and len(running) < PARALLEL and time.time() - began < minutes * 60:
                c = queue.pop(0)
                running[pool.submit(read_chunk, c, work)] = c
                time.sleep(SPACING)
            if not running:
                break
            fin, _ = concurrent.futures.wait(list(running), return_when=concurrent.futures.FIRST_COMPLETED)
            for f in fin:
                c = running.pop(f)
                try:
                    mp3, at, report, problems = f.result()
                except tts.OutOfQuota:
                    if not stop[0]:
                        print("The free daily limit of %s is used up; the next run carries on from chunk %s." % (MODEL, c["id"]),
                              flush=True)
                    stop[0] = True
                    continue
                except (SystemExit, Exception) as e:
                    print("Chunk %s: no take this time (%s)" % (c["id"], e), flush=True)
                    failures[0] += 1
                    if failures[0] >= 3 or (isinstance(e, SystemExit) and e.code in (0, None)):
                        stop[0] = True   # the key was refused, or something is wrong: stop for this run
                    continue
                failures[0] = 0
                if problems:
                    rejected[c["id"]] = rejected.get(c["id"], 0) + 1
                    save("rejected.json", rejected)
                    print("Chunk %s: threw the take away (take %d of %d): %s | %s"
                          % (c["id"], rejected[c["id"]], TAKES, "; ".join(problems[:4]), report), flush=True)
                    continue
                key = "audio/ar/chunks/%s.mp3" % c["id"]
                media.put(mp3, key)
                kept = dict(c, sum=chunk_sum(c), words=len(at), t=[int(round(x * 100)) for x in at],
                            bytes=os.path.getsize(mp3), model=MODEL, voice=VOICE, check=report)
                save("%s.json" % c["id"], kept)
                have[c["id"]] = kept
                rejected.pop(c["id"], None)
                save("rejected.json", rejected)
                print("Chunk %s (%s): kept, %.0f seconds, %.0f%% of the words heard"
                      % (c["id"], ", ".join("%d:%d-%d" % tuple(s) for s in c["segments"]), report["seconds"],
                         report["heard"] * 100), flush=True)
                if publish_to:
                    try:
                        join_all(have)
                        publish(publish_to)
                    except (SystemExit, Exception) as e:   # the end of the run publishes again
                        print("Could not publish yet (%s)" % e, flush=True)
            if time.time() - began > minutes * 60 and queue and not stop[0]:
                print("Time is up for this run; the next run carries on.", flush=True)
                stop[0] = True
                queue = []
    made = join_all(have)
    left = [c["id"] for c in plan(have)]
    print("Made %d surah recording%s; %d chunks still to read%s." % (
        len(made), "" if len(made) == 1 else "s", len(left),
        "" if not [i for i in left if rejected.get(i, 0) >= TAKES] else
        " (failed %d takes, need a look: %s)" % (TAKES, ", ".join(i for i in left if rejected.get(i, 0) >= TAKES))))


def git(*args, check=True):
    return subprocess.run(["git"] + list(args), cwd=ROOT, check=check, capture_output=True, text=True)


def publish(branch="main"):
    """Commit what was read (the chunks' word times, the surahs' word times and the recordings' listing) on
    main (or a trial branch) and push, starting again from its newest commit when another run pushed first."""
    mine = {k: v for k, v in media.index().items() if k.startswith("audio/ar/")}
    folders = [os.path.join(SITE, "audio", "ar"), DATA]
    files = {}
    for folder in folders:
        if os.path.isdir(folder):
            for f in os.listdir(folder):
                if f.endswith(".json"):
                    files[os.path.join(folder, f)] = open(os.path.join(folder, f), encoding="utf-8").read()
    for attempt in range(5):
        git("fetch", "--quiet", "origin", branch)
        git("reset", "--quiet", "--hard", "FETCH_HEAD")
        idx = media.index()
        new = sorted(int(k.split("/")[-1][:-4]) for k, v in mine.items() if idx.get(k) != v)
        idx.update(mine)
        media.save_index(idx)
        for path, text in files.items():
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w", encoding="utf-8").write(text)
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build.py")], cwd=ROOT, check=True,
                       env=dict(os.environ, WORK="quran"))
        git("add", "-A", "data/audio.json", "data/arabic_voice", "site-quran")
        if any(p.endswith(".mp3") for p in git("diff", "--cached", "--name-only").stdout.split()):
            raise SystemExit("A recording is about to be committed to git.")
        if git("diff", "--cached", "--quiet", check=False).returncode == 0:
            print("Nothing new to publish.")
            return
        what = ("surah %d" % new[0]) if len(new) == 1 else ("surahs %s" % ", ".join(map(str, new))) if new else "chunks"
        git("commit", "--quiet", "-m", "Add Arabic voice: " + what)
        if git("push", "--quiet", "origin", "HEAD:" + branch, check=False).returncode == 0:
            print("Published " + what)
            return
        print("Main moved on; trying again.")
        time.sleep(5 + 10 * attempt)
    raise SystemExit("Could not push to main after 5 tries.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["publish"]:
        publish(args[args.index("--branch") + 1] if "--branch" in args else "main")
    elif args[:1] == ["plan"]:
        for c in plan(done()):   # what is still to read, in order
            print(c["id"], " ".join("%d:%d-%d" % tuple(s) for s in c["segments"]), size(
                [(v, ws) for _, v, ws in chunk_lines(c)]))
    else:
        main(int(args[args.index("--minutes") + 1]) if "--minutes" in args else 100,
             int(args[args.index("--max") + 1]) if "--max" in args else None,
             args[args.index("--publish") + 1] if "--publish" in args else None)
