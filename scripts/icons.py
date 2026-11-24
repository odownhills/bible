#!/usr/bin/env python3
"""The sites' icons: the browser tab icon, the phone home-screen icon and the web app manifest's icons.

    python3 scripts/icons.py     draw the icons again into scripts/icons/ (needs Chrome or Chromium)

The Bible site and the study site show a scroll; the Quran site a crescent. Plain shapes in the sites'
lavender on their dark background, readable at 16 pixels: no figures and no writing.

scripts/icons/<kind>/ holds what this script draws, and it is committed, so building a site needs only
to copy it: install() puts the files in a built site's top folder and writes its site.webmanifest
(manifest.json is already the site's list of recordings), and tags() gives every page the lines that
point to them. Running this script again is needed only when a shape or a color changes.
"""
import json
import math
import os
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "icons")
BG, FG = "#171223", "#B79BE8"   # the sites' --bg and --accent

# The drawings, on a 64-unit square. Each is drawn three ways: on a rounded square (the tab icon and the
# manifest's "any" icons), on the full square (Apple's home-screen icon, which the phone rounds itself) and
# smaller on the full square (the manifest's "maskable" icon, which Android may cut to a circle).


def scroll():
    """An open scroll: two rollers with the sheet between them, three lines of writing as plain bars.
    The bars sit on whole pixels at 16 and 32 pixels, so they stay apart in a browser tab."""
    return ('<rect x="8" y="8" width="12" height="48" rx="6" fill="{fg}"/>'
            '<rect x="44" y="8" width="12" height="48" rx="6" fill="{fg}"/>'
            '<rect x="18" y="16" width="28" height="32" fill="{fg}"/>'
            '<rect x="24" y="20" width="16" height="4" rx="2" fill="{bg}"/>'
            '<rect x="24" y="28" width="16" height="4" rx="2" fill="{bg}"/>'
            '<rect x="24" y="36" width="12" height="4" rx="2" fill="{bg}"/>')


def crescent():
    """A crescent: a disc with a smaller disc taken out of its upper right, opening toward it, moved so
    that it sits in the middle of the square."""
    (ax, ay, ar), (bx, by, br) = (0, 0, 23), (11, -8.5, 19)
    # where the two circles cross: the crescent's two tips
    d = math.hypot(bx - ax, by - ay)
    a = (ar * ar - br * br + d * d) / (2 * d)
    h = math.sqrt(ar * ar - a * a)
    mx, my = ax + a * (bx - ax) / d, ay + a * (by - ay) / d
    p1 = (mx + h * (by - ay) / d, my - h * (bx - ax) / d)
    p2 = (mx - h * (by - ay) / d, my + h * (bx - ax) / d)
    # its outline is the outer circle's left and bottom edges and the two tips
    left, bottom, top, right = ax - ar, ay + ar, min(p1[1], p2[1]), max(p1[0], p2[0])
    dx, dy = 32 - (left + right) / 2, 32 - (top + bottom) / 2
    p1, p2 = (p1[0] + dx, p1[1] + dy), (p2[0] + dx, p2[1] + dy)
    f = lambda v: ("%.2f" % v).rstrip("0").rstrip(".")
    # the long way round the outer circle from one tip to the other, back along the inner circle
    path = "M%s %sA%s %s 0 1 0 %s %sA%s %s 0 0 1 %s %sZ" % (
        f(p1[0]), f(p1[1]), f(ar), f(ar), f(p2[0]), f(p2[1]), f(br), f(br), f(p1[0]), f(p1[1]))
    return '<path d="%s" fill="{fg}"/>' % path


SHAPES = {"scroll": scroll, "crescent": crescent}


def svg(kind, frame):
    """frame: "round" (rounded square), "full" (the whole square) or "safe" (the whole square, the
    shape scaled into the middle circle that a maskable icon always keeps)."""
    shape = SHAPES[kind]().format(fg=FG, bg=BG)
    if frame == "round":
        back = '<rect width="64" height="64" rx="14" fill="%s"/>' % BG
    else:
        back = '<rect width="64" height="64" fill="%s"/>' % BG
    if frame == "full":
        shape = '<g transform="translate(4 4) scale(.875)">%s</g>' % shape
    elif frame == "safe":
        shape = '<g transform="translate(9.6 9.6) scale(.7)">%s</g>' % shape
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">%s%s</svg>' % (back, shape)


# file name: (frame, size in pixels)
PNGS = {"icon-16.png": ("round", 16), "icon-32.png": ("round", 32), "icon-48.png": ("round", 48),
        "apple-touch-icon.png": ("full", 180), "icon-192.png": ("round", 192), "icon-512.png": ("round", 512),
        "icon-maskable-512.png": ("safe", 512)}


def chrome():
    """A Chrome or Chromium to draw with: $CHROME, or Playwright's, or one on the PATH."""
    for c in (os.environ.get("CHROME"), "/opt/pw-browsers/chromium", shutil.which("chromium"),
              shutil.which("chromium-browser"), shutil.which("google-chrome")):
        if c and os.path.exists(c):
            return c
    raise SystemExit("No Chrome or Chromium found: set CHROME to one")


def draw(markup, size, path, work):
    """Draw an SVG at size x size pixels into the PNG at path, with Chrome, leaving the corners clear."""
    page = os.path.join(work, "icon.html")
    open(page, "w", encoding="utf-8").write('<html><body style="margin:0">%s</body></html>' % markup.replace(
        "<svg ", '<svg width="%d" height="%d" style="display:block" ' % (size, size), 1))
    subprocess.run([chrome(), "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", "--default-background-color=00000000",
                    "--window-size=%d,%d" % (size, size), "--screenshot=" + path, "file://" + page],
                   check=True, capture_output=True)


def generate():
    from PIL import Image
    with tempfile.TemporaryDirectory() as work:
        for kind in SHAPES:
            out = os.path.join(DIR, kind)
            os.makedirs(out, exist_ok=True)
            open(os.path.join(out, "favicon.svg"), "w", encoding="utf-8").write(svg(kind, "round") + "\n")
            for name, (frame, size) in PNGS.items():
                draw(svg(kind, frame), size, os.path.join(out if size > 48 else work, name), work)
            small = [Image.open(os.path.join(work, "icon-%d.png" % s)) for s in (16, 32, 48)]
            small[2].save(os.path.join(out, "favicon.ico"), format="ICO", sizes=[(16, 16), (32, 32), (48, 48)],
                          append_images=small[:2])
            print("Drew %s/" % os.path.relpath(out, os.path.dirname(HERE)))


FILES = ("favicon.svg", "favicon.ico", "apple-touch-icon.png", "icon-192.png", "icon-512.png",
         "icon-maskable-512.png")


def install(out, kind, name, short_name):
    """Copy the icons of kind ("scroll" or "crescent") into the built site's top folder out, with its
    site.webmanifest (name: the site's title; short_name: the label under a home-screen icon)."""
    for f in FILES:
        shutil.copyfile(os.path.join(DIR, kind, f), os.path.join(out, f))
    manifest = {"name": name, "short_name": short_name, "start_url": "./", "display": "browser",
                "background_color": BG, "theme_color": BG,
                "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                          {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
                          {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png",
                           "purpose": "maskable"}]}
    open(os.path.join(out, "site.webmanifest"), "w", encoding="utf-8").write(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")


def tags(up):
    """The lines in a page's head that point to the icons (up: "../" for each folder below the top)."""
    return ('<link rel="icon" href="{u}favicon.ico" sizes="32x32">\n'
            '<link rel="icon" href="{u}favicon.svg" type="image/svg+xml">\n'
            '<link rel="apple-touch-icon" href="{u}apple-touch-icon.png">\n'
            '<link rel="manifest" href="{u}site.webmanifest">\n').format(u=up)


if __name__ == "__main__":
    generate()
