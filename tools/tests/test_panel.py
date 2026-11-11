"""The panel layout for project pages, built from sample pages through the real templates."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_site import csp_problems, duplicate_ids  # noqa: E402
from sitebuild import built_site  # noqa: E402


def fixture(readouts: list[tuple[str, str]], extra: str = "", body: str = "") -> str:
    outs = "".join(f'[[extra.readouts]]\nlabel = "{k}"\nvalue = "{v}"\n' for k, v in readouts)
    return f'''+++
title = "A sample panel page"
description = "A page for the tests."
[extra]
start = "2026-03"
end = "now"
panel = true
skills = ["Python"]
my_part = "I built it."
result = "It worked."
{outs}[[extra.proof]]
kind = "code"
label = "Code on GitHub"
url = "https://github.com/Thenewmanator15"
{extra}+++
Body text.

{body}

<details class="fold"><summary><h2 id="more">More about it</h2></summary>

Folded text.

</details>
'''


MATRIX = '''[[extra.matrix]]
title = "Radio one"
sub = "the first radio"
cols = ["Board A", "Board B"]
rows = [["Capture", "yes", "no"], ["Survey", "-", "not yet tried"]]
notes = ["A note under the card."]
[[extra.tiles]]
value = "759"
label = "test functions"
[[extra.tiles]]
value = "8"
label = "golden vectors"
'''
PAGES = {
    "rf-wireless-embedded/fx-panel/index.md": fixture([("radios", "3"), ("timing", "0.5 µs")], MATRIX,
                                                     "{{ <matrices /> }}\n\n{{ <tiles /> }}"),
    "rf-wireless-embedded/fx-bare/index.md": fixture([("boards", "2")]),
    "instruments/fx-big/_index.md": fixture([("boards", "2")]),
    "instruments/fx-big/part-one.md": '+++\ntitle = "Part one"\ndescription = "A part."\nweight = 1\n'
                                      '[extra]\npanel = true\n+++\nText.\n',
    "instruments/fx-big/part-two.md": '+++\ntitle = "Part two"\ndescription = "Another part."\nweight = 2\n+++\nText.\n',
}


class Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._site = built_site(PAGES)
        cls.public = cls._site.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._site.__exit__(None, None, None)

    def page(self, path: str) -> str:
        return (self.public / path / "index.html").read_text(encoding="utf-8")

    def test_panel_header_shows_readouts(self):
        h = self.page("rf-wireless-embedded/fx-panel")
        self.assertIn('class="panelhead"', h)
        lcd = re.search(r'<dl class="lcd">(.*?)</dl>', h, re.S)
        self.assertIsNotNone(lcd)
        self.assertIn(">3<", lcd.group(1))
        self.assertIn(">0.5 µs<", lcd.group(1))
        self.assertNotIn('class="toc"', h)
        self.assertEqual(csp_problems(h), [])
        self.assertEqual(duplicate_ids(h), [])

    def test_matrix_cells_have_words(self):
        h = self.page("rf-wireless-embedded/fx-panel")
        self.assertRegex(h, r'<span class="dot-on"><span class="sr">yes</span></span>')
        self.assertRegex(h, r'<span class="dot-off"><span class="sr">no</span></span>')
        self.assertRegex(h, r'<span class="na">–<span class="sr">does not apply</span></span>')
        self.assertRegex(h, r"<td>not yet tried</td>")
        self.assertIn("A note under the card.", h)
        self.assertIn('class="mx"', h)
        self.assertIn('class="mxkey"', h)
        # matrices and tiles sit where the Markdown calls them, before the folds
        self.assertLess(h.index('class="mx"'), h.index('class="stiles"'))
        self.assertLess(h.index('class="stiles"'), h.index('<details class="fold">'))

    def test_tiles_and_cards(self):
        h = self.page("rf-wireless-embedded/fx-panel")
        self.assertRegex(h, r'<dl class="stiles">.*test functions.*759.*golden vectors.*8.*</dl>')
        self.assertIn('class="duo"', h)
        self.assertIn("I built it.", h)
        self.assertIn("It worked.", h)

    def test_folds_stay_in_the_html(self):
        h = self.page("rf-wireless-embedded/fx-panel")
        self.assertRegex(h, r'<details class="fold"><summary><h2 id="more">More about it</h2></summary>')
        self.assertIn("Folded text.", h)

    def test_panel_without_extras_has_no_empty_boxes(self):
        h = self.page("rf-wireless-embedded/fx-bare")
        self.assertIn('class="panelhead"', h)
        self.assertNotIn('class="mx"', h)
        self.assertNotIn('class="stiles"', h)
        self.assertNotIn('class="mxkey"', h)

    def test_part_page_gets_the_header_without_a_screen(self):
        h = self.page("instruments/fx-big/part-one")
        self.assertIn('class="panelhead"', h)
        self.assertNotIn('class="lcd"', h)
        self.assertNotIn('class="toc"', h)
        self.assertIn("Part of", h)
        self.assertIn('class="next"', h)

    def test_pages_without_panel_unchanged(self):
        for path in ("medical-imaging/volsa", "instruments/phovir"):
            h = self.page(path)
            self.assertIn('class="toc"', h, path)
            self.assertNotIn("panelhead", h, path)


if __name__ == "__main__":
    unittest.main()
