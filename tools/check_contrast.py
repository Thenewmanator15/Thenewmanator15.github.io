"""WCAG contrast check of the theme tokens in static/css/tokens.css.

Usage: python tools/check_contrast.py static/css/tokens.css
Exits 0 when every text and trace colour reaches 4.5:1 on its background in all three themes
(scope, paper, hc), and the no-JavaScript media-query copies match their themes.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

THEMES = ("scope", "paper", "hc")
REQUIRED = ["page", "pagetext", "bezel", "panel", "paneldim", "screen", "grid", "trace", "text", "dim",
            "accent", "onaccent", "btn", "btntext", "btnedge", "chtext", "zbg", "ztext", "zdim", "tagbg",
            "dig", "cm"]
# Copies used when the visitor has not picked a theme: which media query maps to which theme.
FALLBACKS = {"prefers-color-scheme: light": "paper", "prefers-contrast: more": "hc"}
MIN_RATIO = 4.5
HEX = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})")


def _rgb(colour: str) -> tuple[float, float, float]:
    m = HEX.fullmatch(colour.strip())
    if not m:
        raise ValueError(colour)
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _luminance(colour: str) -> float:
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in _rgb(colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    a, b = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _blocks(css: str) -> list[tuple[str | None, str, dict[str, str]]]:
    """Every rule as (enclosing @media prelude or None, selector, custom properties)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, stack, buf = [], [], ""
    for ch in css:
        if ch == "{":
            stack.append(buf.strip())
            buf = ""
        elif ch == "}":
            if stack:
                prelude = stack.pop()
                if not prelude.startswith("@"):
                    media = next((p for p in reversed(stack) if p.startswith("@media")), None)
                    decls = {}
                    for d in buf.split(";"):
                        k, sep, v = d.partition(":")
                        if sep and k.strip().startswith("--"):
                            decls[k.strip()[2:]] = v.strip()
                    out.append((media, prelude, decls))
            buf = ""
        else:
            buf += ch
    return out


def _channels(tokens: dict[str, str]) -> set[str]:
    return {k for k in tokens if re.fullmatch(r"c\d+", k)}


def _pairs(t: dict[str, str]) -> list[tuple[str, str]]:
    chans = sorted(_channels(t), key=lambda k: int(k[1:]))
    pairs = [("text", "screen"), ("dim", "screen"), ("dig", "screen"), ("accent", "screen"), ("cm", "screen"),
             ("pagetext", "page"), ("paneldim", "panel"), ("btntext", "panel"), ("cm", "panel"),
             ("btntext", "btn"), ("ztext", "zbg"), ("zdim", "zbg"), ("accent", "zbg"),
             ("onaccent", "accent"), ("zdim", "tagbg"), ("chtext", "cm"),
             # found in the final review: key-figure labels sit on --grid; page text uses --paneldim;
             # pressed digital buttons; project cards inside the zoom pane use the screen's text colours
             ("dim", "grid"), ("paneldim", "page"), ("chtext", "dig"), ("text", "zbg"), ("dim", "zbg"),
             # the "in progress" and "work in progress" labels: accent text on the page
             ("accent", "page")]
    for c in chans:
        pairs += [(c, "screen"), (c, "panel"), ("chtext", c)]
    return pairs


def _theme_problems(name: str, t: dict[str, str]) -> list[str]:
    out = [f"{name}: --{k} is missing" for k in REQUIRED if k not in t]
    for fg, bg in _pairs(t):
        if fg not in t or bg not in t:
            continue
        try:
            ratio = contrast(t[fg], t[bg])
        except ValueError:
            bad = fg if not HEX.fullmatch(t[fg]) else bg
            out.append(f"{name}: --{bad} is {t[bad]!r}, not a hex colour, so --{fg} on --{bg} can't be checked")
            continue
        if ratio < MIN_RATIO:
            out.append(f"{name}: --{fg} {t[fg]} on --{bg} {t[bg]} is {ratio:.2f}:1 (needs {MIN_RATIO}:1)")
    return out


def check(css_text: str) -> list[str]:
    blocks = _blocks(css_text)
    themes: dict[str, dict[str, str]] = {}
    for name in THEMES:
        sel = f"[data-style={name}]"
        merged: dict[str, str] = {}
        for media, selector, decls in blocks:
            if media is None and sel in selector.replace('"', "").replace("'", ""):
                merged |= decls
        themes[name] = merged
    out = []
    for name in THEMES:
        if not themes[name]:
            out.append(f"{name}: no html[data-style={name}] block")
            continue
        out += _theme_problems(name, themes[name])
    all_channels = set().union(*(_channels(t) for t in themes.values()))
    for name, t in themes.items():
        out += [f"{name}: --{c} is missing (every theme needs every channel)"
                for c in sorted(all_channels - _channels(t), key=lambda k: int(k[1:]))]
    for query, name in FALLBACKS.items():
        copies = [d for media, sel, d in blocks if media and query in media and ":not([data-style])" in sel]
        if not copies:
            out.append(f"@media ({query}): no html:not([data-style]) block for {name}")
            continue
        copy = {k: v for d in copies for k, v in d.items()}
        for k in sorted(set(themes[name]) | set(copy)):
            if themes[name].get(k) != copy.get(k):
                out.append(f"@media ({query}): --{k} is {copy.get(k)!r} but {name} has {themes[name].get(k)!r}")
    if not any(media and "forced-colors: active" in media for media, _, _ in blocks):
        out.append("no @media (forced-colors: active) block")
    return out


# Opacity below 1 fades text below the contrast these checks measure, so only these may use it:
# dimmed overlay traces (graphics, not text) and the toast fading in and out.
OPACITY_ALLOWED = {".ov.dim", "#toast"}


def opacity_problems(css_text: str) -> list[str]:
    css = re.sub(r"/\*.*?\*/", "", css_text, flags=re.S)
    out = []
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        for v in re.findall(r"(?<![-\w])opacity\s*:\s*([0-9.]+)", body):
            selectors = [s.strip() for s in sel.split(",")]
            if float(v) < 1 and not all(s in OPACITY_ALLOWED for s in selectors):
                out.append(sel.strip())
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: check_contrast.py TOKENS_CSS", file=sys.stderr)
        return 2
    out = check(Path(argv[0]).read_text(encoding="utf-8"))
    for line in out:
        print(line)
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
