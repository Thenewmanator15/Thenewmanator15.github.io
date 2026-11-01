"""Checks that every public link the site shows still works: proof links and archive copies in
front matter, the footer links in data/site.toml and timeline proof in data/timeline.toml.
(zola check only sees links written in page text.) Needs the network, so it runs in CI.

Usage: python tools/check_links.py content data
Exits 0 when every link answers, 1 with one line per dead link. Standard library only.
"""
from __future__ import annotations

import re
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

SKIP = ("https://www.linkedin.com/",)  # LinkedIn refuses automated requests
TRIES = 3
AGENT = "Mozilla/5.0 (compatible; portfolio link check; +https://thenewmanator15.github.io/)"


def _front(path: Path) -> dict:
    m = re.match(r"\+\+\+\r?\n(.*?)\r?\n\+\+\+", path.read_text(encoding="utf-8"), re.S)
    try:
        return tomllib.loads(m.group(1)) if m else {}
    except tomllib.TOMLDecodeError:
        return {}


def _proof_urls(items) -> list[str]:
    return [u for q in items or [] for u in (q.get("url"), q.get("archive")) if isinstance(u, str)]


def collect(content: Path, data: Path) -> list[str]:
    urls: list[str] = []
    for f in sorted(content.rglob("*.md")):
        urls += _proof_urls(_front(f).get("extra", {}).get("proof"))
    site = data / "site.toml"
    if site.is_file():
        st = tomllib.loads(site.read_text(encoding="utf-8"))
        urls += [l.get("url") for l in st.get("links", []) + st.get("profiles", []) + [st.get("try_it") or {}]]
    tl = data / "timeline.toml"
    if tl.is_file():
        for e in tomllib.loads(tl.read_text(encoding="utf-8")).get("entries", []):
            urls += _proof_urls(e.get("proof"))
    return list(dict.fromkeys(u for u in urls if isinstance(u, str) and u.startswith("https://")))


def fetch(url: str) -> int:
    """The HTTP status for url: HEAD first, then GET for servers that refuse HEAD."""
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": AGENT})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 501):
                continue
            return e.code
    return 0


def check(urls: list[str], fetch=fetch, pause: float = 2.0) -> list[str]:
    out = []
    for url in urls:
        if url.startswith(SKIP):
            continue
        status, err = 0, ""
        for attempt in range(TRIES):
            try:
                status = fetch(url)
                if status < 500:
                    break
            except OSError as e:
                err = str(e)
            time.sleep(pause * (attempt + 1))
        if not 200 <= status < 400:
            out.append(f"{url}: {'HTTP ' + str(status) if status else 'no answer (' + err + ')'}")
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_links.py CONTENT_DIR DATA_DIR", file=sys.stderr)
        return 2
    out = check(collect(Path(argv[0]), Path(argv[1])))
    for line in out:
        print(line)
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
