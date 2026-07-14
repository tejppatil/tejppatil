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

COLS = 130
ROWS = 69
CELL_W = 6.2
CELL_H = 11.5
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
ROW_DUR = 0.08
STAGGER = 0.08       # == ROW_DUR -> a single cursor sweeping down

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
    if IS_DREAMWALKER and y >= 52:
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
parts.append(
    '<defs>'
    f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
    f'</linearGradient>'
    f'<linearGradient id="textGrad" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0%" stop-color="#ffffff"/>'
    f'<stop offset="40%" stop-color="#e1e4e8"/>'
    f'<stop offset="80%" stop-color="#abb4be"/>'
    f'<stop offset="100%" stop-color="#7d8590"/>'
    f'</linearGradient>'
    f'<linearGradient id="chromeGrad" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0%" stop-color="#ffffff"/>'
    f'<stop offset="40%" stop-color="#f1f3f5"/>'
    f'<stop offset="45%" stop-color="#9ca3af"/>'
    f'<stop offset="70%" stop-color="#4b5563"/>'
    f'<stop offset="100%" stop-color="#1f2937"/>'
    f'</linearGradient>'
    f'<linearGradient id="silverGrad" x1="0" y1="0" x2="1" y2="1">'
    f'<stop offset="0%" stop-color="#f3f4f6"/>'
    f'<stop offset="50%" stop-color="#9ca3af"/>'
    f'<stop offset="100%" stop-color="#374151"/>'
    f'</linearGradient>'
    f'<filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">'
    f'<feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000000" flood-opacity="0.8"/>'
    f'</filter>'
    f'<pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">'
    f'<rect width="20" height="20" fill="none"/>'
    f'<path d="M 20 0 L 0 0 0 20" fill="none" stroke="#30363d" stroke-width="0.5" stroke-opacity="0.25"/>'
    f'</pattern>'
    f'</defs>'
)

parts.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#bg)"/>')
parts.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#grid)"/>')
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
    text = (f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="url(#textGrad)" filter="url(#shadow)" '
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
    badge_h = 175
    badge_w = 760
    badge_x = (CANVAS_W - badge_w) // 2
    
    # Animation delay based on 52 rows * 0.08s stagger = 4.16s
    badge_delay = 4.2
    
    # Wrap in animated group if not static
    if STATIC:
        parts.append('<g>')
    else:
        parts.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{badge_delay:.2f}s" dur="0.8s" fill="freeze"/>')
    
    # Outer frame with a custom winged shape, metallic gradient stroke, and drop shadow
    by, bx, bw, bh = badge_y, badge_x, badge_w, badge_h
    pts_outer = f"{bx+50},{by} {bx+bw-50},{by} {bx+bw},{by+50} {bx+bw-40},{by+110} {bx+bw-120},{by+120} {bx+bw-140},{by+150} {CANVAS_W/2},{by+bh} {bx+140},{by+150} {bx+120},{by+120} {bx+40},{by+110} {bx},{by+50}"
    parts.append(f'<polygon points="{pts_outer}" fill="{BG}" stroke="url(#silverGrad)" stroke-width="2.5" filter="url(#shadow)"/>')
    
    # Inner border to create double-border highlight
    pts_inner = f"{bx+52},{by+4} {bx+bw-52},{by+4} {bx+bw-4},{by+50} {bx+bw-42},{by+107} {bx+bw-121},{by+116} {bx+bw-141},{by+145} {CANVAS_W/2},{by+bh-4} {bx+141},{by+145} {bx+121},{by+116} {bx+42},{by+107} {bx+4},{by+50}"
    parts.append(f'<polygon points="{pts_inner}" fill="none" stroke="url(#silverGrad)" stroke-width="1.2" stroke-opacity="0.8"/>')
    
    # Hexagon for padlock at the bottom center
    lock_center_y = by + 144
    hex_pts = f"411,{lock_center_y-14} 435,{lock_center_y-14} 447,{lock_center_y} 435,{lock_center_y+14} 411,{lock_center_y+14} 399,{lock_center_y}"
    parts.append(f'<polygon points="{hex_pts}" fill="{BG}" stroke="url(#silverGrad)" stroke-width="1.5"/>')
    
    # Padlock icon inside hexagon
    lock_x = 415
    lock_y = lock_center_y - 7
    parts.append(f'<rect x="{lock_x}" y="{lock_y}" width="16" height="12" rx="2" fill="none" stroke="url(#silverGrad)" stroke-width="1.5"/>')
    parts.append(f'<path d="M {lock_x+4} {lock_y} A 4 4 0 0 1 {lock_x+12} {lock_y}" fill="none" stroke="url(#silverGrad)" stroke-width="1.5"/>')
    
    # Decorative horizontal cyber lines extending from the padlock hexagon
    parts.append(f'<line x1="160" y1="{lock_center_y}" x2="399" y2="{lock_center_y}" stroke="url(#silverGrad)" stroke-width="1.2" stroke-dasharray="8 4"/>')
    parts.append(f'<line x1="447" y1="{lock_center_y}" x2="686" y2="{lock_center_y}" stroke="url(#silverGrad)" stroke-width="1.2" stroke-dasharray="8 4"/>')
    
    # Accent dots on the ends of the lines
    parts.append(f'<circle cx="160" cy="{lock_center_y}" r="2" fill="url(#silverGrad)"/>')
    parts.append(f'<circle cx="686" cy="{lock_center_y}" r="2" fill="url(#silverGrad)"/>')
    
    # DREAMWALKER4U Text - slanted, bold system font, chrome gradient fill, dark outline, shadow
    font_stack = "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    parts.append(
        f'<text x="{CANVAS_W/2}" y="{by+78}" fill="url(#chromeGrad)" stroke="#090d13" stroke-width="6" paint-order="stroke fill" '
        f'font-family="{font_stack}" font-size="46" font-weight="900" letter-spacing="8px" filter="url(#shadow)" transform="skewX(-10)" transform-origin="{CANVAS_W/2} {by+78}" text-anchor="middle">DREAMWALKER4U</text>'
    )
    
    # Tagline text
    parts.append(
        f'<text x="{CANVAS_W/2}" y="{by+116}" fill="{INK}" font-family="{font_stack}" font-size="12" font-weight="800" '
        f'letter-spacing="5px" text-anchor="middle">THINK. ANALYZE. SECURE. CREATE.</text>'
    )
    
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
