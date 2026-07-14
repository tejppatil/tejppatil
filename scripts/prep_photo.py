"""
Prepare a portrait photo for clean ASCII conversion:
  1. remove the background (rembg) so the subject is isolated
  2. boost LOCAL contrast (CLAHE) so a flatly-lit face gains highlights and
     shadows -- this is what turns a dark blob into a recognizable face
  3. composite the subject onto pure white so the background reads as blank
     (white -> spaces in the ascii ramp)

Output: source-prepped.png (grayscale), consumed by make_ascii_svg.py.
Run once whenever the source photo changes; the ascii SVG itself is static.

    python scripts/prep_photo.py <input.jpg> [output.png]
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image
from rembg import remove

HERE = os.path.dirname(os.path.abspath(__file__))
INP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-photo.jpg")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "source-prepped.png")

# Load and optionally crop to focus on the subject
im = Image.open(INP)
if "Dreamwalker4u.png" in os.path.basename(INP):
    print("Detected Dreamwalker4u.png, using uncropped threshold-mask background removal and badge inversion...")
    gray_orig = np.array(im.convert("L"))
    is_bg = (gray_orig >= 253)
    
    # Apply CLAHE to boost contrast on the hooded figure
    clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
    gray_clahe = clahe.apply(gray_orig)
    
    # Invert the ENTIRE sticker region so that the dark-to-light mapping in make_ascii_svg.py
    # renders the bright elements (visor, text, details) as bright ink, and dark elements as spaces.
    gray_final = gray_clahe.copy()
    gray_final[~is_bg] = 255 - gray_final[~is_bg]
    gray_final[is_bg] = 255
    
    # Feather background edges slightly
    sticker_mask = (~is_bg).astype(np.float32)
    sticker_mask_blur = cv2.GaussianBlur(sticker_mask, (0, 0), 0.5)
    
    out = gray_final.astype(np.float32) * sticker_mask_blur + 255.0 * (1.0 - sticker_mask_blur)
    out = np.clip(out, 0, 255).astype(np.uint8)
    
    Image.fromarray(out, mode="L").save(OUT)
    print("wrote", OUT, out.shape)
else:
    # 1. cut out the subject
    cut = remove(im.convert("RGBA"))
    rgb = np.array(cut.convert("RGB"))
    alpha = np.array(cut.split()[-1])                 # 0 = background

    # 2. local-contrast the luminance (CLAHE)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # a touch of global lift so the face sits in the sparse end of the ramp
    gray = cv2.convertScaleAbs(gray, alpha=1.2, beta=2)

    # 3. paste onto white using the alpha mask (feathered a hair to avoid a halo)
    mask = (alpha.astype(np.float32) / 255.0)
    mask = cv2.GaussianBlur(mask, (0, 0), 0.5)
    out = gray.astype(np.float32) * mask + 255.0 * (1.0 - mask)
    out = np.clip(out, 0, 255).astype(np.uint8)

    Image.fromarray(out, mode="L").save(OUT)
    print("wrote", OUT, out.shape)
