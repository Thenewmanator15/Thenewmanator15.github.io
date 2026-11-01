"""Mathew's writing rules, checked on every piece of site copy.

Usage: python tools/check_copy.py content data templates static/js
Exits 0 when clean, 1 with one line per problem. Missing folders are skipped.

Rules: no sentence with two "and"s (names excepted), no comma before "and", no em dashes,
straight quotes only, no banned words, and nothing that claims the PhD is awarded.
"""
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ALLOWED_NAMES = ["High-Speed and Mixed-Signal Design", "Howard Johnson and Eric Bogatin"]

BANNED = ["delve", "robust", "seamless", "leverage", "pivotal", "showcase", "meticulous", "additionally",
          "crucial", "enhance", "foster", "garner", "landscape", "tapestry", "testament", "underscore",
          "vibrant"]
BANNED_RE = re.compile(r"\b(" + "|".join(BANNED) + r")(s|d|es|ed|ing|ly)?\b", re.I)
HIGHLIGHT_RE = re.compile(r"\b(?<!code )(?<!syntax )highlight(s|ed|ing)?\b", re.I)
PHD_RE = re.compile(r"\bDr\.? [A-Z][a-z]|\b(hold|holds|have|has|earned|completed|awarded)( a| my)? PhD\b", re.I)
CODE_RE = re.compile(r"`[^`]*`")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
FRONT_KEYS = ("title", "description", "my_part", "result", "hero_alt", "still_to_come_note")


def problems(text: str, allowed: list[str] | None = None) -> list[str]:
    names = ALLOWED_NAMES + (allowed or [])
    t = URL_RE.sub(" ", CODE_RE.sub(" ", text))
    out = []
    if "—" in t:
        out.append("em dash")
    if re.search("[‘’“”]", t):
        out.append("curly quote")
    for m in BANNED_RE.finditer(t):
        out.append(f"banned word: {m.group(0)}")
    for m in HIGHLIGHT_RE.finditer(t):
        out.append(f"banned word: {m.group(0)}")
    if PHD_RE.search(t):
        out.append("implies the PhD is awarded")
    for sentence in SENTENCE_SPLIT.split(t):
        s = sentence
        for n in names:
            s = s.replace(n, "NAME")
        if len(re.findall(r"\band\b", s, re.I)) >= 2:
            out.append(f"two 'and's in: {sentence.strip()[:80]}")
        if re.search(r",\s+and\b", s, re.I):
            out.append(f"comma before 'and' in: {sentence.strip()[:80]}")
    return out


def _channel_names(roots: list[Path]) -> list[str]:
    for r in roots:
        f = r / "channels.toml" if r.name == "data" else r.parent / "data" / "channels.toml"
        if f.is_file():
            data = tomllib.loads(f.read_text(encoding="utf-8"))
            return [c.get("name", "") for c in data.get("channels", []) if c.get("name")]
    return []


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def _is_prose(s: str) -> bool:
    return " " in s.strip() and bool(re.search(r"[A-Za-z]{2}", s)) and not URL_RE.fullmatch(s.strip())


def _markdown(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    pieces = []
    m = re.match(r"\+\+\+\n(.*?)\n\+\+\+\n?(.*)", text, re.S)
    body = text
    if m:
        fm, body = tomllib.loads(m.group(1)), m.group(2)
        extra = fm.get("extra", {})
        for k in FRONT_KEYS:
            for src in (fm, extra):
                if isinstance(src.get(k), str):
                    pieces.append(src[k])
        for r in extra.get("readouts", []):
            pieces += [str(r.get("label", "")), str(r.get("value", ""))]
        for p in extra.get("proof", []):
            pieces.append(str(p.get("label", "")))
    body = re.sub(r"```.*?```", " ", body, flags=re.S)
    for sc in re.finditer(r"\{\{\s*<figure\b(.*?)/>\s*\}\}", body, re.S):  # the Tera 2 figure component
        pieces += re.findall(r'(?:alt|caption)\s*=\s*"([^"]*)"', sc.group(1))
    body = re.sub(r"\{\{.*?\}\}|\{%.*?%\}", " ", body, flags=re.S)
    pieces.append(body)
    return [p for p in pieces if p]


def _template(path: Path) -> list[str]:
    html = path.read_text(encoding="utf-8")
    html = re.sub(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", " ", html, flags=re.S)
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    pieces = re.findall(r'\b(?:aria-label|title|alt)\s*=\s*"([^"]*)"', html)
    pieces += [t for t in re.split(r"<[^>]+>", html) if t.strip()]
    return pieces


def _js(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    lits = re.findall(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`([^`]*)`', src)
    return [s for tup in lits for s in tup if s and _is_prose(s)]


def check_paths(paths: list[Path]) -> list[str]:
    names = _channel_names(paths)
    out = []
    for root in paths:
        if not root.exists():
            continue
        files = [root] if root.is_file() else sorted(root.rglob("*"))
        for f in files:
            if f.suffix == ".md":
                pieces = _markdown(f)
            elif f.suffix == ".toml":
                pieces = [s for s in _strings(tomllib.loads(f.read_text(encoding="utf-8"))) if _is_prose(s)]
            elif f.suffix == ".html":
                pieces = _template(f)
            elif f.suffix in (".mjs", ".js"):
                pieces = _js(f)
            else:
                continue
            for piece in pieces:
                for p in problems(piece, names):
                    out.append(f"{f.as_posix()}: {p}")
    return out


def main(argv: list[str]) -> int:
    out = check_paths([Path(a) for a in argv])
    for line in out:
        print(line)
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
