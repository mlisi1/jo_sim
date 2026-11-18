"""Composition toolkit for the docs videos (runs on the host).

A clip is a length and a function frame index -> 1920x1080 RGB image. Clips are built from the rig
frames (~/.cache/jo_sim_media/rig/<shot>/...), title cards and rendered terminals, combined with
split-screen, picture-in-picture, captions and crossfades, and encoded with ffmpeg (H.264, yuv420p,
faststart), plus a poster JPEG. The videos are written by docs/gen/media/videos.py.
"""
import functools, json, os, pathlib, subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 25
RIG = pathlib.Path.home() / '.cache' / 'jo_sim_media' / 'rig'
FONTS = pathlib.Path.home() / '.cache' / 'jo_sim_media' / 'fonts'
ROOT = pathlib.Path(__file__).resolve().parents[3]
VIDEOS = ROOT / 'docs' / 'assets' / 'videos'

NAVY_950, NAVY_900, NAVY_800, NAVY_700 = (2, 6, 23), (11, 18, 32), (17, 26, 46), (28, 39, 64)
CYAN, CYAN_300, AMBER, WHITE, MUTED = (6, 182, 212), (103, 232, 249), (245, 158, 11), (241, 245, 249), (148, 163, 184)
GREEN, RED = (52, 211, 153), (248, 113, 113)


@functools.lru_cache(None)
def font(size, weight='SemiBold', mono=False):
    name = f'JetBrainsMono-{"Bold" if weight == "Bold" else "Regular"}.ttf' if mono else f'Inter-{weight}.ttf'
    return ImageFont.truetype(str(FONTS / name), size)


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


class Clip:
    def __init__(self, n, fn):
        self.n, self.fn = int(n), fn

    def __call__(self, i):
        return self.fn(min(max(int(i), 0), self.n - 1))

    def __len__(self):
        return self.n

    def map(self, f):
        """f(image, i) -> image."""
        return Clip(self.n, lambda i: f(self(i), i))

    def cut(self, a=0, b=None):
        b = self.n if b is None else b
        return Clip(b - a, lambda i: self(a + i))

    def speed(self, k):
        """k > 1: faster (drops frames)."""
        return Clip(int(self.n / k), lambda i: self(round(i * k)))

    def hold(self, n_end=0, n_start=0):
        return Clip(self.n + n_end + n_start, lambda i: self(i - n_start))

    def fade(self, n_in=0, n_out=0, color=NAVY_950):
        def f(img, i):
            a = 1.0
            if n_in and i < n_in:
                a = ease(i / n_in)
            if n_out and i >= self.n - n_out:
                a = min(a, ease((self.n - 1 - i) / n_out))
            return img if a >= 1 else Image.blend(Image.new('RGB', img.size, color), img, a)
        return self.map(f)


# ── sources ─────────────────────────────────────────────────────────────
def frames(shot, cam='main', size=(W, H), crop=None):
    d = RIG / shot / cam
    files = sorted(d.glob('*.png'))
    if not files:
        raise FileNotFoundError(d)

    @functools.lru_cache(8)
    def load(i):
        im = Image.open(files[i]).convert('RGB')
        if crop:
            im = im.crop(crop)
        return cover(im, size)
    return Clip(len(files), load)


def records(shot):
    return [json.loads(line) for line in open(RIG / shot / 'frames.jsonl')]


def cover(im, size, ax=0.5, ay=0.5):
    """Scale and crop to fill `size`; (ax, ay) place the crop (0.5, 0.5: centred)."""
    w, h = size
    k = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x, y = round((im.width - w) * ax), round((im.height - h) * ay)
    return im.crop((x, y, x + w, y + h))


def solid(n, color=NAVY_950):
    img = Image.new('RGB', (W, H), color)
    return Clip(n, lambda i: img)


@functools.lru_cache(1)
def background():
    """Navy with a soft cyan glow at the top, the site's hero style."""
    from PIL import ImageChops
    glow = Image.new('RGB', (W, H), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W * 0.15, -H * 0.4, W * 0.85, H * 0.7), fill=(8, 60, 80))
    return ImageChops.add(Image.new('RGB', (W, H), NAVY_950), glow.filter(ImageFilter.GaussianBlur(220)))


def card(n, title, subtitle=None, logo=True, code=None):
    """A title card: logo, title, subtitle and an optional command line; elements rise in."""
    bg = background()
    render = Image.open(ROOT / 'docs/assets/images/jo_render.png').convert('RGBA') if logo else None

    def f(i):
        img = bg.copy()
        d = ImageDraw.Draw(img)
        t = i / FPS
        y = H // 2 - (150 if logo else 40)
        if render:
            a = ease(t / 0.6)
            r = render.resize((300, 300), Image.LANCZOS)
            r.putalpha(r.getchannel('A').point(lambda v: int(v * a)))
            img.paste(r, (W // 2 - 150, y - 250 + int(20 * (1 - a))), r)
            y += 90
        a = ease((t - 0.25) / 0.6)
        _text_center(d, title, y + int(16 * (1 - a)), font(84, 'Bold'), _mix(NAVY_950, WHITE, a))
        if subtitle:
            a = ease((t - 0.5) / 0.6)
            _text_center(d, subtitle, y + 120 + int(16 * (1 - a)), font(38, 'Regular'), _mix(NAVY_950, MUTED, a))
        if code:
            a = ease((t - 0.8) / 0.6)
            f_ = font(40, mono=True)
            tw = d.textlength(code, font=f_)
            x0, y0 = (W - tw) / 2 - 36, y + 210
            d.rounded_rectangle((x0, y0, x0 + tw + 72, y0 + 76), 14, fill=_mix(NAVY_950, NAVY_700, a),
                                outline=_mix(NAVY_950, CYAN, a), width=2)
            d.text((x0 + 36, y0 + 16), code, font=f_, fill=_mix(NAVY_950, CYAN_300, a))
        return img
    return Clip(n, f)


def _text_center(d, text, y, f, fill):
    d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def _mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def terminal(n, lines, size=(860, 1080), title='bash', font_size=26, typing_cps=28):
    """A rendered terminal. lines: list of (start_frame, kind, text); kind 'cmd' is typed after a
    prompt, 'out' appears at once (text may be a list of (text, colour) spans)."""
    w, h = size
    f = font(font_size, mono=True)
    lh = int(font_size * 1.5)

    def f_(i):
        img = Image.new('RGB', size, NAVY_900)
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, w, 54), fill=NAVY_800)
        for k, c in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
            d.ellipse((24 + 30 * k, 19, 40 + 30 * k, 35), fill=c)
        d.text((w / 2 - d.textlength(title, font=font(22, 'Regular')) / 2, 14), title, font=font(22, 'Regular'), fill=MUTED)
        rows = []
        cols = int((w - 56) // d.textlength('M', font=f))
        for start, kind, text in lines:
            if i < start:
                break
            if kind == 'cmd':
                k = int((i - start) / FPS * typing_cps)
                rows.append([('$ ', GREEN), (text[:k], WHITE)] + ([('▌', CYAN)] if k < len(text) + 10 and (i // 8) % 2 == 0 else []))
            else:
                spans = text if isinstance(text, list) else [(text, MUTED)]
                rows.extend(_wrap(spans, cols))
        max_rows = (h - 80) // lh
        rows = rows[-max_rows:]
        y = 76
        for spans in rows:
            x = 28
            for s, c in spans:
                d.text((x, y), s, font=f, fill=c)
                x += d.textlength(s, font=f)
            y += lh
        return img
    return Clip(n, f_)


def _wrap(spans, cols, indent='  '):
    """Splits a list of (text, colour) spans into rows of at most `cols` characters."""
    rows, row, n = [], [], 0
    for text, colour in spans:
        while text:
            room = cols - n
            if len(text) <= room:
                row.append((text, colour))
                n += len(text)
                break
            cut = text.rfind(' ', 0, room + 1)
            cut = cut if cut > 0 else room
            row.append((text[:cut], colour))
            rows.append(row)
            row, n, text = [(indent, colour)], len(indent), text[cut:].lstrip()
    if row:
        rows.append(row)
    return rows


# ── layout ──────────────────────────────────────────────────────────────
def split(a, b, ratio=0.5, gap=6, ax_a=0.5, ax_b=0.5):
    """Side by side: a on the left (cover-cropped), b on the right; ax_*: horizontal crop anchor."""
    wa = int(W * ratio) - gap // 2
    wb = W - wa - gap

    def f(i):
        img = Image.new('RGB', (W, H), NAVY_950)
        img.paste(cover(a(i), (wa, H), ax_a), (0, 0))
        img.paste(cover(b(i), (wb, H), ax_b), (wa + gap, 0))
        return img
    return Clip(min(len(a), len(b)), f)


def pip(main, small, corner='br', width=560, margin=36, label=None, at=None):
    """small over main, in a corner or with its top-left corner at `at` (x, y)."""
    def f(i):
        img = main(i).copy()
        s = small(i)
        s = s.resize((width, round(width * s.height / s.width)), Image.LANCZOS)
        x = W - width - margin if 'r' in corner else margin
        y = H - s.height - margin if 'b' in corner else margin
        x, y = at or (x, y)
        shadow = Image.new('RGBA', (s.width + 40, s.height + 40), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle((20, 20, s.width + 20, s.height + 20), 16, fill=(0, 0, 0, 150))
        shadow = shadow.filter(ImageFilter.GaussianBlur(12))
        img.paste(shadow, (x - 20, y - 12), shadow)
        mask = Image.new('L', s.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, s.width - 1, s.height - 1), 14, fill=255)
        img.paste(s, (x, y), mask)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((x, y, x + s.width - 1, y + s.height - 1), 14, outline=(255, 255, 255, 60), width=2)
        if label:
            chip(d, label, x + 14, y + 14, size=22)
        return img
    return Clip(len(main), f)


def chip(d, text, x, y, size=24, fg=WHITE, bg=(11, 18, 32), dot=None):
    f = font(size, 'SemiBold')
    tw = d.textlength(text, font=f)
    pad = size * 0.6
    dx = size * 0.9 if dot else 0
    d.rounded_rectangle((x, y, x + tw + 2 * pad + dx, y + size * 1.7), size * 0.85, fill=bg)
    if dot:
        r = size * 0.25
        cy = y + size * 0.85
        d.ellipse((x + pad, cy - r, x + pad + 2 * r, cy + r), fill=dot)
    d.text((x + pad + dx, y + size * 0.3), text, font=f, fill=fg)
    return x + tw + 2 * pad + dx


def st(text, x=None, y=28, dot=None, size=26, frames=None):
    """One stamp for stamps(): x None continues the row after the previous stamp; frames (a, b)
    limits it to that stretch of the clip."""
    return dict(text=text, x=x, y=y, dot=dot, size=size, frames=frames)


@functools.lru_cache(None)
def _pill(text, dot, size):
    """A stamp at full opacity (RGBA), drawn at 3x and reduced for smooth edges."""
    k, f = 3, font(size * 3, 'SemiBold')
    pad, dx, h = size * 0.65 * k, (size * 0.9 * k if dot else 0), round(size * 1.75) * k
    w = round(f.getlength(text) + 2 * pad + dx)
    im = Image.new('RGBA', (w, h), (2, 6, 23, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), h / 2, fill=(2, 6, 23, 215))
    if dot:
        r = size * 0.26 * k
        d.ellipse((pad, h / 2 - r, pad + 2 * r, h / 2 + r), fill=tuple(dot) + (255,))
    d.text((pad + dx, h / 2), text, font=f, fill=WHITE + (255,), anchor='lm')
    return im.resize((w // k, h // k), Image.LANCZOS)


def stamps(clip, items, n_in=14, n_out=14, delay=6, tail=12):
    """Labels naming the views: each eases in (fading and rising), stays, and eases out `tail`
    frames before the end of the clip (or of its `frames` stretch), clear of the final fade."""
    def f(img, i):
        img, end_x = img.copy(), 0
        for s in items:
            pill = _pill(s['text'], s['dot'], s['size'])
            x = end_x + 12 if s['x'] is None else s['x']
            end_x = x + pill.width
            a0, b0 = s['frames'] or (delay, len(clip) - tail)
            a = min(ease((i - a0) / n_in), ease((b0 - i) / n_out))
            if a <= 0:
                continue
            mask = pill.getchannel('A').point(lambda v: int(v * a))
            img.paste(pill.convert('RGB'), (x, s['y'] + round(12 * (1 - a))), mask)
        return img
    return clip.map(f)


def caption(clip, title, sub=None, n_in=12, at=(64, 0), anchor='bl'):
    """A lower-third: amber bar, title and optional subtitle, sliding in."""
    def f(img, i):
        img = img.convert('RGBA')
        a = ease(i / n_in) if n_in else 1
        a = min(a, ease((len(clip) - 1 - i) / 10))
        layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        ft, fs = font(46, 'Bold'), font(28, 'Regular')
        tw = max(d.textlength(title, font=ft), d.textlength(sub, font=fs) if sub else 0)
        bh = 104 if sub else 74
        x = at[0] - int(30 * (1 - a))
        y = H - 64 - bh if anchor == 'bl' else 64
        d.rounded_rectangle((x, y, x + tw + 64, y + bh), 14, fill=(2, 6, 23, int(205 * a)))
        d.rectangle((x, y + 14, x + 6, y + bh - 14), fill=AMBER + (int(255 * a),))
        d.text((x + 30, y + 12), title, font=ft, fill=WHITE + (int(255 * a),))
        if sub:
            d.text((x + 31, y + 66), sub, font=fs, fill=(203, 213, 225, int(255 * a)))
        img.alpha_composite(layer)
        return img.convert('RGB')
    return clip.map(f)


def overlay(clip, draw):
    """draw(ImageDraw, i) on top of every frame."""
    def f(img, i):
        img = img.copy()
        draw(ImageDraw.Draw(img), i)
        return img
    return clip.map(f)


def concat(*clips, xfade=12):
    """Clips one after the other, with crossfades of `xfade` frames."""
    starts, t = [], 0
    for c in clips:
        starts.append(t)
        t += len(c) - xfade
    n = t + xfade

    def f(i):
        for k in range(len(clips) - 1, -1, -1):
            if i >= starts[k]:
                img = clips[k](i - starts[k])
                if k and i - starts[k] < xfade:
                    prev = clips[k - 1](i - starts[k - 1])
                    img = Image.blend(prev, img, ease((i - starts[k]) / xfade))
                return img
    return Clip(n, f)


# ── output ──────────────────────────────────────────────────────────────
def render(clip, name, crf=28, poster_at=None, size=(1600, 900)):
    """Encodes the clip to docs/assets/videos/<name>.mp4 and a poster <name>.jpg."""
    VIDEOS.mkdir(parents=True, exist_ok=True)
    out = VIDEOS / f'{name}.mp4'
    scale = [] if size == (W, H) else ['-vf', f'scale={size[0]}:{size[1]}:flags=lanczos']
    p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                          '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', *scale, '-c:v', 'libx264',
                          '-preset', 'slow', '-crf', str(crf), '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                          '-an', str(out)], stdin=subprocess.PIPE)
    poster_at = len(clip) // 2 if poster_at is None else poster_at
    for i in range(len(clip)):
        img = clip(i)
        if i == poster_at:
            img.resize(size, Image.LANCZOS).save(VIDEOS / f'{name}.jpg', quality=84)
        p.stdin.write(img.tobytes())
        if i % 100 == 0:
            print(f'  {name}: {i}/{len(clip)}', flush=True)
    p.stdin.close()
    p.wait()
    print(f'{out}: {len(clip) / FPS:.1f} s, {out.stat().st_size / 1e6:.1f} MB')
    return out


def preview(clip, path, every=None, cols=4, width=480):
    """A contact sheet of the clip, to check it without playing it."""
    every = every or max(1, len(clip) // 12)
    idx = list(range(0, len(clip), every))
    h = round(width * H / W)
    rows = (len(idx) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * width, rows * h), (0, 0, 0))
    for k, i in enumerate(idx):
        sheet.paste(clip(i).resize((width, h)), ((k % cols) * width, (k // cols) * h))
    sheet.save(path, quality=85)
    return path
