"""
Convert a portrait photo into a CLEAN, monochrome ASCII-art SVG (Andrew6rant
style: one light-gray color, subject isolated on a dark background) that "types"
itself in like a terminal, then holds.

Monochrome is deliberate -- per-character rainbow color is what makes ASCII
portraits look noisy. One fill color + a good density ramp + high contrast (so a
busy background washes out to blank) reads as neat and legible.

GitHub renders SVGs embedded via <img> and runs their SMIL animations there (JS
does not run). Each row is revealed with a left-to-right clip wipe plus a small
block cursor riding the wipe edge, staggered top -> bottom, so the whole
portrait prints once and freezes.
"""
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# defaults to the prepped grayscale image (see prep_photo.py), which already has
# the background removed + local contrast applied.
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-prepped.png")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "avi-ascii.svg")

COLS = 100
ROWS = 53
CELL_W = 8
CELL_H = 15
RAMP = " .`:-=+*cs#%@"  # bright(sparse) -> dark(dense); leading space clears bg

# the prepped image already has bg removed + CLAHE local contrast, so only
# light global tuning is needed here.
CONTRAST = 1.05
BRIGHTNESS = 1.0
GAMMA = 1.18          # >1 brightens mids -> face lands in sparser chars
SHARPEN = False
WHITE_FLOOR = 0.93    # luminance above this is forced to blank (space)

PAD = 20
TITLEBAR_H = 30
STATUS_H = 30
ART_W = COLS * CELL_W
ART_H = ROWS * CELL_H
CANVAS_W = ART_W + PAD * 2
CANVAS_H = TITLEBAR_H + ART_H + STATUS_H + PAD

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
INK = "#c9d1d9"      # the single ascii color (matches Andrew6rant)
CURSOR = "#c9d1d9"

# ---- reveal timing (one-shot; a cursor rasters top -> bottom) -------------
ROW_DUR = 0.11
STAGGER = 0.11       # == ROW_DUR -> a single cursor sweeping down

# ---- 1. sample the image into a COLS x ROWS grayscale grid ----------------
im = Image.open(SRC).convert("L")               # grayscale
if SHARPEN:
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=2))
im = ImageEnhance.Brightness(im).enhance(BRIGHTNESS)
im = ImageEnhance.Contrast(im).enhance(CONTRAST)
im = im.resize((COLS, ROWS), Image.LANCZOS)
px = im.load()

STATIC = bool(os.environ.get("STATIC"))  # emit frozen state for previews
IS_DREAMWALKER = "Dreamwalker4u" in os.path.basename(SRC) or os.path.exists(os.path.join(HERE, "..", "Dreamwalker4u.png"))

rows_txt = []
for y in range(ROWS):
    if IS_DREAMWALKER and y >= 39:
        rows_txt.append(" " * COLS)
        continue
    chars = []
    for x in range(COLS):
        lum = px[x, y] / 255.0
        lum = pow(lum, GAMMA)
        if lum >= WHITE_FLOOR:
            chars.append(" ")
            continue
        idx = int((1.0 - lum) * (len(RAMP) - 1) + 0.5)
        idx = max(0, min(len(RAMP) - 1, idx))
        chars.append(RAMP[idx])
    rows_txt.append("".join(chars))

art_top = TITLEBAR_H + PAD * 0.35

# ---- 2. assemble SVG ------------------------------------------------------
parts = []
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
    f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, '
    f'Menlo, Consolas, monospace">'
)
parts.append('<defs>'
             f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
             f'</linearGradient>'
             f'<linearGradient id="metalGrad" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0%" stop-color="#ffffff"/>'
             f'<stop offset="35%" stop-color="#f1f3f5"/>'
             f'<stop offset="50%" stop-color="#abb4be"/>'
             f'<stop offset="51%" stop-color="#7d8590"/>'
             f'<stop offset="85%" stop-color="#c9d1d9"/>'
             f'<stop offset="100%" stop-color="#f6f8fa"/>'
             f'</linearGradient>'
             f'<linearGradient id="borderGrad" x1="0" y1="0" x2="1" y2="1">'
             f'<stop offset="0%" stop-color="#d1d5db"/>'
             f'<stop offset="50%" stop-color="#4b5563"/>'
             f'<stop offset="100%" stop-color="#111827"/>'
             f'</linearGradient>'
             f'<filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">'
             f'<feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000000" flood-opacity="0.8"/>'
             f'</filter>'
             f'</defs>')

parts.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#bg)"/>')
parts.append(f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" '
             f'fill="none" stroke="{FRAME}" stroke-width="1"/>')

parts.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>')
for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
parts.append(f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
             f'text-anchor="middle">Dreamwalker4u@github: ~$ ./portrait.sh</text>')

# one <text> per row (single color -> no per-char markup, tiny file)
font_size = CELL_H * 0.86
for ry, line in enumerate(rows_txt):
    y = art_top + ry * CELL_H + CELL_H * 0.74
    row_y = art_top + ry * CELL_H
    delay = ry * STAGGER
    safe = html.escape(line)
    text = (f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{INK}" '
            f'font-size="{font_size:.1f}" textLength="{ART_W}" lengthAdjust="spacing">{safe}</text>')

    if STATIC:
        parts.append(text)
        continue

    parts.append(
        f'<clipPath id="r{ry}"><rect x="{PAD}" y="{row_y:.1f}" height="{CELL_H}" width="0">'
        f'<animate attributeName="width" from="0" to="{ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/></rect></clipPath>'
    )
    parts.append(f'<g clip-path="url(#r{ry})">{text}</g>')
    parts.append(
        f'<rect y="{row_y+1:.1f}" width="{CELL_W}" height="{CELL_H-2}" fill="{CURSOR}" opacity="0">'
        f'<animate attributeName="x" from="{PAD}" to="{PAD+ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/>'
        f'<set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/>'
        f'<set attributeName="opacity" to="0" begin="{delay+ROW_DUR:.3f}s"/></rect>'
    )

# ---- 3. draw the vector badge if source is Dreamwalker4u ------------------
if IS_DREAMWALKER:
    badge_y = 620
    badge_w = 720
    badge_x = (CANVAS_W - badge_w) // 2
    bh = 175
    
    # Wrap in animated group if not static
    if STATIC:
        parts.append('<g>')
    else:
        parts.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="4.2s" dur="0.8s" fill="freeze"/>')
    
    # Outer frame with a metallic gradient stroke and a drop shadow filter
    by, bx, bw = badge_y, badge_x, badge_w
    pts = f"{bx},{by+20} {bx+20},{by} {bx+bw-20},{by} {bx+bw},{by+20} {bx+bw},{by+bh-20} {bx+bw-20},{by+bh} {bx+20},{by+bh} {bx},{by+bh-20}"
    parts.append(f'<polygon points="{pts}" fill="{BG}" stroke="url(#metalGrad)" stroke-width="2.5" filter="url(#shadow)"/>')
    
    # Dash lines
    parts.append(f'<line x1="{bx+10}" y1="{by+30}" x2="{bx+bw-10}" y2="{by+30}" stroke="url(#borderGrad)" stroke-width="1.5" stroke-dasharray="6 3"/>')
    parts.append(f'<line x1="{bx+10}" y1="{by+bh-35}" x2="{bx+bw-10}" y2="{by+bh-35}" stroke="url(#borderGrad)" stroke-width="1.5" stroke-dasharray="6 3"/>')
    
    # DREAMWALKER4U Text - Ultra-bold system-ui font stack with metallic gradient, stroke outline, and shadow filter
    font_stack = "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    parts.append(
        f'<text x="{CANVAS_W/2}" y="{by+85}" fill="url(#metalGrad)" stroke="#090d13" stroke-width="5" paint-order="stroke fill" '
        f'font-family="{font_stack}" font-size="46" font-weight="900" letter-spacing="8px" filter="url(#shadow)" text-anchor="middle">DREAMWALKER4U</text>'
    )
    
    # Tagline
    parts.append(
        f'<text x="{CANVAS_W/2}" y="{by+125}" fill="{INK}" font-family="{font_stack}" font-size="13" font-weight="800" '
        f'letter-spacing="5px" text-anchor="middle">THINK. ANALYZE. SECURE. CREATE.</text>'
    )
    
    # Padlock icon
    lock_x = CANVAS_W // 2 - 8
    lock_y = by + bh - 26
    parts.append(f'<rect x="{lock_x}" y="{lock_y}" width="16" height="12" rx="2" fill="none" stroke="url(#metalGrad)" stroke-width="2"/>')
    parts.append(f'<path d="M {lock_x+4} {lock_y} A 4 4 0 0 1 {lock_x+12} {lock_y}" fill="none" stroke="url(#metalGrad)" stroke-width="2"/>')
    
    parts.append('</g>')

# status bar with a steady blinking cursor
status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
status_y = status_line_y + 19
parts.append(f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W}" y2="{status_line_y:.1f}" stroke="{FRAME}"/>')
parts.append(f'<text x="{PAD}" y="{status_y:.1f}" fill="{TITLE_TEXT}" font-size="13">'
             f'Dreamwalker4u@github:~$ whoami <tspan fill="{INK}">Tejas Prakash Patil</tspan></text>')
parts.append(f'<rect x="{PAD+256}" y="{status_y-12:.1f}" width="8" height="14" fill="{INK}">'
             f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
             f'dur="1s" repeatCount="indefinite"/></rect>')

parts.append("</svg>")
svg = "".join(parts)
with open(OUT, "w") as f:
    f.write(svg)
print("wrote", OUT, len(svg), "bytes;", CANVAS_W, "x", CANVAS_H)
