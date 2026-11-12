import datetime
import json
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from check_site import (  # noqa: E402
    EXPECTED_CSP,
    _front,
    _projects,
    anchor_problems,
    calibration_warnings,
    contact_leaks,
    count_project_pages,
    csp_problems,
    duplicate_ids,
    front_matter_problems,
    images_missing_alt,
    is_embedded_image,
    oversize_pages,
    repo_size_problems,
    reserved_path_hits,
    stray_files,
    text_only_pages,
    tracking_scripts,
)

GOOD_HEAD = f'<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="{EXPECTED_CSP}">'
PUBLIC = ROOT / "public"
CONTENT = ROOT / "content"
DATA = ROOT / "data"

# The front-matter contract example from the build plan.
SAMPLE_FRONT_MATTER = '''+++
title = "Wireless packet sniffers"
description = "Two small boards that stream Wi-Fi, Bluetooth and 802.15.4 into Wireshark."
[extra]
start = "2026-03"
end = "2026-10"
featured = true
milestone = false
role = false
skills = ["ESP-IDF", "Zephyr", "Wireshark", "test strategy"]
text_only = false
hero = "hero.jpg"
hero_alt = "Two small green boards plugged into a laptop"
my_part = "..."
result = "..."
[[extra.readouts]]
label = "radios"
value = "3 protocols"
[[extra.proof]]
kind = "code"
label = "Firmware and tests on GitHub"
url = "https://github.com/Thenewmanator15/esp32c6-sniffer"
archive = "https://doi.org/10.5281/zenodo.0000000"
[[extra.proof]]
kind = "photos"
label = "Photos of both boards"
url = "#photos"
[[extra.proof]]
kind = "measurements"
label = "Test logs"
on_request = true
+++
'''

CHANNEL_INDEX = '''+++
title = "Instruments"
[extra]
channel = 1
[[extra.readouts]]
label = "edge"
value = "<1.4 ns"
[[extra.readouts]]
label = "currents"
value = "picoamps"
[[extra.readouts]]
label = "capture"
value = "1 GS/s"
[[extra.readouts]]
label = "speed-up"
value = "~30x"
+++
'''


def _rows(html: str):
    """Each <li class="row..."> with the number of its direct child elements."""
    from html.parser import HTMLParser

    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.stack, self.rows = [], []

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if self.stack and self.stack[-1][0] == "li-row" and len(self.stack) == self.stack[-1][2]:
                self.stack[-1][1][0] += 1
            if tag == "li" and (a.get("class") or "").startswith("row"):
                self.rows.append([tag, a, 0])
                self.stack.append(["li-row", [0], len(self.stack) + 1, self.rows[-1]])
            else:
                self.stack.append([tag, None, None, None])

        def handle_endtag(self, tag):
            if not self.stack:
                return
            top = self.stack.pop()
            if top[0] == "li-row":
                top[3][2] = top[1][0]

    p = P()
    p.feed(html)
    return p.rows


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class Site(tempfile.TemporaryDirectory):
    """A throwaway content/ and data/ pair: the real data files, one channel, one valid project."""

    def __enter__(self):
        root = Path(super().__enter__())
        self.content, self.data = root / "content", root / "data"
        self.data.mkdir()
        for f in DATA.glob("*.toml"):
            (self.data / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
        for c in tomllib.loads((DATA / "channels.toml").read_text(encoding="utf-8"))["channels"]:
            write(self.content / c["slug"] / "_index.md",
                  CHANNEL_INDEX.replace('"Instruments"', f'"{c["name"]}"').replace("channel = 1", f"channel = {c['n']}"))
        self.page = write(self.content / "instruments" / "x" / "index.md", SAMPLE_FRONT_MATTER)
        (self.page.parent / "hero.jpg").write_bytes(b"jpg")
        return self

    def problems(self):
        return front_matter_problems(self.content, self.data)

    def edit(self, old: str, new: str, path: Path | None = None):
        path = path or self.page
        text = path.read_text(encoding="utf-8")
        assert old in text, old
        path.write_text(text.replace(old, new), encoding="utf-8")


class BuiltSite(unittest.TestCase):
    """Run after `zola build`: the real site and its sample content."""

    def test_front_page_works_without_js(self):
        html = (PUBLIC / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('class="tile"'), count_project_pages(CONTENT))
        self.assertEqual(html.count('class="row"'), count_project_pages(CONTENT))  # timeline rows are "row tl"
        self.assertIn("I build the instrument", html)
        self.assertIn("github.com/Thenewmanator15", html)

    def test_every_project_has_dates_and_channel(self):
        self.assertEqual(front_matter_problems(CONTENT, DATA), [])

    def test_text_only_pages_have_no_images(self):
        # No photos of their own. Pictures shown from another site's server (PhovIR's) are allowed.
        for path in text_only_pages(CONTENT):
            html = (PUBLIC / path / "index.html").read_text(encoding="utf-8")
            own = [s for s in re.findall(r'<img[^>]*?\ssrc="([^"]+)"', html) if not is_embedded_image(s)]
            self.assertEqual(own, [], path)

    def test_front_page_carries_the_data_blob(self):
        html = (PUBLIC / "index.html").read_text(encoding="utf-8")
        start = html.index('<script type="application/json" id="scope-data">') + len('<script type="application/json" id="scope-data">')
        blob = json.loads(html[start:html.index("</script>", start)])
        self.assertEqual(set(blob), {"now", "min", "channels", "channelReadouts", "digital", "study", "openSince", "events", "items"})
        self.assertEqual(len(blob["items"]), count_project_pages(CONTENT))
        self.assertEqual([c["n"] for c in blob["channels"]], list(range(1, 8)))
        self.assertTrue(all(len(v) == 4 for v in blob["channelReadouts"].values()))
        item = blob["items"][0]
        self.assertEqual(set(item), {"id", "title", "url", "channel", "start", "end", "featured", "milestone", "role",
                                     "bus_label", "study", "text_only", "summary", "thumb", "thumb_alt", "skills",
                                     "readouts", "proof", "parts", "wip"})
        self.assertTrue(all(set(p) == {"kind", "label", "url", "on_request", "archive"} for p in item["proof"]))
        self.assertTrue(all(set(q) == {"title", "url", "wip"} for i in blob["items"] for q in i["parts"]))
        # Links are resolved at build time: https, or a path on this site (an anchor becomes page path + anchor).
        urls = [p["url"] for i in blob["items"] for p in i["proof"] if p["url"]]
        self.assertTrue(urls and all(u.startswith(("https://", "/")) for u in urls), urls)
        self.assertTrue(all(e["id"] not in {i["id"] for i in blob["items"]} for e in blob["events"]))

    def test_in_progress_labels(self):
        # The pages held back for the first release (1 Nov 2026): thesis photos, the unproven fault, MBDA.
        # PhovIR's sign came off on 2 Nov 2026 once its write-up was done.
        label = '<span class="lbl wip">in progress</span>'
        html = (PUBLIC / "index.html").read_text(encoding="utf-8")
        start = html.index('id="scope-data">') + len('id="scope-data">')
        blob = json.loads(html[start:html.index("</script>", start)])
        self.assertEqual(sorted(i["id"] for i in blob["items"] if i["wip"]), ["mbda", "phd"])
        self.assertEqual(sorted(q["title"] for i in blob["items"] for q in i.get("parts", []) if q["wip"]),
                         ["Capture, timing and the pattern", "The gate", "The timing problem"])
        self.assertIn(label, html)

    def test_parts_are_not_projects(self):
        html = (PUBLIC / "index.html").read_text(encoding="utf-8")
        start = html.index('id="scope-data">') + len('id="scope-data">')
        blob = json.loads(html[start:html.index("</script>", start)])
        phd = [i for i in blob["items"] if i["id"] == "phd"]
        self.assertEqual(len(phd), 1)
        self.assertEqual(len(phd[0]["parts"]), 6)
        self.assertTrue(all(p["url"] for p in phd[0]["parts"]))
        part_urls = {p["url"] for p in phd[0]["parts"]}
        self.assertFalse(part_urls & {i["url"] for i in blob["items"]})
        self.assertEqual(html.count('href="/instruments/phd/"'), 2)  # one tile, one All projects row

    def test_list_rows_fit_their_columns(self):
        # dot, tag, title (with its label), dates, proof kinds: never more than five cells per row
        for page in [PUBLIC / "index.html", *PUBLIC.glob("*/index.html")]:
            for tag, attrs, kids in _rows(page.read_text(encoding="utf-8")):
                self.assertLessEqual(kids, 5, f"{page}: {attrs}")

    def test_sign_only_on_marked_pages(self):
        marked = []
        for p in _projects(CONTENT):
            for f in [p.file, *p.parts]:
                rel = f.relative_to(CONTENT)
                folder = rel.parent if f.name in ("index.md", "_index.md") else rel.with_suffix("")
                page = (PUBLIC / folder / "index.html").read_text(encoding="utf-8")
                has = "still_to_come" in _front(f)[0].get("extra", {})
                self.assertEqual('class="wip-sign"' in page, has, folder)
                if has:
                    marked.append(folder.as_posix())
        self.assertEqual(sorted(marked), ["instruments/phd", "instruments/phd/capture", "instruments/phd/gate",
                                          "instruments/phd/timing-problem", "rf-wireless-embedded/mbda"])

    def test_profile_cards_on_the_front_page(self):
        html = (PUBLIC / "index.html").read_text(encoding="utf-8")
        nav = re.search(r'<nav class="profiles" aria-label="Profiles">(.*?)</nav>', html, re.S)
        self.assertIsNotNone(nav)  # plain links, so they work without JavaScript
        hrefs = re.findall(r'<a class="pcard" href="([^"]+)"', nav.group(1))
        self.assertEqual(hrefs, ["https://www.linkedin.com/in/mathew-newman", "https://orcid.org/0000-0003-1784-3250",
                                 "https://github.com/Thenewmanator15", "https://thenewmanator15.github.io/mptofsims-supplementary/"])
        self.assertLess(html.index('class="profiles"'), html.index('id="scope"'))  # near the top, above the scope
        # each card, and the Try it card, carries its logo as inline SVG: nothing loads from another site,
        # and screen readers skip the picture (the card's name says the same)
        cards = re.findall(r'<a class="pcard[^"]*" href="[^"]+">(.*?)</a>', html, re.S)
        self.assertEqual(len(cards), 5)
        for c in cards:
            self.assertRegex(c, r'<svg class="pico[^"]*" viewBox="[^"]+" aria-hidden="true" focusable="false">')
        self.assertEqual(csp_problems(html), [])

    def test_driver_chart_is_inline_and_themed(self):
        html = (PUBLIC / "instruments" / "phd" / "driver" / "index.html").read_text(encoding="utf-8")
        labels = re.findall(r'<div class="chartbox" role="img" aria-label="([^"]+)"><svg class="chart" aria-hidden="true"', html)
        self.assertTrue(any(l.startswith("Scatter plot of edge time") for l in labels), "chart not inlined with a label")
        self.assertTrue(any(l.startswith("Line chart of common-mode rejection") for l in labels), labels)
        self.assertEqual(csp_problems(html), [])

    def test_front_page_extras(self):
        html = (PUBLIC / "index.html").read_text(encoding="utf-8")
        # the scope's top bar says when the site was last built, in the one date style that isn't a month name
        self.assertRegex(html, r"trig: curiosity · calibrated \d{4}-\d{2}-\d{2}<")
        # a card to try the PDF themes demo, after the "Now" line
        self.assertRegex(html, r'<p class="now">[^<]*</p>\s*<a class="pcard tryit" href="https://thenewmanator15\.github\.io/pdf-themes/">')
        # every page's footer offers references as well as the CV
        for page in PUBLIC.rglob("*.html"):
            if page.name == "index.html":
                self.assertIn("References on request", page.read_text(encoding="utf-8"), page)

    def test_trace_has_a_role(self):
        html = (PUBLIC / "index.html").read_text(encoding="utf-8")
        self.assertRegex(html, r'<div class="plot" id="plot"[^>]*\brole="application"')

    def test_one_date_format(self):
        html = (PUBLIC / "index.html").read_text(encoding="utf-8")
        self.assertIn("2026 – now", html)
        self.assertNotRegex(html, r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}")

    def test_every_built_page_passes_csp_and_anchors(self):
        for page in PUBLIC.rglob("*.html"):
            html = page.read_text(encoding="utf-8")
            self.assertEqual(csp_problems(html), [], page)
            self.assertEqual(anchor_problems(html), [], page)
            self.assertEqual(duplicate_ids(html), [], page)


class FrontMatter(unittest.TestCase):
    def test_sample_site_is_clean(self):
        with Site() as s:
            self.assertEqual(s.problems(), [])

    def test_unknown_skill_flagged(self):
        with Site() as s:
            s.edit('"Zephyr"', '"zephyr"')
            self.assertTrue(any("zephyr" in p for p in s.problems()))

    def flagged(self, old, new, expect, path=None):
        with Site() as s:
            s.edit(old, new, path(s) if path else None)
            out = s.problems()
            self.assertTrue(any(expect in p for p in out), f"{expect!r} not in {out}")

    def test_dates(self):
        self.flagged('start = "2026-03"\n', "", "start")
        self.flagged('end = "2026-10"', 'end = "Oct 2026"', "end")
        self.flagged('start = "2026-03"', 'start = "2026-13"', "start")
        self.flagged('end = "2026-10"', 'end = "2025-01"', "before")

    def test_page_outside_the_channel_sections(self):
        with Site() as s:
            write(s.content / "misc" / "y" / "index.md", SAMPLE_FRONT_MATTER)
            self.assertTrue(any("misc" in p and "channel" in p for p in s.problems()))

    def test_channel_index_rules(self):
        idx = lambda s: s.content / "instruments" / "_index.md"  # noqa: E731
        self.flagged("channel = 1", "channel = 9", "channel", idx)
        self.flagged('[[extra.readouts]]\nlabel = "edge"\nvalue = "<1.4 ns"\n', "", "four", idx)
        self.flagged('label = "currents"', 'label = "edge"', "four", idx)  # four distinct labels

    def test_hero_rules(self):
        self.flagged('hero_alt = "Two small green boards plugged into a laptop"\n', "", "hero_alt")
        self.flagged("text_only = false", "text_only = true", "hero")
        self.flagged('hero = "hero.jpg"', 'hero = "missing.jpg"', "missing.jpg")

    def test_readouts_and_skills(self):
        self.flagged('[[extra.readouts]]\nlabel = "radios"\nvalue = "3 protocols"\n', "", "readouts")
        self.flagged('"test strategy"]', '"test strategy", "Python", "Rust", "Julia"]', "skills")
        self.flagged('skills = ["ESP-IDF", "Zephyr", "Wireshark", "test strategy"]', "skills = []", "skills")

    def test_text_only_needs_no_skills_readouts_or_hero(self):
        with Site() as s:
            text = s.page.read_text(encoding="utf-8")
            text = text.replace("text_only = false", "text_only = true").replace('hero = "hero.jpg"\n', "")
            text = text.replace('hero_alt = "Two small green boards plugged into a laptop"\n', "")
            text = text.replace('skills = ["ESP-IDF", "Zephyr", "Wireshark", "test strategy"]\n', "")
            text = text.replace('[[extra.readouts]]\nlabel = "radios"\nvalue = "3 protocols"\n', "")
            s.page.write_text(text, encoding="utf-8")
            self.assertEqual(s.problems(), [])

    def test_proof_rules(self):
        self.flagged('kind = "code"', 'kind = "blog"', "kind")
        self.flagged('label = "Test logs"\non_request = true', 'label = "Test logs"\non_request = true\nurl = "https://x.example"', "on_request")
        self.flagged('label = "Test logs"\non_request = true', 'label = "Test logs"', "url")
        self.flagged('archive = "https://doi.org/10.5281/zenodo.0000000"', 'archive = "http://archive.org/x"', "archive")
        self.flagged('url = "#photos"', 'url = "javascript:alert(1)"', "url")
        self.flagged('url = "#photos"', 'url = "report.pdf"', "report.pdf")  # a file beside the page must exist
        with Site() as s:
            text = s.page.read_text(encoding="utf-8")
            s.page.write_text(text[:text.index("[[extra.proof]]")] + "+++\n", encoding="utf-8")
            self.assertTrue(any("proof" in p for p in s.problems()))

    def test_still_to_come_rules(self):
        k = "text_only = false"
        self.flagged(k, k + "\nstill_to_come = []", "still_to_come")               # empty: delete the line instead
        self.flagged(k, k + '\nstill_to_come = ["pictures"]', "pictures")         # unknown part
        self.flagged(k, k + '\nstill_to_come = ["dates", "dates"]', "dates")      # repeated
        self.flagged(k, k + '\nstill_to_come = "photos"', "still_to_come")        # not a list
        self.flagged(k, k + '\nstill_to_come_note = "Soon."', "still_to_come_note")  # note without the list
        with Site() as s:  # a real hero may stay while more photos are to come: a warning, never a failure
            s.edit(k, k + '\nstill_to_come = ["photos"]')
            self.assertEqual(s.problems(), [])
            warnings = calibration_warnings(s.content, s.data, datetime.date(2026, 10, 31))
            self.assertTrue(any("instruments/x" in w and "hero" in w for w in warnings), warnings)
        with Site() as s:  # a text_only page has no photos by choice
            text = s.page.read_text(encoding="utf-8")
            text = text.replace("text_only = false", 'text_only = true\nstill_to_come = ["photos"]')
            text = text.replace('hero = "hero.jpg"\n', "").replace('hero_alt = "Two small green boards plugged into a laptop"\n', "")
            text = text.replace('skills = ["ESP-IDF", "Zephyr", "Wireshark", "test strategy"]\n', "")
            text = text.replace('[[extra.readouts]]\nlabel = "radios"\nvalue = "3 protocols"\n', "")
            s.page.write_text(text, encoding="utf-8")
            out = s.problems()
            self.assertTrue(any("text_only" in p and "photos" in p for p in out), out)

    def test_still_to_come_passes_and_applies_to_parts(self):
        with Site() as s:
            s.edit("text_only = false", 'text_only = false\nstill_to_come = ["proof", "dates"]\n'
                                        'still_to_come_note = "Logs to follow."')
            self.assertEqual(s.problems(), [])
        with Site() as s:
            big = s.content / "instruments" / "big"
            write(big / "_index.md", SAMPLE_FRONT_MATTER)
            (big / "hero.jpg").write_bytes(b"jpg")
            write(big / "driver.md", '+++\ntitle = "The driver"\ndescription = "A part."\n[extra]\nstill_to_come = ["photos"]\n+++\n')
            self.assertEqual(s.problems(), [])
            write(big / "driver.md", '+++\ntitle = "The driver"\ndescription = "A part."\n[extra]\nstill_to_come = ["photo"]\n+++\n')
            out = s.problems()
            self.assertTrue(any("driver.md" in p and "photo" in p for p in out), out)

    def test_to_come_proof_rules(self):
        t = 'label = "Test logs"\non_request = true'
        self.flagged(t, 'label = "Test logs"\nto_come = true', "still_to_come")             # the page must be marked
        self.flagged(t, 'label = "Test logs"\nto_come = true\non_request = true', "to_come")
        self.flagged(t, 'label = "Test logs"\nto_come = true\nurl = "https://x.example"', "to_come")
        with Site() as s:
            s.edit("text_only = false", 'text_only = false\nstill_to_come = ["proof"]')
            s.edit(t, 'label = "Test logs"\nto_come = true')
            self.assertEqual(s.problems(), [])
        self.flagged('kind = "certificate"', 'kind = "certificate"\nto_come = true', "to_come",
                     lambda s: s.data / "timeline.toml")                                  # no page to carry a sign

    PANEL = ('panel = true\n[[extra.matrix]]\ntitle = "Radio"\ncols = ["A", "B"]\n'
             'rows = [["Capture", "yes", "no"], ["Survey", "-", "not yet tried"]]\n'
             '[[extra.tiles]]\nvalue = "8"\nlabel = "golden vectors"\n')
    BODY = "\n{{ <matrices /> }}\n\n{{ <tiles /> }}\n"

    def panel_problems(self, keys: str, body: str = BODY) -> list[str]:
        with Site() as s:
            s.edit('my_part = "..."\n', 'my_part = "..."\n' + keys)
            s.page.write_text(s.page.read_text(encoding="utf-8") + body, encoding="utf-8")
            return s.problems()

    def test_a_correct_panel_page_is_clean(self):
        self.assertEqual(self.panel_problems(self.PANEL), [])

    def test_matrix_rows_match_the_columns(self):
        keys = self.PANEL.replace('["Survey", "-", "not yet tried"]', '["Survey", "-"]')
        self.assertEqual(self.panel_problems(keys), ["content/instruments/x/index.md: matrix Radio: row 2 has 2 cells, needs 3"])

    def test_matrix_needs_a_title_and_columns(self):
        keys = self.PANEL.replace('cols = ["A", "B"]\n', "").replace(
            'rows = [["Capture", "yes", "no"], ["Survey", "-", "not yet tried"]]\n', "")
        self.assertEqual(self.panel_problems(keys),
                         ["content/instruments/x/index.md: matrix Radio: needs a title and at least one column"])

    def test_tiles_need_a_value_and_a_label(self):
        keys = self.PANEL.replace('label = "golden vectors"\n', "")
        self.assertEqual(self.panel_problems(keys), ["content/instruments/x/index.md: tiles need a value and a label"])

    def test_matrix_and_tiles_need_panel(self):
        keys = self.PANEL.replace("panel = true\n", "")
        self.assertEqual(self.panel_problems(keys), ["content/instruments/x/index.md: matrix and tiles need panel = true"])

    def test_panel_is_true_or_false(self):
        keys = self.PANEL.replace("panel = true", 'panel = "yes"')
        self.assertIn("content/instruments/x/index.md: panel must be true or false", self.panel_problems(keys))

    def test_matrix_and_tiles_must_be_shown(self):
        self.assertEqual(self.panel_problems(self.PANEL, body="\nNo calls here.\n"),
                         ["content/instruments/x/index.md: has a matrix but never shows it: add {{ <matrices /> }} to the text",
                          "content/instruments/x/index.md: has tiles but never shows them: add {{ <tiles /> }} to the text"])

    def test_matrices_placed_one_at_a_time(self):
        two = self.PANEL + '[[extra.matrix]]\ntitle = "Heat"\ncols = ["45 V"]\nrows = [["20 ns", "hot"]]\n'
        both = '\n{{ <matrices only="Radio" /> }}\n\nText.\n\n{{ <matrices only="Heat" /> }}\n\n{{ <tiles /> }}\n'
        self.assertEqual(self.panel_problems(two, body=both), [])
        one = '\n{{ <matrices only="Radio" /> }}\n\n{{ <tiles /> }}\n'
        self.assertEqual(self.panel_problems(two, body=one),
                         ['content/instruments/x/index.md: matrix Heat is never shown: add {{ <matrices only="Heat" /> }} to the text'])
        typo = both.replace('only="Heat"', 'only="Heta"')
        self.assertEqual(self.panel_problems(two, body=typo),
                         ['content/instruments/x/index.md: matrices only="Heta": no matrix has that title',
                          'content/instruments/x/index.md: matrix Heat is never shown: add {{ <matrices only="Heat" /> }} to the text'])

    def test_role_rules(self):
        self.flagged("role = false", "role = true", "bus_label")
        self.flagged("role = false", 'role = false\nbus_label = "X"', "bus_label")

    def test_bus_label_also_names_a_study_project(self):
        with Site() as s:
            s.edit("role = false", 'role = false\nstudy = true\nbus_label = "PhD"')
            self.assertEqual(s.problems(), [])

    def test_project_ids(self):
        with Site() as s:
            write(s.content / "medical-imaging" / "x" / "index.md", SAMPLE_FRONT_MATTER)
            (s.content / "medical-imaging" / "x" / "hero.jpg").write_bytes(b"jpg")
            self.assertTrue(any("duplicate" in p and "x" in p for p in s.problems()))
        with Site() as s:
            write(s.content / "instruments" / "Bad_Name" / "index.md", SAMPLE_FRONT_MATTER)
            (s.content / "instruments" / "Bad_Name" / "hero.jpg").write_bytes(b"jpg")
            self.assertTrue(any("Bad_Name" in p for p in s.problems()))

    def test_parts_exempt_but_skills_checked(self):
        with Site() as s:
            big = s.content / "instruments" / "big"
            write(big / "_index.md", SAMPLE_FRONT_MATTER)
            (big / "hero.jpg").write_bytes(b"jpg")
            write(big / "gate.md", '+++\ntitle = "The gate"\ndescription = "One part."\n+++\nText.\n')
            self.assertEqual(s.problems(), [])
            write(big / "driver.md", '+++\ntitle = "The driver"\ndescription = "Another."\n[extra]\nskills = ["kicad"]\n+++\n')
            self.assertTrue(any("kicad" in p for p in s.problems()))

    def test_parts_get_the_panel_rules(self):
        with Site() as s:
            big = s.content / "instruments" / "big"
            write(big / "_index.md", SAMPLE_FRONT_MATTER)
            (big / "hero.jpg").write_bytes(b"jpg")
            write(big / "gate.md", '+++\ntitle = "The gate"\ndescription = "One part."\n[extra]\npanel = "no"\n+++\n')
            write(big / "driver.md", '+++\ntitle = "The driver"\ndescription = "Another."\n[extra]\npanel = true\n'
                                     '[[extra.tiles]]\nvalue = "8"\nlabel = "vectors"\n+++\nNo call.\n')
            self.assertEqual(sorted(s.problems()), [
                "content/instruments/big/driver.md: has tiles but never shows them: add {{ <tiles /> }} to the text",
                "content/instruments/big/gate.md: panel must be true or false"])

    def test_big_project_proof_can_come_from_parts(self):
        with Site() as s:
            big = s.content / "instruments" / "big"
            text = SAMPLE_FRONT_MATTER
            write(big / "_index.md", text[:text.index("[[extra.proof]]")] + "+++\n")
            (big / "hero.jpg").write_bytes(b"jpg")
            write(big / "gate.md", '+++\ntitle = "Gate"\ndescription = "A part."\n[[extra.proof]]\nkind = "photos"\n'
                                   'label = "Gate photos"\non_request = true\n+++\n')
            self.assertEqual(s.problems(), [])

    def test_timeline_rules(self):
        tl = lambda s: s.data / "timeline.toml"  # noqa: E731
        self.flagged('date = "2024-01"', 'date = "2024"', "date", tl)
        self.flagged('id = "afhea"', 'id = "afhea"\nmilestone = true', "milestone", tl)
        self.flagged('id = "afhea"\n', "", "id", tl)
        self.flagged('kind = "certificate"', 'kind = "trophy"', "kind", tl)

    def test_channels_file_rules(self):
        ch = lambda s: s.data / "channels.toml"  # noqa: E731
        self.flagged("n = 2\n", "n = 1\n", "duplicate", ch)
        self.flagged('slug = "rf-wireless-embedded"', 'slug = "instruments"', "duplicate", ch)
        self.flagged('colour = "--c2"', 'colour = "--c1"', "colour", ch)
        self.flagged('slug = "teaching-mentoring"', 'slug = "teaching-mentoring"\nalias = 12', "alias", ch)

    def test_digital_and_site_files(self):
        self.flagged('id = "D1"', 'id = "D0"', "duplicate", lambda s: s.data / "digital.toml")
        self.flagged("order = 1", "order = 0", "duplicate", lambda s: s.data / "digital.toml")
        self.flagged('start = "2013-09"', 'start = "Sep 2013"', "study", lambda s: s.data / "site.toml")
        self.flagged('open_to_roles_since = "', 'open_to_roles_since = "x', "open_to_roles_since", lambda s: s.data / "site.toml")

    def test_profile_card_rules(self):
        site = lambda s: s.data / "site.toml"  # noqa: E731
        self.flagged('name = "ORCID"', 'name = ""', "profile", site)
        self.flagged('url = "https://orcid.org/', 'url = "http://orcid.org/', "https", site)
        self.flagged('line = "Research record"', 'line = ""', "line", site)


class Counting(unittest.TestCase):
    def test_projects_count_once_parts_never(self):
        with Site() as s:
            big = s.content / "instruments" / "big"
            write(big / "_index.md", SAMPLE_FRONT_MATTER)
            write(big / "gate.md", "+++\ntitle = 'Gate'\n+++\n")
            write(big / "capture" / "index.md", "+++\ntitle = 'Capture'\n+++\n")
            write(s.content / "medical-imaging" / "solo.md", SAMPLE_FRONT_MATTER)
            self.assertEqual(count_project_pages(s.content), 3)  # x, big, solo

    def test_text_only_pages_listed_by_built_path(self):
        with Site() as s:
            s.edit("text_only = false", "text_only = true")
            self.assertEqual(text_only_pages(s.content), ["instruments/x"])


class Calibration(unittest.TestCase):
    def test_quiet_channel_busy_channel_and_misplaced_project(self):
        import datetime
        with Site() as s:
            s.edit('start = "2026-03"', 'start = "2014-03"')
            s.edit('end = "2026-10"', 'end = "2015-10"')
            for k in range(13):
                write(s.content / "medical-imaging" / f"m{k}" / "index.md",
                      SAMPLE_FRONT_MATTER.replace('"test strategy"', '"DICOM"'))
            out = calibration_warnings(s.content, s.data, datetime.date(2026, 10, 31))
            self.assertTrue(any("Instruments" in w and "5 years" in w for w in out), out)
            self.assertTrue(any("Medical imaging" in w and "13" in w for w in out), out)
            self.assertTrue(any("instruments/x" in w and "Medical imaging" in w for w in out), out)


class CspAndAnchors(unittest.TestCase):
    def test_json_data_block_is_not_a_script(self):
        self.assertEqual(csp_problems(GOOD_HEAD + '<script type="application/json" id="d">{"a":1}</script>'), [])
        self.assertNotEqual(csp_problems(GOOD_HEAD + '<script type="module">import "x"</script>'), [])

    def test_inline_styles_flagged(self):
        self.assertNotEqual(csp_problems(GOOD_HEAD + '<p style="color:red">x</p>'), [])
        self.assertNotEqual(csp_problems(GOOD_HEAD + "<style>p{}</style>"), [])

    def test_own_site_address_is_same_origin(self):
        self.assertEqual(csp_problems(GOOD_HEAD + '<img src="https://thenewmanator15.github.io/a.jpg" alt="a">'), [])
        self.assertNotEqual(csp_problems(GOOD_HEAD + '<img src="https://thenewmanator15.github.io.evil.example/a.jpg" alt="a">'), [])

    def test_duplicate_ids_flagged(self):
        self.assertEqual(duplicate_ids('<h2 id="a"></h2><h2 id="b"></h2>'), [])
        self.assertEqual(duplicate_ids('<h2 id="what-i-did"></h2><p></p><h2 id="what-i-did"></h2>'), ["what-i-did"])

    def test_page_anchors_must_resolve(self):
        self.assertEqual(anchor_problems('<a href="#photos">p</a><section id="photos"></section>'), [])
        self.assertEqual(anchor_problems('<a href="#photos">p</a>'), ["#photos"])
        self.assertEqual(anchor_problems('<a href="#main">skip</a><main id="main"></main>'), [])


class ReservedPaths(unittest.TestCase):
    def test_reserved_paths_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "pdf-themes").mkdir()
            (Path(d) / "instruments").mkdir()
            self.assertEqual(reserved_path_hits(Path(d)), ["pdf-themes"])


class ContactLeaks(unittest.TestCase):
    def test_email_flagged(self):
        self.assertEqual(contact_leaks("<p>mail me@example.com</p>"), ["me@example.com"])

    def test_mailto_flagged(self):
        self.assertNotEqual(contact_leaks('<a href="mailto:x@y.z">'), [])

    def test_phone_flagged(self):
        self.assertNotEqual(contact_leaks("<p>+44 7700 900123</p>"), [])

    def test_units_and_years_not_flagged(self):
        self.assertEqual(contact_leaks("<p>1 GS/s, 150 V, 2026</p>"), [])
        self.assertEqual(contact_leaks("<p>2017 2018 2019 2020</p>"), [])
        self.assertEqual(contact_leaks("<style>@media (min-width: 40em) {}</style>"), [])


class ImagesAlt(unittest.TestCase):
    def test_img_without_alt_flagged(self):
        self.assertEqual(images_missing_alt('<img src="a.jpg">'), ["a.jpg"])

    def test_img_with_alt_passes(self):
        self.assertEqual(images_missing_alt('<img src="a.jpg" alt="Board">'), [])


class Tracking(unittest.TestCase):
    def test_tracking_flagged(self):
        self.assertNotEqual(tracking_scripts('<script src="https://www.googletagmanager.com/gtag/js"></script>'), [])

    def test_own_script_passes(self):
        self.assertEqual(tracking_scripts('<script src="/js/scope-ui.mjs" type="module"></script>'), [])


class RepoSize(unittest.TestCase):
    def test_repo_size_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "big.jpg").write_bytes(b"0" * (3 * 1024 * 1024))
            (Path(d) / "ok.jpg").write_bytes(b"0" * 1024)
            self.assertEqual(repo_size_problems(Path(d)), ["big.jpg: 3.0 MB (limit 2 MB)"])
            self.assertNotEqual(repo_size_problems(Path(d), max_total_mb=1), [])


class OversizePages(unittest.TestCase):
    def test_page_with_heavy_image_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "index.html").write_text('<img src="big.jpg" alt="x">', encoding="utf-8")
            (p / "big.jpg").write_bytes(b"0" * (2 * 1024 * 1024))
            (p / "font.woff2").write_bytes(b"0" * (2 * 1024 * 1024))
            self.assertEqual(len(oversize_pages(p, budget_kb=1500)), 1)
            self.assertEqual(oversize_pages(p, budget_kb=3000), [])

    def test_own_absolute_urls_and_largest_srcset_copy_counted(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "index.html").write_text('<img src="https://thenewmanator15.github.io/s.jpg" srcset="https://thenewmanator15.github.io/s.jpg 640w, '
                                          'https://thenewmanator15.github.io/big.jpg 2000w" alt="x">', encoding="utf-8")
            (p / "s.jpg").write_bytes(b"0" * 1024)
            (p / "big.jpg").write_bytes(b"0" * (2 * 1024 * 1024))
            self.assertEqual(len(oversize_pages(p, budget_kb=1500)), 1)


class Csp(unittest.TestCase):
    def test_good_page_passes(self):
        html = GOOD_HEAD + '<script src="/js/a.js"></script><a href="https://github.com/x">GitHub</a>'
        self.assertEqual(csp_problems(html), [])

    def test_missing_or_wrong_policy_flagged(self):
        self.assertNotEqual(csp_problems('<meta charset="utf-8"><p>hi</p>'), [])
        wrong = '<meta http-equiv="Content-Security-Policy" content="default-src *">'
        self.assertNotEqual(csp_problems(wrong), [])

    def test_inline_script_and_handlers_flagged(self):
        self.assertNotEqual(csp_problems(GOOD_HEAD + "<script>alert(1)</script>"), [])
        self.assertNotEqual(csp_problems(GOOD_HEAD + '<button onclick="x()">b</button>'), [])

    def test_other_origin_resources_flagged(self):
        self.assertNotEqual(csp_problems(GOOD_HEAD + '<script src="https://cdn.example.com/a.js"></script>'), [])
        self.assertNotEqual(csp_problems(GOOD_HEAD + '<link rel="stylesheet" href="https://fonts.googleapis.com/x">'), [])
        self.assertNotEqual(csp_problems(GOOD_HEAD + '<img src="https://example.com/a.png" alt="a">'), [])

    def test_embedded_images_only_from_listed_hosts_with_no_referrer(self):
        ok = '<img src="https://www.phovir.com/a.webp" alt="a" referrerpolicy="no-referrer">'
        self.assertEqual(csp_problems(GOOD_HEAD + ok), [])
        self.assertNotEqual(csp_problems(GOOD_HEAD + '<img src="https://www.phovir.com/a.webp" alt="a">'), [])
        self.assertNotEqual(csp_problems(GOOD_HEAD + '<script src="https://www.phovir.com/a.js"></script>'), [])
        self.assertNotEqual(csp_problems(GOOD_HEAD + '<img src="http://www.phovir.com/a.webp" alt="a" '
                                                     'referrerpolicy="no-referrer">'), [])

    def test_config_policy_matches_expected(self):
        cfg = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
        self.assertEqual(cfg["extra"]["csp"], EXPECTED_CSP)


class StrayFiles(unittest.TestCase):
    def test_stray_files_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            for name in ["ok.md", "secret.pem", ".env.local", "photo.heic", "Portfolio design.md",
                         "Portfolio WIP sign plan.md"]:
                (repo / name).write_text("x", encoding="utf-8")
            (repo / "big.bin").write_bytes(b"0" * (11 * 1024 * 1024))
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            hits = stray_files(repo)
            self.assertEqual(sorted(hits), sorted([".env.local", "Portfolio design.md", "Portfolio WIP sign plan.md",
                                                   "big.bin", "photo.heic", "secret.pem"]))


if __name__ == "__main__":
    unittest.main()
