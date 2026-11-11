"""Checks on the built site (public/) and the content folder, run before every publish.

Usage: python tools/check_site.py public/ content/
Exits 0 when clean, 1 with one line per problem. Calibration warnings are printed but never fail
the run. Standard library only.
"""
from __future__ import annotations

import datetime
import fnmatch
import re
import subprocess
import sys
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

# The one policy every page must carry (the build plan's Global Constraints).
EXPECTED_CSP = (
    "default-src 'self'; img-src 'self' data: https://www.phovir.com; style-src 'self'; script-src 'self'; "
    "font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'"
)

# Paths already used by other project sites under thenewmanator15.github.io.
RESERVED = ["pdf-themes", "LeCroyTRC.jl", "mptofsims-supplementary", "grapevine-privacy", "typst-pdf-ua2"]

TRACKERS = ["googletagmanager", "google-analytics", "gtag/js", "plausible.io", "hotjar", "segment.com",
            "clarity.ms", "connect.facebook", "doubleclick", "matomo", "umami", "cloudflareinsights"]

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".svg", ".heic"}
FONT_EXT = {".woff", ".woff2", ".ttf", ".otf"}

STRAY_PATTERNS = ["*.pem", "*.key", "*.p12", ".env*", "id_*", "*.heic", "*.psd", "*originals*",
                  "Portfolio *.md"]  # the private design and plan documents
STRAY_MAX_BYTES = 10 * 1024 * 1024

# The site's own address: the same origin as "self" in the policy.
SITE_HOSTS = {"thenewmanator15.github.io"}
# Other sites whose images a page may show from their own server (img-src in the policy), and nothing
# else from them. PhovIR's pictures stay on PhovIR's site: they hold the copyright (Mathew, 2 Nov 2026).
EMBED_IMAGE_HOSTS = {"www.phovir.com"}
# Script types that are data, not code: browsers never run them, so the policy doesn't apply.
DATA_SCRIPT_TYPES = {"application/json", "application/ld+json"}

EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
PHONE = re.compile(r"(?<![\w.,/])(\+?\d[\d ]{8,}\d)(?![\w.,/])")
YEAR = re.compile(r"(19|20)\d\d")


class _Tags(HTMLParser):
    """Collects every start tag with its attributes, plus inline script bodies."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.inline_scripts: list[str] = []
        self._in_script_without_src = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        self._in_script_without_src = (tag == "script" and not a.get("src")
                                       and (a.get("type") or "").lower() not in DATA_SCRIPT_TYPES)
        if self._in_script_without_src:
            self.inline_scripts.append("")

    def handle_startendtag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        if self._in_script_without_src:
            self.inline_scripts[-1] += data

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script_without_src = False


def _parse(html: str) -> _Tags:
    p = _Tags()
    p.feed(html)
    return p


def reserved_path_hits(public: Path) -> list[str]:
    return [name for name in RESERVED if (public / name).exists()]


def contact_leaks(html: str) -> list[str]:
    hits = EMAIL.findall(html)
    for m in PHONE.finditer(html):
        groups = m.group(1).replace("+", "").split()
        digits = "".join(groups)
        if len(digits) < 10:
            continue
        if all(len(g) == 4 and YEAR.fullmatch(g) for g in groups):
            continue  # a list of years, not a phone number
        hits.append(m.group(1))
    return hits


def images_missing_alt(html: str) -> list[str]:
    return [a.get("src") or "?" for tag, a in _parse(html).tags
            if tag == "img" and "alt" not in a and a.get("aria-hidden") != "true"]


def tracking_scripts(html: str) -> list[str]:
    out = []
    for tag, a in _parse(html).tags:
        src = (a.get("src") or "") if tag == "script" else ""
        if any(t in src for t in TRACKERS):
            out.append(src)
    return out


def _is_other_origin(url: str) -> bool:
    u = urlparse(url)
    if u.netloc and u.netloc.lower() in SITE_HOSTS and u.scheme in ("https", ""):
        return False
    return bool(u.scheme in ("http", "https") and u.netloc) or url.startswith("//")


def is_embedded_image(url: str) -> bool:
    """An https image on one of the other sites the policy lets pages show."""
    u = urlparse(url)
    return u.scheme == "https" and u.netloc.lower() in EMBED_IMAGE_HOSTS


def duplicate_ids(html: str) -> list[str]:
    """Element ids used more than once on a page (links and labels then point at the wrong one)."""
    counts = Counter(a.get("id") for _, a in _parse(html).tags if a.get("id"))
    return [i for i, k in counts.items() if k > 1]


def anchor_problems(html: str) -> list[str]:
    """Links to "#something" on the same page that point at no element id."""
    tags = _parse(html).tags
    ids = {a.get("id") for _, a in tags if a.get("id")}
    hrefs = [a.get("href") for tag, a in tags if tag == "a" and (a.get("href") or "").startswith("#")]
    return [h for h in dict.fromkeys(hrefs) if len(h) > 1 and h[1:] not in ids]


def csp_problems(html: str) -> list[str]:
    p = _parse(html)
    out = []
    policies = [a.get("content") for tag, a in p.tags
                if tag == "meta" and (a.get("http-equiv") or "").lower() == "content-security-policy"]
    if not policies:
        out.append("no Content-Security-Policy meta tag")
    elif policies[0] != EXPECTED_CSP:
        out.append(f"policy differs from the expected one: {policies[0]!r}")
    if any(s.strip() for s in p.inline_scripts):
        out.append("inline <script> without src")
    for tag, a in p.tags:
        if tag == "style":
            out.append("<style> element (the policy only allows style sheet files)")
        if "style" in a:
            out.append(f"<{tag} style=...> inline style attribute (blocked by the policy)")
        for k in a:
            if k.startswith("on"):
                out.append(f"<{tag} {k}=...> event handler attribute")
        for attr in ("src", "href", "srcset", "poster", "data"):
            v = a.get(attr)
            if not v:
                continue
            if tag == "a" and attr == "href":
                continue  # plain outbound links are fine
            first = v.split(",")[0].strip().split(" ")[0]
            if tag == "img" and attr in ("src", "srcset") and is_embedded_image(first):
                if a.get("referrerpolicy") != "no-referrer":
                    out.append(f"<img src={first}> from another site must send no referrer")
                continue
            if _is_other_origin(first):
                out.append(f"<{tag} {attr}={first}> loads from another origin")
    return out


def _largest_candidate(srcset: str) -> str:
    """The widest file in a srcset: what a large screen downloads."""
    best, best_w = "", -1
    for part in srcset.split(","):
        bits = part.split()
        if not bits:
            continue
        w = int(bits[1][:-1]) if len(bits) > 1 and bits[1].endswith("w") and bits[1][:-1].isdigit() else 0
        if w > best_w:
            best, best_w = bits[0], w
    return best


def oversize_pages(public: Path, budget_kb: int = 1500) -> list[str]:
    out = []
    for page in public.rglob("*.html"):
        total = page.stat().st_size
        seen: set[Path] = set()
        for tag, a in _parse(page.read_text(encoding="utf-8", errors="replace")).tags:
            src = a.get("src") if tag in ("img", "script", "source", "video") else None
            if a.get("srcset") and tag in ("img", "source"):
                src = _largest_candidate(a["srcset"])
            if not src or _is_other_origin(src):
                continue
            u = urlparse(src)
            if u.netloc:  # an absolute address on this site
                src = u.path
            path = (public / src.lstrip("/")) if src.startswith("/") else (page.parent / src)
            path = path.resolve()
            if path in seen or not path.is_file() or path.suffix.lower() in FONT_EXT:
                continue
            seen.add(path)
            total += path.stat().st_size
        if total > budget_kb * 1024:
            out.append(f"{page.relative_to(public).as_posix()}: {total / 1024:.0f} KB (limit {budget_kb} KB)")
    return out


def repo_size_problems(content: Path, max_total_mb: int = 500, max_image_mb: int = 2) -> list[str]:
    out = []
    files = [f for f in content.rglob("*") if f.is_file()]
    total = sum(f.stat().st_size for f in files)
    if total > max_total_mb * 1024 * 1024:
        out.append(f"{content.as_posix()}: {total / 1024 / 1024:.1f} MB in total (limit {max_total_mb} MB)")
    for f in sorted(files):
        size = f.stat().st_size
        if f.suffix.lower() in IMAGE_EXT and size > max_image_mb * 1024 * 1024:
            out.append(f"{f.relative_to(content).as_posix()}: {size / 1024 / 1024:.1f} MB (limit {max_image_mb} MB)")
    return out


def stray_files(repo: Path) -> list[str]:
    tracked = subprocess.run(["git", "ls-files", "--cached"], cwd=repo, capture_output=True,
                             text=True, check=True).stdout.splitlines()
    out = []
    for rel in tracked:
        name = rel.rsplit("/", 1)[-1]
        if any(fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel, pat) for pat in STRAY_PATTERNS):
            out.append(rel)
            continue
        f = repo / rel
        if f.is_file() and f.stat().st_size > STRAY_MAX_BYTES:
            out.append(rel)
    return out


# ---- The content model: front matter and data files (the build plan's contract) ----

YM = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
PROJECT_ID = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
PROOF_KINDS = ("code", "data", "document", "photos", "video", "measurements", "certificate")
BOOL_KEYS = ("featured", "milestone", "panel", "role", "study", "text_only")
TIMELINE_FIELDS = ("id", "title", "date", "summary")
WIP_PARTS = ("write-up", "dates", "photos", "proof")  # the rows of the work-in-progress sign, in order


@dataclass
class Project:
    channel: str  # the top-level folder under content/
    id: str  # the folder (or file) name; also the `f` key in shared links
    file: Path  # index.md, <id>.md, or _index.md for a big project
    big: bool = False
    parts: list[Path] = field(default_factory=list)

    @property
    def folder(self) -> Path:
        return self.file.parent


def _front(path: Path) -> tuple[dict, str | None]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\+\+\+\r?\n(.*?)\r?\n\+\+\+", text, re.S)
    if not m:
        return {}, "no +++ front matter"
    try:
        return tomllib.loads(m.group(1)), None
    except tomllib.TOMLDecodeError as e:
        return {}, f"front matter is not valid TOML ({e})"


def _projects(content: Path) -> list[Project]:
    """Every project: a page in a channel folder, or a sub-folder with _index.md (a big project).
    The pages inside a big project's folder are its parts, never projects."""
    out = []
    for ch in sorted(p for p in content.iterdir() if p.is_dir()):
        for entry in sorted(ch.iterdir()):
            if entry.is_file() and entry.suffix == ".md" and entry.name != "_index.md":
                out.append(Project(ch.name, entry.stem, entry))
            elif entry.is_dir() and (entry / "_index.md").is_file():
                parts = sorted(f for f in entry.rglob("*.md") if f != entry / "_index.md")
                out.append(Project(ch.name, entry.name, entry / "_index.md", True, parts))
            elif entry.is_dir() and (entry / "index.md").is_file():
                out.append(Project(ch.name, entry.name, entry / "index.md"))
    return out


def count_project_pages(content: Path) -> int:
    return len(_projects(content))


def text_only_pages(content: Path) -> list[str]:
    """The built path (under public/) of each text-only project."""
    return [f"{p.channel}/{p.id}" for p in _projects(content)
            if _front(p.file)[0].get("extra", {}).get("text_only") is True]


def _load(data: Path, name: str) -> tuple[dict, str | None]:
    f = data / name
    if not f.is_file():
        return {}, f"data/{name} is missing"
    try:
        return tomllib.loads(f.read_text(encoding="utf-8")), None
    except tomllib.TOMLDecodeError as e:
        return {}, f"data/{name} is not valid TOML ({e})"


def _panel_problems(where: str, ex: dict, body: str) -> list[str]:
    """[[extra.matrix]] cards and [[extra.tiles]] belong to the panel layout and are placed by the text."""
    out = []
    mats, tiles = ex.get("matrix", []), ex.get("tiles", [])
    if (mats or tiles) and ex.get("panel") is not True:
        out.append(f"{where}: matrix and tiles need panel = true")
    for m in mats:
        title, cols = m.get("title"), m.get("cols") or []
        if not title or not cols:
            out.append(f"{where}: matrix {title or '?'}: needs a title and at least one column")
            continue
        for k, row in enumerate(m.get("rows", []), 1):
            if len(row) != len(cols) + 1:
                out.append(f"{where}: matrix {title}: row {k} has {len(row)} cells, needs {len(cols) + 1}")
    if any(not t.get("value") or not t.get("label") for t in tiles):
        out.append(f"{where}: tiles need a value and a label")
    if mats and "<matrices" not in body:
        out.append(f"{where}: has a matrix but never shows it: add {{{{ <matrices /> }}}} to the text")
    if tiles and "<tiles" not in body:
        out.append(f"{where}: has tiles but never shows them: add {{{{ <tiles /> }}}} to the text")
    return out


def _wip_problems(where: str, ex: dict, text_only: bool) -> list[str]:
    """still_to_come marks an unfinished page: a list of WIP_PARTS, each once, with an optional note."""
    out = []
    items, note = ex.get("still_to_come"), ex.get("still_to_come_note")
    if items is None:
        if note is not None:
            out.append(f"{where}: still_to_come_note needs still_to_come (the parts still to come)")
        return out
    if not isinstance(items, list):
        return out + [f'{where}: still_to_come must be a list, such as ["photos"]']
    if not items:
        out.append(f"{where}: still_to_come is empty: delete the line instead")
    for x in items:
        if x not in WIP_PARTS:
            out.append(f"{where}: still_to_come lists {x!r}, which is not one of {', '.join(WIP_PARTS)}")
    for x, k in Counter(map(str, items)).items():
        if k > 1:
            out.append(f"{where}: still_to_come lists {x!r} more than once")
    if note is not None and not (isinstance(note, str) and note.strip()):
        out.append(f"{where}: still_to_come_note must be a sentence, or left out")
    if "photos" in items and text_only:
        out.append(f"{where}: a text_only page has no photos, so still_to_come can't list photos")
    return out


def _proof_problems(item: dict, folder: Path | None, static: Path | None, content: Path,
                    marked: bool | None = False) -> list[str]:
    """`marked`: whether the page has still_to_come; None for timeline entries, which have no page."""
    out = []
    kind, label = item.get("kind"), item.get("label")
    if kind not in PROOF_KINDS:
        out.append(f"proof kind {kind!r} is not one of {', '.join(PROOF_KINDS)}")
    if not isinstance(label, str) or not label.strip():
        out.append("a proof item needs a label")
    on_request, url, archive = item.get("on_request", False), item.get("url"), item.get("archive")
    to_come = item.get("to_come", False)
    if to_come:
        if marked is None:
            out.append(f"timeline proof {label!r} can't be to_come: there is no page to carry the sign")
        elif not marked:
            out.append(f"proof {label!r} is to_come, so the page needs still_to_come")
        if on_request:
            out.append(f"proof {label!r} is to_come, so it can't also be on_request")
        if url:
            out.append(f"proof {label!r} is to_come, so it must not have a url yet")
    if on_request and url:
        out.append(f"proof {label!r} is on_request, so it must not have a url")
    if not on_request and not url and not to_come:
        out.append(f"proof {label!r} needs a url, on_request = true or to_come = true")
    if isinstance(url, str) and url:
        scheme = url.split("/")[0]
        if url.startswith("https://") or (url.startswith("#") and len(url) > 1):
            pass
        elif url.startswith("/"):
            target = url.strip("/")
            if not ((static and (static / target).exists()) or (content / target).exists()
                    or (content / (target + ".md")).exists()):
                out.append(f"proof url {url!r} is not a file in static/ or a page on this site")
        elif ":" in scheme or url.startswith("//"):
            out.append(f"proof url {url!r} must be https://, a #anchor or a file beside the page")
        elif folder is None or not (folder / url).is_file():
            out.append(f"proof file {url!r} is not beside the page")
    if archive is not None and not (isinstance(archive, str) and archive.startswith("https://")):
        out.append(f"proof archive {archive!r} must be an https:// url")
    return out


def front_matter_problems(content: Path, data: Path) -> list[str]:
    out: list[str] = []
    root = content.parent
    static = root / "static"

    def rel(p: Path) -> str:
        try:
            return p.relative_to(root).as_posix()
        except ValueError:
            return p.as_posix()

    files = {}
    for name in ("channels.toml", "digital.toml", "skills.toml", "site.toml", "timeline.toml"):
        files[name], err = _load(data, name)
        if err:
            out.append(err)
    approved = set(files["skills.toml"].get("skills", []))

    def skill_problems(where: str, skills) -> list[str]:
        if not isinstance(skills, list):
            return [f"{where}: skills must be a list"]
        return [f"{where}: skill {s!r} is not in data/skills.toml" for s in skills if s not in approved]

    # channels.toml
    chans = files["channels.toml"].get("channels", [])
    numbers = [c.get("n") for c in chans]
    for key, what in (("n", "number"), ("slug", "slug"), ("colour", "colour")):
        for v, k in Counter(c.get(key) for c in chans).items():
            if k > 1:
                out.append(f"data/channels.toml: duplicate {what} {v!r}" if key != "colour"
                           else f"data/channels.toml: colour {v!r} is used by more than one channel (colours are never reused)")
    for c in chans:
        if not isinstance(c.get("slug"), str) or not PROJECT_ID.fullmatch(c["slug"]):
            out.append(f"data/channels.toml: slug {c.get('slug')!r} must be lower case letters, digits and hyphens")
        if not isinstance(c.get("name"), str) or not c["name"].strip():
            out.append(f"data/channels.toml: channel {c.get('n')!r} needs a name")
        a = c.get("alias")
        if a is not None and (a not in numbers or a == c.get("n")):
            out.append(f"data/channels.toml: alias {a!r} on channel {c.get('n')!r} points to no channel")
    by_slug = {c.get("slug"): c for c in chans}

    # digital.toml
    lines = files["digital.toml"].get("lines", [])
    for key in ("id", "order"):
        for v, k in Counter(d.get(key) for d in lines).items():
            if k > 1:
                out.append(f"data/digital.toml: duplicate {key} {v!r}")

    # site.toml
    site = files["site.toml"]
    for s in site.get("study", []):
        for key in ("start", "end"):
            v = s.get(key)
            if not (isinstance(v, str) and (YM.fullmatch(v) or (key == "end" and v == "now"))):
                out.append(f"data/site.toml: study {s.get('label')!r}: {key} {v!r} is not YYYY-MM")
    since = site.get("open_to_roles_since")
    if since is not None and not (isinstance(since, str) and YM.fullmatch(since)):
        out.append(f"data/site.toml: open_to_roles_since {since!r} is not YYYY-MM")
    for k, pr in enumerate(site.get("profiles", []), 1):
        where = f"data/site.toml: profile {k} ({pr.get('name') or '?'})"
        if not (isinstance(pr.get("name"), str) and pr["name"].strip()):
            out.append(f"{where}: needs a name")
        if not (isinstance(pr.get("url"), str) and pr["url"].startswith("https://")):
            out.append(f"{where}: url must be an https:// address")
        if not (isinstance(pr.get("line"), str) and pr["line"].strip()):
            out.append(f"{where}: needs a line saying what's there")

    # Channel folders and their _index.md
    for c in chans:
        if c.get("alias") is not None:
            continue
        idx = content / str(c.get("slug")) / "_index.md"
        if not idx.is_file():
            out.append(f"{rel(idx)}: missing (every channel in data/channels.toml needs a folder)")
            continue
        fm, err = _front(idx)
        if err:
            out.append(f"{rel(idx)}: {err}")
            continue
        ex = fm.get("extra", {})
        if ex.get("channel") not in numbers:
            out.append(f"{rel(idx)}: extra.channel {ex.get('channel')!r} is not a channel number in data/channels.toml")
        elif ex.get("channel") != c.get("n"):
            out.append(f"{rel(idx)}: extra.channel {ex.get('channel')!r} does not match data/channels.toml (n = {c.get('n')})")
        rs = ex.get("readouts", [])
        labels = [r.get("label") for r in rs if isinstance(r, dict)]
        good = all(isinstance(r, dict) and isinstance(r.get("label"), str) and isinstance(r.get("value"), str) for r in rs)
        if len(rs) != 4 or len(set(labels)) != 4 or not good:
            out.append(f"{rel(idx)}: a channel needs exactly four readouts, each a label and value, with different labels")
    for d in sorted(p for p in content.iterdir() if p.is_dir()):
        if d.name not in by_slug:
            for f in sorted(d.rglob("*.md")):
                out.append(f"{rel(f)}: not inside a channel listed in data/channels.toml")

    # Projects and their parts
    seen: dict[str, Project] = {}
    for p in _projects(content):
        if p.channel not in by_slug:
            continue
        where = rel(p.file)
        if p.id in seen:
            out.append(f"{where}: duplicate project id {p.id!r} (also {rel(seen[p.id].file)})")
        seen.setdefault(p.id, p)
        if not PROJECT_ID.fullmatch(p.id):
            out.append(f"{where}: project id {p.id!r} must be lower case letters, digits and hyphens")
        fm, err = _front(p.file)
        if err:
            out.append(f"{where}: {err}")
            continue
        ex = fm.get("extra", {})
        if not fm.get("title"):
            out.append(f"{where}: missing title")
        start, end = ex.get("start"), ex.get("end")
        if start is None:
            out.append(f"{where}: missing start (YYYY-MM)")
        elif not (isinstance(start, str) and YM.fullmatch(start)):
            out.append(f"{where}: start {start!r} is not YYYY-MM")
        if end is None:
            out.append(f"{where}: missing end (YYYY-MM or \"now\")")
        elif not (isinstance(end, str) and (end == "now" or YM.fullmatch(end))):
            out.append(f"{where}: end {end!r} is not YYYY-MM or \"now\"")
        elif isinstance(start, str) and YM.fullmatch(start) and end != "now" and end < start:
            out.append(f"{where}: end {end} is before start {start}")
        for k in BOOL_KEYS:
            if k in ex and not isinstance(ex[k], bool):
                out.append(f"{where}: {k} must be true or false")
        text_only = ex.get("text_only") is True
        hero = ex.get("hero")
        if hero and text_only:
            out.append(f"{where}: a text_only page must not set hero")
        if hero and not ex.get("hero_alt"):
            out.append(f"{where}: hero needs hero_alt")
        if hero and not (p.folder / str(hero)).is_file():
            out.append(f"{where}: hero {hero} is not in the folder")
        out += _wip_problems(where, ex, text_only)
        out += _panel_problems(where, ex, p.file.read_text(encoding="utf-8").split("+++", 2)[-1])
        parts = [(f, _front(f)) for f in p.parts]
        for f, (pf, perr) in parts:
            if perr:
                out.append(f"{rel(f)}: {perr}")
                continue
            pex = pf.get("extra", {})
            if "panel" in pex and not isinstance(pex["panel"], bool):
                out.append(f"{rel(f)}: panel must be true or false")
            out += _panel_problems(rel(f), pex, f.read_text(encoding="utf-8").split("+++", 2)[-1])
        part_fms = [pf for _, (pf, perr) in parts if not perr]
        own_skills = ex.get("skills", [])
        out += skill_problems(where, own_skills)
        if not text_only:
            rs = ex.get("readouts", [])
            if not 1 <= len(rs) <= 4:
                out.append(f"{where}: needs 1 to 4 readouts (the first is the key figure), has {len(rs)}")
            union = set(own_skills) | {s for pf in part_fms for s in pf.get("extra", {}).get("skills", [])}
            if len(own_skills) > 6 or not union:
                out.append(f"{where}: needs 1 to 6 skills, has {len(own_skills)}")
        role, bus = ex.get("role") is True, ex.get("bus_label")
        if role and not bus:
            out.append(f"{where}: a role needs a bus_label (its name on the D0 roles bus)")
        if bus and not (role or ex.get("study") is True):
            out.append(f"{where}: bus_label is only for roles (role = true) or the study line (study = true)")
        proof = list(ex.get("proof", []))
        for item in ex.get("proof", []):
            out += [f"{where}: {m}" for m in _proof_problems(item, p.folder, static, content, "still_to_come" in ex)]
        for f, (pf, perr) in parts:
            if perr:
                continue
            pex = pf.get("extra", {})
            out += skill_problems(rel(f), pex.get("skills", []))
            out += _wip_problems(rel(f), pex, False)
            for item in pex.get("proof", []):
                out += [f"{rel(f)}: {m}" for m in _proof_problems(item, f.parent, static, content, "still_to_come" in pex)]
            proof += pex.get("proof", [])
        if not proof:
            out.append(f"{where}: needs at least one proof item (its own or its parts')")

    # timeline.toml
    ids = Counter()
    for k, e in enumerate(files["timeline.toml"].get("entries", []), 1):
        where = f"data/timeline.toml: entry {k} ({e.get('id', '?')})"
        for key in TIMELINE_FIELDS:
            if key not in e:
                out.append(f"{where}: missing {key}")
        if "date" in e and not (isinstance(e["date"], str) and YM.fullmatch(e["date"])):
            out.append(f"{where}: date {e['date']!r} is not YYYY-MM")
        if "milestone" in e:
            out.append(f"{where}: timeline entries carry no milestone flag (milestones belong to projects)")
        if "education" in e and not isinstance(e["education"], bool):
            out.append(f"{where}: education must be true or false")
        out += skill_problems(where, e.get("skills", []))
        for item in e.get("proof", []):
            out += [f"{where}: {m}" for m in _proof_problems(item, None, static, content, None)]
        if "id" in e:
            ids[e["id"]] += 1
            if e["id"] in seen:
                out.append(f"{where}: id {e['id']!r} is also a project id")
    out += [f"data/timeline.toml: duplicate id {i!r}" for i, k in ids.items() if k > 1]
    return out


def _year(ym: str, today: float) -> float:
    if ym == "now":
        return today
    y, m = ym.split("-")
    return int(y) + (int(m) - 1) / 12


def calibration_warnings(content: Path, data: Path, today: datetime.date) -> list[str]:
    """Hints for the yearly calibration. Warnings only: they never fail a build."""
    now = today.year + (today.month - 1) / 12
    chans = [c for c in _load(data, "channels.toml")[0].get("channels", []) if c.get("alias") is None]
    name = {c["slug"]: f"CH{c['n']} {c['name']}" for c in chans}
    projects = []
    for p in _projects(content):
        if p.channel in name:
            fm = _front(p.file)[0]
            projects.append((p, fm.get("extra", {})))
    out = []
    for p, ex in projects:
        # A real hero may stay while more photos are to come; a placeholder should go, as the sign stands in for it.
        if ex.get("hero") and "photos" in (ex.get("still_to_come") or []):
            out.append(f"{p.channel}/{p.id}: photos are still to come but the page has a hero photo; "
                       "if it's a placeholder, remove it (the work-in-progress sign stands in for it)")
    for c in chans:
        mine = [ex for p, ex in projects if p.channel == c["slug"]]
        if not mine:
            out.append(f"{name[c['slug']]}: no projects yet")
            continue
        ends = [_year(str(ex.get("end", "now")), now) for ex in mine if YM.fullmatch(str(ex.get("end", ""))) or ex.get("end") == "now"]
        if ends and now - max(ends) > 5:
            out.append(f"{name[c['slug']]}: no project activity for 5 years (last {max(ends):.1f}); a candidate to archive")
        if len(mine) > 12:
            out.append(f"{name[c['slug']]}: {len(mine)} projects, more than about 12; a candidate to split")
    use: dict[str, Counter] = defaultdict(Counter)
    for p, ex in projects:
        if ex.get("text_only") is not True:
            for s in ex.get("skills", []):
                use[s][p.channel] += 1
    home = {}
    for s, counts in use.items():
        (top, k), *rest = counts.most_common()
        if not rest or rest[0][1] < k:
            home[s] = top
    for p, ex in projects:
        skills = ex.get("skills", []) if ex.get("text_only") is not True else []
        if not skills:
            continue
        elsewhere = Counter(home[s] for s in skills if home.get(s) not in (None, p.channel))
        if elsewhere:
            other, k = elsewhere.most_common(1)[0]
            if k > len(skills) / 2:
                out.append(f"{p.channel}/{p.id}: most of its skills belong to {name[other]}; a candidate to move")
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_site.py PUBLIC_DIR CONTENT_DIR", file=sys.stderr)
        return 2
    public, content = Path(argv[0]), Path(argv[1])
    problems: list[str] = []
    problems += [f"reserved path used: /{p}/" for p in reserved_path_hits(public)]
    for page in sorted(public.rglob("*.html")):
        rel = page.relative_to(public).as_posix()
        html = page.read_text(encoding="utf-8", errors="replace")
        problems += [f"{rel}: contact detail published: {x}" for x in contact_leaks(html)]
        problems += [f"{rel}: image without alt text: {x}" for x in images_missing_alt(html)]
        problems += [f"{rel}: tracking script: {x}" for x in tracking_scripts(html)]
        problems += [f"{rel}: {x}" for x in csp_problems(html)]
        problems += [f"{rel}: link to a missing anchor: {x}" for x in anchor_problems(html)]
        problems += [f"{rel}: id used more than once: {x}" for x in duplicate_ids(html)]
    problems += oversize_pages(public)
    problems += repo_size_problems(content)
    problems += front_matter_problems(content, content.parent / "data")
    problems += [f"stray file tracked: {x}" for x in stray_files(Path.cwd())]
    for line in problems:
        print(line)
    for line in calibration_warnings(content, content.parent / "data", datetime.date.today()):
        print(f"warning: {line}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
