#!/usr/bin/env python3
"""Wallpapers 04.11.2026 (author): the cover streaklines coloured like a PIV image, the green 532 nm laser sheet
on black, with a soft glow. Usage: wallpaper_piv.py <cover folder> <output folder>.
Phone 1290x2796 (central part of the plate, all six strips); desktop 3840x2400 (strips 2-4, full plate)."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
LASER = np.array([40, 255, 50], float)/255   # 532 nm green
im = Image.open(src/'COVER_5100x6600.png').convert('L')
W, H = im.size


def colour(g):
    a = np.asarray(g, float)/255
    glow = np.asarray(g.filter(ImageFilter.GaussianBlur(radius=max(2, g.size[0]//600))), float)/255
    core = np.clip(a, 0, 1)[..., None]*(0.75*LASER + 0.25)        # line centres slightly whiter, like a saturated sensor
    halo = np.clip(1.3*glow, 0, 1)[..., None]*LASER*0.55
    return Image.fromarray((np.clip(core + halo, 0, 1)*255).astype(np.uint8))


steps = [('phone', 1290, 2796), ('desktop', 3840, 2400)]
for i, (name, w, h) in enumerate(steps):
    if name == 'phone':
        cw = int(round(H*w/h)); x0 = (W - cw)//2
        crop = im.crop((x0, 0, x0 + cw, H))
    else:
        crop = Image.new('L', (int(round(3343*w/h)), 3343))
        crop.paste(im.crop((0, 1069, W, 1069 + 3343)), ((crop.size[0] - W)//2, 0))
    res = colour(crop.resize((w, h), Image.LANCZOS))
    res.save(out/('WALLPAPER_%s_%dx%d.png' % (name, w, h)))
    print('[%d/%d %3.0f%%] %s %dx%d; ETA %s' % (i + 1, len(steps), 100*(i + 1)/len(steps), name, w, h,
                                                  'done' if i + 1 == len(steps) else '<1 min'), flush=True)
