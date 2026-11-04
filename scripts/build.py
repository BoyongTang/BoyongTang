#!/usr/bin/env python3
"""Draw the BoyongTang profile images: an academic title page and figures in black-and-white manga ink.

Every image is plain SVG. The few glyphs each image uses are cut out of OFL fonts
(Noto Serif JP / SC, Cormorant Garamond) and embedded, so GitHub shows the same
lettering on every device.

    FONT_DIR=/path/to/fonts python3 scripts/build.py

FONT_DIR must hold NotoSerifJP[wght].ttf, NotoSerifSC[wght].ttf,
CormorantGaramond-Medium.ttf, CormorantGaramond-MediumItalic.ttf
and CormorantGaramond-SemiBold.ttf
(all from github.com/google/fonts, ofl/).
"""
import base64
import io
import math
import os
import random
from collections import defaultdict
from html import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets'
FONT_DIR = Path(os.environ.get('FONT_DIR', ROOT / 'fonts-src'))

# family -> (file, weight for variable fonts)
FONTS = {
    'mincho': ('NotoSerifJP[wght].ttf', 500),
    'song': ('NotoSerifSC[wght].ttf', 500),
    'garamond': ('CormorantGaramond-Medium.ttf', None),
    'garamond-i': ('CormorantGaramond-MediumItalic.ttf', None),
    'garamond-b': ('CormorantGaramond-SemiBold.ttf', None),
}

THEMES = {
    'light': dict(paper='#f2f0eb', ink='#161616', tone='#161616', soft='#5c5b58',
                  box='#fbfaf7', rain='#fbfaf7', far='#161616', night='#0d0d0e', nightink='#efede8'),
    'dark': dict(paper='#17181b', ink='#dedad2', tone='#030304', soft='#9b988f',
                 box='#1f2024', rain='#e8e4dc', far='#56544f', night='#0b0b0c', nightink='#efede8'),
}

USED = defaultdict(set)
_measure_cache = {}


def measure_font(fam):
    path = FONT_DIR / FONTS[fam][0]
    if path not in _measure_cache:
        _measure_cache[path] = TTFont(path, lazy=True)
    return _measure_cache[path]


def measure(s, fam, size, ls=0.0):
    f = measure_font(fam)
    cmap, hmtx, upm = f.getBestCmap(), f['hmtx'], f['head'].unitsPerEm
    w = 0
    for ch in s:
        g = cmap.get(ord(ch))
        w += hmtx[g][0] if g else upm
    return w / upm * size + ls * size * len(s)


def f(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')


class Svg:
    def __init__(self, name, w, h, theme, title, desc):
        self.name, self.w, self.h = name, w, h
        self.c = THEMES[theme]
        self.title, self.desc = title, desc
        self.defs, self.body, self.css = [], [], []
        self.fams = set()
        self.n = 0
        self.patterns = {}

    def uid(self, p):
        self.n += 1
        return f'{p}{self.n}'

    def add(self, s):
        self.body.append(s)

    # ---- primitives -------------------------------------------------------
    def text(self, x, y, s, fam, size, fill, anchor='start', ls=0.0, extra=''):
        USED[fam].update(s)
        self.fams.add(fam)
        a = '' if anchor == 'start' else f' text-anchor="{anchor}"'
        l = f' letter-spacing="{f(ls * size)}"' if ls else ''
        return (f'<text x="{f(x)}" y="{f(y)}" font-family="{fam}" font-size="{f(size)}"'
                f' fill="{fill}"{a}{l}{extra}>{escape(s)}</text>')

    def clip(self, x, y, w, h):
        i = self.uid('c')
        self.defs.append(f'<clipPath id="{i}"><rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}"/></clipPath>')
        return i

    def dots(self, r, color=None, step=5.0):
        color = color or self.c['tone']
        key = ('d', round(r, 2), color, step)
        if key not in self.patterns:
            i = self.uid('d')
            self.defs.append(
                f'<pattern id="{i}" width="{f(step)}" height="{f(step)}" patternUnits="userSpaceOnUse"'
                f' patternTransform="rotate(45)"><circle cx="{f(step / 2)}" cy="{f(step / 2)}" r="{f(r)}" fill="{color}"/></pattern>')
            self.patterns[key] = i
        return f'url(#{self.patterns[key]})'

    def hatch(self, color=None, gap=4.0, width=0.9, angle=45):
        color = color or self.c['ink']
        key = ('h', color, gap, width, angle)
        if key not in self.patterns:
            i = self.uid('h')
            self.defs.append(
                f'<pattern id="{i}" width="{f(gap)}" height="{f(gap)}" patternUnits="userSpaceOnUse"'
                f' patternTransform="rotate({angle})"><line x1="0" y1="0" x2="0" y2="{f(gap)}" stroke="{color}" stroke-width="{f(width)}"/></pattern>')
            self.patterns[key] = i
        return f'url(#{self.patterns[key]})'

    def tone_gradient(self, x, y, w, h, r0, r1, steps=18, color=None):
        """Screentone that grows from r0 (top) to r1 (bottom), drawn as aligned bands."""
        out = []
        bh = h / steps
        for k in range(steps):
            t = (k + 0.5) / steps
            r = r0 + (r1 - r0) * t
            if r < 0.18:
                continue
            out.append(f'<rect x="{f(x)}" y="{f(y + k * bh)}" width="{f(w)}" height="{f(bh + 0.6)}" fill="{self.dots(r, color)}"/>')
        return ''.join(out)

    def rain(self, x, y, w, h, color, density, rng, angle=14, width=1.0, opacity=1.0,
             lmin=14, lmax=46, speed=320, clip=None):
        """Falling rain over the box (x, y, w, h). Seamless: one tile drawn twice."""
        cx, cy = x + w / 2, y + h / 2
        d = math.hypot(w, h) + 40
        lines = []
        for _ in range(int(density * d * d / 10000)):
            lx = rng.uniform(-d / 2, d / 2)
            ly = rng.uniform(-d / 2, d / 2)
            ln = rng.uniform(lmin, lmax)
            for off in (0, -d):
                lines.append(f'M{f(lx)} {f(ly + off)}v{f(ln)}')
        anim = self.uid('fall')
        dur = d / speed
        self.css.append(f'@keyframes {anim}{{from{{transform:translateY(0)}}to{{transform:translateY({f(d)}px)}}}}'
                        f'.{anim}{{animation:{anim} {f(dur)}s linear infinite}}')
        cl = f' clip-path="url(#{clip})"' if clip else ''
        return (f'<g{cl} opacity="{f(opacity)}"><g transform="translate({f(cx)} {f(cy)}) rotate({f(angle)})">'
                f'<g class="{anim}"><path d="{"".join(lines)}" stroke="{color}" stroke-width="{f(width)}"'
                f' stroke-linecap="round" fill="none"/></g></g></g>')

    def panel(self, x, y, w, h, width=3.0, color=None):
        return (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="none"'
                f' stroke="{color or self.c["ink"]}" stroke-width="{f(width)}"/>')

    # ---- output -----------------------------------------------------------
    def render(self, font_css):
        css = ''.join(font_css[fam] for fam in sorted(self.fams))
        css += 'text{font-kerning:normal;font-variant-numeric:lining-nums}' + ''.join(self.css)
        css += '@media (prefers-reduced-motion:reduce){*{animation:none!important}}'
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}"'
                f' viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t d">'
                f'<title id="t">{escape(self.title)}</title><desc id="d">{escape(self.desc)}</desc>'
                f'<style>{css}</style><defs>{"".join(self.defs)}</defs>'
                f'<g stroke-linejoin="round">{"".join(self.body)}</g></svg>\n')


# ===========================================================================
# Title page: name and position on the left, a small rainy window on the right
# ===========================================================================

def window_panel(s, x, y, w, h, rng, rain=4.0):
    """A quiet manga still: a window in the rain, books and a cup on the sill."""
    c = s.c
    cl = s.clip(x, y, w, h)
    g = [f'<g clip-path="url(#{cl})">',
         f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{c["paper"]}"/>',
         f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{s.dots(0.55)}"/>']
    m = 0.1 * w
    ox, oy, ow = x + m, y + 0.11 * h, w - 2 * m
    oh = h * 0.56
    sky = s.clip(ox, oy, ow, oh)
    g.append(f'<rect x="{f(ox)}" y="{f(oy)}" width="{f(ow)}" height="{f(oh)}" fill="{c["paper"]}"/>')
    g.append(s.tone_gradient(ox, oy, ow, oh, 1.7, 0.2, 18))

    bx, base = ox - 4, oy + oh
    blds = []
    while bx < ox + ow:
        bw = rng.uniform(18, 46)
        bh = rng.uniform(oh * 0.14, oh * 0.4)
        blds.append(f'<rect x="{f(bx)}" y="{f(base - bh)}" width="{f(bw + 1)}" height="{f(bh)}" fill="{s.dots(1.45, c["far"])}"/>')
        for _ in range(rng.randint(0, 2)):
            wx = bx + rng.uniform(4, max(5, bw - 8))
            wy = base - bh + rng.uniform(6, max(8, bh - 10))
            blds.append(f'<rect x="{f(wx)}" y="{f(wy)}" width="3.2" height="4" fill="{c["rain"]}"/>')
        bx += bw + rng.uniform(-2, 5)
    g.append(f'<g clip-path="url(#{sky})">{"".join(blds)}')
    px, ptop = ox + ow * 0.8, oy + oh * 0.3
    g.append(f'<path d="M{f(px)} {f(base)}V{f(ptop)}M{f(px - 13)} {f(ptop + 10)}h26" stroke="{c["far"]}" stroke-width="2.4" fill="none"/>'
             f'<path d="M{f(ox - 10)} {f(ptop + 4)}Q{f((ox + px) / 2)} {f(ptop + 44)} {f(px - 13)} {f(ptop + 10)}'
             f'M{f(px + 13)} {f(ptop + 10)}Q{f(px + 40)} {f(ptop + 26)} {f(ox + ow + 10)} {f(ptop + 22)}"'
             f' stroke="{c["far"]}" stroke-width="1" fill="none"/>')
    g.append(s.rain(ox, oy, ow, oh, c['rain'], rain, rng, width=1.05, opacity=0.9, speed=240, lmin=10, lmax=30))
    g.append(s.rain(ox, oy, ow, oh, c['tone'], rain / 2, rng, width=0.6, opacity=0.4, speed=280, lmin=10, lmax=30))
    g.append('</g>')
    for _ in range(int(ow * oh / 2600)):
        dx, dy = rng.uniform(ox + 8, ox + ow - 8), rng.uniform(oy + 8, oy + oh - 8)
        r = rng.uniform(1.2, 2.8)
        if rng.random() < 0.35:
            tl = rng.uniform(10, 30)
            g.append(f'<path d="M{f(dx)} {f(dy)}q1.5 {f(-tl / 2)} -1 {f(-tl)}" stroke="{c["box"]}"'
                     f' stroke-width="{f(r * 0.7)}" fill="none" opacity=".7" stroke-linecap="round"/>')
        g.append(f'<circle cx="{f(dx)}" cy="{f(dy)}" r="{f(r)}" fill="{c["box"]}" stroke="{c["ink"]}" stroke-width=".7"/>'
                 f'<path d="M{f(dx - r * 0.7)} {f(dy + r * 0.2)}a{f(r * 0.75)} {f(r * 0.75)} 0 0 0 {f(r * 1.4)} 0"'
                 f' stroke="{c["ink"]}" stroke-width="{f(max(0.7, r * 0.45))}" fill="none"/>')

    t = 10
    g.append(f'<path fill-rule="evenodd" fill="{c["paper"]}" stroke="{c["ink"]}" stroke-width="2"'
             f' d="M{f(ox - t)} {f(oy - t)}h{f(ow + 2 * t)}v{f(oh + 2 * t)}h{f(-ow - 2 * t)}Z'
             f'M{f(ox)} {f(oy)}v{f(oh)}h{f(ow)}v{f(-oh)}Z"/>')
    g.append(f'<path d="M{f(ox - t)} {f(oy - t)}l{f(t)} {f(t)}M{f(ox + ow + t)} {f(oy - t)}l{f(-t)} {f(t)}" stroke="{c["ink"]}" stroke-width=".9"/>')
    mx, hy = ox + ow / 2, oy + oh * 0.4
    g.append(f'<rect x="{f(mx - 4)}" y="{f(oy)}" width="8" height="{f(oh)}" fill="{c["paper"]}" stroke="{c["ink"]}" stroke-width="1.4"/>'
             f'<rect x="{f(ox)}" y="{f(hy - 4)}" width="{f(ow)}" height="8" fill="{c["paper"]}" stroke="{c["ink"]}" stroke-width="1.4"/>'
             f'<rect x="{f(mx + 4)}" y="{f(oy)}" width="2.5" height="{f(oh)}" fill="{s.dots(1)}"/>')
    sy = oy + oh + t
    g.append(f'<path d="M{f(ox - 22)} {f(sy + 12)}h{f(ow + 44)}l-11 14H{f(ox - 11)}Z" fill="{s.hatch(gap=3)}"/>'
             f'<rect x="{f(ox - 22)}" y="{f(sy)}" width="{f(ow + 44)}" height="12" fill="{c["paper"]}" stroke="{c["ink"]}" stroke-width="2"/>')
    bkx = ox + ow * 0.1
    g.append(f'<rect x="{f(bkx)}" y="{f(sy - 11)}" width="78" height="11" fill="{c["paper"]}" stroke="{c["ink"]}" stroke-width="1.6"/>'
             f'<rect x="{f(bkx + 3)}" y="{f(sy - 11)}" width="5" height="11" fill="{c["ink"]}"/>'
             f'<rect x="{f(bkx + 7)}" y="{f(sy - 20)}" width="64" height="9" fill="{s.dots(1.2)}" stroke="{c["ink"]}" stroke-width="1.6"/>'
             f'<path d="M{f(bkx + 12)} {f(sy - 4)}h62M{f(bkx + 12)} {f(sy - 7)}h62" stroke="{c["ink"]}" stroke-width=".55"/>'
             f'<path d="M{f(bkx + 14)} {f(sy - 22)}l48 -6l2.4 2.2l-48 6Z" fill="{c["paper"]}" stroke="{c["ink"]}" stroke-width="1.1"/>')
    cx = ox + ow * 0.74
    g.append(f'<path d="M{f(cx - 14)} {f(sy - 32)}V{f(sy - 5)}q0 5 5 5h18q5 0 5 -5V{f(sy - 32)}" fill="{c["paper"]}" stroke="{c["ink"]}" stroke-width="1.8"/>'
             f'<path d="M{f(cx + 5)} {f(sy - 30)}V{f(sy - 5)}q0 3 -3 4h8q4 0 4 -5V{f(sy - 30)}Z" fill="{s.dots(1.1)}"/>'
             f'<path d="M{f(cx + 14)} {f(sy - 26)}c11 0 11 15 0 15" fill="none" stroke="{c["ink"]}" stroke-width="2"/>'
             f'<ellipse cx="{f(cx)}" cy="{f(sy - 32)}" rx="14" ry="3.6" fill="{c["paper"]}" stroke="{c["ink"]}" stroke-width="1.6"/>'
             f'<ellipse cx="{f(cx)}" cy="{f(sy - 31.6)}" rx="11" ry="2" fill="{c["ink"]}"/>')
    steam = s.uid('steam')
    s.css.append(f'@keyframes {steam}{{0%{{opacity:0;transform:translateY(5px)}}35%{{opacity:.5}}100%{{opacity:0;transform:translateY(-10px)}}}}'
                 f'.{steam}{{animation:{steam} 5s ease-in-out infinite;opacity:0}}')
    for sx, dl in ((-4, 0), (5, 2.2)):
        g.append(f'<path class="{steam}" style="animation-delay:{dl}s" d="M{f(cx + sx)} {f(sy - 40)}c-5 -6 5 -9 0 -15s5 -9 0 -14"'
                 f' fill="none" stroke="{c["ink"]}" stroke-width="1.1" stroke-linecap="round"/>')
    g.append('</g>')
    g.append(s.panel(x, y, w, h, 2.6))
    s.add(''.join(g))


def mixed(s, x, y, parts):
    """One baseline, several fonts: parts = [(text, family, size, fill), ...]."""
    out = []
    for txt, fam, size, fill in parts:
        lead = txt[:len(txt) - len(txt.lstrip())]
        if txt.strip():
            out.append(s.text(x + measure(lead, fam, size), y, txt.strip(), fam, size, fill))
        x += measure(txt, fam, size)
    return ''.join(out)


def title_block(s, x, y, width, mobile):
    c = s.c
    name = 52 if mobile else 60
    out = [s.text(x, y, 'RESEARCH PROFILE', 'garamond-b', 12.5, c['soft'], ls=0.32),
           s.text(x - 2, y + name + 14, 'Boyong Tang', 'garamond-b', name, c['ink']),
           mixed(s, x + 1, y + name + 46, [('Kelvin', 'garamond-i', 20, c['soft']),
                                           ('  ·  ', 'garamond', 20, c['soft']),
                                           ('けるゔぃん・とう', 'mincho', 16.5, c['soft'])])]
    ry = y + name + 70
    out.append(f'<path d="M{f(x)} {f(ry)}H{f(x + width)}" stroke="{c["ink"]}" stroke-width="1.2"/>'
               f'<path d="M{f(x)} {f(ry + 4)}H{f(x + width)}" stroke="{c["ink"]}" stroke-width=".5"/>')
    role = (['Undergraduate · Applied Mathematics', '& Artificial Intelligence'] if mobile
            else ['Undergraduate · Applied Mathematics & Artificial Intelligence'])
    ty = ry + 34
    for ln in role:
        out.append(s.text(x, ty, ln, 'garamond', 19.5, c['ink']))
        ty += 25
    out.append(mixed(s, x, ty, [('Sichuan University, Chengdu', 'garamond-i', 18.5, c['soft']),
                                ('   ', 'garamond', 18.5, c['soft']),
                                ('四川大学', 'song', 14.5, c['soft'])]))
    by = ty + 30
    l1, l2 = 'Observe the unanswered.', 'Mapping questions, methods, and the evidence between them.'
    if mobile:
        l2lines = ['Mapping questions, methods,', 'and the evidence between them.']
    else:
        l2lines = [l2]
    bw = max([measure(l1, 'garamond-i', 25)] + [measure(t, 'garamond', 15.5) for t in l2lines]) + 36
    bh = 50 + 21 * len(l2lines)
    out.append(f'<rect x="{f(x + 5)}" y="{f(by + 5)}" width="{f(bw)}" height="{f(bh)}" fill="{s.hatch(gap=3)}"/>'
               f'<rect x="{f(x)}" y="{f(by)}" width="{f(bw)}" height="{f(bh)}" fill="{c["box"]}" stroke="{c["ink"]}" stroke-width="1.6"/>')
    out.append(s.text(x + 18, by + 34, l1, 'garamond-i', 25, c['ink']))
    for k, ln in enumerate(l2lines):
        out.append(s.text(x + 18, by + 58 + 21 * k, ln, 'garamond', 15.5, c['soft']))
    return ''.join(out), by + bh


def hero(theme, mobile):
    rng = random.Random(7)
    desc = ('Boyong Tang (Kelvin, けるゔぃん・とう). Undergraduate, Applied Mathematics & Artificial Intelligence, '
            'Sichuan University, Chengdu. “Observe the unanswered.” Beside the title, a small black-and-white '
            'manga panel: rain on a window, books and a cup on the sill.')
    if mobile:
        W = 520
        s = Svg('hero', W, 10, theme, 'Boyong Tang — research profile', desc)
        P = (16, 16, 488, 300)
        cap_y = P[1] + P[3] + 26
        tb, end = title_block(s, 28, cap_y + 56, 464, True)
        H = int(end + 28)
    else:
        W, H = 960, 430
        s = Svg('hero', W, H, theme, 'Boyong Tang — research profile', desc)
        P = (616, 30, 324, 330)
        cap_y = P[1] + P[3] + 26
        tb, _ = title_block(s, 30, 58, 540, False)
    s.h = H
    c = s.c
    s.add(f'<rect width="{W}" height="{H}" fill="{c["paper"]}"/>')
    window_panel(s, *P, rng, rain=3.2)
    s.add(mixed(s, P[0] + 2, cap_y, [('Fig. 0', 'garamond-b', 14, c['ink']),
                                      ('   rain on the window; the question stays open.', 'garamond-i', 14.5, c['soft'])]))
    s.add(tb)
    return s


# ===========================================================================
# Colophon: a thin strip of rain, one quiet line
# ===========================================================================

def footer(theme, mobile):
    rng = random.Random(31)
    W, H = (520, 128) if mobile else (960, 112)
    s = Svg('footer', W, H, theme, '今日も、雨。',
            'A thin strip of light rain with one line: 今日も、雨。 — the questions remain open.')
    c = s.c
    x, y, w, h = 20, 18, W - 40, H - 36
    cl = s.clip(x, y, w, h)
    g = [f'<rect width="{W}" height="{H}" fill="{c["paper"]}"/>',
         f'<path d="M{x} {y}H{x + w}" stroke="{c["ink"]}" stroke-width="1.2"/><path d="M{x} {y + 4}H{x + w}" stroke="{c["ink"]}" stroke-width=".5"/>',
         f'<g clip-path="url(#{cl})">',
         s.rain(x, y, w, h, c['ink'], 3.2, rng, width=0.6, opacity=0.3, speed=200, lmin=10, lmax=26),
         '</g>']
    if mobile:
        g.append(s.text(W / 2, y + 44, '今日も、雨。', 'mincho', 19, c['ink'], 'middle', ls=0.14))
        g.append(s.text(W / 2, y + 72, 'the questions remain open.', 'garamond-i', 17, c['soft'], 'middle'))
    else:
        g.append(mixed(s, W / 2 - (measure('今日も、雨。', 'mincho', 19, 0.14) + measure('   —   the questions remain open.', 'garamond-i', 17)) / 2, y + 50,
                       [('今日も、雨。', 'mincho', 19, c['ink']), ('   —   the questions remain open.', 'garamond-i', 17, c['soft'])]))
    s.add(''.join(g))
    return s


# ===========================================================================

def build_fonts():
    css = {}
    for fam, (file, wght) in FONTS.items():
        chars = USED.get(fam)
        if not chars:
            continue
        font = TTFont(FONT_DIR / file)
        cmap = font.getBestCmap()
        missing = [ch for ch in chars if ord(ch) not in cmap and not ch.isspace()]
        if missing:
            raise SystemExit(f'{fam} is missing glyphs: {"".join(sorted(missing))}')
        opts = subset.Options()
        opts.hinting = False
        opts.layout_features = ['kern', 'liga', 'palt', 'lnum']
        opts.name_IDs = [0, 1, 2, 3, 4, 5, 6]
        opts.notdef_outline = True
        sub = subset.Subsetter(opts)
        sub.populate(text=''.join(chars) + ' ')
        sub.subset(font)
        if wght is not None and 'fvar' in font:
            font = instancer.instantiateVariableFont(font, {'wght': wght})
        font.flavor = 'woff2'
        buf = io.BytesIO()
        font.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        css[fam] = f'@font-face{{font-family:"{fam}";src:url(data:font/woff2;base64,{b64}) format("woff2")}}'
    return css


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    svgs = []
    for theme in THEMES:
        for mobile in (False, True):
            for make in (hero, footer):
                svg = make(theme, mobile)
                svgs.append((f'{svg.name}-{theme}{"-mobile" if mobile else ""}.svg', svg))
    css = build_fonts()
    for name, svg in svgs:
        data = svg.render(css)
        (OUT / name).write_text(data, encoding='utf-8')
        print(f'{name:32s} {len(data) / 1024:7.1f} KB')


if __name__ == '__main__':
    main()
