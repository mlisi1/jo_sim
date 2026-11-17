#!/usr/bin/env python3
"""Numbered markers on a screenshot, for the docs. The page explains each number in a list under
the image, so the text stays searchable.

    annotate.py IN.png OUT.jpg [--width 1920] X,Y [X,Y ...]

X,Y are pixel coordinates in IN.png; markers are numbered 1, 2, ... in the order given.
Without markers it only resizes and converts.
"""
import argparse

from PIL import Image, ImageDraw, ImageFont

AMBER, DARK = (245, 158, 11), (15, 23, 42)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--width', type=int, default=1920)
    ap.add_argument('points', nargs='*')
    a = ap.parse_args()
    img = Image.open(a.src).convert('RGB')
    scale = a.width / img.width
    img = img.resize((a.width, round(img.height * scale)), Image.LANCZOS)
    draw = ImageDraw.Draw(img)
    r = 22
    font = ImageFont.truetype(FONT, 26)
    for n, p in enumerate(a.points, 1):
        x, y = (float(v) * scale for v in p.split(','))
        draw.ellipse([x - r - 3, y - r - 3, x + r + 3, y + r + 3], fill=DARK)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=AMBER)
        draw.text((x, y), str(n), font=font, fill=DARK, anchor='mm')
    img.save(a.dst, quality=85, optimize=True, progressive=True)


if __name__ == '__main__':
    main()
