#!/usr/bin/env python3
"""Draw the BoyongTang profile images: a typeset title page and a closing rule.

Every image is plain SVG with a transparent background. The few glyphs each image
uses are cut out of OFL fonts (Noto Serif JP / SC, Cormorant Garamond) and embedded,
so GitHub shows the same lettering on every device.

    FONT_DIR=/path/to/fonts python3 scripts/build.py

FONT_DIR must hold NotoSerifJP[wght].ttf, NotoSerifSC[wght].ttf,
CormorantGaramond-Medium.ttf, CormorantGaramond-MediumItalic.ttf
and CormorantGaramond-SemiBold.ttf (all from github.com/google/fonts, ofl/).
"""
import base64
import io
import os
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

# Matched to GitHub's own light and dark text colours.
THEMES = {
    'light': dict(ink='#1f2328', soft='#59636e', rule='#1f2328'),
    'dark': dict(ink='#e6edf3', soft='#9198a1', rule='#e6edf3'),
}

USED = defaultdict(set)
_measure_cache = {}


def measure_font(fam):
    path = FONT_DIR / FONTS[fam][0]
    if path not in _measure_cache:
        _measure_cache[path] = TTFont(path, lazy=True)
    return _measure_cache[path]


def measure(s, fam, size, ls=0.0):
    font = measure_font(fam)
    cmap, hmtx, upm = font.getBestCmap(), font['hmtx'], font['head'].unitsPerEm
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
        self.body = []
        self.fams = set()

    def add(self, s):
        self.body.append(s)

    def text(self, x, y, s, fam, size, fill, anchor='start', ls=0.0):
        USED[fam].update(s)
        self.fams.add(fam)
        a = '' if anchor == 'start' else f' text-anchor="{anchor}"'
        l = f' letter-spacing="{f(ls * size)}"' if ls else ''
        return (f'<text x="{f(x)}" y="{f(y)}" font-family="{fam}" font-size="{f(size)}"'
                f' fill="{fill}"{a}{l}>{escape(s)}</text>')

    def centred(self, cx, y, parts):
        """One centred baseline in several fonts: parts = [(text, family, size, fill, ls), ...]."""
        total = sum(measure(t, fam, size, ls) for t, fam, size, _, ls in parts)
        x = cx - total / 2
        out = []
        for txt, fam, size, fill, ls in parts:
            lead = txt[:len(txt) - len(txt.lstrip())]
            if txt.strip():
                out.append(self.text(x + measure(lead, fam, size, ls), y, txt.strip(), fam, size, fill, ls=ls))
            x += measure(txt, fam, size, ls)
        return ''.join(out)

    def double_rule(self, cx, y, half):
        c = self.c
        return (f'<path d="M{f(cx - half)} {f(y)}H{f(cx + half)}" stroke="{c["rule"]}" stroke-width="1.1"/>'
                f'<path d="M{f(cx - half)} {f(y + 3.5)}H{f(cx + half)}" stroke="{c["rule"]}" stroke-width=".5"/>')

    def render(self, font_css):
        css = ''.join(font_css[fam] for fam in sorted(self.fams))
        css += 'text{font-kerning:normal;font-variant-numeric:lining-nums}'
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}"'
                f' viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t d">'
                f'<title id="t">{escape(self.title)}</title><desc id="d">{escape(self.desc)}</desc>'
                f'<style>{css}</style>{"".join(self.body)}</svg>\n')


# ===========================================================================
# Title page, set like the first page of a paper
# ===========================================================================

def hero(theme, mobile):
    W = 520 if mobile else 960
    s = Svg('hero', W, 10, theme, 'Boyong Tang — research profile',
            'Boyong Tang (Kelvin, けるゔぃん・とう). Undergraduate, Applied Mathematics & Artificial Intelligence, '
            'Sichuan University, Chengdu.')
    c = s.c
    cx = W / 2
    name = 52 if mobile else 66
    y = 40
    s.add(s.text(cx, y, 'RESEARCH PROFILE', 'garamond-b', 12.5, c['soft'], 'middle', ls=0.34))
    y += name + 20
    s.add(s.text(cx, y, 'Boyong Tang', 'garamond-b', name, c['ink'], 'middle'))
    y += 42
    s.add(s.centred(cx, y, [('Kelvin', 'garamond-i', 20, c['soft'], 0),
                            ('   ·   ', 'garamond', 20, c['soft'], 0),
                            ('けるゔぃん・とう', 'mincho', 16, c['soft'], 0.04)]))
    y += 28
    s.add(s.double_rule(cx, y, 180 if mobile else 260))
    y += 40
    roles = (['Undergraduate · Applied Mathematics', '& Artificial Intelligence'] if mobile
             else ['Undergraduate · Applied Mathematics & Artificial Intelligence'])
    for ln in roles:
        s.add(s.text(cx, y, ln, 'garamond', 20.5, c['ink'], 'middle'))
        y += 26
    s.add(s.centred(cx, y, [('Sichuan University, Chengdu', 'garamond-i', 18.5, c['soft'], 0),
                            ('   ·   ', 'garamond', 18.5, c['soft'], 0),
                            ('四川大学', 'song', 14.5, c['soft'], 0.06)]))
    s.h = int(y + 22)
    return s


# ===========================================================================
# Closing rule
# ===========================================================================

def footer(theme, mobile):
    W = 520 if mobile else 960
    s = Svg('footer', W, 40, theme, 'End of profile', 'A thin closing rule.')
    cx, half = W / 2, (180 if mobile else 260)
    s.add(s.double_rule(cx, 16, half))
    s.add(f'<path d="M{f(cx)} {f(13)}l5 5.25l-5 5.25l-5 -5.25Z" fill="{s.c["rule"]}"/>')
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
