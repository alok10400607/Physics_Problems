#!/usr/bin/env python3
"""Trim large blank margins from figures (e.g. a small drawing saved on a full page).
Usage: python3 -I tools/trim_figures.py [P000164 ...]   (no IDs = every figure in the bank)
A figure is trimmed only when its content covers less than 60% of the image area. Width and height
in the problem file are updated, and figures still narrower than 600 px stay marked needs_redraw."""
import json, pathlib, sys
from PIL import Image, ImageChops
BANK = pathlib.Path(__file__).resolve().parent.parent / "bank"

def trim(path, pad=12):
    im = Image.open(path)
    rgba = im.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255)); bg.alpha_composite(rgba)
    diff = ImageChops.difference(bg.convert("RGB"), Image.new("RGB", rgba.size, "white"))
    box = diff.point(lambda v: 255 if v > 18 else 0).getbbox()
    if not box: return None
    area = (box[2] - box[0]) * (box[3] - box[1])
    if area >= 0.6 * im.size[0] * im.size[1]: return None
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(im.size[0], box[2] + pad), min(im.size[1], box[3] + pad))
    im.crop(box).save(path)
    return im.crop(box).size

if len(sys.argv) == 3 and sys.argv[1] == "--file":   # used by the importer on a single extracted file
    trim(sys.argv[2]); sys.exit(0)
ids = set(sys.argv[1:])
n = 0
for f in sorted((BANK / "problems").rglob("P*.json")):
    p = json.loads(f.read_text())
    if ids and p["id"] not in ids: continue
    changed = False
    for a in p["assets"]:
        if a["format"] not in ("png", "jpg", "webp"): continue
        size = trim(BANK / "assets" / a["file"])
        if size:
            a["width"], a["height"] = size; a["needs_redraw"] = a["needs_redraw"] or size[0] < 600
            changed = True; n += 1; print(f"trimmed {a['id']} to {size[0]}×{size[1]}")
    if changed: f.write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n")
print(f"{n} figure(s) trimmed")
