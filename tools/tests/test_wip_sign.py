"""The work-in-progress sign, built from sample pages through the real templates."""
import html
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_site import csp_problems  # noqa: E402
from sitebuild import built_site  # noqa: E402


def fixture(keys: str, proof: str = "") -> str:
    return f'''+++
title = "A sample page"
description = "A page for the tests."
[extra]
start = "2026-03"
end = "now"
skills = ["Python"]
{keys}
[[extra.readouts]]
label = "boards"
value = "2"
[[extra.proof]]
kind = "code"
label = "Code on GitHub"
url = "https://github.com/Thenewmanator15"
{proof}
+++
Body text.
'''


TO_COME = '[[extra.proof]]\nkind = "measurements"\nlabel = "Test logs"\nto_come = true\n'
PAGES = {
    "instruments/fx-photos/index.md": fixture('still_to_come = ["photos"]\nstill_to_come_note = "Boards soon."', TO_COME),
    "instruments/fx-order/index.md": fixture('still_to_come = ["proof", "photos"]'),
    "instruments/fx-all/index.md": fixture('still_to_come = ["write-up", "dates", "photos", "proof"]'),
    "instruments/fx-note/index.md": fixture('still_to_come = ["dates"]\nstill_to_come_note = "Tom\'s <b>logs</b> & photos"'),
    # a big project whose part is unfinished, while the project itself is not
    "instruments/fx-big/_index.md": fixture(""),
    "instruments/fx-big/part-one.md": '+++\ntitle = "Part one"\ndescription = "A part."\nweight = 1\n'
                                      '[extra]\nstill_to_come = ["photos"]\n+++\nText.\n',
}
ROW = re.compile(r'<text class="wip-row" data-part="([^"]+)"[^>]*>.*?<text class="wip-st (?:pass|wait)"[^>]*>(PASS|WAIT)</text>', re.S)


def rows(page_html: str) -> list[tuple[str, str]]:
    return ROW.findall(page_html)


def text_of(page_html: str, cls: str) -> str:
    """The text of the first <p class="cls">, tags removed, whitespace collapsed (entities kept)."""
    m = re.search(rf'<p class="{cls}">(.*?)</p>', page_html, re.S)
    return " ".join(re.sub(r"<[^>]+>", "", m.group(1)).split()) if m else ""


class Sign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._site = built_site(PAGES)
        cls.public = cls._site.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._site.__exit__(None, None, None)

    def page(self, path: str) -> str:
        return (self.public / path / "index.html").read_text(encoding="utf-8")

    def test_sign_on_marked_project(self):
        h = self.page("instruments/fx-photos")
        self.assertEqual(rows(h), [("write-up", "PASS"), ("dates", "PASS"), ("photos", "WAIT"), ("proof", "PASS")])
        self.assertRegex(h, r'<text class="wip-n"[^>]*>3 / 4</text>')
        self.assertIn("3 of 4 parts done. Still to come: photos. Boards soon.", text_of(h, "wip-note"))
        # the design's sentence, colon included (the colon is for screen readers, hidden on screen)
        self.assertTrue(text_of(h, "wip-note").startswith("Work in progress: 3 of 4 parts done."), text_of(h, "wip-note"))
        self.assertRegex(h, r'<div class="wip-scr" aria-hidden="true">')
        # option B mixed in: the checklist screen shows the trigger armed above a quiet baseline
        self.assertRegex(h, r'<text class="wip-armed"[^>]*>TRIG ▲ ARMED</text>')
        self.assertRegex(h, r'<path class="wip-trig"')
        self.assertRegex(h, r'<path class="wip-tr wip-base"')
        self.assertRegex(h, r'viewBox="0 0 320 120"')
        self.assertEqual(csp_problems(h), [])

    def test_rows_follow_the_fixed_order(self):
        h = self.page("instruments/fx-order")
        self.assertEqual([r for r, s in rows(h) if s == "WAIT"], ["photos", "proof"])
        self.assertIn("2 of 4 parts done. Still to come: photos and proof.", text_of(h, "wip-note"))

    def test_all_four_waiting(self):
        h = self.page("instruments/fx-all")
        self.assertRegex(h, r'<text class="wip-n"[^>]*>0 / 4</text>')
        self.assertIn("0 of 4 parts done. Still to come: write-up, dates, photos and proof.", text_of(h, "wip-note"))

    def test_note_is_escaped_once(self):
        h = self.page("instruments/fx-note")
        self.assertIn("Tom's <b>logs</b> & photos", html.unescape(text_of(h, "wip-note")))  # reads as typed
        self.assertNotIn("<b>logs", h)                                                     # never markup
        self.assertNotIn("&amp;amp;", h)                                                   # escaped once
        self.assertNotIn("&amp;#", h)

    def test_marked_project_is_labelled_where_it_is_listed(self):
        label = '<span class="lbl wip">in progress</span>'
        front = (self.public / "index.html").read_text(encoding="utf-8")
        start = front.index('id="scope-data">') + len('id="scope-data">')
        blob = json.loads(front[start:front.index("</script>", start)])
        item = next(i for i in blob["items"] if i["id"] == "fx-photos")
        self.assertIs(item["wip"], True)
        # proof still to come is not proof yet: out of the blob and out of the row's proof kinds
        self.assertNotIn("Test logs", [q["label"] for q in item["proof"]])
        for page in (self.public / "index.html", self.public / "instruments" / "index.html"):
            row = re.search(r'<li class="row"[^>]*>(?:(?!</li>).)*/instruments/fx-photos/(?:(?!</li>).)*</li>',
                            page.read_text(encoding="utf-8"), re.S).group(0)
            self.assertIn(label, row, page)
            if page.parent == self.public:  # only the front page's rows list proof kinds
                self.assertEqual(re.search(r'<span class="kinds">([^<]*)</span>', row).group(1), "code")
        tile = re.search(r'<a class="tile" href="[^"]*/instruments/fx-photos/".*?</a>', front, re.S).group(0)
        self.assertIn(label, tile)

    def test_unmarked_page_has_no_sign(self):
        h = self.page("medical-imaging/volsa")
        self.assertNotIn('class="wip', h)

    def test_marked_part_leaves_parent_unlabelled(self):
        label = '<span class="lbl wip">in progress</span>'
        parent = self.page("instruments/fx-big")
        self.assertRegex(parent[parent.index('<ol class="parts">'):],
                         r'href="/instruments/fx-big/part-one/">Part one</a>\s*' + re.escape(label))
        self.assertNotIn('class="wip-sign"', parent)
        self.assertIn('class="wip-sign"', self.page("instruments/fx-big/part-one"))
        front = (self.public / "index.html").read_text(encoding="utf-8")
        rows = [r for r in re.findall(r'<li class="row"[^>]*>.*?</li>', front, re.S) if "/instruments/fx-big/" in r]
        self.assertEqual(len(rows), 1)
        self.assertNotIn(label, rows[0])
        start = front.index('id="scope-data">') + len('id="scope-data">')
        blob = json.loads(front[start:front.index("</script>", start)])
        self.assertIs(next(i for i in blob["items"] if i["id"] == "fx-big")["wip"], False)

    def test_to_come_proof_shows_on_the_way(self):
        self.assertIn('Test logs <span class="req">on the way</span>', self.page("instruments/fx-photos"))


if __name__ == "__main__":
    unittest.main()
